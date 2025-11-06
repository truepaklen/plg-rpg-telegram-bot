from __future__ import annotations
import os
from pydantic import BaseModel

class Settings(BaseModel):
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    webhook_base: str = os.getenv("WEBHOOK_BASE", "")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "webhook")
    manager_ids: str = os.getenv("MANAGER_IDS", "")
    super_admin_id: int | None = int(os.getenv("SUPER_ADMIN_ID", "0")) or None
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./plg.sqlite3")
    broadcast_chat_id: int | None = int(os.getenv("BROADCAST_CHAT_ID", "0")) or None
    timezone: str = os.getenv("TZ", "Europe/Helsinki")

    @property
    def manager_id_set(self) -> set[int]:
        ids: set[int] = set()
        for chunk in self.manager_ids.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.add(int(chunk))
            except ValueError:
                pass
        if self.super_admin_id:
            ids.add(self.super_admin_id)
        return ids

settings = Settings()
