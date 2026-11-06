
from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from core.templates import templates
from core.config import Config
from app.db.database import SessionFactory
from app.db.crud import (
    get_events,
    get_event_by_id,
    get_user_by_id,
    create_event,
    update_event,
    delete_event,
)


BASE_DIR = Path(__file__).resolve().parents[3]
EVENTS_UPLOAD_DIR = BASE_DIR / "frontend" / "static" / "uploads" / "events"

router = APIRouter()

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000

ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}


# =========================
# ПРАВА ДОСТУПА
# =========================

def is_admin(user):
    if user is None:
        return False

    return str(user.max_id) in {
        str(x) for x in Config().get_admin_max_ids()
    }


def can_create_event(user):
    if user is None:
        return False

    return is_admin(user) or user.status == "organizer"


def can_manage_event(user, event):
    if user is None or event is None:
        return False

    return is_admin(user) or (
        user.status == "organizer"
        and event.owner == user.id
    )


# =========================
# ПРОВЕРКА ССЫЛОК
# =========================

def validate_event_urls(urls):
    event_urls = []

    if len(urls or []) > 10:
        raise HTTPException(400, "Можно добавить не больше 10 ссылок")

    for value in urls or []:
        value = value.strip()

        if not value:
            continue

        if len(value) > 500:
            raise HTTPException(400, "Ссылка слишком длинная")

        try:
            parsed = urlsplit(value)
            hostname = parsed.hostname
            parsed.port
        except ValueError:
            raise HTTPException(400, "Некорректная ссылка")

        if (
            parsed.scheme not in ("http", "https")
            or not hostname
            or parsed.username
            or parsed.password
        ):
            raise HTTPException(400, "Некорректная ссылка")

        event_urls.append({"url": value})

    return event_urls


# =========================
# ПРОВЕРКА И СОХРАНЕНИЕ ОБЛОЖКИ
# =========================

async def save_event_image(img):
    if not img or not img.filename:
        return None, None

    content = await img.read(MAX_IMAGE_SIZE + 1)

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            400,
            "Размер обложки не должен превышать 5 МБ"
        )

    try:
        image = Image.open(BytesIO(content))

        if image.format not in ALLOWED_FORMATS:
            raise HTTPException(
                400,
                "Поддерживаются только JPG, PNG и WEBP"
            )

        width, height = image.size

        if width < 320 or height < 180:
            raise HTTPException(
                400,
                "Минимальный размер изображения — 320×180"
            )

        if (
            width > 8000
            or height > 8000
            or width * height > MAX_IMAGE_PIXELS
        ):
            raise HTTPException(
                400,
                "Слишком большое разрешение изображения"
            )

        image_format = image.format
        image.verify()

    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
    ):
        raise HTTPException(400, "Некорректное изображение")

    extension = ALLOWED_FORMATS[image_format]

    EVENTS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = EVENTS_UPLOAD_DIR / filename

    destination.write_bytes(content)

    return f"/static/uploads/events/{filename}", destination


def delete_event_image_file(image_url):
    if not image_url:
        return

    prefix = "/static/uploads/events/"

    if not image_url.startswith(prefix):
        return

    filename = image_url[len(prefix):]

    if not filename or Path(filename).name != filename:
        return

    upload_dir = EVENTS_UPLOAD_DIR.resolve()
    image_file = (upload_dir / filename).resolve()

    if image_file.parent != upload_dir:
        return

    try:
        image_file.unlink(missing_ok=True)
    except OSError:
        pass


# =========================
# СПИСОК МЕРОПРИЯТИЙ
# =========================

@router.get("/events")
async def events(request: Request):
    user_id = request.session.get("user_id")
    can_create = False

    async with SessionFactory() as session:
        if user_id:
            user = await get_user_by_id(session, user_id)
            can_create = can_create_event(user)

        event_list = await get_events(session)

    return templates.TemplateResponse(
        request=request,
        name="events.html",
        context={
            "title": "ВЕКТОР — Мероприятия",
            "active_page": "events",
            "events": event_list,
            "can_create": can_create,
        }
    )


# =========================
# СОЗДАНИЕ МЕРОПРИЯТИЯ
# =========================

