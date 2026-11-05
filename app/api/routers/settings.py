from fastapi import APIRouter, Request

from core.templates import templates

router = APIRouter(tags=["Settings"])


@router.get("/settings")
async def settings(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "title": "ВЕКТОР — Настройки",
            "active_page": None,
        }
    )