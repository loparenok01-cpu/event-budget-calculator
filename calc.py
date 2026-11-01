"""Чистые функции расчётов бюджета (TZ, NFR-7).

Streamlit ЗАПРЕЩЁНО импортировать. Тестируются pytest (этап 5).
NULL-план не равен 0: в сумму входит как 0, но отдельно помечается (BR-4).
"""

import re


def plan_total(articles):
    """Итог плана: NULL-планы («не внесено») не дают вклада в сумму."""
    return round(sum((a.get("plan") or 0) for a in articles), 2)


def fact_total(articles):
    """Итог факта (факт обязателен по каждой статье, BR-4)."""
    return round(sum((a.get("fact") or 0) for a in articles), 2)


def limit_balance(limit_value, total):
    """Остаток лимита = лимит − сумма (план или факт, в зависимости от total)."""
    return round((limit_value or 0) - (total or 0), 2)


def limit_total(limit_value, guests, mode="total"):
    """Общий лимит события: режим «на гостя» — только способ ввода (BR-2)."""
    limit = round(float(limit_value or 0), 2)
    if mode == "perGuest":
        return round(limit * (guests or 0), 2)
    return limit


def per_guest(total, guests):
    """Стоимость на гостя; при 0 гостей — None (отображается «—», BR-2)."""
    if not guests or guests <= 0:
        return None
    return round((total or 0) / guests, 2)


_AMOUNT_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
_AMOUNT_GROUPED_RE = re.compile(r"^\d{1,3}(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?$")
_AMOUNT_SPACES = " \u00a0\u202f"


def _clean_amount_text(raw):
    """Нормализованный текст суммы: разряды убраны, запятая → точка.

    None — текст не похож на сумму (ошибка ввода).
    """
    text = str(raw).strip()
    if not text:
        return None
    if _AMOUNT_GROUPED_RE.match(text):
        for space in _AMOUNT_SPACES:
            text = text.replace(space, "")
    elif not _AMOUNT_RE.match(text):
        return None
    return text.replace(",", ".")


def parse_amount(raw, required=False):
    """Разбор суммы ввода: (ok, value).

    Пусто: при required=False → (True, None) — план «не внесено» (BR-4);
    при required=True → (False, None) — факт обязателен.
    Принимаются разделители разрядов (пробел, неразрывный пробел) и
    запятая как десятичный разделитель. Число ≥ 0 валидно, округляется
    до 0,01 ₽; иначе (False, None).
    """
    trimmed = str(raw).strip()
    if trimmed == "":
        return (False, None) if required else (True, None)
    cleaned = _clean_amount_text(trimmed)
    if cleaned is None:
        return False, None
    try:
        value = float(cleaned)
    except ValueError:
        return False, None
    if value != value or value in (float("inf"), float("-inf")) or value < 0:
        return False, None
    return True, round(value, 2)


def format_amount_input(raw):
    """Сумма для поля ввода: разряды через неразрывный пробел (150 000).

    Мусор возвращается как есть — покажем ошибку валидации (FR-6).
    """
    text = str(raw).strip()
    if not text:
        return ""
    cleaned = _clean_amount_text(text)
    if cleaned is None:
        return text
    integer, _, frac = cleaned.partition(".")
    frac = frac.rstrip("0")
    groups = []
    while len(integer) > 3:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    groups.insert(0, integer)
    out = "\u00a0".join(groups)
    if frac:
        out += "," + frac
    return out


def article_delta(plan, fact):
    """Отклонение статьи: план − факт; план NULL → None (BR-3, BR-4).

    Минус — перерасход; при NULL-плане отклонение не считается («—»).
    """
    if plan is None:
        return None
    return round(plan - (fact or 0), 2)


def articles_over(articles):
    """Перерасход по статьям (BR-3): (сумма, количество).

    Считаются только статьи с внесённым планом и фактом > плана.
    """
    overs = [
        a for a in articles
        if a.get("plan") is not None and (a.get("fact") or 0) > a["plan"]
    ]
    total = round(sum((a["fact"] or 0) - a["plan"] for a in overs), 2)
    return total, len(overs)


def articles_under(articles):
    """Экономия по статьям: (сумма, количество) — факт ниже внесённого плана."""
    unders = [
        a for a in articles
        if a.get("plan") is not None and (a.get("fact") or 0) < a["plan"]
    ]
    total = round(sum(a["plan"] - (a["fact"] or 0) for a in unders), 2)
    return total, len(unders)


