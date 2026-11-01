"""Доступ к данным: SQLite (модель TZ §5.3).

Таблицы: event, category, article. Инициализация, миграция, CRUD событий,
копирование события (FR-15). Streamlit не импортируется.
"""

import datetime
import os
import re
import sqlite3
from pathlib import Path

# Путь к БД можно переопределить (тесты работают с отдельным файлом,
# чтобы не затирать данные приложения: CALC_DB_PATH=/tmp/test.db)
DB_PATH = Path(
    os.environ.get("CALC_DB_PATH")
    or Path(__file__).resolve().parent / "database.db"
)

BASE_CATEGORIES = ("Площадка", "Кейтеринг", "Декор", "Ведущий")

EVENT_COLUMNS = (
    "id, name, client, date, guests, budget_limit, limit_mode, "
    "client_paid, client_paid_date, comment, plan_version, "
    "source_order_id, plan_approved, final_amount, final_date, parent_id, "
    "order_date"
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    client TEXT,
    date TEXT,
    guests INTEGER NOT NULL DEFAULT 0 CHECK (guests >= 0),
    budget_limit NUMERIC NOT NULL CHECK (budget_limit > 0),
    limit_mode TEXT NOT NULL DEFAULT 'total',
    client_paid NUMERIC NOT NULL DEFAULT 0 CHECK (client_paid >= 0),
    client_paid_date TEXT,
    comment TEXT,
    plan_version TEXT,
    source_order_id TEXT,
    plan_approved INTEGER NOT NULL DEFAULT 0 CHECK (plan_approved IN (0, 1)),
    final_amount NUMERIC CHECK (final_amount IS NULL OR final_amount >= 0),
    final_date TEXT,
    parent_id INTEGER REFERENCES event(id) ON DELETE SET NULL,
    order_date TEXT
);


CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    is_fixed INTEGER NOT NULL DEFAULT 0 CHECK (is_fixed IN (0, 1))
);

CREATE TABLE IF NOT EXISTS article (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES category(id),
    plan NUMERIC CHECK (plan IS NULL OR plan >= 0),
    fact NUMERIC NOT NULL CHECK (fact >= 0),
    comment TEXT,
    per_person INTEGER NOT NULL DEFAULT 0 CHECK (per_person IN (0, 1))
);

CREATE TABLE IF NOT EXISTS payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    amount NUMERIC NOT NULL CHECK (amount >= 0),
    date TEXT
);
"""

# Добивочные колонки для БД, созданных до появления полей (FR-2, FR-15)
_EVENT_MIGRATION = (
    ("limit_mode", "ALTER TABLE event ADD COLUMN limit_mode TEXT NOT NULL DEFAULT 'total'"),
    ("client_paid", "ALTER TABLE event ADD COLUMN client_paid NUMERIC NOT NULL DEFAULT 0"),
    ("client_paid_date", "ALTER TABLE event ADD COLUMN client_paid_date TEXT"),
    ("comment", "ALTER TABLE event ADD COLUMN comment TEXT"),
    ("plan_version", "ALTER TABLE event ADD COLUMN plan_version TEXT"),
    ("source_order_id", "ALTER TABLE event ADD COLUMN source_order_id TEXT"),
    ("final_amount", "ALTER TABLE event ADD COLUMN final_amount NUMERIC"),
    ("final_date", "ALTER TABLE event ADD COLUMN final_date TEXT"),
    ("parent_id", "ALTER TABLE event ADD COLUMN parent_id INTEGER "
                   "REFERENCES event(id) ON DELETE SET NULL"),
    ("order_date", "ALTER TABLE event ADD COLUMN order_date TEXT"),
)

# Добивочные колонки таблицы article (FR-6, FR-16)
_ARTICLE_MIGRATION = (
    ("per_person", "ALTER TABLE article ADD COLUMN per_person "
                   "INTEGER NOT NULL DEFAULT 0"),
)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Создать таблицы, выполнить миграцию и базовый справочник (BR-1)."""
    with connect() as conn:
        conn.executescript(_SCHEMA)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(event)")}
        for column, ddl in _EVENT_MIGRATION:
            if column not in existing:
                conn.execute(ddl)
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(article)")}
        for column, ddl in _ARTICLE_MIGRATION:
            if column not in existing:
                conn.execute(ddl)
        conn.executemany(
            "INSERT OR IGNORE INTO category (name, is_fixed) VALUES (?, 1)",
            [(name,) for name in BASE_CATEGORIES],
        )
        _migrate_client_paid_to_payments(conn)
        conn.commit()


