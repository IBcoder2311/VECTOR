from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Users, Ideas, Responses, Events

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
    reference_links: list[str],
    deadline: str | None = None,
    region: str | None = None
):
    item = Ideas(
        owner=owner,
        name=name,
        short_description=short_description,
        long_description=long_description,
        required_roles=required_roles,
        reference_links=reference_links,
        roles=[],
        deadline=deadline,
        region=region
    )

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item

async def get_ideas(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 20
):
    if page < 1 or not 1 <= per_page <= 100:
        raise ValueError("Некорректные параметры пагинации")

    offset = (page - 1) * per_page

    result = await session.execute(
        select(Ideas)
        .order_by(Ideas.id.desc())
        .offset(offset)
        .limit(per_page)
    )

    return result.scalars().all()

async def get_random_ideas(
    session: AsyncSession,
    limit: int = 40
):
    result = await session.execute(
        select(Ideas)
        .order_by(func.random())
        .limit(limit)
    )
    return result.scalars().all()

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

async def create_response(
    session: AsyncSession,
    id_idea: int,
    id_user: int,
    description="",
    role: str=""
):
    item = Responses(
        id_idea=id_idea,
        id_user=id_user,
        description=description,
        role=role,
    )
    
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item

async def get_response_by_id(
    session: AsyncSession,
    id: int
):
    result = await session.execute(
        select(Responses).where(Responses.id==id)
    )
    return result.scalar_one_or_none()

async def get_responses_by_idea(
    session: AsyncSession,
    id_idea: int
):
    result = await session.execute(
        select(Responses).where(Responses.id_idea==id_idea)
    )
    return result.scalars().all()

async def get_responses_by_user(
    session: AsyncSession,
    id_user: int
):
    result = await session.execute(
        select(Responses).where(Responses.id_user==id_user)
    )
    return result.scalars().all()

async def get_responses_count(session: AsyncSession, idea_id: int):
    result = await session.execute(
        select(func.count())
        .select_from(Responses)
        .where(Responses.id_idea == idea_id)
    )
    return result.scalar_one()

async def delete_response(
    session: AsyncSession,
    response_id: int
):
    response = await session.get(Responses, response_id)
    
    if response is None:
        return False

    await session.delete(response)
    await session.commit()

    return True

async def accept_response(
    session: AsyncSession,
    response_id: int,
):
    response = await session.get(Responses, response_id)

    if response is None:
        return False

    idea = await session.get(Ideas, response.id_idea)

    if idea is None:
        return False

    roles = list(idea.roles or [])

    if any(member["user_id"] == response.id_user for member in roles):
        return False

    roles.append({
        "user_id": response.id_user,
        "role": response.role,
    })

    idea.roles = roles

    await session.delete(response)
    await session.commit()

    return True


async def reject_response(
    session: AsyncSession,
    response_id: int,
):
    return await delete_response(session, response_id)

# EVENTS

async def create_event(
    session: AsyncSession,
    owner_id: int,
    img: str,
    name: str,
    short_description: str,
    long_description: str,
    region: str | None,
    urls: list[dict]
):
    item = Events(
        owner=owner_id,
        img=img,
        name=name,
        short_description=short_description,
        long_description=long_description,
        region=region,
        urls=urls
    )

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item

async def get_event_by_id(
    session: AsyncSession,
    event_id: int
):
    result = await session.execute(
        select(Events).where(Events.id == event_id)
    )
    return result.scalar_one_or_none()

async def get_events(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0
):
    result = await session.execute(
        select(Events)
        .order_by(Events.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()

async def get_events_by_owner(
    session: AsyncSession,
    owner_id: int
):
    result = await session.execute(
        select(Events).where(Events.owner == owner_id)
    )
    return result.scalars().all()


async def update_event(
    session: AsyncSession,
    event_id: int,
    **updates
):
    event = await session.get(Events, event_id)

    allowed_fields = {
        "img",
        "name",
        "short_description",
        "long_description",
        "region",
        "urls",
    }

    if event is None:
        return None

    if not updates:
        return event

    for field in updates:
        if field not in allowed_fields:
            raise ValueError(f"Нельзя обновлять поле: {field}")

    for field, value in updates.items():
        setattr(event, field, value)

    await session.commit()
    await session.refresh(event)

    return event


async def delete_event(
    session: AsyncSession,
    event_id: int
):
    event = await session.get(Events, event_id)

    if event is None:
        return False

    await session.delete(event)
    await session.commit()

    return True