def remain_to_pay(total, client_paid):
    """Сколько ещё внести: итог − уже внесённые деньги клиента (FR-7).

    Отрицательное — «внесено больше плана/факта».
    """
    return round((total or 0) - (client_paid or 0), 2)


def payments_remain(base_total, paid_total):
    """Остаток к оплате (FR-7, блок «Оплаты»): max(база − внесено, 0).

    base_total — база колонки: лимит («Остаток в пределах лимита») или
    итог факта («Осталось внести по факту»). Переплата не уходит в минус:
    показывается 0, а сам факт переплаты — подписью payments_note.
    """
    remain = round((base_total or 0) - (paid_total or 0), 2)
    return remain if remain > 0 else 0


def payments_over(base_total, paid_total):
    """Сумма переплаты (FR-7): max(внесено − база, 0).

    Переплата фиксируется визуально: её сумма показывается в подписи
    остатка («согласованная переплата +10 000 ₽»), а не только нулём.
    """
    over = round((paid_total or 0) - (base_total or 0), 2)
    return over if over > 0 else 0


def payments_note(base_total, paid_total, fully_label=""):
    """Подпись под остатком оплат (FR-7, колонки «Лимит»/«факт»).

    «согласованная переплата +N ₽» — внесено больше базы (лимита или
    факта), N — сумма переплаты; fully_label — подпись при полной оплате
    (колонка «факт» — «Полностью оплачено»); без fully_label полная
    оплата подписью не отмечается (колонка «Лимит»).
    """
    over = payments_over(base_total, paid_total)
    if over > 0:
        return f"согласованная переплата +{format_money(over)}"
    diff = round((base_total or 0) - (paid_total or 0), 2)
    if diff == 0 and (paid_total or 0) > 0 and fully_label:
        return fully_label
    return ""


def build_summary(limit_value, guests, articles, client_paid=0):
    """Сводка события (FR-7) — единый источник для карточек, таблицы и графика (NFR-8)."""
    plan_sum = plan_total(articles)
    fact_sum = fact_total(articles)
    over_sum, over_count = articles_over(articles)
    under_sum, under_count = articles_under(articles)
    paid = round(float(client_paid or 0), 2)
    return {
        "plan_total": plan_sum,
        "fact_total": fact_sum,
        "balance_plan": limit_balance(limit_value, plan_sum),
        "balance_fact": limit_balance(limit_value, fact_sum),
        "plan_per_guest": per_guest(plan_sum, guests),
        "fact_per_guest": per_guest(fact_sum, guests),
        "deviation": round(fact_sum - plan_sum, 2),
        "deviation_limit": round(fact_sum - (limit_value or 0), 2),
        "deviation_plan_limit": round(plan_sum - (limit_value or 0), 2),
        "client_paid": paid,
        "remain_plan": payments_remain(plan_sum, paid),
        "remain_plan_note": payments_note(plan_sum, paid),
        "remain_limit": payments_remain(limit_value, paid),
        "remain_limit_note": payments_note(limit_value, paid),
        "remain_fact": payments_remain(fact_sum, paid),
        "remain_fact_note": payments_note(fact_sum, paid, "Полностью оплачено"),
        "over_total": over_sum,
        "over_count": over_count,
        "under_total": under_sum,
        "under_count": under_count,
        "articles_count": len(articles),
    }


# ============================================================
# Режим «Расчёт на гостя» (FR-16) и согласованный пересчёт (FR-3)
# ============================================================

