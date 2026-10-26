from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import ForeignKey
from app.db.database import Base

# --------------------ПОЛЬЗОВАТЕЛИ--------------------

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    max_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    img: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    skills: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    urls: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False
    )

# --------------------ИДЕИ--------------------

class Ideas(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    owner: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    short_description: Mapped[str] = mapped_column(
        String(300),
        nullable=False
    )

    long_description: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    required_roles: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    roles: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )

    views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    deadline: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

# --------------------ОТКЛИКИ--------------------

class Responses(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    id_idea: Mapped[int] = mapped_column(
        ForeignKey("ideas.id"),
        nullable=False
    )

    id_user: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

# --------------------МЕРОПРИЯТИЯ--------------------

class Events(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )
    
    owner: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )

    img: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    short_description: Mapped[str] = mapped_column(
        String(300),
        nullable=False
    )

    long_description: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    region: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    urls: Mapped[list[dict]] = mapped_column(
        JSONB,
        default=list,
        nullable=False
    )