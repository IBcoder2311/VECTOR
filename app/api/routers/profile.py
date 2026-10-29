from fastapi import APIRouter, Request
from core.templates import templates

router = APIRouter()

@router.get("/profile")
async def events(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"title": "ВЕКТОР - профиль",
                 "active_page": "none"}
    )