def scenario_totals(articles, guests, base="fact", tariffs=None, limit_value=None):
    """Сценарий «Расчёт на гостя» (FR-16): показ варианта при числе гостей N.

    articles — строки статей (plan, fact, per_person);
    guests — число гостей сценария (целое ≥ 0);
    base — база фикс-статей: "fact" (по умолчанию) или "plan";
    tariffs — dict {article_id: тариф ₽/чел} для статей с per_person;
    limit_value — лимит события для отклонения (или None).

    Переменные статьи (per_person): значение = тариф × N; фикс-статьи:
    значение из бюджета по базе. План NULL при базе "plan" — «не внесено»,
    в итог не входит (BR-4); тариф не задан — статья в итог не входит,
    помечается в missing_tariffs. Ничего не пишет в БД (BR-2).
    """
    if base not in ("fact", "plan"):
        raise ValueError("База сценария — «Факт» или «План»")
    n = int(guests)
    if n < 0:
        raise ValueError("Число гостей сценария ≥ 0")
    tariffs = tariffs or {}
    rows = []
    for article in articles:
        rate = tariffs.get(article.get("id"))
        is_variable = bool(article.get("per_person"))
        base_value = article.get(base)
        base_value = None if base_value is None else round(float(base_value), 2)
        row = {
            "id": article.get("id"),
            "category": article.get("category") or "",
            "is_variable": is_variable,
            "base_value": base_value,
            "rate": None if rate is None else round(float(rate), 2),
            "value": None,
            "no_plan": False,
            "missing_tariff": False,
        }
        if is_variable:
            if rate is None:
                row["missing_tariff"] = True
            else:
                row["value"] = round(float(rate) * n, 2)
        else:
            if base == "plan" and base_value is None:
                row["no_plan"] = True  # «не внесено» — в итог не входит
            else:
                row["value"] = base_value if base_value is not None else 0.0
        rows.append(row)

    fixed_total = round(
        sum(r["value"] for r in rows if not r["is_variable"] and r["value"] is not None),
        2,
    )
    variable_total = round(
        sum(r["value"] for r in rows if r["is_variable"] and r["value"] is not None),
        2,
    )
    total = round(fixed_total + variable_total, 2)
    if base == "fact":
        base_total = fact_total(articles)
    else:
        base_total = plan_total(articles)
    return {
        "rows": rows,
        "guests": n,
        "base": base,
        "fixed_total": fixed_total,
        "variable_total": variable_total,
        "total": total,
        "per_guest": per_guest(total, n),
        "base_total": base_total,
        "deviation_base": round(total - base_total, 2),
        "deviation_limit": (
            None if limit_value is None
            else round(total - (limit_value or 0), 2)
        ),
        "missing_tariffs": [r["id"] for r in rows if r["missing_tariff"]],
    }


def recalculated_limit(rate, guests):
    """Согласованный пересчёт лимита (FR-3): ставка ₽/гость × новые гости."""
    return round((rate or 0) * (guests or 0), 2)


def rescaled_fact(fact, old_guests, new_guests):
    """Пересчёт факта переменной статьи при смене числа гостей (BR-2).

    Ставка ₽/чел сохраняется: новый факт = факт ÷ старые гости × новые гости.
    None — пересчёт невозможен: гостей не было (0), их не стало (0) или
    факт не задан.
    """
    if fact is None:
        return None
    if not old_guests or old_guests <= 0:
        return None
    if not new_guests or new_guests <= 0:
        return None
    return round((float(fact) / old_guests) * new_guests, 2)


def rescale_variable_articles(articles, old_guests, new_guests):
    """Пересчёт факта переменных статей (per_person = 1) при смене гостей.

    Возвращает список (id статьи, новый факт) — только для изменившихся
    сумм. Планы, лимит и фикс-статьи не меняются (BR-2, BR-5).
    """
    updates = []
    for art in articles:
        if not art.get("per_person"):
            continue
        new_fact = rescaled_fact(art.get("fact"), old_guests, new_guests)
        if new_fact is None:
            continue
        if round(float(art.get("fact") or 0), 2) != new_fact:
            updates.append((art["id"], new_fact))
    return updates


def chart_data(articles):
    """Агрегат по категориям для графика (FR-9): [{category, plan, fact}].

    NULL-план участвует как 0 (BR-4); строки с нулевым планом и фактом
    отбрасываются — на диаграмме они не видны. Сортировка — по факту убыв.
    """
    grouped = {}
    for article in articles:
        name = article.get("category") or "Без категории"
        row = grouped.setdefault(name, {"plan": 0.0, "fact": 0.0})
        row["plan"] += article.get("plan") or 0
        row["fact"] += article.get("fact") or 0
    rows = [
        {"category": name, "plan": round(vals["plan"], 2), "fact": round(vals["fact"], 2)}
        for name, vals in grouped.items()
        if vals["plan"] > 0 or vals["fact"] > 0
    ]
    rows.sort(key=lambda r: r["fact"], reverse=True)
    return rows


# ============================================================
# CSV-отчёт (FR-11): строки из summary (NFR-8), без streamlit
# ============================================================

