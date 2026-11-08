#!/usr/bin/env python3
"""Сборка data/hathapradipika.json из двух PDF о «Хат̣хапрадӣпикā».

Источник — русский и английский тома одного исследования: пятнадцать āсан
(стихи 1.19–1.54 критического электронного издания «Light on Haṭha Yoga»,
Оксфорд – Марбург, 2024) вместе с рамкой главы — 1.17–1.18, 1.33–1.34 и
1.55–1.56. Скрипт ничего не сочиняет: он раскладывает текст издания по полям
сайта и проверяет, что каждая содержательная строка исходника попала в данные.

Структура тома:

    шапка (титул, аннотация, «Содержание»)   → страница «О трактате»
    «Как читать аппарат», таблица рукописей  → страница «Приложение»
    «Датировки рукописей: что известно»      → статья «Датировка»
    «Введение», «Четыре главные āсаны»,
    «Переход к пра̄н̣āйāме»                    → страница «Вступление»
    1–15. пятнадцать āсан                    → пятнадцать страниц āсан
    «Сводная статистика», «Особые случаи»    → страница «Примечания»

Запуск:  .venv/bin/python tools/extract_hathapradipika.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hathapradipika.json"

PDF = {
    "ru": ROOT / "sources" / "Хат̣хапрадӣпика̄_ все 15 а̄сан — полный разбор "
                      "по критическому изданию (Оксфорд – Марбург, 2024).pdf",
    "en": ROOT / "sources" / "Haṭhapradīpikā_ all 15 āsanas — a full study "
                            "based on the critical edition "
                            "(Oxford – Marburg, 2024).pdf",
}

# Подписи транслитераций внутри стиха: в русском томе их три, в английском
# две — кириллица нужна только русскому читателю.
VLABELS = {
    "deva": ("Деванагари", "Devanagari"),
    "iast": ("IAST",),
    "cyr": ("Кириллическая транслитерация",),
}

# Подписи, которые стоят отдельной строкой и открывают блок.
LABELS = {
    "apparatus": ("Разночтения по рукописям",
                  "Variant readings in the manuscripts"),
    "footnotes": ("Сноски издания о рукописях",
                  "Edition footnotes about the manuscripts"),
    "words": ("Пословный разбор", "Word-by-word analysis"),
    "literal": ("Буквальный перевод", "Literal translation"),
    "literary": ("Литературный перевод", "Literary translation"),
}

# Подписи, набранные в начале абзаца: полужирным идёт только подпись, дальше
# двоеточие и текст. Без двоеточия это не подпись, а обычная фраза.
RUNIN = {
    "edition": ("Перевод издания (английский)",
                "Edition translation (English)"),
    "own": ("По-русски (наш подстрочник)", "Our rendering"),
    "metre": ("Метр", "Metre"),
    "parallels": ("Параллельные места в других текстах",
                  "Parallel passages in other texts"),
    "sources": ("Источники (места, откуда взят стих)",
                "Sources (where the verse comes from)"),
    "verse_page": ("Страница стиха в электронном издании",
                   "Verse page in the electronic edition"),
    "commentary": ("Комментарий редакторов издания",
                   "Editors’ commentary", "Editors' commentary"),
    "orig": ("Оригинал по-английски", "Original in English"),
}

# Сквозные заголовки тома.
HEADINGS = {
    "contents": ("Содержание", "Contents"),
    "apparatus": ("Как читать аппарат", "How to read the apparatus"),
    "manuscripts": ("Что это за рукописи", "What these manuscripts are"),
    "dating": ("Датировки рукописей", "Dates of the manuscripts"),
    "statistics": ("Сводная статистика", "Summary statistics"),
    "cases": ("Особые случаи", "Special cases"),
}

# Разделы без позы: рамка главы об āсанах.
FRAME = {
    "intro": ("Введение: почему", "Introduction: why"),
    "four": ("Четыре главные", "The four principal"),
    "pranayama": ("Переход к пра̄н̣а̄йа̄ме", "Transition to prāṇāyāma"),
}

# Пятнадцать āсан в порядке издания: ключ сайта → начало заголовка раздела.
POSE_HEADS = {
    "svastikasana": ("1. Свастика̄сана", "1. Svastikāsana"),
    "gomukhasana": ("2. Гомукха̄сана", "2. Gomukhāsana"),
    "virasana": ("3. Вӣра̄сана", "3. Vīrāsana"),
    "kurmasana": ("4. Кӯрма̄сана", "4. Kūrmāsana"),
    "kukkutasana": ("5. Куккут̣а̄сана", "5. Kukkuṭāsana"),
    "uttanakurmaka": ("6. Утта̄накӯрмака", "6. Uttānakūrmaka"),
    "dhanurasana": ("7. Дханура̄сана", "7. Dhanurāsana"),
    "matsyendrapitha": ("8. Матсьендра̄сана", "8. Matsyendrāsana"),
    "pashchimatana": ("9. Паш́чимата̄на", "9. Paścimatāṇa"),
    "mayurasana": ("10. Майӯра̄сана", "10. Mayūrāsana"),
    "shavasana": ("11. Ш́ава̄сана", "11. Śavāsana"),
    "siddhasana": ("12. Сиддха̄сана", "12. Siddhāsana"),
    "padmasana": ("13. Падма̄сана", "13. Padmāsana"),
    "simhasana": ("14. Сим̣ха̄сана", "14. Siṃhāsana"),
    "bhadrasana": ("15. Бхадра̄сана", "15. Bhadrāsana"),
}
POSE_ORDER = list(POSE_HEADS)

# Название позы в IAST — как в заголовке раздела издания.
POSE_IAST = {
    "svastikasana": "Svastikāsana",
    "gomukhasana": "Gomukhāsana",
    "virasana": "Vīrāsana",
    "kurmasana": "Kūrmāsana",
    "kukkutasana": "Kukkuṭāsana",
    "uttanakurmaka": "Uttānakūrmaka",
    "dhanurasana": "Dhanurāsana",
    "matsyendrapitha": "Matsyendrāsana",
    "pashchimatana": "Paścimatāṇa",
    "mayurasana": "Mayūrāsana",
    "shavasana": "Śavāsana",
    "siddhasana": "Siddhāsana",
    "padmasana": "Padmāsana",
    "simhasana": "Siṃhāsana",
    "bhadrasana": "Bhadrāsana / Gorakṣāsana",
}

# Таблицы тома: заголовок первой колонки → отступы колонок.
# pymupdf отдаёт каждую ячейку отдельным блоком, поэтому таблица собирается
# заново: по x определяется колонка, по y — строка.
TABLES = {
    "contents": {"head": ("Раздел", "Section"), "cols": (61.9, 302.7)},
    "manuscripts": {"head": ("Как названо в этом документе",
                             "As named in this document"),
                    "cols": (61.9, 222.5, 382.9)},
    "statistics": {"head": ("Рукопись (как названа", "Manuscript (as named"),
                   "cols": (61.9, 222.5, 382.9)},
    "witnesses": {"head": ("Стих", "Verse"),
                  "cols": (61.9, 302.7)},
}

# Пометка «итоговый раздел» стоит в содержании второй колонкой, но в русском
# томе она слиплась с названием раздела в одну строку.
TOC_MARK = {"ru": "итоговый раздел", "en": "closing section"}

FOOTER = re.compile(r"(Хаṭхапрадипика|Haṭhapradīpikā) — (а̄саны|āsanas)")
VERSE_RANGE = r"\d+\.\d+(?:[–-]\d+)?"
VERSE_HEAD = {"ru": re.compile(r"^Стих (" + VERSE_RANGE + ")"),
              "en": re.compile(r"^Verse (" + VERSE_RANGE + ")")}
VERSE_LIST = {"ru": re.compile(r"^Стихи:\s*"), "en": re.compile(r"^Verses:\s*")}
SENT_END = (".", "!", "?", "…", "»", "”")
CELL_GAP = 12.0          # внутри строки таблицы строки текста идут теснее
TABLE_X = 59.0           # текст абзацев начинается левее (56.7 / 76.2)
COLUMN_TOL = 8.0         # насколько ячейка может отойти от своего отступа


# ------------------------------------------------------------------ чтение PDF

def norm(text: str) -> str:
    text = text.replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def page_lines(lang: str):
    """Строки страниц без склейки: нужны, чтобы не потерять отступы таблиц."""
    doc = pymupdf.open(PDF[lang])
    for pno, page in enumerate(doc):
        rows = []
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                raw = "".join(span["text"] for span in line["spans"])
                text = norm(raw)
                if not text or FOOTER.search(text):
                    continue
                spans = [(s["text"], "Bold" in s["font"]) for s in line["spans"]]
                rows.append({
                    "text": text,
                    "raw": raw,
                    "trail": bool(re.search(r"[ \t]$", raw.rstrip("\u200b"))),
                    "x": round(line["bbox"][0], 1),
                    "y": round(line["bbox"][1], 1),
                    "size": round(max(s["size"] for s in line["spans"]), 1),
                    "spans": spans,
                    "page": pno + 1,
                })
        rows.sort(key=lambda l: (round(l["y"]), l["x"]))
        yield pno + 1, rows


def read_lines(lang: str) -> list[dict]:
    out = []
    for _, rows in page_lines(lang):
        out.extend(rows)
    return out


def read_blocks(lang: str) -> list[dict]:
    """Абзацы издания: pymupdf уже режет страницу на абзацы."""
    doc = pymupdf.open(PDF[lang])
    blocks = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            lines = []
            for line in block.get("lines", []):
                raw = "".join(span["text"] for span in line["spans"])
                text = norm(raw)
                if not text or FOOTER.search(text) or re.fullmatch(r"\|\s*\d+", text):
                    continue
                # выноска markdown в самом издании набрана знаком «>»
                if text == ">":
                    continue
                if text.startswith("> "):
                    text = text[2:]
                    raw = raw.replace(">", "", 1)
                lines.append({
                    "text": text,
                    "trail": bool(re.search(r"[ \t]$", raw.rstrip("\u200b"))),
                    "x": round(line["bbox"][0], 1),
                    "y": round(line["bbox"][1], 1),
                    "size": round(max(s["size"] for s in line["spans"]), 1),
                    "spans": [(s["text"], "Bold" in s["font"])
                              for s in line["spans"]],
                })
            if not lines:
                continue
            lines.sort(key=lambda l: (round(l["y"]), l["x"]))
            merged = []
            for line in lines:
                if merged and abs(line["y"] - merged[-1]["y"]) <= 3.0:
                    merged[-1]["text"] += " " + line["text"]
                    merged[-1]["trail"] = line["trail"]
                    merged[-1]["spans"] = merged[-1]["spans"] + line["spans"]
                else:
                    merged.append(dict(line))
            blocks.append({"page": pno + 1, "y": merged[0]["y"], "lines": merged})
    return join_pages(blocks)


def join_pages(blocks: list[dict]) -> list[dict]:
    """Абзац, разорванный концом страницы, остаётся одним абзацем."""
    out = []
    for block in blocks:
        last = out[-1] if out else None
        if (last and last["page"] == block["page"] - 1
                and last["lines"][-1]["y"] > 745
                and block["y"] < 60
                and last["lines"][-1]["text"][-1:] not in SENT_END
                and block["lines"][0]["size"] == last["lines"][-1]["size"]
                and bold_frac(last["lines"][-1]) < 0.9
                and bold_frac(block["lines"][0]) < 0.9):
            last["lines"].extend(block["lines"])
            continue
        out.append(block)
    return out


# ------------------------------------------------------------------- склейки

# Слово, разорванное выключкой (в узкой колонке или на границе строки):
# в этих томах разрыв идёт без переноса, поэтому его приходится чинить вручную.
FIX: list[tuple[str, str]] = []


def fix(text: str) -> str:
    for broken, whole in FIX:
        text = text.replace(broken, whole)
    return text


def join_lines(lines: list[dict]) -> str:
    """Строки абзаца подряд без потери слов.

    Если строка кончилась пробелом (в PDF он есть, хотя визуально не виден),
    между строками ставится пробел; если пробела нет — слово было разорвано
    выключкой, и части склеиваются.
    """
    text = ""
    prev = None
    for line in lines:
        if prev is None:
            text = line["text"]
        elif prev["text"].endswith("-"):
            text = text + line["text"]
        elif prev["trail"] or not prev["text"][-1:].isalpha() \
                or not line["text"][:1].islower():
            text = text + " " + line["text"]
        else:
            text = text + line["text"]
        prev = line
    return fix(text)


def escaped(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


# ------------------------------------------------------------------ разметка

def bold_frac(line: dict) -> float:
    total = bold = 0
    for text, is_bold in line["spans"]:
        for char in text:
            if char.isspace():
                continue
            total += 1
            bold += 1 if is_bold else 0
    return bold / total if total else 0.0


def prefix_bold(line: dict, prefix: str) -> float:
    """Доля полужирных знаков ровно в той части строки, что совпала с подписью."""
    want = [c for c in prefix if not c.isspace()]
    i = total = bold = 0
    for text, is_bold in line["spans"]:
        for char in text:
            if char.isspace():
                continue
            if i >= len(want):
                return bold / total if total else 0.0
            if char != want[i]:
                return 0.0
            i += 1
            total += 1
            bold += 1 if is_bold else 0
    return bold / total if total else 0.0


def label_of(text: str, table: dict) -> str:
    probe = text.rstrip(":").strip()
    for key, names in table.items():
        for name in names:
            if probe == name:
                return key
    return ""


PAGE_REF = re.compile(r"^[^:]{4,80}: #[A-Za-z0-9_]+$")


def is_page_ref(text: str) -> bool:
    """«Страница стиха в электронном издании: #hp01_017» — набрана не жирным."""
    return bool(PAGE_REF.match(text))


