
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse

from core.templates import templates
from core.config import Config
from urllib.parse import urlparse

from app.db.database import SessionFactory
from app.db.crud import (
    get_ideas_by_owner,
    get_idea_by_id,
    get_user_by_id,
    get_responses_by_idea,
    create_idea,
    create_response,
    delete_idea,
    delete_response,
    add_team_member,
    get_response_by_id,
    get_response_by_user_and_idea,
    create_notification,
)
from app.moderation.moderation import check_text
from app.constants import IDEA_CATEGORIES


router = APIRouter()

async def moderate_or_reject(session, user_id: int, *texts: str):
    for text in texts:
        result = check_text(text or "")

        if result["flagged"]:
            await create_notification(
                session=session,
                user_id=user_id,
                message=(
                    "🚫 Твоя публикация отклонена!\n\n"
                    "Обнаружена запрещённая лексика. "
                    "Исправь текст и попробуй отправить снова."
                ),
            )

            raise HTTPException(
                status_code=400,
                detail="Публикация отклонена модерацией.",
            )
        
def has_idea_access(user, idea) -> bool:
    if user is None or idea is None:
        return False

    admin_ids = Config().get_admin_max_ids()

    is_owner = user.id == idea.owner
    is_admin = int(user.max_id) in admin_ids

    return is_owner or is_admin

def validate_max_chat_link(link: str) -> str:
    link = link.strip()

    if not link:
        raise HTTPException(
            status_code=400,
            detail="Ссылка на MAX-чат обязательна",
        )

    parsed = urlparse(link)

    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or "." not in parsed.netloc
    ):
        raise HTTPException(
            status_code=400,
            detail="Некорректная ссылка на MAX-чат",
        )

    return link


@router.get("/ideas")
async def ideas(request: Request):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user_ideas = await get_ideas_by_owner(
            session,
            user_id,
        )

    return templates.TemplateResponse(
        request=request,
        name="ideas.html",
        context={
            "title": "ВЕКТОР — Мои идеи",
            "active_page": "ideas",
            "ideas": user_ideas,
        },
    )


@router.get("/ideas/create")
async def create_idea_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="create_idea.html",
        context={
            "title": "ВЕКТОР — Создание идеи",
            "active_page": "ideas",
            "categories": IDEA_CATEGORIES,
        },
    )


@router.post("/ideas/create")
async def create_idea_route(
    request: Request,
    title: str = Form(...),
    short_description: str = Form(...),
    description: str = Form(...),
    roles: list[str] = Form(default=[]),
    deadline: str | None = Form(default=None),
    category: str = Form(...),
    region: str | None = Form(default=None),
    reference_links: list[str] = Form(default=[]),
    max_chat_link: str = Form(default=""),
):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        if category not in IDEA_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="Некорректная категория",
            )

        await moderate_or_reject(
            session, user_id,
            title,
            short_description,
            description,
            region or "",
            *roles,
            *reference_links,
            max_chat_link,
        )

        max_chat_link = validate_max_chat_link(max_chat_link)
        
        await create_idea(
            session=session,
            owner=user_id,
            name=title,
            short_description=short_description,
            long_description=description,
            required_roles=roles,
            reference_links=reference_links,
            deadline=deadline or None,
            region=region or None,
            max_chat_link=max_chat_link.strip(),
            category=category,
        )

    return RedirectResponse(
        url="/ideas",
        status_code=303,
    )


@router.get("/ideas/{idea_id}")
async def idea_detail(request: Request, idea_id: int):
    user_id = request.session.get("user_id")

    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            return templates.TemplateResponse(
                request=request,
                name="404.html",
                context={"title": "Идея не найдена"},
                status_code=404,
            )

        user = (
            await get_user_by_id(session, user_id)
            if user_id else None
        )

        author = await get_user_by_id(session, idea.owner)
        responses = await get_responses_by_idea(session, idea_id)

        user_response = None
        is_team_member = False

        if user_id is not None:
            user_response = await get_response_by_user_and_idea(
                session,
                user_id,
                idea_id,
            )

            is_team_member = any(
                member.get("user_id") == user_id
                for member in (idea.roles or [])
            )

        if has_idea_access(user, idea):
            return RedirectResponse(
                url=f"/ideas/{idea_id}/manage",
                status_code=303,
            )

    return templates.TemplateResponse(
        request=request,
        name="idea_detail.html",
        context={
            "title": f"ВЕКТОР — {idea.name}",
            "active_page": "home",
            "idea": idea,
            "author": author,
            "responses": responses,
            "responses_count": len(responses),
            "user_response": user_response,
            "is_team_member": is_team_member,
        },
    )


@router.post("/ideas/{idea_id}/delete")
async def delete_idea_route(request: Request, idea_id: int):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        await delete_idea(session, idea_id)

    return RedirectResponse(
        url="/ideas",
        status_code=303,
    )


@router.post("/ideas/{idea_id}/respond")
async def respond_to_idea(
    request: Request,
    idea_id: int,
    message: str = Form(...),
    role: str = Form(...),
):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None or has_idea_access(user, idea):
            return RedirectResponse(
                url=f"/ideas/{idea_id}",
                status_code=303,
            )

        existing = await get_response_by_user_and_idea(
            session,
            user_id,
            idea_id,
        )

        if existing is not None:
            return RedirectResponse(
                url=f"/ideas/{idea_id}",
                status_code=303,
            )

        await moderate_or_reject(
            session, user_id,
            message, role,
        )

        try:
            await create_response(
                session=session,
                id_idea=idea_id,
                id_user=user_id,
                description=message,
                role=role,
            )

            await create_notification(
                session=session,
                user_id=idea.owner,
                message=(
                    f"📩 Новый отклик на твою идею «{idea.name}»!\n\n"
                    f"Роль: {role}\n"
                    "Открой VECTOR, чтобы посмотреть отклик."
                ),
            )

        except Exception:
            await session.rollback()
            raise

    return RedirectResponse(
        url=f"/ideas/{idea_id}",
        status_code=303,
    )


