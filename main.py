from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from core.templates import templates
from pathlib import Path
from app.api.routers import home, events, ideas, profile, auth, settings
from core.config import Config
from auth.auth_middleware import AuthMiddleware

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="VECTOR")

config = Config()

app.add_middleware(AuthMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=config.get_session_secret(),
    session_cookie="vector_session",
    max_age=60 * 60 * 24 * 7,  # 7 дней
    same_site="lax",
    https_only=True,
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static",
)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={
            "title": "ВЕКТОР — Страница не найдена",
            "active_page": None,
        },
        status_code=404,
    )

app.include_router(home.router)
app.include_router(ideas.router)
app.include_router(events.router)
app.include_router(profile.router)
app.include_router(auth.router) 
app.include_router(settings.router) 