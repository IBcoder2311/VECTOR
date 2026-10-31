from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from core.templates import templates
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
)

router = APIRouter()

TEST_USER_ID = 1


@router.get("/ideas")
async def ideas(request: Request):
    async with SessionFactory() as session:
        user_ideas = await get_ideas_by_owner(
            session,
            TEST_USER_ID
        )
  
    return templates.TemplateResponse(
        request=request,
        name="ideas.html",
        context={
            "title": "ВЕКТОР — Мои идеи",
            "active_page": "ideas",
            "ideas": user_ideas,
        }
    )

@router.get("/ideas/create")
async def create_idea_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="create_idea.html",
        context={
            "title": "ВЕКТОР — Создание идеи",
            "active_page": "ideas",
        }
    )

@router.post("/ideas/create")
async def create_idea_route(
    title: str = Form(...),
    short_description: str = Form(...),
    description: str = Form(...),
    roles: list[str] = Form(default=[]),
    deadline: str | None = Form(default=None),
    region: str | None = Form(default=None),
    reference_links: list[str] = Form(default=[]),
):
    async with SessionFactory() as session:
        await create_idea(
            session=session,
            owner=TEST_USER_ID,
            name=title,
            short_description=short_description,
            long_description=description,
            required_roles=roles,
            reference_links=reference_links,
            deadline=deadline or None,
            region=region or None,
        )

    return RedirectResponse(
        url="/ideas",
        status_code=303
    )


@router.get("/ideas/{idea_id}")
async def idea_detail(request: Request, idea_id: int):
    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if idea is None:
            return templates.TemplateResponse(
                request=request,
                name="404.html",
                context={"title": "Идея не найдена"},
                status_code=404,
            )

        author = await get_user_by_id(session, idea.owner)
        responses = await get_responses_by_idea(session, idea_id)

    if idea.owner == TEST_USER_ID:
        return RedirectResponse(
            url=f"/ideas/{idea_id}/manage"
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
        }
    )

@router.post("/ideas/{idea_id}/respond")
async def respond_to_idea(
    idea_id: int,
    message: str = Form(...),
    role: str = Form(...),
):
    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if idea is None or idea.owner == TEST_USER_ID:
            return RedirectResponse(
                url=f"/ideas/{idea_id}",
                status_code=303
            )

        try:
            await create_response(
                session=session,
                id_idea=idea_id,
                id_user=TEST_USER_ID,
                description=message,
                role=role,
            )
        except Exception:
            await session.rollback()
            raise

    return RedirectResponse(
        url=f"/ideas/{idea_id}",
        status_code=303
    )

@router.post("/ideas/{idea_id}/delete")
async def delete_idea_route(idea_id: int):
    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if idea is not None and idea.owner == TEST_USER_ID:
            await delete_idea(session, idea_id)

    return RedirectResponse(
        url="/ideas",
        status_code=303
    )

@router.post("/ideas/{idea_id}/responses/{response_id}/delete")
async def delete_response_route(
    idea_id: int,
    response_id: int,
):
    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if idea is not None and idea.owner == TEST_USER_ID:
            responses = await get_responses_by_idea(session, idea_id)

            if any(response.id == response_id for response in responses):
                await delete_response(session, response_id)

    return RedirectResponse(
        url=f"/ideas/{idea_id}",
        status_code=303
    )

@router.get("/ideas/{idea_id}/manage")
async def manage_idea(request: Request, idea_id: int):
    async with SessionFactory() as session:
        idea = await get_idea_by_id(session, idea_id)

        if not idea:
            raise HTTPException(status_code=404, detail="Идея не найдена")

        if idea.owner != TEST_USER_ID:
            raise HTTPException(status_code=403, detail="Нет доступа")

        author = await get_user_by_id(session, idea.owner)

        team = []
        for member in idea.roles or []:
            user = await get_user_by_id(session, member["user_id"])

            if user:
                team.append({
                    "user": user,
                    "role": member["role"],
                })

        idea_responses = await get_responses_by_idea(session, idea_id)
        responses = []

        for response in idea_responses:
            user = await get_user_by_id(session, response.id_user)

            if user:
                responses.append({
                    "id": response.id,
                    "role": response.role,
                    "description": response.description,
                    "user": user,
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
            }
        )