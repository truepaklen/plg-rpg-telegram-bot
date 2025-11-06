from __future__ import annotations
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Dispatcher as AioDispatcher
from aiogram.types import Update
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import sys, traceback

from .config import settings
from .db import engine, Base, SessionLocal
from .importer import import_tasks_levels
from .bot import bot, router

app = FastAPI(title="PLG RPG Bot")
Base.metadata.create_all(bind=engine)

def _safe_tz(name: str) -> ZoneInfo:
    """Фолбэк на UTC, если TZ задана неверно (чтобы сервис не падал)."""
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")

@app.on_event("startup")
async def on_startup():
    # импорт Excel при запуске
    with SessionLocal() as db:
        import_tasks_levels(db)
    # aiogram
    app.state.dp = AioDispatcher()
    app.state.dp.include_router(router)
    # планировщик (каждый день 10:00 локального времени)
    app.state.scheduler = AsyncIOScheduler(timezone=_safe_tz(settings.timezone))
    app.state.scheduler.add_job(broadcast_heroes, CronTrigger(hour=10, minute=0))
    app.state.scheduler.start()

@app.on_event("shutdown")
async def on_shutdown():
    try:
        app.state.scheduler.shutdown(wait=False)
    except Exception:
        pass

@app.get("/")
async def root():
    return "OK"

@app.get("/ping")
async def ping():
    return {"pong": True}

@app.get("/healthz")
async def healthz():
    return {"ok": True}

@app.get("/setup-webhook")
async def setup_webhook(secret: str):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="forbidden")
    if not settings.webhook_base:
        raise HTTPException(status_code=400, detail="WEBHOOK_BASE not set")
    url = f"{settings.webhook_base.rstrip('/')}/webhook/{settings.webhook_secret}"
    await bot.set_webhook(url)
    return {"webhook": url}

# >>> Диагностически безопасный обработчик вебхука
@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="forbidden")
    try:
        data = await request.json()
        # логируем сырой апдейт для диагностики
        print("Webhook update:", data, file=sys.stderr)
        update = Update.model_validate(data)
        await app.state.dp.feed_update(bot, update)
        return JSONResponse({"ok": True})
    except Exception as e:
        # ключевой лог — покажет точную причину 500
        print("Webhook error:", e, file=sys.stderr)
        traceback.print_exc()
        # отвечаем 200, чтобы Telegram не долбил повторами
        return JSONResponse({"ok": False}, status_code=200)

async def broadcast_heroes():
    if not settings.broadcast_chat_id:
        return
    from .logic import leaderboard
    with SessionLocal() as db:
        week = leaderboard(db, "week")
        month = leaderboard(db, "month")

    def fmt(rows, title):
        if not rows:
            return f"<b>{title}</b>\nНет данных."
        lines = [f"<b>{title}</b>"]
        for i, (u, xp) in enumerate(rows[:5], start=1):
            name = u.full_name or ("@" + u.username if u.username else str(u.tg_id))
            lines.append(f"{i}. {name} — {xp} XP")
        return "\n".join(lines)

    text = fmt(week, "Герои недели") + "\n\n" + fmt(month, "Герои месяца")
    try:
        await bot.send_message(settings.broadcast_chat_id, text)
    except Exception:
        pass

