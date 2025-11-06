# PLG RPG Telegram Bot

Telegram‑бот для мотивационной игры «RPG in PLG»: импорт заданий и уровней из Excel, учёт выполнений менеджерами, начисление XP и рангов, лидерборды за неделю/месяц.

## Переменные окружения
- `TELEGRAM_TOKEN` — токен из @BotFather
- `WEBHOOK_BASE` — публичный HTTPS вашего хостинга (Render/Timeweb Cloud и т.п.)
- `WEBHOOK_SECRET` — придумайте короткий секрет, напр. `wh_abc123`
- `MANAGER_IDS` — список Telegram ID менеджеров через запятую (опц.)
- `SUPER_ADMIN_ID` — Telegram ID супер-админа (опц.)
- `DATABASE_URL` — `postgresql://...` или `sqlite:///./plg.sqlite3` (опц., по умолчанию SQLite)
- `BROADCAST_CHAT_ID` — ID чата/канала для авто-постов (опц.)
- `TZ` — временная зона, напр. `Europe/Helsinki`

## Команды
- `/start`, `/help`, `/tasks`, `/me`, `/top [week|month|all]`
- менеджеры: `/log <@user|id> <код|название> [count]`
- супер-админ: `/promote <id>`

## Запуск локально
```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.server:app --reload
# затем откройте http://127.0.0.1:8000/healthz
```
Затем установите вебхук, заменив BASE и секрет:
`http://127.0.0.1:8000/setup-webhook?secret=WH_SECRET` (для Telegram нужен HTTPS — используйте ngrok/Timeweb/Render).
