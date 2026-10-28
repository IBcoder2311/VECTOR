"""Seven integration-test circles for VECTOR's PostgreSQL CRUD.

Copy this file into the project root and run only against a dedicated
PostgreSQL test database named `vector_test`:
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://USER:PASSWORD@localhost:5432/vector_test"
    uv run python test_seven_circles.py

The script does not drop tables or existing data. It creates missing tables and
cleans up rows marked with its unique test prefix when it exits.
"""

from __future__ import annotations

import asyncio
import math
import os
from uuid import uuid4

from sqlalchemy import delete, or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import crud
from app.db.database import Base
from app.db.models import Events, Ideas, Responses, Users


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")
RUN_PREFIX = f"sevenCircles{uuid4().hex}X"
INVALID_FK_IDS: set[int] = set()


def validate_test_url(url_text: str) -> None:
    if not url_text:
        raise RuntimeError(
            "Не задан TEST_DATABASE_URL. Укажи отдельную тестовую БД, например vector_test."
        )

    url = make_url(url_text)
    if not url.database or not url.database.endswith("_test"):
        raise RuntimeError(
            f"Отказ запуска: база должна оканчиваться на '_test', сейчас: {url.database!r}."
        )
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("Эти интеграционные испытания рассчитаны на PostgreSQL.")


async def make_user(
    session: AsyncSession,
    label: str,
    status: str = "user",
) -> Users:
    return await crud.create_user(
        session=session,
        max_id=f"{RUN_PREFIX}-{label}",
        name=f"{RUN_PREFIX}-{label}",
        status=status,
    )


async def make_idea(
    session: AsyncSession,
    owner_id: int,
    label: str,
) -> Ideas:
    return await crud.create_idea(
        session=session,
        owner=owner_id,
        name=f"{RUN_PREFIX}-{label}",
        short_description="Короткое тестовое описание",
        long_description="Длинное тестовое описание",
        required_roles=["Python", "Frontend"],
        region="Тестовый регион",
    )


async def make_event(
    session: AsyncSession,
    owner_id: int,
    label: str,
) -> Events:
    return await crud.create_event(
        session=session,
        owner_id=owner_id,
        img="test-event.png",
        name=f"{RUN_PREFIX}-{label}",
        short_description="Короткое описание мероприятия",
        long_description="Полное описание мероприятия",
        region="Тестовый регион",
        urls=[{"title": "Сайт", "url": "https://example.com"}],
    )


async def expect_integrity_error(
    session: AsyncSession,
    operation,
    description: str,
) -> None:
    try:
        await operation
    except IntegrityError:
        await session.rollback()
        return
    else:
        await session.rollback()
        raise AssertionError(f"БД не отклонила нарушение целостности: {description}")


# КРУГ 1. Обычный CRUD для пользователей, идей, откликов и мероприятий.
async def circle_1_happy_path(session: AsyncSession) -> None:
    user = await make_user(session, "circle1-owner", status="organization")
    applicant = await make_user(session, "circle1-applicant")

    assert (await crud.get_user_by_id(session, user.id)).id == user.id
    assert (await crud.get_user_by_max_id(session, user.max_id)).id == user.id

    updated_user = await crud.update_user(
        session,
        user.id,
        name="VECTOR test organization",
        description="Обновлённое описание",
        skills=["Python"],
        urls=[{"title": "GitHub", "url": "https://example.com/repo"}],
    )
    assert updated_user is not None
    assert updated_user.name == "VECTOR test organization"
    assert updated_user.description == "Обновлённое описание"
    assert updated_user.skills == ["Python"]

    idea = await make_idea(session, user.id, "circle1-idea")
    assert (await crud.get_idea_by_id(session, idea.id)).id == idea.id
    assert idea.id in [item.id for item in await crud.get_ideas_by_owner(session, user.id)]

    updated_idea = await crud.update_idea(
        session,
        idea.id,
        name="Обновлённая идея",
        required_roles=["Backend"],
    )
    assert updated_idea is not None
    assert updated_idea.name == "Обновлённая идея"
    assert updated_idea.required_roles == ["Backend"]

    response = await crud.create_response(
        session, id_idea=idea.id, id_user=applicant.id, description="Хочу участвовать"
    )
    assert (await crud.get_response_by_id(session, response.id)).id == response.id
    assert response.id in [r.id for r in await crud.get_responses_by_idea(session, idea.id)]
    assert response.id in [r.id for r in await crud.get_responses_by_user(session, applicant.id)]
    assert await crud.delete_response(session, response.id) is True
    assert await crud.get_response_by_id(session, response.id) is None
    assert await crud.delete_response(session, response.id) is False

    event = await make_event(session, user.id, "circle1-event")
    assert (await crud.get_event_by_id(session, event.id)).id == event.id
    assert event.id in [e.id for e in await crud.get_events_by_owner(session, user.id)]
    updated_event = await crud.update_event(session, event.id, name="Обновлённое мероприятие")
    assert updated_event is not None
    assert updated_event.name == "Обновлённое мероприятие"
    assert await crud.delete_event(session, event.id) is True
    assert await crud.get_event_by_id(session, event.id) is None
    assert await crud.delete_event(session, event.id) is False

    assert await crud.delete_idea(session, idea.id) is True
    assert await crud.get_idea_by_id(session, idea.id) is None
    assert await crud.delete_idea(session, idea.id) is False


