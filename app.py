"""Калькулятор бюджета события — интерфейс (Streamlit).

Только отображение и вызовы db.py / calc.py (TZ, §5.5).
"""

import csv
import datetime
import html
import io

import plotly.graph_objects as go
import streamlit as st

import calc
import db

st.set_page_config(page_title="Калькулятор бюджета события", layout="wide")

# Визуальный стиль (NFR-9): спокойная палитра по образцу «Обложка2»,
# единые радиусы, карточки, заметное главное действие, состояния
# наведения/фокуса, короткие анимации. Внешние библиотеки, шрифты,
# изображения и API не используются — только CSS и системные шрифты.
APP_CSS = """
:root{
  --ap-gold:#A8802F;
  --ap-gold-soft:#E9DFC7;
  --ap-ink:#3B372F;
  --ap-mute:#5A564A;
  --ap-blue:#1C6DC1;
  --ap-line:#E5E0D2;
  --ap-card:#FFFDF8;
  --ap-current:#FFF8E9;
  --ap-radius:12px;
  --ap-t:.18s ease;
  --ap-shadow:0 1px 3px rgba(59,55,47,.07);
  --ap-shadow-h:0 6px 18px rgba(59,55,47,.12);
}

/* --- Крупная обложка (входной экран списка) --- */
.ap-hero{
  position:relative; overflow:hidden;
  margin:4px 0 18px; padding:54px 46px;
  border-radius:var(--ap-radius);
  background:
    radial-gradient(420px 260px at 10% 15%, rgba(255,255,255,.95), transparent 70%),
    radial-gradient(380px 300px at 88% 10%, rgba(255,246,214,.9), transparent 70%),
    radial-gradient(500px 320px at 75% 95%, rgba(223,244,230,.9), transparent 72%),
    radial-gradient(360px 260px at 18% 100%, rgba(253,236,220,.85), transparent 72%),
    linear-gradient(112deg,#FFFBEB 0%,#FFF7DA 45%,#EAF7EE 100%);
  box-shadow:var(--ap-shadow);
  animation:ap-rise .4s ease both;
}
.ap-hero__title{
  font-family:Georgia,"Times New Roman",serif;
  font-size:clamp(34px,4.4vw,52px);
  line-height:1.15; color:#9A752C; letter-spacing:.5px;
  text-shadow:0 1px 0 rgba(255,255,255,.7);
}
.ap-hero__sub{
  margin-top:10px; font-size:21px; color:#57544A; max-width:60ch;
}
.ap-hero__spark{
  position:absolute; top:16px; right:26px;
  font-size:22px; color:var(--ap-gold); opacity:.65;
  letter-spacing:16px;
  animation:ap-twinkle 3.2s ease-in-out infinite;
}
@keyframes ap-rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes ap-twinkle{50%{opacity:.3}}

/* --- Ограниченная ширина текста --- */
p,li,[data-testid="stCaptionContainer"]{max-width:78ch}
[data-testid="stCaptionContainer"]{color:var(--ap-mute)}

/* --- Иерархия заголовков: serif задаётся темой (headingFont),
       подписи групп — мягкие, с разрядкой --- */
h4{color:var(--ap-mute);letter-spacing:.03em}

/* --- Единые радиусы карточек (bordered-контейнеры Streamlit) --- */
div:has(> [data-testid="stVerticalBlock"]){border-radius:var(--ap-radius)}

/* --- Метрики как карточки --- */
[data-testid="stMetric"]{
  background:linear-gradient(180deg,#FFFDF7,#FBF7EC);
  border:1px solid var(--ap-line);
  border-radius:var(--ap-radius);
  padding:12px 16px;
  transition:border-color var(--ap-t),box-shadow var(--ap-t);
}
[data-testid="stMetric"]:hover{
  border-color:var(--ap-gold-soft); box-shadow:var(--ap-shadow);
}
[data-testid="stMetricLabel"]{color:var(--ap-mute);font-size:15px}
[data-testid="stMetricValue"]{color:var(--ap-ink)}

/* --- Кнопки: единый радиус, состояния наведения --- */
[data-testid="stBaseButton"]{
  border-radius:var(--ap-radius);
  transition:box-shadow var(--ap-t),transform var(--ap-t),
             background-color var(--ap-t),border-color var(--ap-t);
}
[data-testid="stBaseButton-secondary"]{
  background:var(--ap-card); border:1px solid var(--ap-line);
}
[data-testid="stBaseButton-secondary"]:hover{
  border-color:var(--ap-gold-soft);
  box-shadow:var(--ap-shadow);
  filter:brightness(1.02);
}
/* --- Подсказка кнопки «Домой»: всплывающая по наведению ---
   Встроенная подсказка Streamlit живёт в портале с position:fixed и
   после клика (перерисовка) не закрывается — остаётся на экране.
   Своя подсказка на CSS: появляется при наведении и исчезает, когда
   курсор уходит; знак «?» — как у Streamlit, но без залипания */
.st-key-btn-home [data-testid="stButton"]{position:relative; z-index:2}
.st-key-btn-home [data-testid="stButton"]::before{
  content:"?";
  position:absolute; right:9px; top:50%; transform:translateY(-50%);
  width:18px; height:18px; border-radius:50%;
  background:var(--ap-gold-soft); color:#6E5417;
  font-size:12px; line-height:18px; text-align:center;
  pointer-events:none;
}
.st-key-btn-home [data-testid="stButton"]::after{
  content:"Вернуться на главный экран";
  position:absolute; left:0; bottom:calc(100% + 8px); z-index:30;
  padding:6px 10px; border-radius:8px;
  background:var(--ap-ink); color:#FFFDF8;
  font-size:14px; line-height:1.2; white-space:nowrap;
  opacity:0; visibility:hidden; pointer-events:none;
  transition:opacity var(--ap-t),visibility var(--ap-t);
}
.st-key-btn-home [data-testid="stButton"]:hover::after{
  opacity:1; visibility:visible;
}

/* Скачивание CSV — как второстепенное действие, но заметное */
[data-testid="stDownloadButton"]{
  background:var(--ap-card); border:1px solid var(--ap-line);
}
[data-testid="stDownloadButton"]:hover{
  border-color:var(--ap-gold-soft);
  box-shadow:var(--ap-shadow);
}
/* Заметное главное действие — «Создать событие» */
[data-testid="stBaseButton-primary"]{
  padding:11px 28px; font-size:18px; font-weight:600;
  box-shadow:0 2px 6px rgba(168,128,47,.32);
}
[data-testid="stBaseButton-primary"]:hover{
  transform:translateY(-1px);
  box-shadow:0 6px 16px rgba(168,128,47,.38);
}
[data-testid="stBaseButton-primary"]:active{transform:translateY(0)}

/* --- Фокус и поля ввода --- */
:focus-visible{outline:2px solid var(--ap-gold); outline-offset:2px}
[data-testid="stTextInput"],[data-testid="stNumberInput"],
[data-testid="stDateInput"],[data-testid="stSelectbox"]{
  transition:box-shadow var(--ap-t);
}
[data-testid="stTextInput"]:focus-within,[data-testid="stNumberInput"]:focus-within,
[data-testid="stDateInput"]:focus-within,[data-testid="stSelectbox"]:focus-within{
  box-shadow:0 0 0 3px rgba(168,128,47,.18);
  border-radius:var(--ap-radius);
}
/* Ссылки: наведение — темнее золота, подчёркивание из темы */
a:hover{color:#8A6A22}

/* --- Строки таблицы статей и карточки событий — как кнопки (NFR-9) --- */
/* Селектор выбирает обёртку строки (метка .ap-row-mark); от контейнера
   страницы защищает :not(...). ВАЖНО: перенос строки внутри селектора
   создаёт десцендентный комбинатор — :not() пишем в той же строке */
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark, .ap-head-mark):not([data-testid="stMainBlockContainer"]){
  padding:10px 16px;
}
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]){
  background:var(--ap-card);
  border:1px solid var(--ap-line);
  border-radius:var(--ap-radius);
  box-shadow:var(--ap-shadow);
  transition:box-shadow var(--ap-t),border-color var(--ap-t),
             background-color var(--ap-t),transform var(--ap-t);
}
/* Текущая строка: открытое событие, редактируемая статья */
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-current):not([data-testid="stMainBlockContainer"]){
  background:var(--ap-current);
  border-color:#D9C08A;
  box-shadow:0 0 0 1px rgba(168,128,47,.30), var(--ap-shadow);
}
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]):hover{
  background:#FFFDF1;
  border-color:#D9C08A;
  box-shadow:var(--ap-shadow-h);
  transform:translateY(-1px);
}
.ap-row-mark,.ap-row-current,.ap-head-mark,.ap-meta-mark{display:none}
/* Якорь мгновенного перехода к форме статьи (UI): не занимает места */
.ap-anchor{display:block;height:0;scroll-margin-top:12px}

/* --- Адаптив таблицы статей (NFR-9): узкий контейнер → подпись в ячейке --- */
/* Ориентир — ширина контейнера страницы, а не окна: работает и со
   свёрнутым сайдбаром. Широкий вид даёт шапка таблицы, узкий — подписи
   .ap-cl внутри ячеек (категория — заголовок карточки, ниже пары значений) */
[data-testid="stMainBlockContainer"]{container-type:inline-size}
.ap-cl{
  display:none;
  margin-right:6px;
  color:var(--ap-mute);
  font-weight:600;
  font-size:.85em;
}
.ap-cl--calc{color:var(--ap-blue)}
/* FR-6: расчётный тариф ₽/чел под суммой переменной статьи */
.ap-rate{
  display:block;
  margin-top:1px;
  font-size:.8em;
  font-weight:500;
  color:var(--ap-mute);
  white-space:nowrap;
}
@container (max-width:820px){
  /* шапка скрыта — подписи живут в ячейках */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-head-mark):not([data-testid="stMainBlockContainer"]){display:none}
  .ap-cl{display:inline}
  /* строка-карточка: категории-заголовок на всю ширину, ниже — пары;
     селектор находит только ячейки строки (в ячейках есть .ap-cl),
     вложенные колонки кнопок действий не затрагиваются */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl){
    column-gap:8px;
    row-gap:6px;
  }
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]{
    flex:1 1 calc(50% - 4px);
    min-width:0;
  }
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:first-child{
    flex-basis:100%;
  }
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:last-child{
    flex-basis:100%;
  }
  /* в режиме сценария (7 ячеек) комментарий — отдельной строкой */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(7)) > [data-testid="stColumn"]:nth-child(6){
    flex-basis:100%;
  }
  /* плотность строк: без двойных отступов абзацев */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stMarkdownContainer"] p{
    margin:0;
  }
  /* у stMarkdownContainer отрицательный нижний отступ (-1rem) гасит
     стандартный margin абзаца; при margin:0 у p ячейка схлопывалась
     на 18px и текст налезал на следующую строку */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stMarkdownContainer"]{
    margin-bottom:0;
  }
  /* категория — заголовок карточки */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:first-child [data-testid="stMarkdownContainer"] p{
    font-size:19px;
    font-weight:700;
    color:var(--ap-ink);
  }
}
/* Широкий режим (контейнер >820px; запрос строго complementary к узкому
   max-width:820, чтобы не было мёртвой зоны на дробных ширинах — на ней
   gap оставался 18px и шапка «Отклонение» переносилась): зазор колонок
   18px → 8px, иначе шапка (Отклонение=100px) и значения не помещаются */
@container (width > 820px){
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-head-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]{
    column-gap:8px;
  }
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl){
    column-gap:8px;
  }
  /* min-width:0 — без него колонка кнопок (min-content кнопок с
     nowrap) забирает ~7px у соседей, и комментарий переносился */
  div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]{
    min-width:0;
  }
}
/* кнопки действий строк статей: компактные и всегда в одну строку
   (в узком и широком режимах — иначе текст кнопок обрезается) */
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]{
  column-gap:8px;
}
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{
  /* basis=max-content: кнопка «Изменить» (90px) не влезала в половину при
     50/50 — колонки растут от натуральной ширины кнопок */
  flex:1 1 max-content;
  min-width:0;
}
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) > [data-testid="stVerticalBlock"] [data-testid^="stBaseButton"]{
  padding:5px 8px;
  font-size:14px;
  white-space:nowrap;
  /* натуральная ширина: колонка подстраивается под кнопку, а не наоборот */
  width:auto;
}

/* Группы кнопок действий («Изменить/Копировать/Удалить», подтверждение
   удаления, кнопки платежей). Признак группы — кнопка в первой колонке:
   у внешней строки (Клиент · Дата · Факт) в первой колонке кнопки нет,
   поэтому её раскладка 3/2/2 не затрагивается.

   Колонка = натуральной ширине своей кнопки (min-width:auto не даёт ей
   сжаться ниже текста) и растёт от неё: кнопки стоят в ряд, пока хватает
   места, и переносятся целиком, когда не хватает — наезда не бывает */
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid^="stBaseButton"]){
  flex-wrap:wrap;
  column-gap:6px;
  row-gap:8px;
}
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid^="stBaseButton"]) > [data-testid="stColumn"],
div:has(> [data-testid="stVerticalBlock"]):has(.ap-row-mark):not([data-testid="stMainBlockContainer"]) [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-cl) > [data-testid="stColumn"]:last-child [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:first-child [data-testid^="stBaseButton"]) > [data-testid="stColumn"]{
  /* колонка не уже своей кнопки (Streamlit ставит min-width:0 — из-за этого
     кнопки сжимались и наезжали); при нехватке места колонка переносится */
  flex:1 1 max-content;
  min-width:max-content;
}

/* --- Адаптивная шапка метрик бюджета (NFR-9): полное имя клиента и суммы
   без многоточия. Скрытая метка .ap-meta-mark (колонка «ID») помечает строку
   метрик: flex-колонки Streamlit заменяются сеткой с весами; перенос текста
   вместо nowrap+ellipsis у value/label/delta метрик --- */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark){
  /* !important — на случай inline display у Streamlit (проверено пробой:
     в 1.66 display задан классом, но защиты от регрессии не бывает много) */
  display:grid !important;
  column-gap:18px;
  row-gap:14px;
}
/* маркер — только сигнал для селекторов; контейнер его markdown скрыт,
   иначе в колонке «ID» остаётся пустая строка сверху */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMarkdownContainer"]:has(.ap-meta-mark){
  display:none;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) > [data-testid="stColumn"]{
  /* min-width:0 — гасит media-правило Streamlit «стек в 1 строку» (иначе
     колонка с min-width:calc(100%-27px) не влезает в ячейку сетки);
     width:auto — гасит width:calc(share% - 18px) у .stColumn: в сетке
     процент считается от дорожки (404*16.7% - 18 = 49px) и колонки
     схлопывались до 4–49px вместо растяжения на всю дорожку */
  min-width:0 !important;
  width:auto !important;
}
/* у метрик Streamlit — nowrap+ellipsis; вместо многоточия — перенос */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricLabel"],
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricLabel"] *,
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricValue"],
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricValue"] *,
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricDelta"],
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricDelta"] *{
  white-space:normal;
  overflow:visible;
  text-overflow:clip;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricValue"],
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricValue"] *{
  /* суммы разделены неразрывными пробелами — без anywhere ячейка
     переполняется, а браузер сам ищет место для переноса */
  overflow-wrap:anywhere;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) [data-testid="stMetricLabel"] *{
  overflow-wrap:break-word;
}
/* Тиры по ширине контейнера: 6 в ряд (>=1240), 3 в ряд (754–1239),
   2 в ряд (496–753), 1 в ряд (<496). Веса fr: «Клиент» ~1/3 ширины —
   имя читается в 2–3 строки; денег хватает на 6 цифр и ₽ */
@container (width >= 1240px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark){
    grid-template-columns:10fr 31fr 10fr 17.5fr 13.5fr 18fr;
  }
}
@container (width >= 754px) and (width < 1240px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark){
    grid-template-columns:1fr 1.6fr 1fr;
  }
}
@container (width >= 496px) and (width < 754px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark){
    grid-template-columns:1fr 1fr;
  }
}
@container (width < 496px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark){
    grid-template-columns:1fr;
  }
}
/* Заметка FR-7: широкий контейнер (>=754) — полной строкой под метриками,
   узкий — caption в колонке «Лимит» (как было) */
[data-testid="stMarkdownContainer"]:has(.ap-meta-note){display:none}
@container (width >= 754px){
  [data-testid="stMarkdownContainer"]:has(.ap-meta-note){display:block}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .ap-meta-mark) > [data-testid="stColumn"]:nth-child(4) [data-testid="stCaptionContainer"]{
    display:none;
  }
}
.ap-meta-note{
  color:var(--ap-mute);
  font-size:15.75px;
  margin:0;
}

/* --- Плавное появление блоков при переключении экранов и строк --- */
[data-testid="stMainBlockContainer"] > div > *{
  animation:ap-fade .22s ease both;
}
/* только opacity: transform в fill-mode блокировал бы подъём строки
   при наведении (animation перекрывает обычные свойства) */
@keyframes ap-fade{from{opacity:0;transform:translateY(4px)}to{opacity:1}}

/* --- «На гостя» в группах ПЛАН/ФАКТ — увеличенный акцент (NFR-9) --- */
.ap-pg{
  font-size:16px; color:var(--ap-mute);
  margin:4px 0 8px;
}
.ap-pg__v{
  display:inline-block;
  font-size:clamp(16px, 3.2vw, 32px); font-weight:650; line-height:1.15;
  color:var(--ap-blue);
  overflow-wrap:anywhere;
}

/* --- Оплата по факту (FR-7): выделение цветом и размером шрифта --- */
.ap-pay-fact{
  font-size:16px;
  margin:6px 0 2px;
}
.ap-pay-fact__l{color:var(--ap-mute);}
.ap-pay-fact__l--red{color:#B3423B; font-weight:600;}
.ap-pay-fact__v{
  display:inline-block;
  font-size:clamp(16px, 3.2vw, 32px); font-weight:650; line-height:1.15;
  color:var(--ap-mute);
  overflow-wrap:anywhere;
}
.ap-pay-fact__v--red{color:#B3423B;}
.ap-pay-fact__v--mute{font-size:20px;}
.ap-pay-note{
  font-size:20px; font-weight:650; line-height:1.25;
  color:#2F7A4D;
  margin:2px 0 8px;
}

/* --- Группа «ОПЛАТЫ» (FR-7): две колонки «Лимит»/«факт» по образцу.
   Сетка (не таблица): строки сжимаются на узких карточках без выезда
   за край. Строки, отмеченные в образце, подсвечены мягким фоном
   (var(--ap-current)) --- */
.ap-pay-wrap{container-type:inline-size;}
.ap-pay{
  display:grid;
  margin:2px 0 4px;
  font-size:13.5px;
}
.ap-pay__row{
  display:grid;
  grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr) minmax(0,.85fr);
  border-top:1px solid var(--ap-line);
}
.ap-pay__head{border-top:0;}
.ap-pay__head .ap-pay__h{
  padding:0 4px 4px; text-align:right;
  font-size:12px; font-weight:600; color:var(--ap-mute);
}
.ap-pay__head .ap-pay__h:first-child{text-align:left;}
.ap-pay__l{
  padding:3px 4px; color:var(--ap-mute);
  overflow-wrap:anywhere;
}
.ap-pay__l--red{color:#B3423B; font-weight:600;}
.ap-pay__v{
  padding:3px 4px; text-align:right;
  font-variant-numeric:tabular-nums;
  /* суммы с неразрывными пробелами переносятся, а не распирают колонку */
  overflow-wrap:anywhere;
}
.ap-pay__row--hl{background:var(--ap-current);}
/* Остаток по факту: значение шире колонки «факт» — сумма с ₽ не переносится */
.ap-pay__v--wide{grid-column:2 / -1;}
.ap-pay__note{
  border-top:0; padding:0 4px 4px;
  font-size:12px; color:var(--ap-mute);
}
.ap-pay__n{grid-column:1 / -1;}
.ap-pay__note .ap-pay-note{
  margin:0; font-size:15px;
}
/* Крупное значение остатка по факту масштабируется по ширине карточки:
   сумма с ₽ — единый неразрывный токен (calc.format_money), поэтому
   уменьшение шрифта гарантирует одну строку */
.ap-pay-wrap .ap-pay-fact__v{
  font-size:clamp(11px, 10cqw, 32px);
}
/* Узкая карточка: подпись отдельной строкой, суммы — двумя колонками */
@container (width < 260px){
  .ap-pay{font-size:12.5px;}
  .ap-pay__row{grid-template-columns:minmax(0,1fr) minmax(0,1fr);}
  .ap-pay__l{grid-column:1 / -1; padding-bottom:0;}
  .ap-pay__v--wide{grid-column:1 / -1;}
  .ap-pay__head span:empty{display:none;}
}

/* --- Перерасход/экономия по статьям (BR-3) — мягкий фон, как в образце --- */
.ap-ou{
  background:var(--ap-current);
  border-radius:10px;
  padding:8px 10px;
  margin:6px 0 4px;
  font-size:14px;
}
.ap-ou__r{
  display:flex; justify-content:space-between;
  gap:8px; align-items:baseline;
  flex-wrap:wrap;
}
.ap-ou__l{color:var(--ap-mute); min-width:0;}
.ap-ou__v{
  font-weight:650; overflow-wrap:anywhere;
}
.ap-ou__v--red{color:#B3423B;}
.ap-ou__v--green{color:#2F7A4D;}
.ap-ou__c{font-size:12px; color:var(--ap-mute); margin:0 0 4px;}

/* --- Уважение к настройке «уменьшенное движение» --- */
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
}
"""

