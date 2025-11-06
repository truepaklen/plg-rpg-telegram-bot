from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Literal
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from .models import User, Task, Level, Submission

@dataclass
class Profile:
    user: User
    level: Level | None
    next_level: Level | None
    progress_to_next: float | None  # 0..1

def ensure_user(db: Session, tg_id: int, username: str | None, full_name: str | None) -> User:
    u = db.scalar(select(User).where(User.tg_id == tg_id))
    if u:
        changed = False
        if username and u.username != username: u.username = username; changed = True
        if full_name and u.full_name != full_name: u.full_name = full_name; changed = True
        if changed: db.commit()
        return u
    u = User(tg_id=tg_id, username=username, full_name=full_name, xp_total=0)
    db.add(u); db.commit(); return u

def get_profile(db: Session, user: User) -> Profile:
    levels = list(db.scalars(select(Level).order_by(Level.xp_required.asc())))
    current = None; nextl = None
    for lev in levels:
        if user.xp_total >= lev.xp_required: current = lev
        elif not nextl: nextl = lev
    progress = None
    if current and nextl:
        span = max(1, nextl.xp_required - current.xp_required)
        progress = (user.xp_total - current.xp_required) / span
    elif not current and nextl:
        progress = user.xp_total / max(1, nextl.xp_required)
    return Profile(user=user, level=current, next_level=nextl, progress_to_next=progress)

def find_task(db: Session, query: str) -> Task | None:
    query = query.strip().lower()
    t = db.scalar(select(Task).where(func.lower(Task.code) == query))
    if t: return t
    return db.scalars(select(Task).where(func.lower(Task.name).like(f"%{query}%")).limit(1)).first()

def award(db: Session, target_user: User, task: Task, count: int, manager: User | None) -> Submission:
    total_xp = task.xp * max(1, count)
    s = Submission(user_id=target_user.id, task_id=task.id, manager_id=manager.id if manager else None, count=count, xp_awarded=total_xp)
    target_user.xp_total += total_xp
    db.add(s); db.commit(); return s

def leaderboard(db: Session, period: Literal["week","month","all"]) -> list[tuple[User,int]]:
    if period == "all":
        q = (select(User, func.coalesce(func.sum(Submission.xp_awarded), 0))
             .join(Submission, isouter=True).group_by(User.id)
             .order_by(func.coalesce(func.sum(Submission.xp_awarded), 0).desc()))
    else:
        now = datetime.now(timezone.utc)
        start = (now - relativedelta(days=now.weekday())) if period == "week" else now.replace(day=1)
        q = (select(User, func.coalesce(func.sum(Submission.xp_awarded), 0))
             .join(Submission).where(Submission.created_at >= start)
             .group_by(User.id).order_by(func.sum(Submission.xp_awarded).desc()))
    return list(db.execute(q).all())
