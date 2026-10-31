from fastapi import APIRouter, Request
from core.templates import templates
from app.db.crud import get_random_ideas, get_responses_count
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