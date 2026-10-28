from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]

templates = Jinja2Templates(
    directory=BASE_DIR / "frontend" / "templates"
)

@router.get("/ideas")
async def ideas(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="ideas.html",
        context={"title": "ВЕКТОР - Мои идеи",
                 "active_page": "ideas"}
    )
