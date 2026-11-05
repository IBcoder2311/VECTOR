from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from core.templates import templates
from app.db.crud import get_random_ideas, get_responses_count, search_ideas
from app.db.database import SessionFactory
from app.constants import IDEA_CATEGORIES

router = APIRouter()


@router.get("/")
async def home(
    request: Request,
    category: str | None = Query(default=None),
):
    if category not in IDEA_CATEGORIES:
        category = None

    async with SessionFactory() as session:
        ideas = await get_random_ideas(
            session,
            limit=40,
            category=category,
        )

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
            "title": "ВЕКТОР — главная страница",
            "active_page": "home",
            "ideas": ideas_with_responses,
            "categories": IDEA_CATEGORIES,
            "selected_category": category,
        },
    )

@router.get("/search")
async def search_ideas_route(
    request: Request,
    q: str = Query(default="", max_length=100),
    category: str | None = Query(default=None),
):
    query = q.strip()

    if category not in IDEA_CATEGORIES:
        category = None

    if not query and not category:
        return RedirectResponse(url="/", status_code=303)

    async with SessionFactory() as session:
        if query:
            found_ideas = await search_ideas(
                session,
                query,
                limit=40,
                category=category,
            )
        else:
            found_ideas = await get_random_ideas(
                session,
                limit=40,
                category=category,
            )

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
            "title": f"ВЕКТОР — Поиск: {query}" if query else "ВЕКТОР — Категории",
            "active_page": "home",
            "ideas": ideas_with_responses,
            "search_query": query,
            "categories": IDEA_CATEGORIES,
            "selected_category": category,
        },
    )