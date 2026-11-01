"""Демо-событие для быстрой проверки интерфейса.

Запуск из корня проекта:
    python seed_demo.py

Создаёт событие «Демо-день рождения» с заполненными статьями.
Если такое событие уже есть — удаляет старое и создаёт заново.
"""

import db


def main():
    db.init_db()
    for ev in db.list_events():
        if ev["name"] == "Демо-день рождения":
            db.delete_event(ev["id"])

    event_id = db.create_event(
        name="Демо-день рождения",
        client="Иванова Мария",
        date="2026-11-14",
        guests=50,
        budget_limit=150000,
    )

    articles = [
        ("Площадка", 40000, 45000, "Переплата за доп. час"),
        ("Кейтеринг", 55000, 50000, ""),
        ("Декор", 25000, 15000, ""),
        ("Ведущий", 20000, 20000, "Ещё не оплачен"),
        ("Фотограф", 0, 15000, "Договорились без плана"),
    ]
    for category, plan, fact, comment in articles:
        category_id = db.get_or_create_category(category)
        db.create_article(event_id, category_id, plan, fact, comment)

    print(f"Готово: демо-событие id={event_id}, статей: {len(articles)}")


if __name__ == "__main__":
    main()
