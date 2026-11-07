from fastapi import HTTPException

from app.db.crud import create_notification
from app.moderation.moderation import check_text


async def moderate_or_reject(session, user_id: int, *texts: str):
    for text in texts:
        result = check_text(text or "")

        if result["flagged"]:
            await create_notification(
                session=session,
                user_id=user_id,
                message=(
                    "🚫 Твоя публикация отклонена!\n\n"
                    "Обнаружена запрещённая лексика. "
                    "Исправь текст и попробуй снова."
                ),
            )

            raise HTTPException(
                status_code=400,
                detail="Публикация отклонена модерацией.",
            )