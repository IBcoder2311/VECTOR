from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from core.templates import templates
from app.db.crud import get_random_ideas, get_responses_count, search_ideas
from app.db.database import SessionFactory

router = APIRouter()


@router.get("/")
async def home(request: Request):
    async with SessionFactory() as session:
        ideas = await get_random_ideas(session, limit=40)

        ideas_with_responses = []
        for idea in ideas:
            responses_count = await get_responses_count(session, idea.id)
            ideas_with_responses.append({
                "idea": idea,
                "responses_count": responses_count,
            })

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "title": "ВЕКТОР - главная страница",
            "active_page": "home",
            "ideas": ideas_with_responses,
        },
    )

@router.get("/search")
async def search_ideas_route(
    request: Request,
    q: str = Query(default="", max_length=100),
):
    query = q.strip()

    if not query:
        return RedirectResponse(url="/", status_code=303)

    async with SessionFactory() as session:
        found_ideas = await search_ideas(session, query, limit=40)

        ideas_with_responses = []
        for idea in found_ideas:
            responses_count = await get_responses_count(session, idea.id)
            ideas_with_responses.append({
                "idea": idea,
                "responses_count": responses_count,
            })

    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "title": f"ВЕКТОР — Поиск: {query}",
            "active_page": "home",
            "ideas": ideas_with_responses,
            "search_query": query,
        },
    )