# КРУГ 2. Пагинация и случайная подборка.
async def circle_2_pagination_and_random(session: AsyncSession) -> None:
    owner = await make_user(session, "circle2-owner", status="organization")

    baseline_idea_ids = set((await session.execute(select(Ideas.id))).scalars().all())
    created_ideas = [await make_idea(session, owner.id, f"circle2-idea-{i}") for i in range(5)]
    all_expected_idea_ids = baseline_idea_ids | {idea.id for idea in created_ideas}

    page_size = 3
    page_count = math.ceil(len(all_expected_idea_ids) / page_size)
    paged_ids: list[int] = []
    for page_number in range(1, page_count + 1):
        page = await crud.get_ideas(session, page=page_number, per_page=page_size)
        assert len(page) <= page_size
        paged_ids.extend(idea.id for idea in page)

    # Stable ordering means offset pagination doesn't skip or repeat records
    # merely because each page query returned rows in an unspecified order.
    assert paged_ids == sorted(all_expected_idea_ids, reverse=True), (
        "get_ideas должна сортировать по Ideas.id.desc() перед offset/limit"
    )

    random_items = await crud.get_random_ideas(session, limit=3)
    assert len(random_items) == min(3, len(all_expected_idea_ids))
    assert len({idea.id for idea in random_items}) == len(random_items)
    assert {idea.id for idea in random_items}.issubset(all_expected_idea_ids)

    baseline_event_ids = set((await session.execute(select(Events.id))).scalars().all())
    created_events = [await make_event(session, owner.id, f"circle2-event-{i}") for i in range(5)]
    all_expected_event_ids = baseline_event_ids | {event.id for event in created_events}

    event_page_size = 2
    event_offsets = range(0, len(all_expected_event_ids), event_page_size)
    paged_event_ids: list[int] = []
    for offset in event_offsets:
        events = await crud.get_events(session, limit=event_page_size, offset=offset)
        assert len(events) <= event_page_size
        paged_event_ids.extend(event.id for event in events)

    assert paged_event_ids == sorted(all_expected_event_ids, reverse=True), (
        "get_events должна сохранять сортировку по Events.id.desc()"
    )


