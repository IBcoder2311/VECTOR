from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[3]

templates = Jinja2Templates(
    directory=BASE_DIR / "frontend" / "templates"
)

@router.get("/events")
async def events(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={"title": "ВЕКТОР - Мероприятия",
                 "active_page": "events"}
    )
