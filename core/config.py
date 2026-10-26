import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy.engine import URL

class Config():
    def __init__(self):
        self.CORE_DIR = Path(__file__).resolve().parent
        load_dotenv(self.CORE_DIR / ".env")
        
    def create_url_db(self):
        return URL.create(
            drivername="postgresql+asyncpg",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "vector"),
        )

    def get_data_maxtoken(self):
        return os.getenv("MAX_BOT_TOKEN")