st.markdown(f"<style>{APP_CSS}</style>", unsafe_allow_html=True)

db.init_db()

SCREENS = ["Список событий", "Бюджет события", "Сводка с графиком"]

ART_PLACEHOLDER = "— выберите —"
ART_OTHER = "Другое…"


def _format_money_field(key):
    """Разряды в поле суммы: 150000 → 150 000 (FR-6)."""
    st.session_state[key] = calc.format_amount_input(st.session_state.get(key, ""))


def _amount_value(key, default=None):
    """Сумма из поля формы (строка с разрядами) → число; None — пусто или мусор."""
    ok, value = calc.parse_amount(st.session_state.get(key, ""), required=False)
    if not ok:
        return default
    return value


if "screen" not in st.session_state:
    st.session_state.screen = SCREENS[0]
if "selected_event_id" not in st.session_state:
    st.session_state.selected_event_id = None
if "nav_back" not in st.session_state:
    # id события-источника перехода «открыть прообраз» — для кнопки
    # «← Вернуться в копию» (FR-15)
    st.session_state.nav_back = None
if "show_event_form" not in st.session_state:
    st.session_state.show_event_form = False
if "event_errors" not in st.session_state:
    st.session_state.event_errors = []
if "event_notice" not in st.session_state:
    st.session_state.event_notice = None
if "budget_notice" not in st.session_state:
    st.session_state.budget_notice = None
if "art_form_open" not in st.session_state:
    st.session_state.art_form_open = False
if "art_edit_id" not in st.session_state:
    st.session_state.art_edit_id = None
if "art_errors" not in st.session_state:
    st.session_state.art_errors = []
if "art_confirm_delete" not in st.session_state:
    st.session_state.art_confirm_delete = None
if "unlock_confirm" not in st.session_state:
    st.session_state.unlock_confirm = False
if "ev_edit_id" not in st.session_state:
    st.session_state.ev_edit_id = None
if "ev_confirm_delete" not in st.session_state:
    st.session_state.ev_confirm_delete = None

if st.session_state.pop("art_reset", False):
    st.session_state.art_category = ART_PLACEHOLDER
    st.session_state.art_cat_search = ""
    st.session_state.art_custom = ""
    st.session_state.art_plan = ""
    st.session_state.art_fact = ""
    st.session_state.art_comment = ""
    st.session_state.art_per_person = False
    st.session_state.art_rate = ""
    st.session_state.art_rate_fact = ""
    st.session_state.art_errors = []
    st.session_state.art_edit_id = None

for _key, _default in (
    ("art_category", ART_PLACEHOLDER),
    ("art_cat_search", ""),
    ("art_custom", ""),
    ("art_plan", ""),
    ("art_fact", ""),
    ("art_comment", ""),
    ("art_per_person", False),
    ("art_rate", ""),
    ("art_rate_fact", ""),
):
    if _key not in st.session_state:
        st.session_state[_key] = _default

