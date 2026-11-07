import asyncio
from app.db.models import Users, Ideas, Responses, Events, Notifications
from app.db.database import create_tables

if __name__ == "__main__":
    asyncio.run(create_tables())
    print("ok") 