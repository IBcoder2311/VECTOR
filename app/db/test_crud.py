import asyncio
import uuid

from app.db.database import SessionFactory
from app.db.crud import (
    create_user,
    create_idea,
    get_idea_by_id,
    delete_idea,
)


async def test_create_and_delete_idea():
    async with SessionFactory() as session:
        user = await create_user(
            session=session,
            max_id=f"test_{uuid.uuid4().hex[:12]}",
            name="Тестовый пользователь",
        )

        print(f"Пользователь создан: {user.id}")

        idea = await create_idea(
            session=session,
            owner=user.id,
            name="Тестовая идея",
            short_description="Проверка CRUD",
            long_description="Временная идея для тестирования.",
            required_roles=["Python-разработчик"],
            deadline=None,
            region="Тестовый регион",
        )

        idea_id = idea.id
        print(f"Идея создана: {idea_id}")

        # Проверяем, что идея существует
        found_idea = await get_idea_by_id(session, idea_id)
        assert found_idea is not None
        assert found_idea.name == "Тестовая идея"

        # Удаляем идею
        deleted = await delete_idea(session, idea_id)
        assert deleted is True

        # Проверяем удаление
        found_idea = await get_idea_by_id(session, idea_id)
        assert found_idea is None

        print("ТЕСТ ПРОЙДЕН!")


if __name__ == "__main__":
    asyncio.run(test_create_and_delete_idea())