@router.get("/ideas/{idea_id}/edit")
async def edit_idea_page(request: Request, idea_id: int):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        return templates.TemplateResponse(
            request=request,
            name="edit_idea.html",
            context={
                "title": f"ВЕКТОР — Редактирование: {idea.name}",
                "active_page": "ideas",
                "idea": idea,
                "categories": IDEA_CATEGORIES,
            },
        )


@router.post("/ideas/{idea_id}/edit")
async def edit_idea_route(
    request: Request,
    idea_id: int,
    title: str = Form(...),
    short_description: str = Form(...),
    description: str = Form(...),
    roles: list[str] = Form(default=[]),
    reference_links: list[str] = Form(default=[]),
    deadline: str | None = Form(default=None),
    category: str = Form(...),
    region: str | None = Form(default=None),
    max_chat_link: str = Form(default=""),
):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        if category not in IDEA_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail="Некорректная категория",
            )

        await moderate_or_reject(
            session, user_id,
            title,
            short_description,
            description,
            region or "",
            *roles,
            *reference_links,
            max_chat_link,
        )

        max_chat_link = validate_max_chat_link(max_chat_link)

        idea.name = title.strip()
        idea.short_description = short_description.strip()
        idea.long_description = description.strip()

        idea.required_roles = [
            role.strip()
            for role in roles
            if role.strip()
        ]

        idea.reference_links = [
            link.strip()
            for link in reference_links
            if link.strip()
        ]

        idea.deadline = deadline or None
        idea.category = category
        idea.region = region.strip() if region else None
        idea.max_chat_link = max_chat_link.strip()

        await session.commit()

    return RedirectResponse(
        url=f"/ideas/{idea_id}/manage",
        status_code=303,
    )


@router.post("/ideas/{idea_id}/responses/cancel")
async def cancel_own_response_route(request: Request, idea_id: int):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        idea = await get_idea_by_id(session, idea_id)

        if idea is not None:
            response = await get_response_by_user_and_idea(
                session,
                user_id,
                idea_id,
            )

            if response is not None:
                await delete_response(session, response.id)

    return RedirectResponse(
        url=f"/ideas/{idea_id}",
        status_code=303,
    )


@router.post("/ideas/{idea_id}/responses/{response_id}/reject")
async def reject_response_route(
    request: Request,
    idea_id: int,
    response_id: int,
):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        response = await get_response_by_id(session, response_id)

        if response is not None and response.id_idea == idea_id:
            response_user_id = response.id_user

            await delete_response(session, response_id)

            await create_notification(
                session=session,
                user_id=response_user_id,
                message=(
                    f"Отклик на идею «{idea.name}» отклонён.\n\n"
                    "Можешь продолжить поиск проектов в VECTOR."
                ),
            )

    return RedirectResponse(
        url=f"/ideas/{idea_id}/manage",
        status_code=303,
    )


@router.post("/ideas/{idea_id}/responses/{response_id}/accept")
async def accept_response_route(
    request: Request,
    idea_id: int,
    response_id: int,
):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        response = await get_response_by_id(session, response_id)

        if response is not None and response.id_idea == idea_id:
            response_user_id = response.id_user

            added = await add_team_member(
                session,
                idea_id,
                response_user_id,
                response.role,
            )

            if added:
                await delete_response(session, response_id)

                message = (
                    f"🎉 Твой отклик на идею «{idea.name}» принят!\n\n"
                    "Ты добавлен в команду."
                )

                if idea.max_chat_link:
                    message += (
                        f"\n\nСсылка на MAX-чат команды:\n"
                        f"{idea.max_chat_link}"
                    )

                await create_notification(
                    session=session,
                    user_id=response_user_id,
                    message=message,
                )

    return RedirectResponse(
        url=f"/ideas/{idea_id}/manage",
        status_code=303,
    )


@router.get("/ideas/{idea_id}/manage")
async def manage_idea(request: Request, idea_id: int):
    async with SessionFactory() as session:
        user_id = request.session["user_id"]

        user = await get_user_by_id(session, user_id)
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            raise HTTPException(
                status_code=404,
                detail="Идея не найдена",
            )

        if not has_idea_access(user, idea):
            raise HTTPException(
                status_code=403,
                detail="Нет доступа",
            )

        author = await get_user_by_id(session, idea.owner)

        team = []

        for member in idea.roles or []:
            team_user = await get_user_by_id(
                session,
                member["user_id"],
            )

            if team_user:
                team.append({
                    "user": team_user,
                    "role": member["role"],
                })

        idea_responses = await get_responses_by_idea(
            session,
            idea_id,
        )

        responses = []

        for response in idea_responses:
            response_user = await get_user_by_id(
                session,
                response.id_user,
            )

            if response_user:
                responses.append({
                    "id": response.id,
                    "role": response.role,
                    "description": response.description,
                    "user": response_user,
                })

        return templates.TemplateResponse(
            request=request,
            name="idea_manage.html",
            context={
                "idea": idea,
                "author": author,
                "team": team,
                "responses": responses,
                "responses_count": len(responses),
                "is_admin": (
                    int(user.max_id) in Config().get_admin_max_ids()
                ),
            },
        )
