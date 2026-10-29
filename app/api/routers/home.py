from fastapi import APIRouter, Request
from core.templates import templates

router = APIRouter()

@router.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"title": "ВЕКТОР - главная страница",
                 "active_page": "home"}
    )
