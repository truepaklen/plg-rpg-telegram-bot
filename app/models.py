from __future__ import annotations
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, BigInteger, DateTime, ForeignKey, func
from .db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_manager: Mapped[bool] = mapped_column(default=False)
    xp_total: Mapped[int] = mapped_column(Integer, default=0)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    xp: Mapped[int] = mapped_column(Integer)

class Level(Base):
    __tablename__ = "levels"
    num: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    xp_required: Mapped[int] = mapped_column(Integer)
    reward: Mapped[str | None] = mapped_column(String(255))

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    count: Mapped[int] = mapped_column(Integer, default=1)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