def report_rows(event, summary, articles, payments=None):
    """Строки отчёта CSV (FR-11): шапка события, статьи, итоги, оплаты.

    event — dict события, summary — build_summary(...), articles — строки
    статей, payments — список платежей (dict с amount и date). Блок «Оплаты»
    в отчёте повторяет вид экрана клиента (FR-7).
    """
    payments = payments or []
    date = format_date(event.get("date"))
    rows = [
        [event.get("name") or ""],
        ["Клиент", event.get("client") or ""],
        ["Дата", date or ""],
        ["Гостей", event.get("guests")],
        ["Лимит", event.get("budget_limit")],
        [],
        ["Категория", "План", "Факт", "Отклонение", "Статус", "Комментарий"],
    ]
    for article in articles:
        plan = article.get("plan")
        fact = article.get("fact") or 0
        delta = article_delta(plan, fact)
        if plan is None:
            status = "Статья без плана"
        elif fact > plan:
            status = "Перерасход"
        elif fact < plan:
            status = "Экономия"
        else:
            status = "В норме"
        rows.append([
            article.get("category") or "",
            "" if plan is None else plan,
            article.get("fact"),
            "" if delta is None else delta,
            status,
            article.get("comment") or "",
        ])
    rows.append([])
    plan_pg = summary["plan_per_guest"]
    fact_pg = summary["fact_per_guest"]
    over_sum, over_count = summary["over_total"], summary["over_count"]
    under_sum, under_count = summary["under_total"], summary["under_count"]
    articles_count = summary["articles_count"]
    rows.extend([
        ["Итого план", summary["plan_total"]],
        ["Итого факт", summary["fact_total"]],
        ["Остаток лимита (план)", summary["balance_plan"]],
        ["Остаток лимита (факт)", summary["balance_fact"],
         "перерасход лимита" if summary["balance_fact"] < 0 else ""],
        ["На гостя (план)", plan_pg if plan_pg is not None else "—"],
        ["На гостя (факт)", fact_pg if fact_pg is not None else "—"],
    ])
    # Блок «ОПЛАТЫ» — две колонки «Лимит»/«факт» (FR-7, макет «Режим Оплаты»)
    rows.append([])
    rows.append(["ОПЛАТЫ"])
    rows.append(["", "Лимит", "факт"])
    rows.append(["К оплате", event.get("budget_limit"), summary["fact_total"]])
    rows.append(["Внесено итого", summary["client_paid"], ""])
    for pay in payments:
        rows.append(["Платёж", pay.get("amount"), format_date(pay.get("date"))])
    rows.append(["Остаток в пределах лимита", summary["remain_limit"], ""])
    rows.append(["Осталось внести по плану", summary["remain_plan"]])
    rows.append(["Осталось внести по факту", "", summary["remain_fact"]])
    # Подписи состояния: одна и та же переплата не дублируется, если лимит
    # и план совпадают (как в интерфейсе); подпись плана — отдельной строкой
    limit_note = summary["remain_limit_note"]
    if limit_note == summary["remain_plan_note"]:
        limit_note = ""
    if limit_note or summary["remain_fact_note"]:
        rows.append(["", limit_note, summary["remain_fact_note"]])
    if summary["remain_plan_note"]:
        rows.append(["", summary["remain_plan_note"], ""])
    rows.extend([
        ["Перерасход по статьям", over_sum if over_sum > 0 else "—",
         f"у {over_count} из {articles_count} статей" if over_sum > 0 else ""],
        ["Экономия по статьям", under_sum if under_sum > 0 else "—",
         f"у {under_count} из {articles_count} статей" if under_sum > 0 else ""],
    ])
    return rows


# ============================================================
# Калькулятор (FR-12): чистая логика, состояние — dict
# ============================================================

def calc_new_state():
    """Начальное состояние калькулятора."""
    return {"acc": None, "op": None, "cur": "0", "fresh": True, "error": False}


def calc_display(state):
    """Строка дисплея: «Деление на 0» или текущий ввод (запятая как разделитель)."""
    if state["error"]:
        return "Деление на 0"
    return state["cur"].replace(".", ",")


def calc_result(state):
    """Числовой результат для копирования; при ошибке/пустоте — None."""
    if state["error"]:
        return None
    try:
        return float(state["cur"])
    except ValueError:
        return None


def calc_set_number(state, raw):
    """Ввод числа с клавиатуры (FR-12): пробел/запятая → точка; мусор игнорируется."""
    text = str(raw).strip().replace(" ", "").replace(",", ".")
    if not text:
        return state
    try:
        value = float(text)
    except ValueError:
        return state
    if value != value or value in (float("inf"), float("-inf")):
        return state
    return {"acc": state["acc"], "op": state["op"],
            "cur": f"{value:.12g}", "fresh": False, "error": False}


_CMD_PART = re.compile(
    r"\d+(?:[.,]\d+)?|[.,]\d+"          # число: 12, 12.5, 12,5, .5
    r"|[+\-*/×÷=]"                       # операции
    r"|[A-Za-zА-Яа-яЁё]+"               # команды словами (C, сброс, back…)
    r"|⌫"                                # символ стирания
)


