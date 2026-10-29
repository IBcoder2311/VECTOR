from fastapi import APIRouter, Request
from core.templates import templates

router = APIRouter()

@router.get("/ideas")
async def ideas(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ideas.html",
        context={"title": "ВЕКТОР - Мои идеи",
                 "active_page": "ideas"}
    )