if st.session_state.pop("reset_event_form", False):
    st.session_state.ev_name = ""
    st.session_state.ev_client = ""
    st.session_state.ev_order_date = None
    st.session_state.ev_date = None
    st.session_state.ev_guests = 0
    st.session_state.ev_limit_mode = "Всего"
    st.session_state.ev_limit = ""
    st.session_state.ev_payments = []
    st.session_state.ev_comment = ""
    st.session_state.ev_plan_version = ""
    st.session_state.ev_source_id = ""
    st.session_state.ev_recalc_limit = False
    st.session_state.event_errors = []
    st.session_state.ev_edit_id = None
    # виджеты платежей (key ev_pay_*) снимаются следующим ререном (UI)
    st.session_state.clear_pay_widgets = True


for _key, _default in (
    ("ev_name", ""),
    ("ev_client", ""),
    ("ev_order_date", None),
    ("ev_date", None),
    ("ev_guests", 0),
    ("ev_limit_mode", "Всего"),
    ("ev_limit", ""),
    ("ev_payments", []),
    ("ev_comment", ""),
    ("ev_plan_version", ""),
    ("ev_source_id", ""),
    ("ev_recalc_limit", False),
):
    if _key not in st.session_state:
        st.session_state[_key] = _default

# FR-14: Streamlit сбрасывает значение неактивного виджета (экрана с полем
# поиска нет). Запрос храним в не-виджетном ev_search_store; восстанавливаем,
# если предыдущий ререн был не на списке (сброс сделала система, а не
# пользователь). Очистка пользователем на самом списке не трогается.
if st.session_state.get("_last_render_screen") != "Список событий":
    st.session_state["ev_search"] = st.session_state.get("ev_search_store", "")

st.sidebar.title("Калькулятор бюджета")


def _go_home():
    """Возврат на главный экран из любого места (сброс выбора и форм)."""
    st.session_state.screen = SCREENS[0]
    st.session_state.selected_event_id = None
    st.session_state.nav_back = None
    # закрыть открытые формы, иначе «Домой» из формы события ничего не меняет
    _close_event_form()
    _close_article_form()


def _scroll_to_anchor(anchor_id):
    """Мгновенный переход к якорю (UI): один iframe с script, height=0.

    Streamlit перерисовывает страницу сверху, поэтому при длинном списке
    статей форма правки оказывается не в поле зрения. Компонент просит
    браузер прокрутить родительскую страницу к метке формы.
    """
    st.components.v1.html(
        f"""
        <script>
        const doc = window.parent.document;
        const target = doc.getElementById("{anchor_id}");
        if (target) {{
            target.scrollIntoView({{ behavior: "instant", block: "start" }});
        }}
        </script>
        """,
        height=0,
    )


st.sidebar.button(
    ":material/home: Домой",
    key="btn-home",
    on_click=_go_home,
    width="stretch",
)
st.sidebar.radio("Навигация", SCREENS, key="screen")

# FR-10: режим просмотра — скрывает формы и кнопки редактирования
st.sidebar.toggle("Режим просмотра (клиент)", key="view_mode", value=False)


def _on_scenario_toggle():
    """Сброс тарифов сценария при выключении режима (FR-16)."""
    if not st.session_state.get("scenario_mode"):
        for _key in [
            _k for _k in list(st.session_state) if _k.startswith("sc_tariff_")
        ]:
            del st.session_state[_key]


# FR-16: «Расчёт на гостя» — сценарий без изменения данных события
st.sidebar.toggle(
    "Расчёт на гостя (сценарий)",
    key="scenario_mode",
    value=False,
    help=(
        "Показывает вариант бюджета при другом числе гостей; "
        "событие не изменяется"
    ),
    on_change=_on_scenario_toggle,
)


def _on_calc_command():
    """Командная строка калькулятора (FR-12): ввод числа и действий без мыши.

    Enter в поле разбирает ввод («12500,50 + 3500 =», «+», «C»…) и очищает
    поле. Мусор игнорируется, состояние калькулятора не меняется.
    """
    text = st.session_state.get("calc_input") or ""
    state = st.session_state.get("calc_state") or calc.calc_new_state()
    new_state, ok = calc.calc_parse_command(state, text)
    if ok:
        st.session_state.calc_state = new_state
    st.session_state.calc_input = ""


# FR-12: калькулятор доступен на всех экранах
with st.sidebar.expander("Калькулятор"):
    _calc = st.session_state.setdefault("calc_state", calc.calc_new_state())
    st.markdown(f"### `{calc.calc_display(_calc)}`")
    for _row in (
        ("7", "8", "9", "÷"),
        ("4", "5", "6", "×"),
        ("1", "2", "3", "−"),
        ("0", ",", "+", "="),
        ("C", "back"),
    ):
        _cols = st.columns(len(_row))
        for _col, _key in zip(_cols, _row):
            _label = "⌫" if _key == "back" else _key
            if _col.button(_label, key=f"calc-btn-{_key}", width="stretch"):
                st.session_state.calc_state = calc.calc_press(_calc, _key)
                st.rerun()
    st.text_input(
        "Число с клавиатуры (или команда)",
        key="calc_input",
        placeholder="12500,50 + 3500   или   +   или   C",
        on_change=_on_calc_command,
    )
    st.caption("Ввод и Enter: результат считается сразу, = не нужен")
    if st.button("Копировать результат", key="calc-copy"):
        st.session_state.calc_show_copy = True
    if st.session_state.get("calc_show_copy"):
        _res = calc.calc_result(_calc)
        if _res is None:
            st.caption("Нечего копировать")
        else:
            st.code(str(_res), language=None)
            st.caption("Выделите и нажмите Ctrl+C")

if st.session_state.event_notice:
    st.success(st.session_state.event_notice)
    st.session_state.event_notice = None


def validate_event_form():
    """Проверки ввода события (NFR-3, сообщения на русском)."""
    name = (st.session_state.ev_name or "").strip()
    client = (st.session_state.ev_client or "").strip()
    guests = st.session_state.ev_guests
    mode = st.session_state.ev_limit_mode
    # FR-6: денежные поля формы — строки с разрядами, разбираем их в числа
    ok_limit, limit = calc.parse_amount(st.session_state.ev_limit, required=False)
    comment = (st.session_state.ev_comment or "").strip()
    plan_version = (st.session_state.ev_plan_version or "").strip()
    source_id = (st.session_state.ev_source_id or "").strip()

    errors = []

    if not name:
        errors.append("Укажите мероприятие")
    elif len(name) > 100:
        errors.append("Мероприятие: не более 100 символов")

    if len(client) > 100:
        errors.append("Клиент: не более 100 символов")

    if guests is None or guests < 0:
        errors.append("Число гостей — целое ≥ 0")
    elif mode == "На гостя" and guests == 0:
        errors.append("Для режима «на гостя» нужно хотя бы 1 гость")

    if not ok_limit:
        errors.append("Лимит — число ≥ 0")
    elif limit is None:
        errors.append(
            "Укажите лимит на одного гостя (больше 0)"
            if mode == "На гостя"
            else "Укажите лимит бюджета (больше 0)"
        )
    elif limit <= 0:
        errors.append(
            "Лимит на гостя должен быть больше 0"
            if mode == "На гостя"
            else "Лимит должен быть больше 0"
        )

    if len(comment) > 200:
        errors.append("Комментарий: не более 200 символов")
    if len(plan_version) > 50:
        errors.append("Версия плана: не более 50 символов")
    if len(source_id) > 50:
        errors.append("ID исходного заказа: не более 50 символов")

    return name, client, errors


def _reset_search():
    """Сброс поискового запроса (FR-14): callback до создания виджетов —
    присвоение ev_search допустимо."""
    st.session_state["ev_search"] = ""
    st.session_state["ev_search_store"] = ""


def _open_budget(event_id, back_to=None):
    """Переход на экран бюджета: callback выполняется до создания виджетов —
    присваивание ключа «screen» (виджет радио в сайдбаре) допустимо.
    back_to — id события, из которого перешли (кнопка «Вернуться в копию»)."""
    st.session_state.selected_event_id = event_id
    st.session_state.screen = "Бюджет события"
    st.session_state.nav_back = back_to


def _start_edit_event(event_id):
    """Предзаполнение формы события для редактирования (FR-3, как в прототипе)."""
    ev = db.get_event(event_id)
    if not ev:
        return
    st.session_state.ev_edit_id = event_id
    st.session_state.show_event_form = True
    st.session_state.event_errors = []
    st.session_state.ev_recalc_limit = False  # FR-3: по умолчанию лимит не трогаем
    st.session_state.ev_name = ev["name"]
    st.session_state.ev_client = ev["client"] or ""
    st.session_state.ev_order_date = (
        datetime.date.fromisoformat(ev["order_date"]) if ev.get("order_date") else None
    )
    st.session_state.ev_date = (
        datetime.date.fromisoformat(ev["date"]) if ev["date"] else None
    )
    st.session_state.ev_guests = ev["guests"]
    # Храним общий лимит; при режиме «на гостя» показываем ставку.
    per_guest_mode = ev["limit_mode"] == "perGuest"
    st.session_state.ev_limit_mode = "На гостя" if per_guest_mode else "Всего"
    limit = float(ev["budget_limit"])
    guests = ev["guests"] or 0
    if per_guest_mode and guests > 0:
        limit = round(limit / guests, 2)
    st.session_state.ev_limit = calc.format_amount_input(str(limit))
    # Виджеты платежей (key ev_pay_*) переключаем на новое событие: без
    # сброса ключей Streamlit показал бы значения прошлой формы (UI)
    st.session_state.clear_pay_widgets = True
    pays = db.payments_of(event_id)
    st.session_state.ev_payments = [
        {"date": datetime.date.fromisoformat(p["date"]) if p.get("date") else None,
         "amount": calc.format_amount_input(str(p["amount"] or 0))}
        for p in pays
    ] or [{"date": None, "amount": ""}]
    st.session_state.ev_comment = ev["comment"] or ""
    st.session_state.ev_plan_version = ev["plan_version"] or ""
    st.session_state.ev_source_id = ev["source_order_id"] or ""
    st.session_state.screen = "Список событий"


def _rescale_variable_articles(event_id, old_guests, new_guests):
    """Пересчёт факта переменных статей при смене числа гостей (BR-2).

    Ставка ₽/чел сохраняется: новый факт = факт ÷ старые гости × новые
    гости. Планы, лимит и фикс-статьи не меняются. Возвращает текст
    уведомления (пустая строка — пересчёта не было).
    """
    if old_guests == new_guests:
        return ""
    arts = db.articles_of(event_id)
    if not any(art.get("per_person") for art in arts):
        return ""
    if not old_guests:
        return (
            " Переменные статьи не пересчитаны: раньше гостей не было — "
            "ставку ₽/чел определить нельзя"
        )
    if not new_guests:
        return (
            " Переменные статьи не пересчитаны: гостей стало 0 — "
            "пересчёт по ставке ₽/чел невозможен"
        )
    updates = calc.rescale_variable_articles(arts, old_guests, new_guests)
    if not updates:
        return ""
    db.update_articles_fact(updates)
    return (
        f" Пересчитаны переменные статьи ({len(updates)}): факт — по новому "
        "числу гостей, ставка ₽/чел сохранена"
    )


def _copy_event(event_id):
    """Копирование события (FR-15): выбор переключается на копию."""
    copy_id = db.copy_event(event_id)
    if copy_id:
        st.session_state.selected_event_id = copy_id
        # Сброс поиска: копия должна быть видна в списке
        st.session_state.ev_search = ""
        st.session_state.ev_search_store = ""
        st.session_state.event_notice = (
            "Копия создана: план скопирован, факт обнулён"
        )


def _clear_payment_widget_keys():
    """Сброс ключей виджетов платежей (UI): иначе Streamlit показывает старые
    значения при переключении между событиями и при удалении строк."""
    for _key in [
        k for k in st.session_state
        if k.startswith(("ev_pay_date_", "ev_pay_amt_", "ev_pay_del_"))
    ]:
        del st.session_state[_key]


# Сброс/закрытие формы ставит флаг: ключи виджетов снимаются до их создания
if st.session_state.pop("clear_pay_widgets", False):
    _clear_payment_widget_keys()


def _close_event_form():
    """Закрыть форму события и очистить её ошибки."""
    st.session_state.show_event_form = False
    st.session_state.event_errors = []
    # ключи виджетов платежей снимаются следующим ререном (UI)
    st.session_state.clear_pay_widgets = True


