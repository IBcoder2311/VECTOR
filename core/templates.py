from pathlib import Path
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parents[1]

templates = Jinja2Templates(
    directory=BASE_DIR / "frontend" / "templates"
)