def runin_split(text: str, line: dict):
    """Подпись в начале абзаца: до двоеточия, полужирная, из списка RUNIN."""
    pos = text.find(":")
    if pos < 0 or pos > 160:
        return None
    label = text[:pos].strip()
    for key, names in RUNIN.items():
        for name in names:
            if not label.startswith(name):
                continue
            if prefix_bold(line, label) > 0.5 or is_page_ref(text):
                return key, label, text[pos + 1:].strip()
    return None


def runin_name(text: str):
    """Полужирная строка-подпись, набранная без текста после двоеточия."""
    probe = text.rstrip(":").strip()
    for key, names in RUNIN.items():
        for name in names:
            if probe.startswith(name):
                return key
    return None


def classify(block: dict, lang: str) -> list[dict]:
    """Абзац → элемент разметки."""
    lines = block["lines"]
    text = join_lines(lines)
    first = lines[0]
    if first["size"] >= 18.0:
        return [{"kind": "h1", "text": text}]
    if first["size"] >= 14.5:
        return [{"kind": "h2", "text": text}]
    if first["size"] >= 12.0 and VERSE_HEAD[lang].match(text):
        return [{"kind": "h4", "text": text,
                 "verse": VERSE_HEAD[lang].match(text).group(1)}]
    if first["size"] >= 12.0:
        return [{"kind": "h3", "text": text}]
    if all(bold_frac(line) > 0.9 for line in lines):
        key = label_of(text, dict(VLABELS, **LABELS))
        if key:
            return [{"kind": "label", "key": key, "text": text.rstrip(":")}]
        key = runin_name(text)
        if key:
            return [{"kind": "runin", "key": key, "label": text.rstrip(":"),
                     "rest": ""}]
        return [{"kind": "label", "key": "misc", "text": text.rstrip(":"),
                 "runin_like": bool(runin_name(text))}]
    hit = runin_split(text, first)
    if hit:
        key, label, rest = hit
        return [{"kind": "runin", "key": key, "label": label, "rest": rest}]
    return [{"kind": "p", "text": text, "lines": lines}]