def _payment_items_from_form():
    """Сбор и валидация платежей формы события (FR-7).

    Возвращает (items, errors): items — строки {"amount", "date"} для
    replace_payments; пустые строки пропускаются (платёж не заполнен).
    """
    items, errors = [], []
    rows = st.session_state.get("ev_payments") or []
    if len(rows) > 10:
        errors.append("Не более 10 платежей")
    for p in rows:
        text = (str(p.get("amount") or "")).strip()
        if not text:
            continue  # незаполненная строка — платёж не внесён
        ok, value = calc.parse_amount(text)
        if not ok or value is None:
            errors.append("Сумма платежа — число ≥ 0")
            continue
        d = p.get("date")
        if d is None:
            errors.append("Укажите дату каждого платежа")
            continue
        items.append({
            "amount": value,
            "date": d.isoformat() if hasattr(d, "isoformat") else d,
        })
    return items, errors


def _ask_delete_event(event_id):
    st.session_state.ev_confirm_delete = event_id


def _cancel_delete_event():
    st.session_state.ev_confirm_delete = None


def _do_delete_event(event_id):
    db.delete_event(event_id)
    st.session_state.ev_confirm_delete = None
    if st.session_state.selected_event_id == event_id:
        st.session_state.selected_event_id = None
    st.session_state.event_notice = "Событие удалено"


