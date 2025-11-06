from __future__ import annotations
import os, re
import pandas as pd
from sqlalchemy import delete
from sqlalchemy.orm import Session
from .models import Task, Level

TASKS_FILES = ["data/Банк Заданий .xlsx", "data/Bank Zadanii.xlsx"]
LEVELS_FILES = ["data/Уровни и награды.xlsx", "data/Levels.xlsx"]

def _num(val) -> int:
    if pd.isna(val): return 0
    if isinstance(val, (int, float)): return int(val)
    m = re.search(r"\d+", str(val))
    return int(m.group(0)) if m else 0

DEFAULT_TASKS = [
    ("Выход на подмену в свой выходной, чтобы помочь команде", 30),
    ("Тайный гость на 100% (идеальная проверка сервиса)", 25),
    ("Именной положительный отзыв от гостя", 20),
    ("Топ-продажи специальных блюд за месяц", 15),
    ("Самый высокий средний чек за месяц", 15),
    ("Обучение стажёра и помощь в сдаче аттестации", 10),
    ("Привёл друга на работу (рекомендация сотрудника)", 30),
    ("100% прохождение всех тестов на обучающей платформе", 10),
    ("Посещение всех обучающих тренингов (100% посещений)", 10),
]

DEFAULT_LEVELS = [
    (1, "Яйцечос", 50, "Ручка"),
    (2, "Халдей", 100, "Блокнот"),
    (3, "Блюдонос", 250, "Билеты в театр"),
    (4, "Офик", 500, "Билеты на концерт"),
    (5, "Старший-смотрящий", 800, "Ящик пива"),
    (6, "Дед", 1000, "Значок"),
    (7, "Маг-колдун", 1500, "Кепка"),
    (8, "Гуру сервиса", 2000, "Футболка"),
    (9, "Профик", 3000, "Толстовка"),
    (10, "Супергерой", 5000, "10000"),
]

def import_tasks_levels(db: Session) -> tuple[int, int]:
    db.execute(delete(Task)); db.execute(delete(Level))
    # tasks
    rows = None
    for path in TASKS_FILES:
        if os.path.exists(path):
            df = pd.read_excel(path, sheet_name=0)
            df.columns = [str(c).strip() for c in df.columns]
            name_col = next((c for c in df.columns if str(c).lower().startswith("название")), None)
            xp_col = next((c for c in df.columns if str(c).lower().startswith("xp")), None)
            if name_col and xp_col:
                rows = [(str(r[name_col]).strip(), _num(r[xp_col])) for _, r in df.iterrows()]
                break
    if rows is None: rows = DEFAULT_TASKS
    tasks = [Task(code=f"T{i:03d}", name=n, xp=int(x)) for i,(n,x) in enumerate(rows, start=1)]
    db.add_all(tasks)
    # levels
    lev_rows = None
    for path in LEVELS_FILES:
        if os.path.exists(path):
            df = pd.read_excel(path, sheet_name=0)
            df.columns = [str(c).strip() for c in df.columns]
            need = {
                "num": next((c for c in df.columns if str(c).lower().startswith("уровень")), None),
                "title": next((c for c in df.columns if str(c).lower().startswith("звание")), None),
                "xp_required": next((c for c in df.columns if str(c).lower().startswith("xp")), None),
                "reward": next((c for c in df.columns if str(c).lower().startswith("награда")), None),
            }
            if all(need.values()):
                lev_rows = [
                    (_num(r[need["num"]]), str(r[need["title"]]).strip(), _num(r[need["xp_required"]]), str(r[need["reward"]]).strip())
                    for _, r in df.iterrows()
                ]
                break
    if lev_rows is None: lev_rows = DEFAULT_LEVELS
    db.add_all([Level(num=int(n), title=t, xp_required=int(x), reward=r) for n,t,x,r in lev_rows])
    db.commit()
    return len(tasks), len(lev_rows)