# ------------------------------------------------------------------- таблицы

def column_of(line: dict, cols: tuple[float, ...]) -> int:
    col, best = 0, COLUMN_TOL
    for idx, x in enumerate(cols):
        if abs(line["x"] - x) < best:
            best = abs(line["x"] - x)
            col = idx
    return col


def build_rows(rows: list[dict], cols: tuple[float, ...]) -> list[list[str]]:
    """Строки таблицы: новая строка начинается там, где есть первая колонка.

    Строка таблицы может перейти со страницы на страницу (так набрана таблица
    свидетелей), поэтому меряем не только y, но и номер страницы. Ячейки одной
    строки стоят на одной высоте с разбросом в пару пунктов, поэтому сначала
    собираются начала строк, а уже потом к ним подвешиваются прочие ячейки.
    """
    zero = [l for l in rows if column_of(l, cols) == 0]
    other = [l for l in rows if column_of(l, cols) != 0]
    out = []
    for line in zero:
        new_row = not out
        if not new_row:
            last_page, last_y = out[-1]["last"]
            if line["page"] != last_page or line["y"] - last_y > CELL_GAP:
                new_row = True
        if new_row:
            out.append({"start": (line["page"], line["y"]),
                        "last": (line["page"], line["y"]),
                        "cells": [[] for _ in cols]})
        else:
            out[-1]["last"] = (line["page"], line["y"])
        out[-1]["cells"][0].append(line)
    for line in other:
        target = None
        for row in reversed(out):
            if row["start"] <= (line["page"], line["y"] + 3.0):
                target = row
                break
        if target is None:
            continue
        target["cells"][column_of(line, cols)].append(line)
    return [[join_lines(cell) for cell in row["cells"]] for row in out if row["cells"][0]]


