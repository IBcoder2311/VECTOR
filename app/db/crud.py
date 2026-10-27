from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Users, Ideas, Responses, Events

"""
Базовые команды:
1. Пользователи — Users

Функция	               Что делает

create_user	           Создаёт пользователя при первом входе через MAX
get_user_by_id	       Находит пользователя по внутреннему ID
get_user_by_max_id	   Находит пользователя по ID в MAX
update_user	           Обновляет имя, описание, аватар, навыки, ссылки
delete_user	           На всякий случай

2. Идеи — Ideas

Функция	               Что делает

create_idea	           Создаёт идею от имени пользователя
get_idea_by_id         Получает одну идею
get_ideas	           Получает список идей для каталога
get_ideas_by_owner	   Получает идеи конкретного пользователя
update_idea	           Изменяет описание, роли, дедлайн и другие поля
delete_idea	           Удаляет идею
increment_idea_views   Увеличивает счётчик просмотров

3. Отклики — Responses

Функция	               Что делает

create_response	       Создаёт отклик на идею
get_response_by_id	   Получает конкретный отклик
get_responses_by_idea  Показывает отклики на идею её владельцу
get_responses_by_user  Показывает отклики пользователя
delete_response	       Удаляет отклик

4. Мероприятия — Events

Функция	               Что делает

create_event	       Создаёт мероприятие
get_event_by_id	       Получает одно мероприятие
get_events	           Получает список мероприятий
get_events_by_owner	   Получает мероприятия организации
update_event	       Изменяет мероприятие
delete_event	       Удаляет мероприятие

"""


# USERS
async def create_user(
    session: AsyncSession,
    max_id: str,
    name: str,
    img="frontend/static/img/avatar.jpg",
    status="user",
):
    item = Users(
        max_id=max_id,
        name=name,
        img=img,
        status=status,
        skills=[],
        urls=[],
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item

async def get_user_by_id(session: AsyncSession, user_id: int):
    result = await session.execute(
        select(Users).where(Users.id==user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_max_id(session: AsyncSession, max_id: str):
    result = await session.execute(
        select(Users).where(Users.max_id==max_id)
    )
    return result.scalar_one_or_none()

async def update_user(session: AsyncSession, user_id: int, **updates):
    user = await session.get(Users, user_id)

    allowed_fields = {"name", "description", "img", "skills", "urls"}

    if user is None:
        return None

    if not updates:
        return user
    
    for field in updates:
        if field not in allowed_fields:
            raise ValueError(f"Нельзя обновлять поле: {field}")

    for field, value in updates.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    return user


async def update_user_status(
    session: AsyncSession,
    user_id: int,
    new_status: str,
):
    allowed_statuses = {"user", "admin", "organization"}

    if new_status not in allowed_statuses:
        raise ValueError(f"Недопустимый статус: {new_status}")

    user = await session.get(Users, user_id)

    if user is None:
        return None

    user.status = new_status

    await session.commit()
    await session.refresh(user)

    return user


# IDEAS

async def create_idea(
    session: AsyncSession,
    owner: int,
    name: str,
    short_description: str,
    long_description: str,
    required_roles: list[str],
    deadline: str | None = None,
    region: str | None = None
):
    item = Ideas(
        owner=owner,
        name=name,
        short_description=short_description,
        long_description=long_description,
        required_roles=required_roles,
        roles=[],
        deadline=deadline,
        region=region
    )

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item

async def get_idea_by_id(session: AsyncSession, idea_id: int):
    result = await session.execute(
        select(Ideas).where(Ideas.id==idea_id)
    )
    return result.scalar_one_or_none()

async def get_ideas_by_owner(session: AsyncSession, owner_id: int):
    result = await session.execute(
        select(Ideas).where(Ideas.owner==owner_id)
    )
    return result.scalars().all()

async def update_idea(session: AsyncSession, idea_id: int, **updates):
    idea = await session.get(Ideas, idea_id)
    
    allowed_fields = {"name", "short_description", "long_description", "required_roles", "deadline", "region"}

    if idea is None:
        return None
    
    if not updates:
        return idea
    
    for field in updates:
        if field not in allowed_fields:
            raise ValueError(f"Нельзя обновлять поле: {field}")

    for field, value in updates.items():
        setattr(idea, field, value)

    await session.commit()
    await session.refresh(idea)

    return idea

async def delete_idea(session: AsyncSession, idea_id: int):
    idea = await session.get(Ideas, idea_id)

    if idea is None:
        return False

    await session.delete(idea)
    await session.commit()

    return True


# RESPONSES


# EVENTS