@router.get("/events/create")
async def create_event_page(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(401, "Необходима авторизация")

    async with SessionFactory() as session:
        user = await get_user_by_id(session, user_id)

        if user is None:
            raise HTTPException(401, "Пользователь не найден")

        if not can_create_event(user):
            raise HTTPException(
                403,
                "У вас нет прав на создание мероприятий"
            )

    return templates.TemplateResponse(
        request=request,
        name="event_create.html",
        context={
            "title": "ВЕКТОР — Создание мероприятия",
            "active_page": "events",
        }
    )


@router.post("/events/create")
async def create_event_route(
    request: Request,
    name: str = Form(...),
    short_description: str = Form(...),
    long_description: str = Form(...),
    region: str = Form(""),
    img: UploadFile | None = File(None),
    urls: list[str] | None = Form(None),
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(401, "Необходима авторизация")

    name = name.strip()
    short_description = short_description.strip()
    long_description = long_description.strip()
    region = region.strip() or None

    if not name or not short_description or not long_description:
        raise HTTPException(400, "Заполните обязательные поля")

    if len(name) > 150 or len(short_description) > 300:
        raise HTTPException(400, "Превышена допустимая длина текста")

    if len(long_description) > 10000:
        raise HTTPException(400, "Полное описание слишком длинное")

    if region and len(region) > 200:
        raise HTTPException(400, "Название региона слишком длинное")

    event_urls = validate_event_urls(urls)

    image_path = None
    destination = None

    try:
        async with SessionFactory() as session:
            user = await get_user_by_id(session, user_id)

            if user is None:
                raise HTTPException(401, "Пользователь не найден")

            if not can_create_event(user):
                raise HTTPException(
                    403,
                    "У вас нет прав на создание мероприятий"
                )

            image_path, destination = await save_event_image(img)

            await create_event(
                session=session,
                owner_id=user.id,
                img=image_path or "",
                name=name,
                short_description=short_description,
                long_description=long_description,
                region=region,
                urls=event_urls,
            )

    except Exception:
        if destination:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    return RedirectResponse("/events", status_code=303)


# =========================
# ПРОСМОТР МЕРОПРИЯТИЯ
# =========================

@router.get("/events/{event_id}")
async def event_detail(request: Request, event_id: int):
    user_id = request.session.get("user_id")

    async with SessionFactory() as session:
        event = await get_event_by_id(session, event_id)

        if event is None:
            raise HTTPException(404, "Мероприятие не найдено")

        organizer = await get_user_by_id(session, event.owner)

        current_user = (
            await get_user_by_id(session, user_id)
            if user_id else None
        )

        can_manage = can_manage_event(current_user, event)

    return templates.TemplateResponse(
        request=request,
        name="event_detail.html",
        context={
            "title": f"ВЕКТОР — {event.name}",
            "active_page": "events",
            "event": event,
            "organizer": organizer,
            "can_manage": can_manage,
        }
    )


# =========================
# РЕДАКТИРОВАНИЕ
# =========================

@router.get("/events/{event_id}/edit")
async def edit_event_page(request: Request, event_id: int):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(401, "Необходима авторизация")

    async with SessionFactory() as session:
        user = await get_user_by_id(session, user_id)
        event = await get_event_by_id(session, event_id)

        if event is None:
            raise HTTPException(404, "Мероприятие не найдено")

        if not can_manage_event(user, event):
            raise HTTPException(403, "Нет прав на редактирование")

    return templates.TemplateResponse(
        request=request,
        name="event_edit.html",
        context={
            "title": f"ВЕКТОР — Редактирование: {event.name}",
            "active_page": "events",
            "event": event,
        }
    )


@router.post("/events/{event_id}/edit")
async def edit_event_route(
    request: Request,
    event_id: int,
    name: str = Form(...),
    short_description: str = Form(...),
    long_description: str = Form(...),
    region: str = Form(""),
    img: UploadFile | None = File(None),
    urls: list[str] | None = Form(None),
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(401, "Необходима авторизация")

    name = name.strip()
    short_description = short_description.strip()
    long_description = long_description.strip()
    region = region.strip() or None

    if not name or not short_description or not long_description:
        raise HTTPException(400, "Заполните обязательные поля")

    if len(name) > 150 or len(short_description) > 300:
        raise HTTPException(400, "Превышена допустимая длина текста")

    if len(long_description) > 10000:
        raise HTTPException(400, "Полное описание слишком длинное")

    if region and len(region) > 200:
        raise HTTPException(400, "Название региона слишком длинное")

    event_urls = validate_event_urls(urls)

    destination = None
    new_image_path = None
    old_image_path = None

    try:
        async with SessionFactory() as session:
            user = await get_user_by_id(session, user_id)
            event = await get_event_by_id(session, event_id)

            if event is None:
                raise HTTPException(404, "Мероприятие не найдено")

            if not can_manage_event(user, event):
                raise HTTPException(403, "Нет прав на редактирование")

            old_image_path = event.img

            new_image_path, destination = await save_event_image(img)

            updates = {
                "name": name,
                "short_description": short_description,
                "long_description": long_description,
                "region": region,
                "urls": event_urls,
            }

            if new_image_path:
                updates["img"] = new_image_path

            await update_event(
                session,
                event_id,
                **updates
            )

    except Exception:
        if destination:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
        raise

    if new_image_path and old_image_path:
        delete_event_image_file(old_image_path)

    return RedirectResponse(
        f"/events/{event_id}",
        status_code=303
    )


# =========================
# УДАЛЕНИЕ
# =========================

@router.post("/events/{event_id}/delete")
async def delete_event_route(request: Request, event_id: int):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(401, "Необходима авторизация")

    async with SessionFactory() as session:
        user = await get_user_by_id(session, user_id)
        event = await get_event_by_id(session, event_id)

        if event is None:
            raise HTTPException(404, "Мероприятие не найдено")

        if not can_manage_event(user, event):
            raise HTTPException(403, "Нет прав на удаление")

        old_image_path = event.img

        await delete_event(session, event_id)

    delete_event_image_file(old_image_path)

    return RedirectResponse("/events", status_code=303)