def drop_pages_headers(part: list[dict], cols: tuple[float, ...], head: str) -> tuple[list[dict], list[dict]]:
    """Повторный заголовок каждой страницы: его строки в таблицу не идут."""
    bands = []
    for line in part:
        if abs(line["x"] - cols[0]) <= COLUMN_TOL and line["text"].startswith(head):
            bands.append((line["page"], line["y"]))
    if not bands:
        return [], part
    kept, dropped = [], []
    for line in part:
        hit = any(page == line["page"] and y - 1.0 <= line["y"] <= y + 12.5
                  for page, y in bands)
        (dropped if hit else kept).append(line)
    return dropped, kept


def table(key: str, lang: str, lines: list[dict]):
    """Таблица по её заголовку: от первой строки заголовка до первого абзаца."""
    spec = TABLES[key]
    head = spec["head"][0 if lang == "ru" else 1]
    start = None
    for i, line in enumerate(lines):
        if line["x"] >= TABLE_X and line["text"].startswith(head):
            start = i
            break
    if start is None:
        return None
    part: list[dict] = []
    for line in lines[start:]:
        # таблица кончается там, где строка перестаёт стоять на отступе колонки
        if line["x"] < TABLE_X:
            break
        if min(abs(line["x"] - x) for x in spec["cols"]) > COLUMN_TOL:
            break
        part.append(line)
    if not part:
        return None
    dropped, part = drop_pages_headers(part, spec["cols"], head)
    rows = build_rows(part, spec["cols"])
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    header = None
    if dropped:
        header = build_rows(dropped, spec["cols"])[0]
    if header:
        rows = [row for row in rows if row != header]
        rows.insert(0, header)
    edges = part[0] if not dropped else dropped[0]
    return {"rows": rows, "first": edges, "last": part[-1] if part else edges}


def span_of(tab: dict) -> tuple[tuple[int, float], tuple[int, float]]:
    first, last = tab["first"], tab["last"]
    return (first["page"], first["y"] - 1.0), (last["page"], last["y"] + 1.0)


def inside(block: dict, ranges: list) -> bool:
    here = (block["page"], block["y"])
    return any(lo <= here <= hi for lo, hi in ranges)


def fix_contents(table_obj: dict, lang: str) -> None:
    """«итоговый раздел» — вторая колонка содержания, слипшаяся с первой."""
    mark = TOC_MARK[lang]
    for row in table_obj["rows"]:
        for i in (0, 1):
            cell = row[i]
            if not cell or mark not in cell:
                continue
            other = 1 - i
            if row[other]:
                continue
            rest = cell.replace(mark, "").strip(" ,;—-")
            if len(rest) < 3:
                continue
            row[i] = rest
            row[other] = mark


# ------------------------------------------------------------------- сборка

