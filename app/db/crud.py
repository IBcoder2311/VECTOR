from sqlalchemy import select
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
    
    for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Нельзя обновлять поле: {field}")
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    return user

# IDEAS


# RESPONSES


# EVENTS