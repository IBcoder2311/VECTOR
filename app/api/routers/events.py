from fastapi import APIRouter, Request
from core.templates import templates

router = APIRouter()

@router.get("/events")
async def events(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={"title": "ВЕКТОР - Мероприятия",
                 "active_page": "events"}
    )