class Sequence:
    """Линейный разбор раздела: стихи, подписи, переводы, таблицы."""

    def __init__(self, lang: str):
        self.lang = lang
        self.blocks: list[dict] = []
        self.para: list[dict] = []
        self.card: list[dict] = []
        self.card_verse = ""
        self.collect: dict | None = None
        self.section: dict | None = None      # открытая карточка-стих

    # --- сбросы -----------------------------------------------------------
    def flush_para(self) -> None:
        if self.para:
            self.blocks.append({"type": "p", "text": join_lines(self.para)})
            self.para = []

    def flush_card(self) -> None:
        if self.card:
            self.blocks.append({"type": "verse_card", "verses": self.card_verse,
                                "sections": self.card})
        self.card = []
        self.card_verse = ""

    def flush_collect(self) -> None:
        if self.collect is None:
            return
        block, self.collect = self.collect, None
        items = [x for x in block["items"] if x]
        if not items:
            self.blocks.append({"type": "label", "label": block["label"]})
            return
        key = block["key"]
        label = block["label"]
        if key == "apparatus":
            self.blocks.append({"type": "list", "ordered": False, "label": label,
                                "items": [{"html": escaped(t)} for t in items]})
        elif key == "words":
            groups = [split_words(t, self.lang) for t in items]
            out = {"type": "words", "label": label}
            if all(g[1] for g in groups):
                out["groups"] = [g[1] for g in groups]
                out["titles"] = [g[0] for g in groups]
            else:
                out["paragraphs"] = items
            self.blocks.append(out)
        else:
            self.blocks.append({"type": "prose", "key": key, "label": label,
                                "paragraphs": items})

    def flush_all(self) -> None:
        self.flush_para()
        self.flush_collect()
        self.flush_card()

    # --- разбор -----------------------------------------------------------
    def feed(self, token: dict, block: dict) -> None:
        kind = token["kind"]
        if kind == "h4":
            self.flush_all()
            self.blocks.append({"type": "h4", "text": token["text"]})
            self.card_verse = token["verse"]
        elif kind == "label":
            if token["key"] in ("deva", "iast", "cyr"):
                self.flush_para()
                self.flush_collect()
                self.section = {"type": "verse", "key": token["key"],
                                "label": token["text"], "lines": []}
                self.card.append(self.section)
            else:
                self.flush_all()
                self.collect = {"key": token["key"], "label": token["text"],
                                "items": []}
        elif kind == "runin":
            if token["key"] == "verse_page":
                self.flush_all()
                text = token["label"] + (": " + token["rest"] if token["rest"] else "")
                self.blocks.append({"type": "p", "text": text})
            else:
                self.flush_all()
                self.collect = {"key": token["key"], "label": token["label"],
                                "items": [token["rest"]] if token["rest"] else []}
        else:                                  # p
            if self.collect is not None:
                self.collect["items"].append(token["text"])
            elif self.section is not None and not is_page_ref(token["text"]):
                self.section["lines"].extend(l["text"] for l in token["lines"])
            else:
                self.flush_para()
                self.para = list(token["lines"])

    def place(self, block: dict) -> None:
        """Таблица или иной готовый блок встаёт на своё место в потоке."""
        self.flush_all()
        self.blocks.append(block)

    def close(self) -> list[dict]:
        self.flush_all()
        return self.blocks


def split_words(text: str, lang: str):
    """Разбор «1.19. слово — значение; слово — значение» на пары."""
    match = re.match(r"^(" + VERSE_RANGE + r")\.\s*", text)
    if match:
        title = ("Стих " if lang == "ru" else "Verse ") + match.group(1)
        body = text[match.end():]
    else:
        title, body = "", text
    items, depth, start = [], 0, 0
    for i, char in enumerate(body):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            items.append(body[start:i])
            start = i + 1
    items.append(body[start:])
    pairs: list[list[str]] = []
    for item in (x.strip() for x in items):
        if not item:
            continue
        depth, cut = 0, -1
        for i, char in enumerate(item):
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and item.startswith(" - ", i):
                cut = i
                break
        if cut < 0:
            pairs.append([item, ""])
        else:
            pairs.append([item[:cut].strip(), item[cut + 3:].strip()])
    return title, pairs


# --------------------------------------------------------------- разбор тома

def target_of(label: str, lang: str) -> tuple[str, str]:
    i = 0 if lang == "ru" else 1
    for key, names in POSE_HEADS.items():
        if label.startswith(names[i]):
            return "pose", key
    for key, names in FRAME.items():
        if label.startswith(names[i]):
            return "frame", key
    for key, names in HEADINGS.items():
        if label.startswith(names[i]):
            return "part", key
    return "", ""


def segments(blocks: list[dict], lang: str):
    """Абзацы, разбитые по заголовкам: (заголовок, границы, абзацы)."""
    out = []
    cur = {"head": None, "block": None, "blocks": []}
    for block in blocks:
        tokens = classify(block, lang)
        if tokens[0]["kind"] in ("h1", "h2", "h3"):
            out.append(cur)
            cur = {"head": tokens[0], "block": block, "blocks": []}
        else:
            cur["blocks"].append(block)
    out.append(cur)
    return [seg for seg in out if seg["head"] or seg["blocks"]]


def name_gloss(heading: str):
    """«1. Свастика̄сана — «благая» поза» → номер, название, пояснение."""
    number = ""
    text = heading.strip()
    match = re.match(r"^(\d+)\.\s*", text)
    if match:
        number = match.group(1)
        text = text[match.end():]
    if " — " in text:
        name, gloss = text.split(" — ", 1)
    else:
        name, gloss = text, ""
    return number, name.strip(), gloss.strip()


