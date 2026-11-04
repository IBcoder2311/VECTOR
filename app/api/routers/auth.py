from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from auth.auth_init import validate_max_init_data
from app.db.database import SessionFactory
from app.db.crud import get_user_by_max_id, create_user
from core.config import Config


router = APIRouter(prefix="/auth", tags=["Auth"])

config = Config()


class MaxAuthRequest(BaseModel):
    init_data: str
    return_to: str = "/"


def get_safe_return_url(url: str) -> str:
    if not url.startswith("/") or url.startswith("//"):
        return "/"

    return url


@router.post("/max")
async def authenticate_with_max(
    data: MaxAuthRequest,
    request: Request,
):
    bot_token = config.get_data_maxtoken()

    if not bot_token:
        raise HTTPException(
            status_code=500,
            detail="MAX_BOT_TOKEN не настроен",
        )

    max_data = validate_max_init_data(
        init_data=data.init_data,
        bot_token=bot_token,
    )

    if max_data is None:
        raise HTTPException(
            status_code=401,
            detail="Недействительные данные авторизации MAX",
        )

    max_user = max_data["user"]

    max_id = str(max_user["id"])

    name = (
        max_user.get("name")
        or " ".join(
            filter(
                None,
                [
                    max_user.get("first_name"),
                    max_user.get("last_name"),
                ],
            )
        )
        or max_user.get("username")
        or "Пользователь"
    )

    img = max_user.get("photo_url") or "frontend/static/img/avatar.jpg"

    async with SessionFactory() as session:
        user = await get_user_by_max_id(session, max_id)

        if user is None:
            try:
                user = await create_user(
                    session=session,
                    max_id=max_id,
                    name=name,
                    img=img,
                )
            except IntegrityError:
                await session.rollback()
                user = await get_user_by_max_id(session, max_id)

                if user is None:
                    raise HTTPException(
                        status_code=500,
                        detail="Не удалось создать пользователя",
                    )

    request.session.clear()
    request.session["user_id"] = user.id

    return JSONResponse(
        {
            "ok": True,
            "redirect_url": get_safe_return_url(data.return_to),
        }
    )