from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from core.templates import templates
from app.db.database import SessionFactory
from app.db.crud import get_user_by_id, update_user

router = APIRouter()

TEST_USER_ID = 1

@router.get("/profile")
async def profile(request: Request):
    async with SessionFactory() as session:
        user = await get_user_by_id(session, TEST_USER_ID)

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"title": "Пользователь не найден"},
            status_code=404,
        )

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "title": "ВЕКТОР — Мой профиль",
            "active_page": "none",
            "user": user,
            "is_owner": True,
        }
    )

@router.post("/profile/update")
async def profile_update(
    section: str = Form(...),
    name: str | None = Form(None),
    description: str | None = Form(None),
    skills: list[str] = Form(default=[]),
    link_titles: list[str] = Form(default=[]),
    links: list[str] = Form(default=[]),
):
    updates = {}

    if section == "name" and name is not None:
        updates["name"] = name.strip()

    elif section == "about" and description is not None:
        updates["description"] = description.strip()

    elif section == "skills":
        updates["skills"] = [
            skill.strip()
            for skill in skills
            if skill.strip()
        ]

    elif section == "links":
        urls = []

        for title, url in zip(link_titles, links):
            title = title.strip()
            url = url.strip()

            if title and url:
                urls.append({
                    "title": title,
                    "url": url,
                })

        updates["urls"] = urls

    if updates:
        async with SessionFactory() as session:
            await update_user(
                session,
                TEST_USER_ID,
                **updates,
            )

    return RedirectResponse(
        url="/profile",
        status_code=303,
    )

@router.get("/users/{user_id}")
async def user_profile(request: Request, user_id: int):
    async with SessionFactory() as session:
        user = await get_user_by_id(session, user_id)

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"title": "Пользователь не найден"},
            status_code=404,
        )

    is_owner = user.id == TEST_USER_ID

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "title": f"ВЕКТОР — {user.name}",
            "active_page": "none",
            "user": user,
            "is_owner": is_owner,
        }
    )