def build_lang(lang: str):
    blocks = read_blocks(lang)
    lines = read_lines(lang)
    segs = segments(blocks, lang)

    doc = {"about": [], "appendix": [], "prologue": [], "notes": [],
           "dating": None, "poses": {}, "heads": {}, "closing": None,
           "title": "", "asanasTitle": "", "notesTitle": ""}
    tables: dict[str, dict] = {}

    for idx, seg in enumerate(segs):
        head = seg["head"]
        if head is None or head["kind"] == "h1":
            # шапка тома: титул и аннотация
            seq = Sequence(lang)
            if head is not None:
                seq.blocks.append({"type": "title", "text": head["text"]})
                doc["title"] = head["text"].split(":")[0].strip()
            for block in seg["blocks"]:
                for token in classify(block, lang):
                    seq.feed(token, block)
            doc["about"].extend(seq.close())
            continue

        label = head["text"]
        kind, key = target_of(label, lang)
        nxt = segs[idx + 1] if idx + 1 < len(segs) else None
        lo = (seg["block"]["page"], seg["block"]["y"] - 4.0)
        if nxt and nxt["block"] is not None:
            hi = (nxt["block"]["page"], nxt["block"]["y"] - 4.0)
        else:
            hi = (10 ** 6, 10 ** 6)
        seg_lines = [l for l in lines if lo <= (l["page"], l["y"]) < hi]
        skip = []                       # (page, y) блоков, ушедших в таблицу

        if kind == "part" and key == "contents":
            seq = Sequence(lang)
            seq.blocks.append({"type": "subhead", "label": label})
            entries = []
            tab = table("contents", lang, seg_lines)
            if tab:
                fix_contents(tab, lang)
                tables["contents"] = tab
                entries.append(span_of(tab) + ({"type": "table",
                                                "rows": tab["rows"]},))
            place_tables(seq, seg["blocks"], lang, entries)
            doc["about"].extend(seq.close())

        elif kind == "part" and key in ("apparatus", "manuscripts"):
            seq = Sequence(lang)
            seq.blocks.append({"type": "subhead", "label": label})
            if key == "apparatus":
                paras = [join_lines(b["lines"]) for b in seg["blocks"]]
                note = []
                if paras and runin_name(paras[-1]):
                    note = [paras.pop()]
                if paras:
                    seq.blocks.append({"type": "list", "ordered": False,
                                       "items": [{"html": escaped(p)}
                                                 for p in paras]})
                if note:
                    seq.blocks.append({"type": "note", "paragraphs": note})
            else:
                entries = []
                tab = table("manuscripts", lang, seg_lines)
                if tab:
                    tables["manuscripts"] = tab
                    entries.append(span_of(tab) + ({"type": "table",
                                                    "rows": tab["rows"]},))
                place_tables(seq, seg["blocks"], lang, entries)
            doc["appendix"].extend(seq.close())

        elif kind == "part" and key == "dating":
            paras = [join_lines(b["lines"]) for b in seg["blocks"]]
            doc["dating"] = {"title": label, "blocks": [
                {"type": "p", "text": p} for p in paras]}

        elif kind == "frame":
            if not doc["prologue"] or doc["prologue"][-1].get("label", "") != label:
                doc["prologue"].append({"type": "subhead", "label": label})
            seq = Sequence(lang)
            for block in seg["blocks"]:
                for token in classify(block, lang):
                    seq.feed(token, block)
            doc["prologue"].extend(seq.close())

        elif kind == "pose":
            seq = Sequence(lang)
            doc["heads"][key] = label
            for block in seg["blocks"]:
                for token in classify(block, lang):
                    seq.feed(token, block)
            doc["poses"][key] = seq.close()

        elif kind == "part" and key == "statistics":
            seq = Sequence(lang)
            seq.blocks.append({"type": "subhead", "label": label})
            entries = []
            tab = table("statistics", lang, seg_lines)
            if tab:
                tables["statistics"] = tab
                entries.append(span_of(tab) + ({"type": "table",
                                                "rows": tab["rows"]},))
                tail = [l for l in seg_lines
                        if (l["page"], l["y"]) > (tab["last"]["page"],
                                                  tab["last"]["y"])]
            else:
                tail = seg_lines
            wit = table("witnesses", lang, tail)
            if wit:
                tables["witnesses"] = wit
                entries.append(span_of(wit) + ({"type": "table",
                                                "rows": wit["rows"]},))
            place_tables(seq, seg["blocks"], lang, entries)
            doc["notes"].extend(seq.close())

        elif kind == "part" and key == "cases":
            seq = Sequence(lang)
            seq.blocks.append({"type": "subhead", "label": label})
            paras = [join_lines(b["lines"]) for b in seg["blocks"]]
            closing = []
            items = []
            for p in paras:
                if re.match(r"^\d+\.\s", p):
                    items.append(p)
                else:
                    closing.append(p)
            if items:
                seq.blocks.append({"type": "list", "ordered": False,
                                   "items": [{"html": escaped(p)} for p in items]})
            if closing:
                seq.blocks.append({"type": "note", "paragraphs": closing})
                doc["closing"] = closing
            doc["notes"].extend(seq.close())

        else:
            raise SystemExit(f"{lang}: некуда положить раздел «{label}»")

    poses = []
    for key in POSE_ORDER:
        if key not in doc["poses"]:
            raise SystemExit(f"{lang}: нет раздела позы {key}")
        poses.append((key, doc["poses"][key], doc["heads"][key]))
    return doc, poses, tables


def place_tables(seq: Sequence, seg_blocks: list[dict], lang: str,
                 entries: list) -> None:
    """Таблицы вставляются туда, где они стоят в томе: по первому их блоку."""
    placed: set[int] = set()
    spans = [(lo, hi) for lo, hi, _ in entries]
    for block in seg_blocks:
        here = (block["page"], block["y"])
        for idx, (lo, hi, table_block) in enumerate(entries):
            if idx not in placed and lo <= here <= hi:
                seq.place(table_block)
                placed.add(idx)
        if any(lo <= here <= hi for lo, hi in spans):
            continue
        tokens = classify(block, lang)
        if tokens[0]["kind"] == "p" and block["lines"][0]["size"] < 10.0:
            seq.place({"type": "note", "paragraphs": [tokens[0]["text"]]})
            continue
        for token in tokens:
            seq.feed(token, block)
    for idx, (lo, hi, table_block) in enumerate(entries):
        if idx not in placed:
            seq.place(table_block)