# КРУГ 3. Отсутствующие записи и защита от обновления неизвестных полей.
async def circle_3_missing_rows_and_allowlists(session: AsyncSession) -> None:
    missing_id = -987654321
    assert await crud.get_user_by_id(session, missing_id) is None
    assert await crud.get_user_by_max_id(session, f"{RUN_PREFIX}-missing") is None
    assert await crud.get_idea_by_id(session, missing_id) is None
    assert await crud.get_response_by_id(session, missing_id) is None
    assert await crud.get_event_by_id(session, missing_id) is None
    assert await crud.update_user(session, missing_id, name="x") is None
    assert await crud.update_idea(session, missing_id, name="x") is None
    assert await crud.update_event(session, missing_id, name="x") is None
    assert await crud.delete_idea(session, missing_id) is False
    assert await crud.delete_response(session, missing_id) is False
    assert await crud.delete_event(session, missing_id) is False

    user = await make_user(session, "circle3-user")
    idea = await make_idea(session, user.id, "circle3-idea")
    org = await make_user(session, "circle3-org", status="organization")
    event = await make_event(session, org.id, "circle3-event")

    try:
        await crud.update_user(session, user.id, status="admin")
    except ValueError:
        pass
    else:
        raise AssertionError("update_user разрешил менять status в обход отдельной функции")

    try:
        await crud.update_idea(session, idea.id, owner=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("update_idea разрешил менять owner")

    try:
        await crud.update_event(session, event.id, owner=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("update_event разрешил менять owner")

    try:
        await crud.update_user_status(session, user.id, "superadmin")
    except ValueError:
        pass
    else:
        raise AssertionError("update_user_status принял неизвестный статус")

    assert (await crud.get_user_by_id(session, user.id)).name == user.name
    assert (await crud.get_idea_by_id(session, idea.id)).owner == user.id
    assert (await crud.get_event_by_id(session, event.id)).owner == org.id


# КРУГ 4. Внешние ключи не позволяют создавать записи-сироты.
async def circle_4_foreign_keys(session: AsyncSession) -> None:
    fake_owner_id = -int(uuid4().int % 2_000_000_000) - 1
    fake_user_id = fake_owner_id - 1
    fake_idea_id = fake_owner_id - 2
    INVALID_FK_IDS.update({fake_owner_id, fake_user_id, fake_idea_id})

    await expect_integrity_error(
        session,
        crud.create_idea(
            session,
            owner=fake_owner_id,
            name=f"{RUN_PREFIX}-orphan-idea",
            short_description="test",
            long_description="test",
            required_roles=[],
        ),
        "Ideas.owner ссылается на несуществующего пользователя",
    )
    await expect_integrity_error(
        session,
        crud.create_response(
            session,
            id_idea=fake_idea_id,
            id_user=fake_user_id,
            description="test",
        ),
        "Responses содержит несуществующие id_idea/id_user",
    )
    await expect_integrity_error(
        session,
        crud.create_event(
            session,
            owner_id=fake_owner_id,
            img="test.png",
            name=f"{RUN_PREFIX}-orphan-event",
            short_description="test",
            long_description="test",
            region=None,
            urls=[],
        ),
        "Events.owner ссылается на несуществующего пользователя",
    )


# КРУГ 5. Уникальность отклика и восстановление сессии после IntegrityError.
async def circle_5_unique_constraints_and_rollback(
    session: AsyncSession,
) -> None:
    user = await make_user(session, "circle5-user")
    idea = await make_idea(session, user.id, "circle5-idea")

    # Создаём первый отклик
    first = await crud.create_response(
        session,
        id_idea=idea.id,
        id_user=user.id,
        description="Первый отклик",
    )

    # Сохраняем значения до rollback:
    # после него ORM-объекты могут потребовать повторной загрузки.
    idea_id = idea.id
    user_id = user.id
    user_max_id = user.max_id
    first_response_id = first.id

    # Повторный отклик должен нарушить UNIQUE(id_idea, id_user)
    await expect_integrity_error(
        session,
        crud.create_response(
            session,
            id_idea=idea_id,
            id_user=user_id,
            description="Дубликат",
        ),
        "два отклика одной пары (id_idea, id_user)",
    )

    # Проверяем, что первый отклик остался в БД
    responses = await crud.get_responses_by_idea(session, idea_id)
    assert len(responses) == 1
    assert responses[0].id == first_response_id

    # Повторный max_id должен нарушить UNIQUE
    await expect_integrity_error(
        session,
        crud.create_user(
            session,
            max_id=user_max_id,
            name="Повторный MAX ID",
        ),
        "повторный Users.max_id",
    )

    # Проверяем, что исходный пользователь существует
    existing_user = await crud.get_user_by_max_id(session, user_max_id)
    assert existing_user is not None
    assert existing_user.id == user_id


# КРУГ 6. Удаление идеи каскадно удаляет её отклики, но сохраняет пользователей.
async def circle_6_delete_idea_cascade(session: AsyncSession) -> None:
    owner = await make_user(session, "circle6-owner")
    applicant = await make_user(session, "circle6-applicant")
    idea = await make_idea(session, owner.id, "circle6-idea")
    response = await crud.create_response(
        session, id_idea=idea.id, id_user=applicant.id, description="Отклик для каскада"
    )

    assert await crud.delete_idea(session, idea.id) is True
    assert await crud.get_response_by_id(session, response.id) is None
    assert await crud.get_user_by_id(session, owner.id) is not None
    assert await crud.get_user_by_id(session, applicant.id) is not None


# КРУГ 7. Удаление пользователя проверяет цепочку Users -> Ideas/Events -> Responses.
async def circle_7_delete_user_cascade(session: AsyncSession) -> None:
    owner = await make_user(session, "circle7-owner", status="organization")
    applicant = await make_user(session, "circle7-applicant")
    other_owner = await make_user(session, "circle7-other-owner")

    owned_idea = await make_idea(session, owner.id, "circle7-owned-idea")
    other_idea = await make_idea(session, other_owner.id, "circle7-other-idea")
    owned_event = await make_event(session, owner.id, "circle7-owned-event")
    response_to_owned_idea = await crud.create_response(
        session, id_idea=owned_idea.id, id_user=applicant.id, description="Отклик 1"
    )
    response_to_other_idea = await crud.create_response(
        session, id_idea=other_idea.id, id_user=applicant.id, description="Отклик 2"
    )

    # Удаляем владельца напрямую, потому что delete_user в CRUD пока нет.
    owner_row = await session.get(Users, owner.id)
    assert owner_row is not None
    await session.delete(owner_row)
    await session.commit()

    assert await crud.get_user_by_id(session, owner.id) is None
    assert await crud.get_idea_by_id(session, owned_idea.id) is None
    assert await crud.get_event_by_id(session, owned_event.id) is None
    assert await crud.get_response_by_id(session, response_to_owned_idea.id) is None
    assert await crud.get_response_by_id(session, response_to_other_idea.id) is not None
    assert await crud.get_user_by_id(session, applicant.id) is not None
    assert await crud.get_idea_by_id(session, other_idea.id) is not None

    # Удаление автора откликов не удаляет сами идеи и их владельцев.
    applicant_row = await session.get(Users, applicant.id)
    assert applicant_row is not None
    await session.delete(applicant_row)
    await session.commit()

    assert await crud.get_response_by_id(session, response_to_other_idea.id) is None
    assert await crud.get_idea_by_id(session, other_idea.id) is not None
    assert await crud.get_user_by_id(session, other_owner.id) is not None


async def cleanup_test_rows(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Delete only records belonging to this run, including rows from failed tests."""
    test_user_ids = select(Users.id).where(Users.max_id.startswith(RUN_PREFIX))
    test_idea_ids = select(Ideas.id).where(Ideas.name.startswith(RUN_PREFIX))

    async with session_factory() as session:
        response_condition = or_(
            Responses.id_idea.in_(test_idea_ids),
            Responses.id_user.in_(test_user_ids),
            Responses.id_idea.in_(INVALID_FK_IDS) if INVALID_FK_IDS else False,
            Responses.id_user.in_(INVALID_FK_IDS) if INVALID_FK_IDS else False,
        )
        await session.execute(delete(Responses).where(response_condition))
        await session.execute(
            delete(Events).where(
                or_(
                    Events.name.startswith(RUN_PREFIX),
                    Events.owner.in_(INVALID_FK_IDS) if INVALID_FK_IDS else False,
                )
            )
        )
        await session.execute(
            delete(Ideas).where(
                or_(
                    Ideas.name.startswith(RUN_PREFIX),
                    Ideas.owner.in_(INVALID_FK_IDS) if INVALID_FK_IDS else False,
                )
            )
        )
        await session.execute(delete(Users).where(Users.max_id.startswith(RUN_PREFIX)))
        await session.commit()


async def main() -> int:
    validate_test_url(TEST_DATABASE_URL)
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    circles = [
        ("Круг 1/7 — основной CRUD", circle_1_happy_path),
        ("Круг 2/7 — пагинация и random", circle_2_pagination_and_random),
        ("Круг 3/7 — отсутствующие записи и allowlist", circle_3_missing_rows_and_allowlists),
        ("Круг 4/7 — внешние ключи", circle_4_foreign_keys),
        ("Круг 5/7 — уникальность и rollback", circle_5_unique_constraints_and_rollback),
        ("Круг 6/7 — удаление идеи и каскад", circle_6_delete_idea_cascade),
        ("Круг 7/7 — каскадное удаление пользователя", circle_7_delete_user_cascade),
    ]
    failures: list[tuple[str, Exception]] = []

    try:
        # create_all создаёт отсутствующие таблицы, но не меняет существующие ограничения.
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        print(f"Тестовая БД: {make_url(TEST_DATABASE_URL).database}")
        print(f"Маркер тестовых данных: {RUN_PREFIX}")
        for title, test in circles:
            try:
                async with session_factory() as session:
                    await test(session)
                print(f"✅ {title}")
            except Exception as exc:  # продолжить остальные круги и показать все проблемы
                failures.append((title, exc))
                print(f"❌ {title}: {type(exc).__name__}: {exc}")

        if failures:
            print("\nИТОГ: крепость пока не прошла испытания.")
            for title, exc in failures:
                print(f" - {title}: {type(exc).__name__}: {exc}")
            return 1

        print("\n🏰 ВСЕ СЕМЬ КРУГОВ ПРОЙДЕНЫ.")
        return 0
    finally:
        try:
            await cleanup_test_rows(session_factory)
        finally:
            await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