def render_events_screen():
    # Крупная обложка входного экрана (NFR-9): только CSS, без картинок
    st.markdown(
        '<div class="ap-hero">'
        '<div class="ap-hero__spark">✦ ✧</div>'
        '<div class="ap-hero__title">Калькулятор бюджета события</div>'
        '<div class="ap-hero__sub">План, факт и лимит — под контролем</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.title("События")

    # FR-10: в режиме просмотра скрываем создание/редактирование
    view_only = st.session_state.view_mode
    if view_only:
        st.caption("Режим просмотра: редактирование скрыто")

    if not view_only and st.button(
        "+ Создать событие" if not st.session_state.show_event_form else "Скрыть форму",
        key="btn-toggle-event-form",
        # Заметное главное действие (NFR-9): primary, пока форма закрыта
        type="primary" if not st.session_state.show_event_form else "secondary",
    ):
        if st.session_state.show_event_form:
            _close_event_form()
        else:
            st.session_state.show_event_form = True
            st.session_state.ev_edit_id = None
            st.session_state.event_errors = []
        st.rerun()

    if st.session_state.show_event_form and not view_only:
        editing_ev_id = st.session_state.ev_edit_id
        st.subheader(
            "Изменить событие" if editing_ev_id else "Новое событие"
        )

        st.text_input(
            "Мероприятие *",
            max_chars=100,
            placeholder="Например: День рождения",
            key="ev_name",
        )
        c1, c2 = st.columns(2)
        c1.text_input(
            "Клиент",
            max_chars=100,
            placeholder="Например: Мария Сидорова",
            key="ev_client",
        )
        c2.date_input("Дата заказа", key="ev_order_date", format="DD/MM/YYYY")
        c3, c4 = st.columns(2)
        c3.date_input("Дата мероприятия", key="ev_date", format="DD/MM/YYYY")
        c4.number_input(
            "Количество гостей *", min_value=0, step=1, key="ev_guests",
        )
        st.caption("0 гостей допустим — ₽/гость будет «—»; для режима «на гостя» — минимум 1")

        mode = st.radio(
            "Лимит", ["Всего", "На гостя"], horizontal=True, key="ev_limit_mode",
        )
        limit_label = (
            "Лимит на одного гостя, ₽ *" if mode == "На гостя" else "Лимит бюджета, ₽ *"
        )
        st.text_input(
            limit_label,
            key="ev_limit",
            placeholder="Например: 120 000",
            on_change=_format_money_field,
            args=("ev_limit",),
        )

        # FR-3, BR-2: согласованный пересчёт лимита — только явным чекбоксом
        if st.session_state.ev_edit_id and mode == "На гостя":
            st.checkbox(
                "Согласованный пересчёт лимита",
                key="ev_recalc_limit",
                help=(
                    "Включите, если с клиентом согласовано новое число гостей: "
                    "лимит будет = ставка ₽/гость × новые гости. Без включения "
                    "сохранённый лимит не меняется (FR-3, BR-2)"
                ),
            )

        guests = st.session_state.ev_guests or 0
        limit = _amount_value("ev_limit")
        if limit and limit > 0:
            if mode == "На гостя" and guests > 0:
                total = calc.limit_total(limit, guests, "perGuest")
                editing_now = bool(st.session_state.ev_edit_id)
                recalc_now = bool(st.session_state.ev_recalc_limit)
                if editing_now and not recalc_now:
                    original = db.get_event(st.session_state.ev_edit_id)
                    st.caption(
                        f"Общий лимит останется прежним: "
                        f"{calc.format_money(original['budget_limit']) if original else '—'}. "
                        "Чтобы пересчитать по ставке × гости — включите "
                        "«Согласованный пересчёт лимита»"
                    )
                else:
                    st.caption(
                        f"Общий лимит: {calc.format_money(total)} "
                        f"({guests} × {calc.format_money(limit)})"
                    )
            elif mode == "Всего" and guests > 0:
                st.caption(
                    f"{calc.format_money(limit)} ÷ {guests} гостей = "
                    f"{calc.format_money(limit / guests)} на гостя"
                )
        else:
            st.caption("Всего на событие" if mode == "Всего" else
                       "Укажите лимит на гостя и число гостей — посчитаем общий")

        # Блок «Оплаты» (FR-7): список платежей «дата + сумма», до 10 строк;
        # пустая строка — платёж не внесён
        st.markdown("**Оплаты**")
        ev_for_pay = st.session_state.ev_edit_id
        arts_for_pay = db.articles_of(ev_for_pay) if ev_for_pay else []
        fact_total_pay = calc.fact_total(arts_for_pay)
        pays_list = st.session_state.get("ev_payments") or []
        if not pays_list:
            st.session_state.ev_payments = [{"date": None, "amount": ""}]
            pays_list = st.session_state.ev_payments
        paid_total_form = 0.0
        for p in pays_list:
            ok_pay, val_pay = calc.parse_amount(
                p.get("amount") or "", required=False
            )
            if ok_pay and val_pay is not None:
                paid_total_form += val_pay
        remain_tip = calc.payments_remain(fact_total_pay, paid_total_form)
        if ev_for_pay and arts_for_pay:
            st.caption(f"Осталось внести по факту: {calc.format_money(remain_tip)}")
        else:
            st.caption("Осталось внести по факту: будет рассчитан позже")
        for i, p in enumerate(pays_list):
            c1, c2, c3 = st.columns([2, 2, 1])
            pays_list[i]["date"] = c1.date_input(
                f"Дата платежа {i + 1}", value=p.get("date"),
                format="DD/MM/YYYY", key=f"ev_pay_date_{i}",
            )
            pays_list[i]["amount"] = c2.text_input(
                f"Сумма платежа {i + 1}, ₽", value=p.get("amount") or "",
                key=f"ev_pay_amt_{i}", on_change=_format_money_field,
                args=(f"ev_pay_amt_{i}",),
            )
            if c3.button("Удалить", key=f"ev_pay_del_{i}"):
                pays_list.pop(i)
                st.session_state.ev_payments = pays_list
                # ключи виджетов сдвигаются — сняты на следующем ререне (UI)
                st.session_state.clear_pay_widgets = True
                st.rerun()
        st.session_state.ev_payments = pays_list
        if len(pays_list) < 10:
            if st.button("+ Добавить платёж", key="ev_pay_add"):
                pays_list.append({"date": None, "amount": ""})
                st.session_state.ev_payments = pays_list
                st.rerun()

        text_cols = st.columns(3)
        text_cols[0].text_input(
            "Комментарий",
            max_chars=200,
            key="ev_comment",
            placeholder="Например: копия плана свадьбы",
        )
        text_cols[1].text_input(
            "Версия плана",
            max_chars=50,
            key="ev_plan_version",
            placeholder="Например: v2 от 18/10/2026",
        )
        text_cols[2].text_input(
            "ID исходного заказа",
            max_chars=50,
            key="ev_source_id",
            placeholder="ID события-прообраза",
        )

        for message in st.session_state.event_errors:
            st.error(message)

        col_save, col_cancel = st.columns([1, 1])
        save_label = (
            "Сохранить изменения"
            if st.session_state.ev_edit_id
            else "Сохранить"
        )
        if col_save.button(
            save_label, type="primary", key="btn-event-submit"
        ):
            name, client, errors = validate_event_form()
            pay_items, pay_errors = _payment_items_from_form()
            errors += pay_errors
            if errors:
                st.session_state.event_errors = errors
                st.rerun()

            guests = st.session_state.ev_guests
            mode = st.session_state.ev_limit_mode
            editing_ev_id = st.session_state.ev_edit_id
            # Прежние данные события: от них считается пересчёт переменных
            # статей при смене числа гостей (BR-2)
            original = db.get_event(editing_ev_id) if editing_ev_id else None
            old_guests = (original["guests"] or 0) if original else 0
            limit_value = _amount_value("ev_limit")
            # FR-3, BR-2: лимит при редактировании в режиме «На гостя»
            # пересчитывается только по чекбоксу «Согласованный пересчёт лимита»
            if mode == "На гостя":
                if editing_ev_id and not st.session_state.get("ev_recalc_limit"):
                    limit_total = original["budget_limit"] if original else 0
                else:
                    limit_total = calc.limit_total(
                        limit_value, guests, "perGuest"
                    )
            else:
                limit_total = limit_value
            event_date = st.session_state.ev_date
            order_date = st.session_state.ev_order_date
            # Деньги клиента живут в таблице payment (FR-7); legacy-поля
            # event (client_paid, final_*) больше не заполняются
            fields = dict(
                name=name,
                client=client,
                date=event_date.isoformat() if event_date else None,
                guests=guests,
                budget_limit=limit_total,
                limit_mode="perGuest" if mode == "На гостя" else "total",
                client_paid=0,
                client_paid_date=None,
                final_amount=None,
                final_date=None,
                order_date=order_date.isoformat() if order_date else None,
                comment=(st.session_state.ev_comment or "").strip(),
                plan_version=(st.session_state.ev_plan_version or "").strip(),
                source_order_id=(st.session_state.ev_source_id or "").strip(),
            )
            if editing_ev_id:
                db.update_event(editing_ev_id, **fields)
                st.session_state.selected_event_id = editing_ev_id
                notice = "Событие обновлено"
                # BR-2: факт переменных статей пересчитывается под новое
                # число гостей (ставка ₽/чел сохраняется); планы и лимит — нет
                notice += _rescale_variable_articles(
                    editing_ev_id, old_guests, guests
                )
                saved_id = editing_ev_id
            else:
                saved_id = db.create_event(**fields)
                st.session_state.selected_event_id = saved_id
                # Сброс поиска: новое событие должно быть видно в списке
                st.session_state.ev_search = ""
                st.session_state.ev_search_store = ""
                notice = "Событие создано"
            db.replace_payments(saved_id, pay_items)
            st.session_state.show_event_form = False
            st.session_state.event_errors = []
            st.session_state.event_notice = notice
            st.session_state.reset_event_form = True
            st.rerun()

        if col_cancel.button("Отмена", key="btn-cancel-event"):
            _close_event_form()
            st.rerun()

    events = db.list_events()

    if not events:
        st.info("Событий ещё нет — создайте первое событие")
        return

    # FR-14: поиск по мероприятию и клиенту (без учёта регистра, частичное)
    st.text_input(
        "Поиск по мероприятию или клиенту",
        key="ev_search",
        placeholder="Название события или имя клиента",
    )
    st.session_state["ev_search_store"] = st.session_state["ev_search"]

    query = (st.session_state.ev_search or "").strip().lower()
    if query:
        visible = [
            ev for ev in events
            if query in ev["name"].lower()
            or (ev["client"] and query in ev["client"].lower())
        ]
        cnt_col, reset_col = st.columns([3, 1])
        cnt_col.caption(f"Найдено: {len(visible)} из {len(events)}")
        reset_col.button(
            "Сбросить поиск", key="btn-reset-search", on_click=_reset_search,
        )
    else:
        visible = events
        st.caption(f"Событий: {len(events)}")

    if not visible:
        st.info("Ничего не найдено — нажмите «Сбросить поиск», чтобы вернуться к полному списку")
        return

    for ev in visible:
        arts = db.articles_of(ev["id"])
        fact = calc.fact_total(arts)
        balance = calc.limit_balance(ev["budget_limit"], fact)
        with st.container(border=True):
            # Метка карточки + подсветка текущего (открытого) события (NFR-9)
            cur_cls = (
                "ap-row-mark ap-row-current"
                if ev["id"] == st.session_state.selected_event_id
                else "ap-row-mark"
            )
            st.markdown(f'<span class="{cur_cls}"></span>', unsafe_allow_html=True)
            left, mid, right = st.columns([3, 2, 3])
            with left:
                st.markdown(f"**{ev['name']}**")
                st.caption(f"ID: {ev['id']}" + (f" · Клиент: {ev['client']}" if ev["client"] else ""))
                # Подпись карточки: версия плана · комментарий, если заполнены (FR-1)
                note = " · ".join(
                    part for part in (ev["plan_version"], ev["comment"]) if part
                )
                if note:
                    st.caption(note)
                # Привязка копии к прообразу (FR-15)
                if ev["parent_id"]:
                    parent_ev = db.get_event(ev["parent_id"])
                    if parent_ev:
                        st.caption(
                            f"Копия события «{parent_ev['name']}» "
                            f"(ID {parent_ev['id']})"
                        )
                else:
                    copies = db.copies_of(ev["id"])
                    if copies:
                        st.caption(
                            "Создана копия: "
                            + ", ".join(f"ID {c['id']}" for c in copies)
                        )
            with mid:
                date_value = ev["date"] or "Дата не указана"
                if ev["date"]:
                    date_value = calc.format_date(ev["date"])
                st.caption(f"Дата: {date_value} · Гостей: {ev['guests']}")
                st.caption(f"Лимит: {calc.format_money(ev['budget_limit'])}")
            with right:
                st.caption(f"Факт: {calc.format_money(fact)}")
                if balance < 0:
                    st.markdown(f":red[Остаток лимита: {calc.format_money(balance)}]")
                else:
                    st.caption(f"Остаток лимита: {calc.format_money(balance)}")
                if st.button(
                    "Открыть бюджет", key=f"btn-open-{ev['id']}",
                    on_click=_open_budget, args=(ev["id"],),
                ):
                    pass
                # Кнопки перехода по привязке (FR-15): видны и в режиме просмотра
                if ev["parent_id"] and db.get_event(ev["parent_id"]):
                    st.button(
                        "Открыть прообраз", key=f"ev-parent-{ev['id']}",
                        on_click=_open_budget,
                        args=(ev["parent_id"], ev["id"]),
                    )
                elif not ev["parent_id"]:
                    _copies = db.copies_of(ev["id"])
                    if _copies:
                        st.button(
                            "Открыть копию", key=f"ev-copyopen-{ev['id']}",
                            on_click=_open_budget, args=(_copies[0]["id"],),
                        )
                if view_only:
                    continue
                confirming = st.session_state.ev_confirm_delete == ev["id"]
                if confirming:
                    st.caption("Удалить событие со всеми статьями?")
                    c1, c2 = st.columns(2)
                    c1.button(
                        "Да, удалить", key=f"ev-del-yes-{ev['id']}",
                        on_click=_do_delete_event, args=(ev["id"],),
                    )
                    c2.button(
                        "Отмена", key=f"ev-del-no-{ev['id']}",
                        on_click=_cancel_delete_event,
                    )
                else:
                    r1, r2, r3 = st.columns(3)
                    r1.button(
                        "Изменить", key=f"ev-edit-{ev['id']}",
                        on_click=_start_edit_event, args=(ev["id"],),
                    )
                    r2.button(
                        "Копировать", key=f"ev-copy-{ev['id']}",
                        on_click=_copy_event, args=(ev["id"],),
                    )
                    r3.button(
                        "Удалить", key=f"ev-del-{ev['id']}",
                        on_click=_ask_delete_event, args=(ev["id"],),
                    )


def _event_guests():
    """Число гостей текущего события (0 — если событие не выбрано)."""
    ev_id = st.session_state.get("selected_event_id")
    ev = db.get_event(ev_id) if ev_id else None
    return (ev["guests"] if ev else 0) or 0


def _rate_from_sum(value, guests):
    """Тариф ₽/чел = сумма ÷ гости (FR-6); None — показатель не определён."""
    pg = calc.per_guest(value, guests)
    if pg is None:
        return None
    return calc.format_amount_input(str(pg))


def _sync_rate_from_sum(amount_key, rate_key):
    """Поле тарифа следует за суммой: сумма ÷ гостей (FR-6).

    Ввод суммы вручную пересчитывает тариф; обратная подстановка
    (тариф → сумма) работает через _on_art_*_tariff_change.
    """
    if not st.session_state.get("art_per_person"):
        return
    ok, value = calc.parse_amount(
        st.session_state.get(amount_key, ""), required=False
    )
    if not ok:
        return
    if value is None:
        st.session_state[rate_key] = ""
        return
    rate = _rate_from_sum(value, _event_guests())
    if rate is not None:
        st.session_state[rate_key] = rate


def _start_edit_article(article_id):
    art = db.get_article(article_id)
    if not art:
        return
    st.session_state.art_form_open = True
    st.session_state.art_edit_id = article_id
    st.session_state.art_category = art["category"]
    st.session_state.art_cat_search = ""
    st.session_state.art_custom = ""
    st.session_state.art_plan = (
        "" if art["plan"] is None else calc.format_amount_input(str(art["plan"]))
    )
    st.session_state.art_fact = calc.format_amount_input(str(art["fact"]))
    st.session_state.art_comment = art["comment"] or ""
    st.session_state.art_per_person = bool(art["per_person"])
    # Тарифы в статье не хранятся (FR-16): поля — помощники для расчёта.
    # FR-6: заполненная сумма показывает свой тариф = сумма ÷ гостей.
    # BR-5: при согласованном плане тариф плана заблокирован и показывает
    # плановый тариф = план ÷ число гостей события.
    rate_plan = ""
    rate_fact = ""
    if art["per_person"]:
        guests = _event_guests()
        if art["plan"] is not None:
            rate_plan = _rate_from_sum(art["plan"], guests) or ""
        rate_fact = _rate_from_sum(art["fact"], guests) or ""
    st.session_state.art_rate = rate_plan
    st.session_state.art_rate_fact = rate_fact
    st.session_state.art_errors = []
    st.session_state.art_confirm_delete = None
    # Форма открывается над таблицей: просим промотку к её верхней границе,
    # иначе при длинном списке статей форму приходится искать вверху (UI).
    st.session_state.art_form_scroll = True


def _on_art_plan_change():
    _format_money_field("art_plan")
    _sync_rate_from_sum("art_plan", "art_rate")


def _on_art_fact_change():
    _format_money_field("art_fact")
    _sync_rate_from_sum("art_fact", "art_rate_fact")


def _on_art_tariff_change():
    """Подстановка плана из тарифа × гостей события (FR-6).

    Помощь при первоначальном планировании: ввод тарифа ₽/чел заполняет
    поле «План» суммой = тариф × число гостей. Согласованный план не
    меняется (BR-5); значение «План» можно поправить вручную.
    """
    _format_money_field("art_rate")
    if not st.session_state.get("art_per_person"):
        return
    ok, rate = calc.parse_amount(
        st.session_state.get("art_rate", ""), required=False
    )
    ev_id = st.session_state.get("selected_event_id")
    if not ok or rate is None or not ev_id:
        return
    ev = db.get_event(ev_id)
    if not ev or ev["plan_approved"]:
        return
    st.session_state.art_plan = calc.format_amount_input(
        str(round(rate * (ev["guests"] or 0), 2))
    )


def _on_art_fact_tariff_change():
    """Подстановка факта из тарифа × гостей события (FR-6).

    Факт правится всегда (BR-5 блокирует только план), поэтому тариф
    факта подставляет сумму = тариф × число гостей в поле «Факт».
    """
    _format_money_field("art_rate_fact")
    if not st.session_state.get("art_per_person"):
        return
    ok, rate = calc.parse_amount(
        st.session_state.get("art_rate_fact", ""), required=False
    )
    ev_id = st.session_state.get("selected_event_id")
    if not ok or rate is None or not ev_id:
        return
    ev = db.get_event(ev_id)
    if not ev:
        return
    st.session_state.art_fact = calc.format_amount_input(
        str(round(rate * (ev["guests"] or 0), 2))
    )


def _close_article_form():
    st.session_state.art_form_open = False
    st.session_state.art_reset = True


def _ask_delete_article(article_id):
    st.session_state.art_confirm_delete = article_id


def _cancel_delete_article():
    st.session_state.art_confirm_delete = None


def _do_delete_article(article_id):
    db.delete_article(article_id)
    st.session_state.art_confirm_delete = None
    st.session_state.budget_notice = "Статья удалена"


def _approve_plan(event_id):
    db.set_plan_approved(event_id, True)
    st.session_state.unlock_confirm = False
    st.session_state.budget_notice = (
        "План согласован — изменение плановых сумм заблокировано"
    )


def _ask_unlock():
    st.session_state.unlock_confirm = True


def _cancel_unlock():
    st.session_state.unlock_confirm = False


def _do_unlock(event_id):
    db.set_plan_approved(event_id, False)
    st.session_state.unlock_confirm = False
    st.session_state.budget_notice = "План разблокирован"


def _go_to_events():
    st.session_state.screen = "Список событий"


def validate_article_form(ev):
    """Проверки формы статьи (BR-1, BR-4, BR-5; сообщения на русском)."""
    category = st.session_state.art_category
    custom = st.session_state.art_custom.strip()
    comment = st.session_state.art_comment.strip()

    errors = []
    category_name = None

    if category == ART_PLACEHOLDER:
        errors.append("Выберите категорию")
    elif category == ART_OTHER:
        if not custom:
            errors.append("Укажите название категории")
        elif len(custom) > 50:
            errors.append("Категория: не более 50 символов")
        else:
            category_name = custom
    else:
        category_name = category

    # BR-5: план согласован — план берётся из сохранённой статьи, поле заблокировано.
    if ev["plan_approved"]:
        editing = (
            db.get_article(st.session_state.art_edit_id)
            if st.session_state.art_edit_id
            else None
        )
        plan = (True, editing["plan"] if editing else None)
    else:
        plan = calc.parse_amount(st.session_state.art_plan, required=False)
        if not plan[0]:
            errors.append("План — число ≥ 0 или пусто")

    fact = calc.parse_amount(st.session_state.art_fact, required=True)
    if not fact[0]:
        errors.append("Факт обязателен: число ≥ 0 (0 — если ещё не тратили)")

    # FR-6: тарифы в форме статьи — необязательные помощники, но мусор не принимаем
    if st.session_state.get("art_per_person"):
        rate = calc.parse_amount(
            st.session_state.get("art_rate", ""), required=False
        )
        if not rate[0]:
            errors.append("Тариф плана — число ≥ 0 или пусто")
        rate_fact = calc.parse_amount(
            st.session_state.get("art_rate_fact", ""), required=False
        )
        if not rate_fact[0]:
            errors.append("Тариф факта — число ≥ 0 или пусто")

    data = {
        "category": category_name,
        "plan": plan[1] if plan[0] else None,
        "fact": fact[1] if fact[0] else 0,
        "comment": comment,
        # FR-6, FR-16: признак «Тарификация на человека», без авто-установки
        "per_person": 1 if st.session_state.get("art_per_person") else 0,
    }
    return errors, data


def render_article_form(ev):
    st.subheader(
        "Редактировать статью" if st.session_state.art_edit_id else "Новая статья"
    )

    # Выбор категории (FR-5): список по алфавиту + поиск по первым буквам
    # наименования расхода; «Другое» — всегда последним пунктом
    categories = sorted(
        (c["name"] for c in db.list_categories()), key=str.casefold
    )
    search = (st.session_state.get("art_cat_search") or "").strip().casefold()
    matched = [
        c for c in categories if not search or c.casefold().startswith(search)
    ]
    st.text_input(
        "Поиск статьи",
        key="art_cat_search",
        placeholder="Первые буквы наименования — например: Кей",
    )
    if search and not matched:
        st.caption("Ничего не найдено — уточните первые буквы или выберите «Другое»")
    options = [ART_PLACEHOLDER, *matched, ART_OTHER]
    if st.session_state.art_category not in options:
        options.insert(1, st.session_state.art_category)

    st.selectbox("Категория *", options, key="art_category")

    if st.session_state.art_category == ART_OTHER:
        st.text_input(
            "Название категории *", max_chars=50, key="art_custom",
            placeholder="Например: Фотограф",
        )

    approved = bool(ev["plan_approved"])
    # FR-6, FR-16: признак переменной статьи — всегда вручную, по умолчанию выключен.
    # Чекбокс выше сумм: тарифы стоят под своими графами «План» и «Факт».
    st.checkbox(
        "Тарификация на человека",
        key="art_per_person",
        help=(
            "Статья переменная (например, банкет, кейтеринг): участвует в "
            "пересчёте в режиме «Расчёт на гостя» (FR-16)"
        ),
    )

    st.text_input(
        "План, ₽",
        key="art_plan",
        disabled=approved,
        placeholder="Пусто = «нет в плане», 0 = явный ноль",
        on_change=_on_art_plan_change,
    )
    if approved:
        st.caption("План согласован — изменение заблокировано (BR-5)")
    if st.session_state.art_per_person:
        # FR-6: поле-помощник — подставляет план = тариф × гости события.
        # BR-5: при согласованном плане поле заблокировано и показывает
        # плановый тариф = план ÷ число гостей события.
        st.text_input(
            "Тариф плана, ₽/чел",
            key="art_rate",
            placeholder="Например: 2500",
            disabled=approved,
            on_change=_on_art_tariff_change,
            help=(
                "При вводе тарифа в поле «План» подставляется сумма = "
                "тариф × число гостей события; при правке «Плана» тариф "
                "пересчитывается как план ÷ гости"
            ),
        )
        if approved:
            st.caption(
                "План согласован — тариф плана заблокирован и равен "
                "плановой сумме ÷ число гостей (BR-5)"
            )
        else:
            st.caption(
                f"План = тариф × {ev['guests']} гостей события — посчитается "
                "автоматически; значение «План» можно поправить вручную"
            )

    st.text_input(
        "Факт, ₽ *", key="art_fact",
        placeholder="Точная сумма по факту, 0 = факт ещё не определён",
        on_change=_on_art_fact_change,
    )
    if st.session_state.art_per_person:
        # FR-6: поле-помощник — подставляет факт = тариф × гости события
        st.text_input(
            "Тариф факта, ₽/чел",
            key="art_rate_fact",
            placeholder="Например: 2500",
            on_change=_on_art_fact_tariff_change,
            help=(
                "При вводе тарифа в поле «Факт» подставляется сумма = "
                "тариф × число гостей события; тариф показывает факт ÷ "
                "гости и пересчитывается при правке «Факта»"
            ),
        )
        st.caption(
            f"Факт = тариф × {ev['guests']} гостей события — посчитается "
            "автоматически; значение «Факт» можно поправить вручную"
        )
    st.text_input("Комментарий", max_chars=200, key="art_comment")

    for message in st.session_state.art_errors:
        st.error(message)

    col_save, col_cancel = st.columns([1, 1])
    if col_save.button("Сохранить", type="primary", key="btn-art-submit"):
        errors, data = validate_article_form(ev)
        if errors:
            st.session_state.art_errors = errors
            st.rerun()

        category_id = db.get_or_create_category(data["category"])
        editing_id = st.session_state.art_edit_id
        if editing_id:
            db.update_article(
                editing_id, category_id, data["plan"], data["fact"],
                data["comment"], data["per_person"],
            )
            st.session_state.budget_notice = "Статья обновлена"
        else:
            db.create_article(
                ev["id"], category_id, data["plan"], data["fact"],
                data["comment"], data["per_person"],
            )
            st.session_state.budget_notice = "Статья добавлена"
        _close_article_form()
        st.rerun()

    if col_cancel.button("Отмена", key="btn-art-cancel"):
        _close_article_form()
        st.rerun()


def _render_scenario_panel(ev, arts):
    """Панель сценария «Расчёт на гостя» (FR-16).

    Считает вариант бюджета при другом числе гостей; данные события
    не изменяются — перенос вручную. Возвращает результат scenario_totals.
    """
    st.markdown("#### Расчёт на гостя (сценарий)")
    st.caption(
        "Вариант бюджета при другом числе гостей. Данные события не изменяются — "
        "значения переносятся вручную (FR-16)"
    )
    # Дефолты панели — текущие параметры события (сброс при смене события)
    if st.session_state.get("scenario_event_id") != ev["id"]:
        st.session_state["scenario_event_id"] = ev["id"]
        st.session_state["scenario_guests"] = ev["guests"]
        st.session_state["scenario_base"] = "Факт"

    ctrl = st.columns([1, 1, 3])
    ctrl[0].number_input(
        "Гостей в сценарии", min_value=0, step=1, key="scenario_guests",
    )
    base_label = ctrl[1].radio(
        "База фикс-статей", ["Факт", "План"], key="scenario_base", horizontal=True,
    )
    base_key = "fact" if base_label == "Факт" else "plan"

    variable = [a for a in arts if a["per_person"]]
    tariffs = {}
    invalid_tariffs = []
    if variable:
        t_cols = st.columns(min(len(variable), 4))
        hints = []
        for i, art in enumerate(variable):
            key = f"sc_tariff_{art['id']}"
            t_cols[i % 4].text_input(
                f"Тариф «{art['category']}, ₽/чел»",
                key=key,
                placeholder="Например: 2 500",
                on_change=_format_money_field,
                args=(key,),
            )
            ok, value = calc.parse_amount(
                st.session_state.get(key, ""), required=False
            )
            if ok and value is not None:
                tariffs[art["id"]] = value
            elif not ok:
                invalid_tariffs.append(art)
            base_value = art.get(base_key)
            if ev["guests"] > 0 and base_value:
                hints.append(
                    f"{art['category']}: сейчас {calc.format_money(base_value)} "
                    f"÷ {ev['guests']} = "
                    f"{calc.format_money(calc.per_guest(base_value, ev['guests']))}\u00a0₽/гость"
                )
        if hints:
            st.caption(" · ".join(hints))
    else:
        st.caption("Статей с тарификацией на человека нет — фикс-статьи берутся из бюджета как есть")

    for art in invalid_tariffs:
        st.error(f"Тариф статьи «{art['category']}» — число ≥ 0")

    result = calc.scenario_totals(
        arts,
        st.session_state.scenario_guests or 0,
        base=base_key,
        tariffs=tariffs,
        limit_value=ev["budget_limit"],
    )

    # Меняющиеся цифры сценария — в рамке, чтобы их заметил клиент (FR-16)
    with st.container(border=True):
        res = st.columns(4)
        res[0].metric("Итог расчёта", calc.format_money(result["total"]))
        pg = result["per_guest"]
        if pg is not None:
            res[1].metric("На гостя (сценарий)", calc.format_money(pg))
        else:
            res[1].metric("На гостя (сценарий)", "—")
        dev_lim = result["deviation_limit"]
        if dev_lim is None:
            res[2].metric("Отклонение от лимита", "—")
        elif dev_lim > 0:
            res[2].metric(
                "Отклонение от лимита", f"+{calc.format_money(dev_lim)}",
                delta="превышение лимита", delta_color="red",
            )
        elif dev_lim < 0:
            res[2].metric(
                "Отклонение от лимита", f"−{calc.format_money(abs(dev_lim))}",
            )
        else:
            res[2].metric("Отклонение от лимита", "0\u00a0₽")
        dev_base = result["deviation_base"]
        if dev_base > 0:
            res[3].metric(
                "От текущего итога", f"+{calc.format_money(dev_base)}",
                delta="дороже базы", delta_color="red",
            )
        elif dev_base < 0:
            res[3].metric(
                "От текущего итога", f"−{calc.format_money(abs(dev_base))}",
                delta="дешевле базы", delta_color="green",
            )
        else:
            res[3].metric("От текущего итога", "0\u00a0₽")
    if result["per_guest"] is None:
        st.caption("укажите число гостей сценария")
    if result["missing_tariffs"]:
        names = ", ".join(
            art["category"] for art in arts
            if art["id"] in result["missing_tariffs"]
        )
        st.warning(
            f"Не указан тариф — статья не входит в итог: {names}"
        )
    return result


def _ap_cl(label, blue=False):
    """Подпись значения для узкого экрана (NFR-9, адаптив таблицы).

    В широком виде скрыта CSS (её даёт шапка таблицы), в узком
    (@container ≤820px) видна перед значением — «План: 70 000 ₽».
    """
    cls = "ap-cl ap-cl--calc" if blue else "ap-cl"
    return f'<span class="{cls}">{label}: </span>'


def _ap_rate(value):
    """Расчётный тариф ₽/чел под суммой статьи (FR-6, BR-2).

    Показывается только у переменных статей и только когда показатель
    определён (гости > 0, сумма внесена); иначе строки нет.
    """
    if value is None:
        return ""
    money = calc.format_money(value)[:-2]
    return f'<span class="ap-rate">{money}\u00a0₽/чел</span>'


def _pay_fact_html(remain_fact, note):
    """Оплата по факту (FR-7) — выделена цветом и размером шрифта.

    «Осталось внести по факту» — красным, когда есть что вносить;
    «согласованная переплата»/«Полностью оплачено» — зелёным. Показатели
    «в пределах лимита» выделения не имеют (обычный вид).
    """
    if remain_fact > 0:
        label = (
            '<span class="ap-pay-fact__l ap-pay-fact__l--red">'
            "Осталось внести по факту:</span>"
        )
        value = (
            '<span class="ap-pay-fact__v ap-pay-fact__v--red">'
            f"{calc.format_money(remain_fact)}</span>"
        )
    else:
        # Полная оплата/переплата: остаток 0, а не «—» (FR-7, образец клиента);
        # состояние поясняет зелёная подпись «Полностью оплачено»/
        # «согласованная переплата +N ₽»
        label = '<span class="ap-pay-fact__l">Осталось внести по факту:</span>'
        value = f'<span class="ap-pay-fact__v">{calc.format_money(0)}</span>'
    html = f'<div class="ap-pay-fact">{label} {value}</div>'
    if note:
        html += f'<div class="ap-pay-note">{note}</div>'
    return html


def _over_under_html(summary):
    """Перерасход и экономия по статьям (BR-3) — мягкий фон, как в образце.

    Порядок строк — «Перерасход», затем «Экономия»; сумма и количество статей
    «у N из M» берутся из build_summary (NFR-8). Пометка «Статья без плана»
    сюда не попадает: это не перерасход и не экономия.
    """
    total = summary["articles_count"]

    def line(label, value, count, value_cls):
        if value > 0:
            value_html = (
                f'<span class="ap-ou__v {value_cls}">'
                f"{calc.format_money(value)}</span>"
            )
            caption = (
                f'<div class="ap-ou__c">у {count} из {total} статей</div>'
            )
        else:
            value_html = '<span class="ap-ou__v">—</span>'
            caption = ""
        return (
            f'<div class="ap-ou__r"><span class="ap-ou__l">{label}:</span>'
            f"{value_html}</div>{caption}"
        )

    return (
        '<div class="ap-ou">'
        + line(
            "Перерасход по статьям", summary["over_total"],
            summary["over_count"], "ap-ou__v--red",
        )
        + line(
            "Экономия по статьям", summary["under_total"],
            summary["under_count"], "ap-ou__v--green",
        )
        + "</div>"
    )


def _payments_html(ev, summary, payments):
    """Группа «ОПЛАТЫ» (FR-7) — таблица «Лимит»/«факт» по образцу клиента.

    Порядок строк: «К оплате» (лимит и итог факта) → «Внесено итого» (сумма
    платежей) → «Платёж» (дата в колонке «факт», по строке на платёж) →
    «Остаток в пределах лимита» (лимит − внесено) → «Осталось внести по
    плану» (итог плана − внесено) → «Осталось внести по факту» (итог факта −
    внесено).

    Мягким фоном выделены строки, отмеченные в образце: «Внесено итого» и
    «Осталось внести по плану». Оплата по факту выделена цветом и размером
    шрифта: остаток — красным, переплата/полная оплата — зелёной подписью.
    Остатки не уходят в минус (BR-4). Данные — только из build_summary (NFR-8).
    """
    def row(label, limit_value="", fact_value="", hl=False, label_cls=""):
        cls = "ap-pay__row" + (" ap-pay__row--hl" if hl else "")
        label_class = "ap-pay__l" + (f" {label_cls}" if label_cls else "")
        return (
            f'<div class="{cls}">'
            f'<span class="{label_class}">{label}</span>'
            f'<span class="ap-pay__v">{limit_value}</span>'
            f'<span class="ap-pay__v">{fact_value}</span></div>'
        )

    def note(text):
        return (
            '<div class="ap-pay__row ap-pay__note">'
            f'<span class="ap-pay__n">{text}</span></div>'
        )

    rem_fact = summary["remain_fact"]
    if rem_fact > 0:
        fact_cell = (
            '<span class="ap-pay-fact__v ap-pay-fact__v--red">'
            f"{calc.format_money(rem_fact)}</span>"
        )
        fact_label_cls = "ap-pay__l--red"
    else:
        # Остатки не уходят в минус: 0 ₽ + зелёная подпись состояния (FR-7)
        fact_cell = (
            f'<span class="ap-pay-fact__v">{calc.format_money(0)}</span>'
        )
        fact_label_cls = ""

    rows = [
        '<div class="ap-pay__row ap-pay__head"><span></span>'
        '<span class="ap-pay__h">Лимит</span>'
        '<span class="ap-pay__h">факт</span></div>',
        row(
            "К оплате",
            calc.format_money(ev["budget_limit"]),
            calc.format_money(summary["fact_total"]),
        ),
        row("Внесено итого", calc.format_money(summary["client_paid"]), hl=True),
    ]
    for pay in payments:
        # Сумма — в колонке «Лимит», дата — в колонке «факт» (FR-7)
        rows.append(
            row(
                "Платёж",
                calc.format_money(pay.get("amount")),
                calc.format_date(pay.get("date")) or "—",
            )
        )
    limit_note = summary["remain_limit_note"]
    plan_note = summary["remain_plan_note"]
    rows.append(
        row("Остаток в пределах лимита", calc.format_money(summary["remain_limit"]))
    )
    # Подпись переплаты не дублируется, когда лимит и план совпадают
    if limit_note and limit_note != plan_note:
        rows.append(note(limit_note))
    rows.append(
        row(
            "Осталось внести по плану",
            calc.format_money(summary["remain_plan"]),
            hl=True,
        )
    )
    if plan_note:
        rows.append(note(plan_note))
    rows.append(
        '<div class="ap-pay__row">'
        f'<span class="ap-pay__l{" " + fact_label_cls if fact_label_cls else ""}">'
        "Осталось внести по факту</span>"
        f'<span class="ap-pay__v ap-pay__v--wide">{fact_cell}</span></div>'
    )
    if summary["remain_fact_note"]:
        rows.append(
            note(f'<span class="ap-pay-note">{summary["remain_fact_note"]}</span>')
        )
    return (
        '<div class="ap-pay-wrap"><div class="ap-pay">'
        + "".join(rows)
        + "</div></div>"
    )


def render_budget_screen():
    ev = None
    if st.session_state.selected_event_id:
        ev = db.get_event(st.session_state.selected_event_id)

    if not ev:
        st.title("Бюджет события")
        st.info("Выберите событие в списке")
        st.button("← К списку событий", key="btn-back-events", on_click=_go_to_events)
        return

    if st.session_state.budget_notice:
        st.success(st.session_state.budget_notice)
        st.session_state.budget_notice = None

    # Данные сводки нужны и шапке (отклонение), и группам ПЛАН/ФАКТ/ОПЛАТЫ (NFR-8)
    arts = db.articles_of(ev["id"])
    payments_list = db.payments_of(ev["id"])
    paid_total = sum(float(p.get("amount") or 0) for p in payments_list)
    summary = calc.build_summary(
        ev["budget_limit"], ev["guests"], arts, paid_total
    )

    # Шапка события
    view_only = st.session_state.view_mode
    if view_only:
        st.caption("Режим просмотра: редактирование скрыто")
    head = st.columns([4, 1])
    head[0].title(ev["name"])
    if not view_only:
        head[1].button(
            "Изменить событие", key="btn-edit-event",
            on_click=_start_edit_event, args=(ev["id"],),
        )
    # Привязка копии/прообраза (FR-15): подписи и навигация в обычном потоке
    # (вне колонок) — меньше перестроений DOM при переходах копия ↔ прообраз.
    # Одна кнопка с фиксированным ключом budget-nav-link переиспользуется,
    # а не удаляется/создаётся при смене направления.
    nav_label, nav_args = None, None
    if ev["parent_id"]:
        parent_ev = db.get_event(ev["parent_id"])
        if parent_ev:
            st.caption(
                f"Копия события «{parent_ev['name']}» (ID {parent_ev['id']})"
            )
            nav_label, nav_args = "Перейти к прообразу", (parent_ev["id"], ev["id"])
    else:
        _copies = db.copies_of(ev["id"])
        if _copies:
            st.caption(
                "Создана копия: " + ", ".join(f"ID {c['id']}" for c in _copies)
            )
        # «Вернуться в копию» — только если пришли из этой копии
        _nav = st.session_state.nav_back
        _nav_ev = db.get_event(_nav) if _nav else None
        if _nav_ev and _nav_ev["parent_id"] == ev["id"]:
            nav_label, nav_args = "← Вернуться в копию", (_nav_ev["id"],)
    if nav_label:
        st.button(
            nav_label, key="budget-nav-link",
            on_click=_open_budget, args=nav_args,
        )
    meta = st.columns(6)
    # Скрытая метка строки: CSS (APP_CSS) делает шапку метрик адаптивной —
    # перенос длинного имени/сумм вместо многоточия и 6/3/2/1 колонку
    # по ширине контейнера; иначе полное имя клиента не читается
    meta[0].markdown('<span class="ap-meta-mark"></span>', unsafe_allow_html=True)
    meta[0].metric("ID", ev["id"])
    meta[1].metric("Клиент", ev["client"] or "—")
    meta[2].metric("Гостей", ev["guests"])
    meta[3].metric("Лимит", calc.format_money(ev["budget_limit"]))
    # Расчёт лимита на гостя (BR-2): лимит ÷ гости; при 0 гостей — «—»
    meta[4].metric(
        "На гостя (лимит)",
        calc.format_money(calc.per_guest(ev["budget_limit"], ev["guests"])),
    )
    dev_lim = summary["deviation_limit"]
    if dev_lim > 0:
        meta[5].metric(
            "Отклонение (Факт − Лимит)", f"+{calc.format_money(dev_lim)}",
            delta="превышение лимита", delta_color="red",
        )
    elif dev_lim < 0:
        meta[5].metric(
            "Отклонение (Факт − Лимит)", f"−{calc.format_money(abs(dev_lim))}",
        )
    else:
        meta[5].metric("Отклонение (Факт − Лимит)", "0\u00a0₽")
    # Лимит и план — независимые показатели (заметка в шапке любого события):
    # узкий контейнер — caption в колонке «Лимит» (как раньше), широкий
    # (>=754px) — полной строкой под метриками (переключает CSS .ap-meta-note)
    _note = "Лимит — договорённость с клиентом, план — расчёт по статьям. Это 2 разных показателя: расхождение допустимо, для наглядности рекомендуется регулировать статьей «Прочие расходы»."
    meta[3].caption(_note)
    st.markdown(f'<p class="ap-meta-note">{_note}</p>', unsafe_allow_html=True)
    date_value = "Дата не указана"
    if ev["date"]:
        date_value = calc.format_date(ev["date"])
    # Лимит на гостя вынесен в метрику шапки «На гостя (лимит)» (FR-7)
    st.caption(f"Дата: {date_value}")

    extra = st.columns(3)
    extra[0].caption(f"Версия плана: {ev['plan_version'] or '—'}")
    extra[1].caption(f"Комментарий: {ev['comment'] or '—'}")
    extra[2].caption(f"ID исходного заказа: {ev['source_order_id'] or '—'}")

    # BR-5: согласование / разблокировка плана
    approved = bool(ev["plan_approved"])
    if not view_only:
        col_plan, col_badge = st.columns([1, 2])
        with col_plan:
            if not approved:
                st.button(
                    "Согласовать план", key="btn-approve-plan",
                    on_click=_approve_plan, args=(ev["id"],),
                )
            elif st.session_state.unlock_confirm:
                st.warning(
                    f"Разблокировать план события «{ev['name']}»? "
                    "План снова можно будет изменять."
                )
                c1, c2 = st.columns(2)
                c1.button(
                    "Да, разблокировать", key="btn-unlock-yes",
                    on_click=_do_unlock, args=(ev["id"],),
                )
                c2.button("Отмена", key="btn-unlock-no", on_click=_cancel_unlock)
            else:
                st.button(
                    "Разблокировать план", key="btn-unlock", on_click=_ask_unlock,
                )
        with col_badge:
            if approved:
                st.caption("План согласован — поле «План» заблокировано (BR-5)")
    elif approved:
        st.caption("План согласован")

    # Сводка (FR-7): группы ПЛАН / ФАКТ / ОПЛАТЫ; данные из build_summary (NFR-8)
    col_plan, col_fact, col_pay = st.columns(3)

    with col_plan:
        with st.container(border=True):
            st.markdown("#### ПЛАН")
            st.markdown(f"**Итого:** {calc.format_money(summary['plan_total'])}")
            plan_pg = summary["plan_per_guest"]
            # Выделение увеличенным шрифтом (NFR-9, CSS .ap-pg)
            st.markdown(
                '<div class="ap-pg">На гостя (план): '
                f'<span class="ap-pg__v">{calc.format_money(plan_pg)}</span></div>'
                if plan_pg is not None
                else '<div class="ap-pg">На гостя (план): '
                '<span class="ap-pg__v">—</span></div>',
                unsafe_allow_html=True,
            )
            # Отклонение плана от лимита (FR-7): превышение — красным
            pdev = summary["deviation_plan_limit"]
            if pdev > 0:
                st.markdown(
                    f"**Отклонение (План − Лимит):** :red[**+{calc.format_money(pdev)}**]"
                )
                st.caption("план превышает лимит")
            else:
                st.markdown(
                    f"**Отклонение (План − Лимит):** {calc.format_money(pdev)}"
                )
            dev = summary["deviation"]
            if dev > 0:
                st.markdown(
                    f"**Отклонение (Факт − План):** :red[**+{calc.format_money(dev)}**]"
                )
            elif dev < 0:
                st.markdown(
                    f"**Отклонение (Факт − План):** :green[**{calc.format_money(dev)}**]"
                )
            else:
                st.markdown(
                    f"**Отклонение (Факт − План):** {calc.format_money(dev)}"
                )

    with col_fact:
        with st.container(border=True):
            st.markdown("#### ФАКТ")
            st.markdown(f"**Итого:** {calc.format_money(summary['fact_total'])}")
            fact_pg = summary["fact_per_guest"]
            # Выделение увеличенным шрифтом (NFR-9, CSS .ap-pg)
            if fact_pg is not None:
                st.markdown(
                    '<div class="ap-pg">На гостя (факт): '
                    f'<span class="ap-pg__v">{calc.format_money(fact_pg)}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ap-pg">На гостя (факт): '
                    '<span class="ap-pg__v">—</span></div>',
                    unsafe_allow_html=True,
                )
                st.caption("укажите число гостей")

            # Перерасход и экономия по статьям — мягкий фон, как в образце
            st.markdown(_over_under_html(summary), unsafe_allow_html=True)

    with col_pay:
        with st.container(border=True):
            st.markdown("#### ОПЛАТЫ")
            # Две колонки «Лимит»/«факт» (FR-7, макет «Режим Оплаты»):
            # «К оплате», «Внесено итого», «Платёж» (дата в колонке «факт»),
            # «Остаток в пределах лимита», «Осталось внести по плану»,
            # «Осталось внести по факту». Показатели «в пределах лимита» —
            # обычным видом; выделена только оплата по факту: остаток —
            # красным, переплата/полная оплата — зелёным (цвет и размер шрифта)
            st.markdown(
                _payments_html(ev, summary, payments_list),
                unsafe_allow_html=True,
            )

    st.divider()

    # FR-16: панель сценария над таблицей статей; данные — из calc (NFR-8)
    scenario = None
    scenario_rows = {}
    if st.session_state.scenario_mode:
        scenario = _render_scenario_panel(ev, arts)
        scenario_rows = {r["id"]: r for r in scenario["rows"]}

    # Действия над таблицей статей: «К списку событий» и «+ Добавить статью»
    if not view_only:
        top_act = st.columns([1, 1])
        top_act[0].button("← К списку событий", key="btn-back-events-top", on_click=_go_to_events)
        if top_act[1].button(
            "+ Добавить статью" if not st.session_state.art_form_open else "Скрыть форму",
            key="btn-toggle-article-form",
        ):
            if st.session_state.art_form_open:
                _close_article_form()
            else:
                st.session_state.art_form_open = True
                st.session_state.art_errors = []
                st.session_state.art_form_scroll = True
            st.rerun()
    else:
        st.button("← К списку событий", key="btn-back-events-top", on_click=_go_to_events)

    # Якорная метка над формой статьи: цель мгновенного перехода (UI)
    st.markdown(
        '<span id="ap-article-form" class="ap-anchor"></span>',
        unsafe_allow_html=True,
    )
    if st.session_state.pop("art_form_scroll", False):
        _scroll_to_anchor("ap-article-form")

    if st.session_state.art_form_open and not view_only:
        render_article_form(ev)

    if not arts:
        st.info("Статьй пока нет — добавьте первую")
        return

    if scenario is not None:
        # Веса колонок: строка в bordered-контейнере уже шапки (751px при
        # контенте 820px); ячейки обязаны вмещать шапку «Отклонение» (100px),
        # комментарий (119px) и кнопки (≈175px) — расчёт от row-контейнера
        widths = [3.0, 1.75, 1.75, 1.65, 2.6, 3.2, 4.7]
        labels = ["Категория", "План", "Факт", "Расчёт", "Отклонение", "Комментарий", ""]
    else:
        widths = [3.3, 2.5, 2.5, 2.9, 3.5, 5.1]
        labels = ["Категория", "План", "Факт", "Отклонение", "Комментарий", ""]
    # Шапка и строки — в контейнерах: строки видны карточками на фоне
    # страницы, оттенки — как у кнопок (NFR-9)
    with st.container():
        st.markdown('<span class="ap-head-mark"></span>', unsafe_allow_html=True)
        header = st.columns(widths)
        for cell, label in zip(header, labels):
            # Колонка «Расчёт» (сценарий) — выделена, чтобы меняющиеся цифры
            # были заметны клиенту в режиме просмотра (FR-16)
            if label == "Расчёт":
                cell.markdown(f":blue[**{label}**]")
            else:
                cell.markdown(f"**{label}**")

    for art in arts:
        # Строка как карточка на фоне страницы (NFR-9): контейнер +
        # метка .ap-row-mark для CSS; редактируемая статья подсвечена
        with st.container(border=True):
            cur_cls = (
                "ap-row-mark ap-row-current"
                if st.session_state.art_edit_id == art["id"]
                else "ap-row-mark"
            )
            st.markdown(f'<span class="{cur_cls}"></span>', unsafe_allow_html=True)
            cols = st.columns(widths)
            delta = calc.article_delta(art["plan"], art["fact"])
            # Подписи для узкого экрана (NFR-9): тот же список labels,
            # что в шапке таблицы — один источник подписей
            lb_plan, lb_fact = labels[1], labels[2]
            if scenario is not None:
                lb_calc, lb_dev, lb_comment = labels[3], labels[4], labels[5]
            else:
                lb_dev, lb_comment = labels[3], labels[4]
            with cols[0]:
                # Без подписи: в узком виде категория — заголовок карточки
                st.write(art["category"])
                if art["plan"] is None:
                    st.caption("Статья без плана")
            # BR-4: план NULL — «не внесено» («—»), 0 — явный ноль
            # FR-6: у переменной статьи под суммами — расчётный ₽/чел
            rate_plan = rate_fact = None
            if art["per_person"]:
                if art["plan"] is not None:
                    rate_plan = calc.per_guest(art["plan"], ev["guests"])
                rate_fact = calc.per_guest(art["fact"], ev["guests"])
            cols[1].markdown(
                f'{_ap_cl(lb_plan)}'
                + ("—" if art["plan"] is None else calc.format_money(art["plan"]))
                + _ap_rate(rate_plan),
                unsafe_allow_html=True,
            )
            cols[2].markdown(
                f"{_ap_cl(lb_fact)}{calc.format_money(art['fact'])}"
                f"{_ap_rate(rate_fact)}",
                unsafe_allow_html=True,
            )

            if scenario is not None:
                # Колонка «Расчёт» (FR-16): значение сценария по статье,
                # выделено цветом и полужирным
                srow = scenario_rows.get(art["id"])
                if srow is None or srow["value"] is None:
                    cols[3].markdown(
                        f"{_ap_cl(lb_calc, blue=True)}—", unsafe_allow_html=True
                    )
                    if srow is not None and srow["no_plan"]:
                        cols[3].caption("не внесено")
                else:
                    cols[3].markdown(
                        f'{_ap_cl(lb_calc, blue=True)}'
                        f":blue[**{calc.format_money(srow['value'])}**]",
                        unsafe_allow_html=True,
                    )
                dev_col, comment_col, actions_col = cols[4], cols[5], cols[6]
            else:
                dev_col, comment_col, actions_col = cols[3], cols[4], cols[5]

            if delta is None:
                dev_col.markdown(
                    f"{_ap_cl(lb_dev)}—", unsafe_allow_html=True
                )
            elif delta < 0:
                dev_col.markdown(
                    f'{_ap_cl(lb_dev)}:red[**{calc.format_money(delta)}**]',
                    unsafe_allow_html=True,
                )
                # BR-3: сигнальная подпись — там же, где красное отклонение
                dev_col.caption(":red[Перерасход]")
            else:
                dev_col.markdown(
                    f'{_ap_cl(lb_dev)}'
                    f"{'+' if delta > 0 else ''}{calc.format_money(delta)}",
                    unsafe_allow_html=True,
                )

            comment_col.markdown(
                f"{_ap_cl(lb_comment)}{html.escape(art['comment'] or '—')}",
                unsafe_allow_html=True,
            )

            if view_only:
                continue
            with actions_col:
                confirming = st.session_state.art_confirm_delete == art["id"]
                if confirming:
                    d1, d2 = st.columns(2)
                    d1.button(
                        "Да", key=f"art-del-yes-{art['id']}",
                        on_click=_do_delete_article, args=(art["id"],),
                    )
                    d2.button(
                        "Нет", key=f"art-del-no-{art['id']}",
                        on_click=_cancel_delete_article,
                    )
                else:
                    e1, e2 = st.columns(2)
                    e1.button(
                        "Изменить", key=f"art-edit-{art['id']}",
                        on_click=_start_edit_article, args=(art["id"],),
                    )
                    e2.button(
                        "Удалить", key=f"art-del-{art['id']}",
                        on_click=_ask_delete_article, args=(art["id"],),
                    )
                if confirming:
                    st.caption("Удалить статью?")

    # Возврат к списку и дублирование кнопки добавления статьи внизу
    bottom_act = st.columns([1, 1])
    bottom_act[0].button(
        "← К списку событий", key="btn-back-events-2", on_click=_go_to_events
    )
    if not view_only and bottom_act[1].button(
        "+ Добавить статью" if not st.session_state.art_form_open else "Скрыть форму",
        key="btn-toggle-article-form-bottom",
    ):
        if st.session_state.art_form_open:
            _close_article_form()
        else:
            st.session_state.art_form_open = True
            st.session_state.art_errors = []
            st.session_state.art_form_scroll = True
        st.rerun()


def render_summary_screen():
    """Сводка с графиком (FR-9, §5.4): те же данные build_summary (NFR-8)."""
    st.title("Сводка с графиком")

    ev = None
    if st.session_state.selected_event_id:
        ev = db.get_event(st.session_state.selected_event_id)

    if not ev:
        st.info("Выберите событие в списке")
        st.button("← К списку событий", key="btn-back-events-3", on_click=_go_to_events)
        return

    client_line = f" · Клиент: {ev['client']}" if ev["client"] else ""
    st.caption(f"Событие: {ev['name']}{client_line}")
    # Возврат в копию (FR-15), если пришли из неё через прообраз
    _nav = st.session_state.nav_back
    _nav_ev = db.get_event(_nav) if _nav else None
    if _nav_ev and _nav_ev["parent_id"] == ev["id"]:
        st.button(
            "← Вернуться в копию", key="summary-nav-back",
            on_click=_open_budget, args=(_nav_ev["id"],),
        )
    arts = db.articles_of(ev["id"])
    payments_list = db.payments_of(ev["id"])
    paid_total = sum(float(p.get("amount") or 0) for p in payments_list)

    summary = calc.build_summary(
        ev["budget_limit"], ev["guests"], arts, paid_total
    )

    # Метрики (TZ §5.4): итоги, остатки лимита, ₽/гость, перерасход, статус лимита
    row1 = st.columns(4)
    row1[0].metric("Итого план", calc.format_money(summary["plan_total"]))
    row1[1].metric("Итого факт", calc.format_money(summary["fact_total"]))
    row1[2].metric("Остаток лимита (план)", calc.format_money(summary["balance_plan"]))
    row1[3].metric("Остаток лимита (факт)", calc.format_money(summary["balance_fact"]))

    row2 = st.columns(4)
    plan_pg = summary["plan_per_guest"]
    fact_pg = summary["fact_per_guest"]
    row2[0].metric(
        "На гостя (план)",
        calc.format_money(plan_pg) if plan_pg is not None else "—",
    )
    row2[1].metric(
        "На гостя (факт)",
        calc.format_money(fact_pg) if fact_pg is not None else "—",
    )
    over_total, over_count = summary["over_total"], summary["over_count"]
    row2[2].metric(
        "Перерасход по статьям",
        calc.format_money(over_total) if over_total > 0 else "—",
    )
    if over_total > 0:
        st.caption(f"Перерасход по статьям — у {over_count} из {summary['articles_count']} статей")
    if summary["under_total"] > 0:
        st.caption(
            f"Экономия по статьям — {calc.format_money(summary['under_total'])} "
            f"у {summary['under_count']} из {summary['articles_count']} статей"
        )
    if summary["balance_fact"] < 0:
        row2[3].metric("Статус лимита", "Перерасход")
    else:
        row2[3].metric("Статус лимита", "В пределах")

    # Оплаты клиента (FR-7): «в пределах лимита» — обычным видом; выделена
    # только оплата по факту — красным остаток, зелёная переплата/полная оплата
    row3 = st.columns(4)
    row3[0].metric("Внесено клиентом", calc.format_money(summary["client_paid"]))
    row3[1].metric(
        "Остаток в пределах лимита", calc.format_money(summary["remain_limit"])
    )
    if summary["remain_limit_note"]:
        row3[1].caption(summary["remain_limit_note"])
    row3[2].metric(
        "Осталось внести по плану", calc.format_money(summary["remain_plan"])
    )
    if summary["remain_plan_note"]:
        row3[2].caption(summary["remain_plan_note"])
    row3[3].markdown(
        _pay_fact_html(summary["remain_fact"], summary["remain_fact_note"]),
        unsafe_allow_html=True,
    )

    st.divider()

    # Диаграммы структуры расходов (FR-9) — из того же набора статей, что и
    # сводка/таблица (NFR-8); агрегация — calc.chart_data
    rows = calc.chart_data(arts)
    plan_rows = [r for r in rows if r["plan"] > 0]
    fact_rows = [r for r in rows if r["fact"] > 0]

    st.markdown("#### Структура расходов по категориям")
    chart_cols = st.columns(2)

    with chart_cols[0]:
        if plan_rows:
            fig_plan = go.Figure(
                go.Pie(
                    labels=[r["category"] for r in plan_rows],
                    values=[r["plan"] for r in plan_rows],
                    hole=0.35,
                    sort=False,
                )
            )
            fig_plan.update_layout(
                title="План", height=380, margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_plan, width="stretch")
        else:
            st.info("План не внесён — диаграмма появится после заполнения плана")

    with chart_cols[1]:
        if fact_rows:
            fig_fact = go.Figure(
                go.Pie(
                    labels=[r["category"] for r in fact_rows],
                    values=[r["fact"] for r in fact_rows],
                    hole=0.35,
                    sort=False,
                )
            )
            fig_fact.update_layout(
                title="Факт", height=380, margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_fact, width="stretch")
        else:
            st.info("Факт не внесён — диаграмма появится после заполнения факта")

    # Экспорт отчёта клиенту (FR-11): utf-8-sig и «;» для Excel; данные из summary (NFR-8)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerows(calc.report_rows(ev, summary, arts, payments_list))
    st.download_button(
        "Скачать отчёт (CSV)",
        data=buffer.getvalue().encode("utf-8-sig"),
        file_name=f"otchet-sobytiya-{ev['id']}.csv",
        mime="text/csv",
    )

    st.button("← К списку событий", key="btn-back-events-4", on_click=_go_to_events)


if st.session_state.screen == "Список событий":
    render_events_screen()
elif st.session_state.screen == "Бюджет события":
    render_budget_screen()
else:
    render_summary_screen()

# Фиксируем экран для логики восстановления поиска (FR-14)
st.session_state["_last_render_screen"] = st.session_state.screen