def first_paragraph(blocks: list[dict]) -> str:
    for block in blocks:
        if block["type"] == "p":
            return block["text"]
    return ""


def build() -> dict:
    ru, ru_poses, ru_tables = build_lang("ru")
    en, en_poses, en_tables = build_lang("en")

    poses = []
    for number, ((key, ru_text, ru_head), (key_en, en_text, en_head)) in enumerate(
            zip(ru_poses, en_poses), start=1):
        assert key == key_en, (key, key_en)
        ru_num, ru_name, ru_gloss = name_gloss(ru_head)
        en_num, en_name, en_gloss = name_gloss(en_head)
        verses = {"ru": "", "en": ""}
        for block in ru_text:
            if block["type"] == "p" and VERSE_LIST["ru"].match(block["text"]):
                verses["ru"] = VERSE_LIST["ru"].sub("", block["text"]).strip()
                break
        for block in en_text:
            if block["type"] == "p" and VERSE_LIST["en"].match(block["text"]):
                verses["en"] = VERSE_LIST["en"].sub("", block["text"]).strip()
                break
        poses.append({
            "key": key,
            "iast": POSE_IAST[key],
            "number": number,
            "name": {"ru": ru_name, "en": en_name},
            "gloss": {"ru": ru_gloss, "en": en_gloss},
            "verses": verses,
            "text": {"ru": ru_text, "en": en_text},
        })

    doc = {
        "id": "hathapradipika",
        "chapter": 1,
        "title": {"ru": ru["title"], "en": en["title"]},
        "asanasTitle": {"ru": f"Āсаны «{ru['title']}»",
                        "en": f"The āsanas of the {en['title']}"},
        "notesTitle": {"ru": "Сводная статистика и особые случаи",
                       "en": "Summary statistics and special cases"},
        "about": {"ru": ru["about"], "en": en["about"]},
        "prologue": {"ru": ru["prologue"], "en": en["prologue"]},
        "dating": {"ru": ru["dating"], "en": en["dating"]},
        "datingSummary": DATING_SUMMARY,
        "appendix": {"ru": ru["appendix"], "en": en["appendix"]},
        "notes": {"ru": ru["notes"], "en": en["notes"]},
        "closing": {"ru": ru["closing"] or [], "en": en["closing"] or []},
        "poses": poses,
    }
    return doc


# --------------------------------------------------------------- датировка

DATING_SUMMARY = {
    "label": {"ru": "На чём основано (по словам самого издания)",
              "en": "Basis (in the edition’s own words)"},
    "note": {
        "ru": "«В издании прямо датирована одна рукопись, Sarasvatī Bhavan, шифр "
              "30109, Ва̄ра̄н̣асӣ… Сплошная проверка исходников издания… дала "
              "ещё пять датированных списков».",
        "en": "“One manuscript is explicitly dated in the edition, Sarasvatī "
              "Bhavan, ms. no. 30109, Vārāṇasī… A systematic check of the "
              "edition’s sources… yielded five more dated copies.”",
    },
    "items": [
        {
            "who": {"ru": "Sarasvatī Bhavan, шифр 30109, Ва̄ра̄н̣асӣ («эта-1»)",
                    "en": "Sarasvatī Bhavan, ms. no. 30109, Vārāṇasī (“eta-1”)"},
            "when": {"ru": "1496 г. н. э.", "en": "1496 CE"},
            "work": {
                "ru": "«В издании прямо датирована одна рукопись… в комментариях "
                      "к стихам 1.24 и 1.56 редакторы называют её «oldest dated "
                      "manuscript» — старейшей датированной. Год в ридере не "
                      "напечатан; в публичных материалах проекта «Light on Haṭha "
                      "Yoga» он назван: 1496 год н. э.»",
                "en": "“One manuscript is explicitly dated in the edition… in the "
                      "comments on verses 1.24 and 1.56 the editors call it the "
                      "“oldest dated manuscript”. The year is not printed in the "
                      "reader; the project’s public materials give it as 1496 CE.”",
            },
        },
        {
            "who": {"ru": "Сва̄тма̄ра̄ма (время авторства)",
                    "en": "Svātmārāma (time of authorship)"},
            "when": {"ru": "начало XV в.", "en": "the early 15th century"},
            "work": {
                "ru": "«…всего около столетия от предполагаемого времени "
                      "авторства Сва̄тма̄ра̄мы (начало XV в.)».",
                "en": "“…only about a century from the supposed time of "
                      "Svātmārāma’s authorship (the early 15th century).”",
            },
        },
        {
            "who": {"ru": "Пять рукописей с датами в колофонах",
                    "en": "Five manuscripts dated in their colophons"},
            "when": {"ru": "1626/27, 1636/37, 1650/51, 1667/68, 1745/46",
                     "en": "1626/27, 1636/37, 1650/51, 1667/68, 1745/46"},
            "work": {
                "ru": "«Но уже сейчас картина такая: самые ранние датированные "
                      "списки — 1496 (30109), 1626/27 (MSPP 2230), 1636/37 "
                      "(29899), 1650/51 (30069), 1667/68 (Jodhpur 23709), "
                      "1745/46 (Jodhpur 02237)».",
                "en": "“But the picture is already clear: the earliest dated "
                      "copies are 1496 (30109), 1626/27 (MSPP 2230), 1636/37 "
                      "(29899), 1650/51 (30069), 1667/68 (Jodhpur 23709), "
                      "1745/46 (Jodhpur 02237).”",
            },
        },
        {
            "who": {"ru": "Для сравнения: издание Кайвальядха̄мы 1970 г.",
                    "en": "For comparison: the Kaivalyadhāma edition of 1970"},
            "when": {"ru": "1629 г. — старейшая датированная рукопись; текст: "
                           "«1350–1550»",
                     "en": "1629 — its oldest dated manuscript; the text: "
                           "“1350–1550”"},
            "work": {
                "ru": "«…издание Кайвальядха̄мы 1970 г. опиралось всего на 9 "
                      "рукописей, и его старейшая датированная рукопись — 1629 г. "
                      "(Calcutta No. TH 321); датировка самого текста там дана "
                      "широко: «1350–1550». Рукопись 1496 г. в новом корпусе — "
                      "качественный сдвиг».",
                "en": "“…the Kaivalyadhāma edition of 1970 relied on only 9 "
                      "manuscripts, and its oldest dated manuscript is from 1629 "
                      "(Calcutta No. TH 321); the date assigned to the text itself "
                      "is broad: “1350–1550”. A manuscript of 1496 in the new "
                      "corpus is a qualitative step forward.”",
            },
        },
    ],
}


