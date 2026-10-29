from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routers import home, events, ideas, profile

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="VECTOR")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "frontend" / "static"),
    name="static",
)

app.include_router(home.router)
app.include_router(ideas.router)
app.include_router(events.router)
app.include_router(profile.router)