"""Автотесты функций расчётов calc.py (этап 5, NFR-7).

Streamlit не используется. Запуск: pytest из корня проекта.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calc


def article(plan, fact, category="Площадка"):
    return {"category": category, "plan": plan, "fact": fact}


# ============================================================
# Итоги (BR-4: NULL-план ≠ 0)
# ============================================================

def test_plan_total_ignores_null():
    arts = [article(None, 100), article(200, 50)]
    assert calc.plan_total(arts) == 200


def test_plan_total_empty():
    assert calc.plan_total([]) == 0


def test_fact_total():
    arts = [article(100, 10.1), article(None, 20.2)]
    assert calc.fact_total(arts) == 30.3  # 30.300000000000004 → 30.3


# ============================================================
# Лимит (BR-2)
# ============================================================

def test_limit_balance():
    assert calc.limit_balance(100000, 90000) == 10000
    assert calc.limit_balance(100000, 110000) == -10000
    assert calc.limit_balance(None, 50) == -50


def test_limit_total_mode_total():
    assert calc.limit_total(150000, 25, "total") == 150000


def test_limit_total_mode_per_guest():
    assert calc.limit_total(3000, 10, "perGuest") == 30000


def test_per_guest_zero_guests_is_none():
    assert calc.per_guest(100000, 0) is None
    assert calc.per_guest(100000, None) is None


def test_per_guest():
    assert calc.per_guest(140000, 50) == 2800


# ============================================================
# Разбор ввода сумм
# ============================================================

def test_parse_amount_empty_optional():
    assert calc.parse_amount("  ") == (True, None)  # план «не внесено»


def test_parse_amount_empty_required():
    assert calc.parse_amount("", required=True) == (False, None)  # факт обязателен


def test_parse_amount_valid():
    assert calc.parse_amount("1200,5") == (True, 1200.5)  # запятая — разделитель дробной части
    assert calc.parse_amount("1200.5") == (True, 1200.5)
    assert calc.parse_amount("0") == (True, 0.0)


def test_parse_amount_invalid():
    assert calc.parse_amount("-5") == (False, None)
    assert calc.parse_amount("abc") == (False, None)


def test_parse_amount_thousand_separators():
    assert calc.parse_amount("150 000") == (True, 150000.0)
    assert calc.parse_amount("150\u00a0000") == (True, 150000.0)
    assert calc.parse_amount("1 250 000,5") == (True, 1250000.5)
    assert calc.parse_amount("1 2") == (False, None)  # разряды не по 3 — мусор
    assert calc.parse_amount("12 345 6") == (False, None)


def test_format_amount_input():
    assert calc.format_amount_input("150000") == "150\u00a0000"
    assert calc.format_amount_input("150 000") == "150\u00a0000"  # пробелы → неразрывные
    assert calc.format_amount_input("1250000,5") == "1\u00a0250\u00a0000,5"
    assert calc.format_amount_input("150000.0") == "150\u00a0000"
    assert calc.format_amount_input("1200.50") == "1\u00a0200,5"
    assert calc.format_amount_input("1200.5") == "1\u00a0200,5"
    assert calc.format_amount_input("999") == "999"
    assert calc.format_amount_input("") == ""
    assert calc.format_amount_input("abc") == "abc"  # мусор не переписываем
    assert calc.format_amount_input("-5") == "-5"


def test_format_amount_input_roundtrip():
    for raw in ("150000", "150 000", "1250000,5", "0", "1200.5"):
        ok, value = calc.parse_amount(calc.format_amount_input(raw))
        assert ok
        assert value == calc.parse_amount(raw)[1]


# ============================================================
# Отклонение статьи и правила перерасхода (BR-3, BR-4)
# ============================================================

def test_article_delta():
    assert calc.article_delta(100, 150) == -50
    assert calc.article_delta(100, 50) == 50
    assert calc.article_delta(None, 150) is None  # без плана — «—»
    assert calc.article_delta(0, 0) == 0  # явный ноль плана


def test_articles_over():
    arts = [
        article(100, 150),   # перерасход 50
        article(None, 999),  # без плана — не считается
        article(200, 200),   # ровно план — не считается
        article(0, 15000),   # явный план 0 — перерасход 15000 (BR-4)
    ]
    total, count = calc.articles_over(arts)
    assert total == 15050
    assert count == 2


def test_articles_under():
    arts = [
        article(100, 50),    # экономия 50
        article(None, 1),    # без плана — не считается
        article(200, 200),   # ровно план
    ]
    total, count = calc.articles_under(arts)
    assert total == 50
    assert count == 1


# ============================================================
# Деньги клиента (FR-7)
# ============================================================

def test_remain_to_pay():
    assert calc.remain_to_pay(140000, 50000) == 90000
    assert calc.remain_to_pay(145000, 50000) == 95000
    assert calc.remain_to_pay(30000, 50000) == -20000  # внесено больше


def test_remain_to_pay_empty_paid():
    assert calc.remain_to_pay(100000, 0) == 100000
    assert calc.remain_to_pay(100000, None) == 100000


# ============================================================
# Сводка (FR-7): эталонные числа демо-события
# ============================================================

DEMO_ARTS = [
    article(40000, 45000, "Площадка"),
    article(55000, 50000, "Кейтеринг"),
    article(25000, 15000, "Декор"),
    article(20000, 20000, "Ведущий"),
    article(0, 15000, "Фотограф"),
]


def test_build_summary_demo():
    s = calc.build_summary(150000, 50, DEMO_ARTS)
    assert s["plan_total"] == 140000
    assert s["fact_total"] == 145000
    assert s["balance_plan"] == 10000
    assert s["balance_fact"] == 5000
    assert s["deviation_plan_limit"] == -10000  # план 140000 − лимит 150000
    assert s["plan_per_guest"] == 2800
    assert s["fact_per_guest"] == 2900
    assert s["deviation"] == 5000
    assert s["deviation_limit"] == -5000  # факт 145000 − лимит 150000
    assert s["over_total"] == 20000  # Площадка 5000 + Фотограф 15000
    assert s["over_count"] == 2
    assert s["under_total"] == 15000
    assert s["under_count"] == 2
    assert s["articles_count"] == 5
    assert s["remain_plan"] == 140000
    assert s["remain_fact"] == 145000
    assert s["remain_limit"] == 150000  # лимит − внесено (0)


def test_build_summary_with_client_paid():
    s = calc.build_summary(150000, 50, DEMO_ARTS, client_paid=50000)
    assert s["client_paid"] == 50000
    assert s["remain_plan"] == 90000
    assert s["remain_fact"] == 95000
    assert s["remain_limit"] == 100000  # лимит 150000 − 50000


# ============================================================
# Оплаты клиента (FR-7): несколько платежей
# ============================================================

def test_payments_remain_clamps_overpayment():
    # Остаток к оплате не уходит в минус: переплата — отдельной подписью
    assert calc.payments_remain(50000, 30000) == 20000
    assert calc.payments_remain(50000, 50000) == 0
    assert calc.payments_remain(50000, 70000) == 0
    assert calc.payments_remain(None, None) == 0


def test_payments_over_amount():
    # Сумма переплаты — отдельный показатель (FR-7): её видно в подписи
    assert calc.payments_over(50000, 30000) == 0
    assert calc.payments_over(50000, 50000) == 0
    assert calc.payments_over(50000, 70000) == 20000
    assert calc.payments_over(None, None) == 0


def test_payments_note_states():
    over_note = "согласованная переплата +" + calc.format_money(20000)
    # Колонка «факт»: при полной оплате — «Полностью оплачено»
    assert calc.payments_note(50000, 30000, "Полностью оплачено") == ""
    assert calc.payments_note(50000, 50000, "Полностью оплачено") == "Полностью оплачено"
    # Переплата фиксируется суммой: +20 000 ₽ видно в подписи
    assert calc.payments_note(50000, 70000, "Полностью оплачено") == over_note
    # Факт 0 и ничего не внесено — подписывать нечего
    assert calc.payments_note(0, 0, "Полностью оплачено") == ""
    # Колонка «Лимит»: подпись только при переплате
    assert calc.payments_note(700000, 700000) == ""
    assert calc.payments_note(700000, 715000) == (
        "согласованная переплата +" + calc.format_money(15000)
    )


def test_build_summary_payments_notes():
    # Полная оплата факта: лимит ещё не выбран
    s = calc.build_summary(150000, 50, DEMO_ARTS, client_paid=145000)
    assert s["remain_fact_note"] == "Полностью оплачено"
    assert s["remain_limit_note"] == ""
    assert s["remain_limit"] == 5000
    # Переплата и по факту, и по лимиту: суммы видно в подписях (FR-7)
    s_over = calc.build_summary(150000, 50, DEMO_ARTS, client_paid=160000)
    assert s_over["remain_fact_note"] == (
        "согласованная переплата +" + calc.format_money(15000)
    )  # внесено 160000 − факт 145000
    assert s_over["remain_limit_note"] == (
        "согласованная переплата +" + calc.format_money(10000)
    )  # внесено 160000 − лимит 150000
    assert s_over["remain_fact"] == 0
    assert s_over["remain_limit"] == 0


def test_build_summary_remain_plan_not_negative():
    """«Осталось внести по плану» тоже не уходит в минус (FR-7)."""
    arts = [article(100000, 105000)]
    s = calc.build_summary(150000, 0, arts, client_paid=110000)
    assert s["remain_plan"] == 0
    assert s["remain_plan_note"] == (
        "согласованная переплата +" + calc.format_money(10000)
    )
    # Без переплаты подписи нет, остаток считается как раньше
    s_ok = calc.build_summary(150000, 0, arts, client_paid=40000)
    assert s_ok["remain_plan"] == 60000
    assert s_ok["remain_plan_note"] == ""


def test_build_summary_over_limit():
    arts = [article(200000, 200000)]
    s = calc.build_summary(150000, 0, arts)
    assert s["balance_plan"] == -50000
    assert s["balance_fact"] == -50000
    assert s["deviation_plan_limit"] == 50000  # план превышает лимит
    assert s["deviation_limit"] == 50000  # перерасход лимита: красный в шапке
    assert s["plan_per_guest"] is None
    assert s["fact_per_guest"] is None


# ============================================================
# График (FR-9): агрегация по категориям
# ============================================================

def test_chart_data_aggregates_and_sorts():
    arts = [
        article(100, 500, "Декор"),
        article(200, 300, "Площадка"),
        article(50, 200, "Декор"),  # та же категория — суммируется
    ]
    rows = calc.chart_data(arts)
    assert rows[0] == {"category": "Декор", "plan": 150.0, "fact": 700.0}
    assert rows[1] == {"category": "Площадка", "plan": 200.0, "fact": 300.0}


def test_chart_data_drops_zero_rows():
    arts = [article(None, 0, "Пустая"), article(0, 0, "Нулевая")]
    assert calc.chart_data(arts) == []


def test_chart_data_null_plan_counts_zero():
    arts = [article(None, 15000, "Фотограф")]
    rows = calc.chart_data(arts)
    assert rows == [{"category": "Фотограф", "plan": 0.0, "fact": 15000.0}]


# ============================================================
# Форматирование денег
# ============================================================

def test_format_money():
    def norm(value):
        return calc.format_money(value).replace(" ", " ")

    assert calc.format_money(None) == "—"
    assert norm(120000) == "120 000 ₽"
    assert norm(120000.5) == "120 000,5 ₽"
    assert norm(-10000) == "-10 000 ₽"
    assert norm(0) == "0 ₽"


# ============================================================
# CSV-отчёт (FR-11)
# ============================================================

def test_report_rows_structure():
    event = {"name": "Демо", "client": "Мария", "date": "2026-11-14",
             "guests": 25, "budget_limit": 150000,
             "client_paid_date": "2026-10-01",
             "final_amount": 145000, "final_date": "2026-11-14"}
    arts = [
        article(40000, 45000, "Площадка"),
        article(None, 5000, "Фотограф"),
    ]
    payments = [
        {"amount": 15000, "date": "2026-10-01"},
        {"amount": 5000, "date": "2026-10-15"},
    ]
    s = calc.build_summary(150000, 25, arts, client_paid=20000)
    rows = calc.report_rows(event, s, arts, payments)
    assert rows[0] == ["Демо"]
    assert ["Клиент", "Мария"] in rows
    assert ["Дата", "14/11/2026"] in rows
    assert ["Гостей", 25] in rows
    assert ["Категория", "План", "Факт", "Отклонение", "Статус", "Комментарий"] in rows
    assert ["Площадка", 40000, 45000, -5000, "Перерасход", ""] in rows
    assert ["Фотограф", "", 5000, "", "Статья без плана", ""] in rows
    assert ["Итого план", 40000] in rows
    assert ["Итого факт", 50000] in rows
    assert ["Остаток лимита (план)", 110000] in rows
    assert ["Остаток лимита (факт)", 100000, ""] in rows
    assert ["На гостя (план)", 1600.0] in rows
    assert ["На гостя (факт)", 2000.0] in rows
    # Блок «ОПЛАТЫ» (FR-7): две колонки «Лимит»/«факт», платежи построчно
    assert ["ОПЛАТЫ"] in rows
    assert ["", "Лимит", "факт"] in rows
    assert ["К оплате", 150000, 50000] in rows
    assert ["Внесено итого", 20000.0, ""] in rows
    assert ["Платёж", 15000, "01/10/2026"] in rows
    assert ["Платёж", 5000, "15/10/2026"] in rows
    assert ["Остаток в пределах лимита", 130000, ""] in rows
    assert ["Осталось внести по факту", "", 30000.0] in rows
    assert ["Осталось внести по плану", 20000.0] in rows
    assert ["Перерасход по статьям", 5000, "у 1 из 2 статей"] in rows
    assert ["Экономия по статьям", "—", ""] in rows


def test_report_rows_without_payments():
    """Отчёт без платежей: «Внесено итого» 0, лимит из event."""
    event = {"name": "X", "client": "", "date": None, "guests": 0,
             "budget_limit": 100}
    arts = [article(50, 40)]
    s = calc.build_summary(100, 0, arts)
    rows = calc.report_rows(event, s, arts)
    assert ["К оплате", 100, 40] in rows
    assert ["Внесено итого", 0.0, ""] in rows
    assert ["Остаток в пределах лимита", 100, ""] in rows
    assert ["Осталось внести по факту", "", 40.0] in rows


def test_report_rows_payments_notes():
    """Подписи переплаты и полной оплаты — строкой под остатками (FR-7)."""
    event = {"name": "X", "client": "", "date": None, "guests": 0,
             "budget_limit": 100}
    arts = [article(None, 100)]
    # Переплата и по лимиту (100 → 120), и по факту (100 → 120):
    # подписи фиксируют сумму переплаты +20 ₽
    s = calc.build_summary(100, 0, arts, client_paid=120)
    rows = calc.report_rows(event, s, arts, [{"amount": 120, "date": "2026-10-01"}])
    over_note = "согласованная переплата +" + calc.format_money(20)
    assert ["", over_note, over_note] in rows
    # Полная оплата факта при неполном лимите: подпись только в колонке «факт»
    event_full = dict(event, budget_limit=150)
    s_full = calc.build_summary(150, 0, arts, client_paid=100)
    rows_full = calc.report_rows(
        event_full, s_full, arts, [{"amount": 100, "date": "2026-10-01"}]
    )
    assert ["", "", "Полностью оплачено"] in rows_full


def test_report_rows_payments_order_matches_sample():
    """Порядок блока «ОПЛАТЫ» — как в образце клиента (FR-7)."""
    event = {"name": "X", "client": "", "date": None, "guests": 0,
             "budget_limit": 150}
    arts = [article(100, 100)]
    s = calc.build_summary(150, 0, arts, client_paid=50)
    rows = calc.report_rows(
        event, s, arts, [{"amount": 50, "date": "2026-10-20"}]
    )
    start = rows.index(["ОПЛАТЫ"])
    labels = [r[0] for r in rows[start:] if r and r[0]]
    assert labels == [
        "ОПЛАТЫ",
        "К оплате",
        "Внесено итого",
        "Платёж",
        "Остаток в пределах лимита",
        "Осталось внести по плану",
        "Осталось внести по факту",
        "Перерасход по статьям",
        "Экономия по статьям",
    ]


def test_report_rows_over_limit_flag():
    event = {"name": "X", "client": "", "date": None, "guests": 0, "budget_limit": 100}
    arts = [article(150, 200)]
    s = calc.build_summary(100, 0, arts)
    rows = calc.report_rows(event, s, arts)
    assert ["Остаток лимита (факт)", -100, "перерасход лимита"] in rows


# ============================================================
# Калькулятор (FR-12)
# ============================================================

def test_calc_sum():
    s = calc.calc_new_state()
    for key in ("1", "2", "+", "3", "4", "="):
        s = calc.calc_press(s, key)
    assert calc.calc_result(s) == 46
    assert calc.calc_display(s) == "46"


def test_calc_multiply_with_comma():
    s = calc.calc_new_state()
    for key in ("2", ",", "5", "×", "4", "="):
        s = calc.calc_press(s, key)
    assert calc.calc_result(s) == 10


def test_calc_division_by_zero():
    s = calc.calc_new_state()
    for key in ("5", "÷", "0", "="):
        s = calc.calc_press(s, key)
    assert s["error"] is True
    assert calc.calc_display(s) == "Деление на 0"
    assert calc.calc_result(s) is None
    # после сбоя калькулятор снова работает
    s = calc.calc_press(s, "C")
    assert calc.calc_display(s) == "0"


def test_calc_backspace_and_clear():
    s = calc.calc_new_state()
    for key in ("1", "2", "3", "back"):
        s = calc.calc_press(s, key)
    assert calc.calc_result(s) == 12
    s = calc.calc_press(s, "C")
    assert calc.calc_result(s) == 0


def test_calc_float_protection():
    s = calc.calc_new_state()
    for key in ("0", ",", "1", "+", "0", ",", "2", "="):
        s = calc.calc_press(s, key)
    assert calc.calc_result(s) == 0.3  # не 0.30000000000000004


def test_calc_set_number_keyboard():
    s = calc.calc_new_state()
    s = calc.calc_set_number(s, "12 500,50")
    assert calc.calc_result(s) == 12500.5
    assert calc.calc_display(s) == "12500,5"
    s2 = calc.calc_set_number(s, "мусор")
    assert s2 == s  # мусор игнорируется


def test_calc_command_sum_equals():
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "12500,50 + 3500 =")
    assert ok
    assert calc.calc_result(s) == 16000.5
    assert calc.calc_display(s) == "16000,5"


def test_calc_command_auto_equals():
    # «=» в конце не обязателен: результат считается сразу
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "12500,50 + 3500")
    assert ok
    assert calc.calc_result(s) == 16000.5
    assert calc.calc_display(s) == "16000,5"
    # «100 + 50» сразу даёт 150; повторный «=» — no-op
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "100 + 50")
    assert ok and calc.calc_result(s) == 150
    s, ok = calc.calc_parse_command(s, "=")
    assert ok and calc.calc_result(s) == 150


def test_calc_command_single_operator_and_spaces():
    s = calc.calc_press(calc.calc_new_state(), "1")
    s = calc.calc_press(s, "2")
    s, ok = calc.calc_parse_command(s, "+")
    assert ok and s["op"] == "+"  # операция в конце ждёт число
    s, ok = calc.calc_parse_command(s, "12 500")
    assert ok and calc.calc_result(s) == 12512  # пробелы + авто-=


def test_calc_command_clear_and_back():
    s, ok = calc.calc_parse_command(calc.calc_press(calc.calc_new_state(), "9"), "C")
    assert ok and calc.calc_result(s) == 0
    s, ok = calc.calc_parse_command(calc.calc_press(calc.calc_new_state(), "9"), "стереть")
    assert ok and calc.calc_result(s) == 0  # до нуля → сброс ввода
    s = calc.calc_press(calc.calc_new_state(), "1")
    s = calc.calc_press(s, "2")
    s, ok = calc.calc_parse_command(s, "⌫")
    assert ok and calc.calc_result(s) == 1


def test_calc_command_division_by_zero_and_star_slash():
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "10/0=")
    assert ok and s["error"] is True
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "3 * 4 =")
    assert ok and calc.calc_result(s) == 12
    s, ok = calc.calc_parse_command(calc.calc_new_state(), "3×4=")
    assert ok and calc.calc_result(s) == 12


def test_calc_command_garbage_ignored():
    s = calc.calc_press(calc.calc_new_state(), "5")
    s2, ok = calc.calc_parse_command(s, "abc")
    assert not ok and s2 == s
    s2, ok = calc.calc_parse_command(s, "5++")
    assert ok  # двойной плюс не ломает: вторая операция перезаписывает op
    s2, ok = calc.calc_parse_command(s, "")
    assert not ok and s2 == s


# ============================================================
# Сценарий «Расчёт на гостя» (FR-16) и пересчёт лимита (FR-3)
# ============================================================

def sc_article(aid, plan, fact, category="Площадка", per_person=0):
    return {"id": aid, "category": category, "plan": plan, "fact": fact,
            "per_person": per_person}


# Статьи события «Юбилей Олега» (пример менеджера): лимит 77000
SC_ARTS = [
    sc_article(1, 56700, 59400, "Банкетное обслуживание", per_person=1),
    sc_article(2, 5000, 4500, "Декор"),
    sc_article(3, 5000, 5000, "Фотограф"),
    sc_article(4, 10000, 12000, "Ведущий"),
]


def test_scenario_fixed_only_base_fact():
    # база «Факт», признак «на человека» не проставлен ни у одной статьи
    arts = [
        sc_article(1, 56700, 59400, "Банкетное обслуживание"),
        sc_article(2, 5000, 4500, "Декор"),
    ]
    result = calc.scenario_totals(arts, 25, base="fact", limit_value=77000)
    assert result["fixed_total"] == 63900  # 59400 + 4500
    assert result["variable_total"] == 0
    assert result["total"] == 63900
    assert result["deviation_limit"] == -13100  # 63900 − 77000
    assert result["deviation_base"] == 0
    assert result["missing_tariffs"] == []


def test_scenario_variable_recalc_example():
    # Банкетное обслуживание — переменная статья, тариф 2500 ₽/чел
    result = calc.scenario_totals(
        SC_ARTS, 25, base="fact", tariffs={1: 2500}, limit_value=77000,
    )
    rows = {r["id"]: r for r in result["rows"]}
    assert rows[1]["value"] == 62500  # 2500 × 25
    assert rows[1]["base_value"] == 59400  # текущий факт для сравнения
    assert result["variable_total"] == 62500
    assert result["fixed_total"] == 21500  # 4500 + 5000 + 12000
    assert result["total"] == 84000
    assert result["per_guest"] == 3360  # 84000 ÷ 25
    assert result["deviation_limit"] == 7000  # 84000 − 77000
    assert result["deviation_base"] == 3100  # 84000 − 80900 (текущий факт)


def test_scenario_base_plan_and_null_plan():
    arts = SC_ARTS + [sc_article(5, None, 900, "Фотограф2")]
    result = calc.scenario_totals(arts, 25, base="plan", tariffs={1: 2500})
    rows = {r["id"]: r for r in result["rows"]}
    assert rows[2]["value"] == 5000  # фикс-статья берёт план
    assert rows[5]["no_plan"] is True
    assert rows[5]["value"] is None  # NULL-план — «не внесено», в итог не входит
    assert result["fixed_total"] == 20000  # 5000 + 5000 + 10000
    assert result["total"] == 82500  # 62500 + 20000
    assert result["base_total"] == 76700  # итог плана (NULL не даёт вклада)
    assert result["deviation_base"] == 5800


def test_scenario_zero_guests():
    result = calc.scenario_totals(SC_ARTS, 0, base="fact", tariffs={1: 2500})
    assert result["per_guest"] is None  # «—», BR-2
    rows = {r["id"]: r for r in result["rows"]}
    assert rows[1]["value"] == 0  # тариф × 0
    assert result["total"] == 21500  # только фикс-часть


def test_scenario_missing_tariff():
    result = calc.scenario_totals(SC_ARTS, 25, base="fact")  # тариф не задан
    rows = {r["id"]: r for r in result["rows"]}
    assert rows[1]["missing_tariff"] is True
    assert rows[1]["value"] is None
    assert result["missing_tariffs"] == [1]
    assert result["total"] == 21500  # переменная статья не входит в итог


def test_scenario_invalid_input():
    import pytest
    with pytest.raises(ValueError):
        calc.scenario_totals(SC_ARTS, -1)
    with pytest.raises(ValueError):
        calc.scenario_totals(SC_ARTS, 25, base="total")


def test_recalculated_limit():
    assert calc.recalculated_limit(3000, 10) == 30000
    assert calc.recalculated_limit(3000.5, 3) == 9001.5
    assert calc.recalculated_limit(None, 10) == 0
    assert calc.recalculated_limit(3000, 0) == 0


# ============================================================
# Пересчёт переменных статей при смене числа гостей (BR-2)
# ============================================================

def var_article(art_id, plan, fact, per_person=1):
    return {
        "id": art_id, "category": "Кейтеринг", "plan": plan, "fact": fact,
        "per_person": per_person,
    }


def test_rescaled_fact_keeps_rate():
    assert calc.rescaled_fact(100000, 40, 50) == 125000
    assert calc.rescaled_fact(60000, 40, 20) == 30000
    assert calc.rescaled_fact(0, 40, 50) == 0


def test_rescaled_fact_rounds_to_two_decimals():
    assert calc.rescaled_fact(10000, 3, 4) == 13333.33


def test_rescaled_fact_without_guests_is_none():
    assert calc.rescaled_fact(100000, 0, 50) is None
    assert calc.rescaled_fact(100000, 40, 0) is None
    assert calc.rescaled_fact(None, 40, 50) is None


def test_rescale_variable_articles_only_variable():
    arts = [
        var_article(1, 100000, 100000),
        var_article(2, 50000, 50000, per_person=0),
    ]
    assert calc.rescale_variable_articles(arts, 40, 50) == [(1, 125000)]


def test_rescale_variable_articles_skips_unchanged():
    arts = [var_article(1, 100000, 100000)]
    assert calc.rescale_variable_articles(arts, 40, 40) == []


def test_rescale_variable_articles_without_guests():
    arts = [var_article(1, 100000, 100000)]
    assert calc.rescale_variable_articles(arts, 0, 50) == []
    assert calc.rescale_variable_articles(arts, 40, 0) == []


# ============================================================
# Формат даты — дд/мм/гггг
# ============================================================

def test_format_date():
    assert calc.format_date("2026-11-14") == "14/11/2026"
    assert calc.format_date("2026-01-05") == "05/01/2026"
    assert calc.format_date("2026-12-31") == "31/12/2026"


def test_format_date_empty():
    assert calc.format_date("") == ""
    assert calc.format_date(None) == ""