def calc_parse_command(state, text):
    """Командная строка калькулятора (FR-12): ввод числа и действий без мыши.

    Разбирает ввод вида «12500,50 + 3500», «+», «C», «стереть», «=».
    Если команда заканчивается числом при ожидающей операции — «=»
    подставляется автоматически, результат виден сразу («12500,50 + 3500»
    → 16000,5). Пробелы внутри числа убираются («12 500» → 12500).
    Возвращает (new_state, ok): ok=False — мусор, состояние не меняется.
    """
    text = (text or "").strip().replace(" ", "")
    if not text:
        return state, False
    parts = _CMD_PART.findall(text)
    if not parts or "".join(parts) != text:
        return state, False  # есть неразобранный мусор
    s = state
    for part in parts:
        low = part.lower()
        if re.fullmatch(r"\d+(?:[.,]\d+)?|[.,]\d+", part):
            s = calc_set_number(s, part)
        elif part == "+":
            s = calc_press(s, "+")
        elif part in ("-", "−"):
            s = calc_press(s, "−")
        elif part in ("*", "×"):
            s = calc_press(s, "×")
        elif part in ("/", "÷"):
            s = calc_press(s, "÷")
        elif part == "=":
            s = calc_press(s, "=")
        elif low in ("c", "с", "сброс", "reset"):
            s = calc_press(s, "C")
        elif low in ("back", "стереть", "⌫"):
            s = calc_press(s, "back")
        else:
            return state, False
    # Команда заканчивается числом при ожидающей операции → считаем сразу
    if s["op"] is not None and not s["fresh"] and not s["error"]:
        s = calc_apply_op(s)
    return s, True


def calc_apply_op(state):
    """Применить ожидающую операцию к acc и текущему числу."""
    if state["op"] is None or state["acc"] is None or state["error"]:
        return state
    a = state["acc"]
    b = float(state["cur"])
    op = state["op"]
    if op == "+":
        result = a + b
    elif op == "−":
        result = a - b
    elif op == "×":
        result = a * b
    else:  # "÷"
        if b == 0:
            return {"acc": None, "op": None, "cur": state["cur"],
                    "fresh": True, "error": True}
        result = a / b
    # Защита от 0.1 + 0.2: округление до 12 значащих цифр
    return {"acc": None, "op": None, "cur": f"{round(result, 12):.12g}",
            "fresh": True, "error": False}


def calc_press(state, key):
    """Обработка нажатия кнопки калькулятора (FR-12); возвращает новое состояние.

    Клавиши: '0'–'9', ',', '+', '−', '×', '÷', '=', 'C', 'back'.
    """
    if key == "C":
        return calc_new_state()
    if state["error"]:
        return state
    s = dict(state)
    if key == "back":
        if s["fresh"]:
            return s
        cur = s["cur"][:-1] if len(s["cur"]) > 1 else "0"
        s["cur"] = cur
        if cur == "0":
            s["fresh"] = True
    elif key == ",":
        if s["fresh"]:
            s["cur"] = "0."
            s["fresh"] = False
        elif "." not in s["cur"]:
            s["cur"] += "."
    elif len(key) == 1 and key.isdigit():
        if s["fresh"]:
            s["cur"] = key
            s["fresh"] = False
        elif len(s["cur"].replace("-", "").replace(".", "")) < 15:
            s["cur"] = key if s["cur"] == "0" else s["cur"] + key
    elif key in ("+", "−", "×", "÷"):
        if s["op"] is not None and not s["fresh"]:
            s = calc_apply_op(s)
        if not s["error"]:
            s["acc"] = float(s["cur"])
            s["op"] = key
            s["fresh"] = True
    elif key == "=":
        s = calc_apply_op(s)
    return s


def format_money(value):
    """120000 → «120 000 ₽», 120000.5 → «120 000,5 ₽»; None → «—»."""
    if value is None:
        return "—"
    rounded = round(float(value), 2)
    if rounded == int(rounded):
        num = f"{int(rounded):,}".replace(",", "\u00a0")
    else:
        whole, _, frac = f"{rounded:.2f}".rstrip("0").rstrip(".").partition(".")
        num = f"{int(whole):,}".replace(",", "\u00a0") + "," + frac
    return f"{num}\u00a0₽"


def format_date(value):
    """Дата из БД (ISO «ГГГГ-ММ-ДД») → «ДД/ММ/ГГГГ»; пусто — пустая строка."""
    if not value:
        return ""
    year, month, day = value.split("-")
    return f"{day}/{month}/{year}"