# ------------------------------------------------------------------ проверки

def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200b", "")).strip()


UNESCAPE = (("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"))


def unescape(text: str) -> str:
    for a, b in UNESCAPE:
        text = text.replace(a, b)
    return text


def textbag(value, out: list[str]) -> None:
    """Все строки данных — в один список, вместе с подписями перед абзацами."""
    if isinstance(value, str):
        out.append(unescape(value))
    elif isinstance(value, list):
        if value and all(isinstance(v, list) for v in value):
            for row in value:               # строка таблицы: ячейки подряд
                textbag(row, out)
                out.append(" ".join(c for c in row if isinstance(c, str)))
        else:
            for item in value:
                textbag(item, out)
    elif isinstance(value, dict):
        for item in value.values():
            textbag(item, out)
        groups = value.get("groups")
        if isinstance(groups, list):
            titles = value.get("titles") or [""] * len(groups)
            for title, group in zip(titles, groups):
                body = "; ".join((a + " - " + b) if b else a for a, b in group)
                out.append(body)
                num = title.split()[-1] if title else ""
                out.append(f"{num}. {body}")
        label = value.get("label")
        if isinstance(label, str):
            out.append(unescape(label) + ":")
            for key in ("paragraphs", "items"):
                for item in value.get(key) or []:
                    sub: list[str] = []
                    textbag(item, sub)
                    out.extend(unescape(label) + " " + x for x in sub)
                    out.extend(unescape(label) + ": " + x for x in sub)


def coverage(doc: dict, lang: str) -> list[str]:
    """Строки исходника, которых нет в данных."""
    parts: list[str] = []
    textbag(doc, parts)
    haystack = squash(" ".join(parts))
    tight = re.sub(r"\s+", "", haystack)
    misses = []
    for block in read_blocks(lang):
        text = squash(join_lines(block["lines"]))
        if len(text) < 4:
            continue
        if text in haystack or re.sub(r"\s+", "", text) in tight:
            continue
        misses.append((block["page"], text))
    return misses


def check_dating(doc: dict) -> int:
    """Каждая цитата в блоке датировки должна стоять в тексте статьи дословно."""
    bad = 0
    for lang in ("ru", "en"):
        blocks = doc["dating"][lang]["blocks"]
        src = squash(" ".join(b["text"] for b in blocks))
        for item in DATING_SUMMARY["items"]:
            for text in (item["work"][lang],):
                for piece in re.split(r"…", text):
                    piece = squash(piece).strip("«»\"“” .,;:")
                    if len(piece) < 25:
                        continue
                    if piece not in src:
                        bad += 1
                        print(f"  [{lang}] цитата не найдена: {piece[:110]}")
        for piece in re.split(r"…", DATING_SUMMARY["note"][lang]):
            piece = squash(piece).strip("«»\"“” .,;:")
            if len(piece) >= 25 and piece not in src:
                bad += 1
                print(f"  [{lang}] цитата не найдена: {piece[:110]}")
    if bad:
        print("датировка: цитаты расходятся с текстом статьи — исправить")
    return bad


def main() -> None:
    doc = build()
    if "--check" in sys.argv:
        bad = check_dating(doc)
        for lang in ("ru", "en"):
            misses = coverage(doc, lang)
            print(f"[{lang}] строк исходника без пары: {len(misses)}")
            for page, text in misses[:40]:
                print(f"   p{page}: {text[:150]}")
            bad += len(misses)
        sys.exit(1 if bad else 0)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    quotes = check_dating(doc)
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size} байт, "
          f"{len(doc['poses'])} āсан")
    for lang in ("ru", "en"):
        misses = coverage(doc, lang)
        print(f"[{lang}] строк исходника без пары: {len(misses)}")
        for page, text in misses[:12]:
            print(f"   p{page}: {text[:140]}")
    if quotes:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