def _migrate_client_paid_to_payments(conn):
    """Перенос «Внесено клиентом» (client_paid + дата) в строку платежа.

    Одноразово: события с client_paid > 0, у которых ещё нет платежей,
    получают одну строку (amount = client_paid, date = client_paid_date).
    Legacy-поля в event не трогаются (остаются для совместимости миграций).
    """
    rows = conn.execute(
        "SELECT id, client_paid, client_paid_date FROM event "
        "WHERE client_paid > 0 "
        "AND id NOT IN (SELECT DISTINCT event_id FROM payment)"
    ).fetchall()
    for row in rows:
        conn.execute(
            "INSERT INTO payment (event_id, amount, date) VALUES (?, ?, ?)",
            (row["id"], row["client_paid"], row["client_paid_date"]),
        )


def list_events():
    """Все события (для списка, FR-1)."""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM event ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_event(event_id):
    with connect() as conn:
        row = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM event WHERE id = ?",
            (event_id,),
        ).fetchone()
    return dict(row) if row else None


def create_event(
    name, client, date, guests, budget_limit,
    limit_mode="total", client_paid=0, client_paid_date=None,
    comment="", plan_version="", source_order_id="",
    final_amount=None, final_date=None,
    order_date=None,
):
    """Создать событие; возвращает новый id."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO event (name, client, date, guests, budget_limit, "
            "limit_mode, client_paid, client_paid_date, comment, plan_version, "
            "source_order_id, final_amount, final_date, order_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name, client, date, guests, budget_limit,
                limit_mode or "total", client_paid or 0, client_paid_date,
                comment, plan_version, source_order_id,
                final_amount, final_date, order_date,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def update_event(
    event_id, name, client, date, guests, budget_limit,
    limit_mode="total", client_paid=0, client_paid_date=None,
    comment="", plan_version="", source_order_id="",
    final_amount=None, final_date=None,
    order_date=None,
):
    with connect() as conn:
        conn.execute(
            "UPDATE event SET name = ?, client = ?, date = ?, guests = ?, "
            "budget_limit = ?, limit_mode = ?, client_paid = ?, "
            "client_paid_date = ?, comment = ?, plan_version = ?, "
            "source_order_id = ?, final_amount = ?, final_date = ?, order_date = ? "
            "WHERE id = ?",
            (
                name, client, date, guests, budget_limit,
                limit_mode or "total", client_paid or 0, client_paid_date,
                comment, plan_version, source_order_id,
                final_amount, final_date, order_date, event_id,
            ),
        )
        conn.commit()


def delete_event(event_id):
    """Удалить событие; статьи удаляются каскадом (NFR-6);
    привязки копий очищаются автоматически (ON DELETE SET NULL)."""
    with connect() as conn:
        conn.execute("DELETE FROM event WHERE id = ?", (event_id,))
        conn.commit()


def copies_of(event_id):
    """События-копии данного события (привязка parent_id), по убыванию id."""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM event WHERE parent_id = ? "
            "ORDER BY id DESC",
            (event_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _today_ru():
    """Сегодняшняя дата в формате отображения — дд/мм/гггг."""
    return datetime.date.today().strftime("%d/%m/%Y")


def _bump_plan_version(version):
    """«v2 от 10/10/2026» → «v3 от <сегодня>»; иначе/пусто → «v1 от <сегодня>»."""
    today = _today_ru()
    match = re.match(r"v(\d+)", version or "")
    if not match:
        return f"v1 от {today}"
    return f"v{int(match.group(1)) + 1} от {today}"


def copy_event(event_id):
    """Копия события (FR-15): независимая карточка, план статей копируется,
    факт = 0, платежи (сумма и дата) переносятся, согласование и
    окончательный расчёт не переносятся. Возвращает id копии или None."""
    with connect() as conn:
        src = conn.execute(
            f"SELECT {EVENT_COLUMNS} FROM event WHERE id = ?",
            (event_id,),
        ).fetchone()
        if not src:
            return None
        today = _today_ru()
        cursor = conn.execute(
            "INSERT INTO event (name, client, date, guests, budget_limit, "
            "limit_mode, client_paid, client_paid_date, comment, plan_version, "
            "source_order_id, plan_approved, parent_id, order_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                src["name"] + " (копия)",
                src["client"],
                src["date"],
                src["guests"],
                src["budget_limit"],
                src["limit_mode"] or "total",
                src["client_paid"] or 0,
                src["client_paid_date"],
                f"копия события «{src['name']}» от {today}",
                _bump_plan_version(src["plan_version"]),
                src["source_order_id"] or src["id"],
                0,
                src["id"],
                src["order_date"],
            ),
        )
        copy_id = cursor.lastrowid
        # FR-15: план статей копируется, факт = 0; платежи переносятся
        # как строки (уже внесённые деньги сохраняются).
        articles = conn.execute(
            "SELECT category_id, plan, comment, per_person "
            "FROM article WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        conn.executemany(
            "INSERT INTO article (event_id, category_id, plan, fact, comment, "
            "per_person) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            [
                (copy_id, art["category_id"], art["plan"], art["comment"],
                 art["per_person"])
                for art in articles
            ],
        )
        payments = conn.execute(
            "SELECT amount, date FROM payment WHERE event_id = ?",
            (event_id,),
        ).fetchall()
        conn.executemany(
            "INSERT INTO payment (event_id, amount, date) VALUES (?, ?, ?)",
            [(copy_id, pay["amount"], pay["date"]) for pay in payments],
        )
        conn.commit()
        return copy_id


def set_plan_approved(event_id, approved):
    """Согласование/разблокировка плана (BR-5)."""
    with connect() as conn:
        conn.execute(
            "UPDATE event SET plan_approved = ? WHERE id = ?",
            (1 if approved else 0, event_id),
        )
        conn.commit()


# ============================================================
# Категории (BR-1)
# ============================================================

def list_categories():
    """Справочник: базовые (is_fixed=1) первыми, затем пользовательские."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, is_fixed FROM category "
            "ORDER BY is_fixed DESC, id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_or_create_category(name):
    """id категории по имени; новая пользовательская — в общий справочник."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM category WHERE name = ?", (name,)
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO category (name, is_fixed) VALUES (?, 0)", (name,)
        )
        conn.commit()
        return cursor.lastrowid


# ============================================================
# Статьи бюджета
# ============================================================

def articles_of(event_id):
    """Статьи события с названием категории (для таблицы и итогов)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT a.id, a.event_id, a.category_id, a.plan, a.fact, a.comment, "
            "a.per_person, "
            "c.name AS category "
            "FROM article a JOIN category c ON c.id = a.category_id "
            "WHERE a.event_id = ? ORDER BY a.id",
            (event_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_article(article_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT a.id, a.event_id, a.category_id, a.plan, a.fact, a.comment, "
            "a.per_person, "
            "c.name AS category "
            "FROM article a JOIN category c ON c.id = a.category_id "
            "WHERE a.id = ?",
            (article_id,),
        ).fetchone()
    return dict(row) if row else None


def create_article(event_id, category_id, plan, fact, comment, per_person=0):
    """Создать статью; plan — None («не внесено») или число ≥ 0 (BR-4);
    per_person — признак «Тарификация на человека» (FR-16), 0/1."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO article (event_id, category_id, plan, fact, comment, "
            "per_person) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, category_id, plan, fact, comment, int(bool(per_person))),
        )
        conn.commit()
        return cursor.lastrowid


def update_article(article_id, category_id, plan, fact, comment, per_person=0):
    with connect() as conn:
        conn.execute(
            "UPDATE article SET category_id = ?, plan = ?, fact = ?, comment = ?, "
            "per_person = ? "
            "WHERE id = ?",
            (category_id, plan, fact, comment, int(bool(per_person)), article_id),
        )
        conn.commit()


def delete_article(article_id):
    with connect() as conn:
        conn.execute("DELETE FROM article WHERE id = ?", (article_id,))
        conn.commit()


def update_articles_fact(items):
    """Массовое обновление факта статей: список (id статьи, новый факт).

    Пересчёт факта переменных статей при смене числа гостей (BR-2).
    """
    if not items:
        return
    with connect() as conn:
        conn.executemany(
            "UPDATE article SET fact = ? WHERE id = ?",
            [(round(float(fact), 2), article_id) for article_id, fact in items],
        )
        conn.commit()


# ============================================================
# Платежи клиента (FR-7, блок «Оплаты»)
# ============================================================

def payments_of(event_id):
    """Платежи события в порядке добавления (строки «дата + сумма»)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, event_id, amount, date FROM payment "
            "WHERE event_id = ? ORDER BY id",
            (event_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def replace_payments(event_id, items):
    """Заменить весь список платежей события (простой путь сохранения).

    items — список dict {"amount": число, "date": ISO-строка или None}.
    Старые строки удаляются, новые вставляются одним проходом.
    """
    with connect() as conn:
        conn.execute("DELETE FROM payment WHERE event_id = ?", (event_id,))
        conn.executemany(
            "INSERT INTO payment (event_id, amount, date) VALUES (?, ?, ?)",
            [
                (event_id, round(float(p["amount"]), 2), p.get("date"))
                for p in items
            ],
        )
        conn.commit()


def payments_total(event_id):
    """Сумма всех платежей события (₽)."""
    with connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payment "
            "WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    return round(float(row["total"]), 2)
