from __future__ import annotations
from aiogram import Bot, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import User, Task, Level
from .logic import ensure_user, get_profile, find_task, award, leaderboard
from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=settings.telegram_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
router = Router()

def is_manager(user: User) -> bool:
    return user.is_manager or (user.tg_id in settings.manager_id_set)

@router.message(Command("start"))
async def cmd_start(msg: Message):
    with SessionLocal() as db:
        u = ensure_user(db, msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
        prof = get_profile(db, u)
        text = [f"Привет, <b>{msg.from_user.full_name}</b>!", f"Твой XP: <b>{u.xp_total}</b>"]
        if prof.level:
            text.append(f"Твой уровень: <b>{prof.level.num}</b> — {prof.level.title} (порог {prof.level.xp_required} XP)")
        if prof.next_level:
            pct = int((prof.progress_to_next or 0) * 100)
            text.append(f"До след. уровня: {prof.next_level.num} — {pct}% из {prof.next_level.xp_required} XP")
        text.append("\nКоманды: /tasks /me /top [week|month|all]")
        if is_manager(u):
            text.append("Команда менеджера: /log <@user|id> <код|название> [count]")
        await msg.answer("\n".join(text))

@router.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer("<b>Справка</b>\n• /tasks — список заданий\n• /me — мой профиль\n• /top [week|month|all] — топ игроков\n• /log <@user|id> <код|название> [count] — менеджеры учитывают выполнение\n• /promote <id> — super admin назначает менеджера")

@router.message(Command("tasks"))
async def cmd_tasks(msg: Message):
    with SessionLocal() as db:
        rows = list(db.scalars(select(Task).order_by(Task.code.asc())))
        if not rows:
            await msg.answer("Заданий пока нет."); return
        chunks = [f"<code>{t.code}</code> — {t.name} (+{t.xp} XP)" for t in rows]
        await msg.answer("\n".join(chunks))

@router.message(Command("me"))
async def cmd_me(msg: Message):
    with SessionLocal() as db:
        u = ensure_user(db, msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
        prof = get_profile(db, u)
        lines = [f"XP: <b>{u.xp_total}</b>"]
        if prof.level: lines.append(f"Уровень: <b>{prof.level.num}</b> — {prof.level.title}")
        if prof.next_level:
            pct = int((prof.progress_to_next or 0) * 100)
            lines.append(f"Прогресс к {prof.next_level.num}: {pct}% ({u.xp_total}/{prof.next_level.xp_required})")
        await msg.answer("\n".join(lines))

@router.message(Command("top"))
async def cmd_top(msg: Message):
    args = (msg.text or "").split()
    period = args[1] if len(args)>=2 and args[1] in {"week","month","all"} else "week"
    with SessionLocal() as db:
        rows = leaderboard(db, period)
        if not rows: await msg.answer("Пока нет данных по топу."); return
        lines = [f"<b>Топ ({period})</b>"]
        for i, (u, total) in enumerate(rows[:10], start=1):
            uname = u.full_name or ("@" + u.username if u.username else str(u.tg_id))
            lines.append(f"{i}. {uname} — {total} XP")
        await msg.answer("\n".join(lines))

@router.message(Command("promote"))
async def cmd_promote(msg: Message):
    if not settings.super_admin_id or msg.from_user.id != settings.super_admin_id:
        await msg.answer("Недостаточно прав."); return
    parts = (msg.text or "").split()
    if len(parts) < 2: await msg.answer("Укажите Telegram ID пользователя: /promote <id>"); return
    try: uid = int(parts[1])
    except ValueError: await msg.answer("ID должен быть числом."); return
    with SessionLocal() as db:
        u = db.scalar(select(User).where(User.tg_id == uid))
        if not u: await msg.answer("Пользователь не найден (он должен написать боту /start)."); return
        u.is_manager = True; db.commit()
        await msg.answer(f"Назначен менеджером: {u.full_name or u.username or uid}")

@router.message(Command("log"))
async def cmd_log(msg: Message):
    from .models import User  # avoid circular import in type hints
    with SessionLocal() as db:
        manager = ensure_user(db, msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
        if not (manager.is_manager or manager.tg_id in settings.manager_id_set):
            await msg.answer("Команда доступна только менеджерам."); return
        parts = (msg.text or "").split(maxsplit=3)
        if len(parts) < 3: await msg.answer("Формат: /log <@user|id> <код|часть названия> [count]"); return
        who_raw, task_raw = parts[1], parts[2]
        count = 1
        if len(parts) >= 4:
            try: count = max(1, int(parts[3]))
            except ValueError: pass
        # resolve user
        target = None
        if who_raw.startswith("@"):
            username = who_raw[1:]
            target = db.scalar(select(User).where(User.username == username))
        else:
            try: tid = int(who_raw); target = db.scalar(select(User).where(User.tg_id == tid))
            except ValueError: pass
        if not target: await msg.answer("Не найден пользователь. Он должен сначала написать /start боту."); return
        task = find_task(db, task_raw)
        if not task: await msg.answer("Задание не найдено. Посмотрите /tasks"); return
        from .logic import get_profile, award
        old_prof = get_profile(db, target)
        sub = award(db, target, task, count, manager)
        new_prof = get_profile(db, target)
        text = (f"Зачтено: <b>{task.name}</b> ×{count} (+{task.xp*count} XP)\n"
                f"Игрок: {target.full_name or target.username or target.tg_id}\n"
                f"Итого XP: <b>{target.xp_total}</b>")
        if (new_prof.level and not old_prof.level) or (new_prof.level and old_prof.level and new_prof.level.num != old_prof.level.num):
            text += f"\n🎉 Новый уровень: <b>{new_prof.level.num}</b> — {new_prof.level.title}! Награда: {new_prof.level.reward}"
            try: await bot.send_message(target.tg_id, "Поздравляем! У тебя новый уровень! Посмотри /me")
            except Exception: pass
        await msg.answer(text)
