#!/usr/bin/env python3
"""Сборка data/dattatreyayogasastra.json из двух PDF о «Даттāтрея-йога-ш́āстре».

Источник — русский и английский тома одного исследования: три āсаны
(Падмāсана 34–38, Ш́авāсана 24cd–26, Випарӣта-каран̣ӣ 146–149) по
критическому изданию Дж. Маллинсона (Пондичерри – Оксфорд, 2024).
Скрипт ничего не сочиняет: он раскладывает текст издания по полям сайта и
проверяет, что каждая содержательная строка исходника попала в данные.

Структура издания:

    шапка (титул, методологические правила)   → страница «О трактате»
    «Система йоги … и статус поз»             → страница «Вступление»
    «Как читать аппарат разночтений»          → страница «Приложение»
    «Таблица рукописей и свидетельств»        → страница «Приложение»
    «Датировка …» и «Экскурс …»               → статья «Датировка»
    1. Падмāсана, 2. Ш́авāсана, 3. Випарӣта-каран̣ӣ → три страницы āсан
    «Сравнительный конкорданс»                → страница «Примечания»
    «Текстологические выводы»                 → страница «Примечания»

Запуск:  .venv/bin/python tools/extract_dattatreya.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

import diacritics  # диакритика терминов и названий поз

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dattatreyayogasastra.json"

PDF = {
    "ru": ROOT / "sources" / "«Даттāтрея-йога-ш́āстра»_ три āсаны "
                      "(Падмāсана, Ш́авāсана, Випарӣта-каран̣ӣ).pdf",
    "en": ROOT / "sources" / "Dattātreyayogaśāstra_ all 3 āsanas "
                            "(Padmāsana, Śavāsana, Viparītakaraṇī).pdf",
}

# Подписи транслитераций внутри стиха. В русском томе их три, в английском
# две (деванагари и IAST): кириллица нужна только русскому читателю.
VLABELS = {
    "deva": ("Деванагари", "Devanagari", "Devanāgarī"),
    "iast": ("Транслитерация IAST", "IAST", "IAST transliteration"),
    "cyr": ("Кириллица", "Cyrillic"),
}

# Заголовки-подписи разделов страницы (стоят у левого поля).
LABELS = {
    "apparatus": ("Аппарат разночтений по рукописям",
                  "Variant readings in the manuscripts"),
    "parallels": ("Параллельные места и цитаты",
                  "Параллельные места в других текстах",
                  "Parallel passages & Testimonia",
                  "Parallel passages in other texts",
                  "Parallel passages"),
    "words": ("Пословный разбор", "Word-by-word analysis"),
    "literal": ("Буквальный перевод", "Literal translation"),
    "literary": ("Литературный перевод", "Literary translation"),
    "commentary": ("Комментарий редакторов", "Editors’ commentary",
                   "Editors' commentary"),
}

# Сквозные заголовки издания (14 pt у левого поля).
HEADINGS = {
    "contents": ("Содержание", "Contents"),
    "apparatus": ("Как читать аппарат разночтений", "How to read the apparatus"),
    "manuscripts": ("Таблица рукописей и свидетельств",
                    "Manuscripts and Witnesses Reference Table"),
    "dating": ("Датировка «Даттāтрея-йога-ш́āстры»",
               "Dating of the Dattātreyayogaśāstra"),
    "excursus": ("Экскурс:", "Excursus:"),
    "concordance": ("Сравнительный конкорданс", "Comparative Concordance"),
    "conclusions": ("Текстологические выводы", "Textological Summary"),
}
# «Система йоги …» набрана кеглем основного текста, но это заголовок.
PROLOGUE_HEAD = ("Система йоги в «Даттāтрея-йога-ш́āстре» и статус поз",
                 "The System of Yoga in the Dattātreyayogaśāstra and its Postures")

POSE_HEADS = {
    "padmasana": ("1. Падмāсана", "1. Padmāsana"),
    "shavasana": ("2. Ш́авāсана", "2. Śavāsana"),
    "viparitakarani": ("3. Випарӣта-каран̣ӣ", "3. Viparītakaraṇī"),
}

# Разрыв внутри слова: колонки таблиц набраны узко, и текст рвёт длинное слово
# без переноса — иногда пробелом внутри строки, иногда переносом строки. Пары
# собраны по фактическим разрывам обоих томов; `check_fixes()` сообщает, если
# исходник перестанет их давать.
FIX = [
    ("Правительстве нная", "Правительственная"),
    ("научно-исслед овательский", "научно-исследовательский"),
    ("исследователь ский", "исследовательский"),
    ("Dattātreyabodh a", "Dattātreyabodha"),
    ("Northern/Wester n", "Northern/Western"),
    ("Dattātreyayogaś āstra", "Dattātreyayogaśāstra"),
    ("caturaśītilakṣeṣ v", "caturaśītilakṣeṣv"),
    ("jaṭharāgni-vivar dhanam", "jaṭharāgnivivardhanam"),
    ("Haṭhapradīpik ā", "Haṭhapradīpikā"),
    ("Випарӣта-кара н̣ӣ", "Випарӣта-каран̣ӣ"),
    ("Хатха-прадипик а", "Хатха-прадипика"),
    ("Ш́āрн̇гадхара-п аддхати", "Ш́āрн̇гадхара-паддхати"),
    ("Йога-чинтаман и", "Йога-чинтамани"),
    ("заимствовавши й", "заимствовавший"),
    # ячейки конкорданса: номер стиха и цитата слиплись, слово разорвано
    ("34–38caturaśītila", "34–38 caturaśītila"),
    ("1.45–47uttānau", "1.45–47 uttānau"),
    ("146–149karaṇa", "146–149 karaṇa"),
    ("3.79–82karaṇaṃ", "3.79–82 karaṇaṃ"),
    ("24cduttānaśavav", "24cd uttānaśavav"),
    ("1.32uttānaśavavad", "1.32 uttānaśavavad"),
    ("«Даттāтрея-йог а-ш́āстре»", "«Даттāтрея-йога-ш́āстре»"),
    ("«Хат̣ха-йога-пр адӣпике»", "«Хат̣ха-йога-прадӣпике»"),
    ("текстологическ ой", "текстологической"),
    ("Трансформаци я", "Трансформация"),
    ("Стилистическа я", "Стилистическая"),
    ("karaṇa ṃ", "karaṇaṃ"),
    ("Хатха-ратнавал и", "Хатха-ратнавали"),
    ("Śārṅgadharapa ddhati", "Śārṅgadharapaddhati"),
    ("Śivānandasaras vatī", "Śivānandasarasvatī"),
]

NEW_PARA = 20.0          # интервал между абзацами (внутри строки ~14.4)
NEW_HEAD = 22.0          # шаг строк перенесённого заголовка (~19.7)
COL_X = [113.0, 212.0, 311.0, 410.0]
TABLE_XMIN = 105.0
CELL_GAP = 16.0          # разрыв между записями первого столбца
# Внутри ячейки строки идут с шагом 14–15 pt, а между записями — от 17 pt:
# порог 16 отделяет одно от другого (замерено по обоим томам).

VERSE_HEAD = re.compile(r"^(?:Стих|Verse)\s+(\d+(?:\.\d+)?(?:cd|ab)?)\b")
NUM_HEAD = re.compile(r"^\d+\.\s")
NUMBERED = re.compile(r"^\d+\.$")
INLINE_NAMES = ("Деванагари", "Devanagari", "Devanāgarī", "IAST", "Кириллица",
                "Cyrillic", "Пословный разбор и перевод",
                "Word-by-word analysis and translation",
                "Буквальный перевод", "Literal Translation", "Literal translation",
                "Литературный перевод", "Literary Translation", "Literary translation")
DEVA_NAMES = ("Деванагари", "Devanagari", "Devanāgarī")
# «Деванагари: …» — подпись блока внутри статьи; в русском томе она стоит в
# одной строке с текстом, в английском — отдельной строкой.
INLINE_LABEL = re.compile(r"^(" + "|".join(INLINE_NAMES) + r")\s*:\s*(.*)$")


# ------------------------------------------------------------------ чтение PDF

def norm(text: str) -> str:
    text = text.replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_lines(lang: str) -> list[dict]:
    """Строки издания подряд, с координатами и кеглем."""
    doc = pymupdf.open(PDF[lang])
    out: list[dict] = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                raw = "".join(s["text"] for s in line["spans"])
                text = norm(raw)
                if not text:
                    continue
                out.append({
                    "text": text,
                    "trail": bool(re.search(r"[ \t]$", raw.rstrip("\u200b"))),
                    "page": pno + 1,
                    "y": round(line["bbox"][1], 1),
                    "x": round(line["bbox"][0], 1),
                    "size": round(max(s["size"] for s in line["spans"]), 1),
                    "deva": any("Mangal" in s["font"] for s in line["spans"]),
                })
    return out


# ------------------------------------------------------------------- склейки

def fix(text: str) -> str:
    """Склеивает слово, разорванное выключкой внутри строки таблицы."""
    for broken, whole in FIX:
        text = text.replace(broken, whole)
    return text


def join_lines(lines: list[dict]) -> str:
    """Строки подряд: если строка не кончилась пробелом, слово было разорвано."""
    text = ""
    prev: dict | None = None
    for line in lines:
        if prev is None:
            text = line["text"]
        elif prev["trail"] or not prev["text"][-1:].isalpha() \
                or not line["text"][:1].islower():
            text = text + " " + line["text"]
        else:
            text = text + line["text"]           # слово разорвано выключкой
        prev = line
    return fix(text)


# незакрытая разметка в самом издании: «(**bindu* / amṛta*)» — восстанавливаем
# жирный шрифт, как он и был задуман в исходном документе, без правки слов
MARKUP = [("(**bindu* / amṛta*)", "(<strong>bindu</strong> / amṛta)")]

# цитата в источнике набрана markdown-выноской: строка начинается с «> »
QUOTE_MARK = "&gt; "


def markup(html: str) -> str:
    for broken, whole in MARKUP:
        html = html.replace(broken, whole)
    return html


def split_quote(html: str) -> tuple[str, list[dict]] | None:
    """Пункт с выноской «> …»: текст пункта, затем цитата и её продолжение."""
    if QUOTE_MARK not in html:
        return None
    head, rest = html.split(QUOTE_MARK, 1)
    body = rest.replace(QUOTE_MARK, "")
    match = re.match(r"(.*?//\s*\d+\s*//)\s*(.*)$", body, re.S)
    if not match:
        return None
    verse, tail = match.group(1).strip(), match.group(2).strip()
    out: list[dict] = [{"type": "quote", "paragraphs": [verse]}]
    quoted = re.match(r"([«“].*?[»”]\.)\s*(.*)$", tail, re.S)
    if quoted:
        out[0]["paragraphs"].append(quoted.group(1))
        tail = quoted.group(2).strip()
    if tail:
        out.append({"type": "p", "html": tail})
    return head.strip(), out


def escaped(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def paragraphs(lines: list[dict]) -> list[str]:
    return [join_lines([line]) for line in lines if line["text"].strip()]


# ------------------------------------------------------------------- таблицы

def column_of(x: float) -> int:
    best, dist = 0, 1e9
    for i, cx in enumerate(COL_X):
        if abs(x - cx) < dist:
            best, dist = i, abs(x - cx)
    return best


def line_key(line: dict) -> tuple[int, float, float]:
    return (line["page"], round(line["x"], 1), round(line["y"], 1))


def heading_kind(text: str) -> str:
    low = text.lower()
    for kind, names in HEADINGS.items():
        for name in names:
            if low.startswith(name.lower()):
                return kind
    return ""


def table_region(lines: list[dict], kind: str) -> tuple[list[dict], set]:
    """Строки таблицы: от её заголовка до первой строки у левого поля.

    Абзац между заголовком и таблицей (в английском томе он есть) таблицу не
    обрывает: концом считается левая строка, стоящая уже ниже её первой строки.
    """
    head = next((l for l in lines
                 if l["size"] >= 13.5 and l["x"] < 90
                 and heading_kind(l["text"]) == kind), None)
    if head is None:
        raise SystemExit("не найден заголовок таблицы: " + kind)
    body = [l for l in lines
            if (l["page"], l["y"]) > (head["page"], head["y"])
            and l["x"] >= TABLE_XMIN]
    if not body:
        raise SystemExit("пустая таблица: " + kind)
    first = (body[0]["page"], body[0]["y"])
    left = [l for l in lines
            if (l["page"], l["y"]) > first and l["x"] < TABLE_XMIN]
    end = (left[0]["page"], left[0]["y"]) if left else (10 ** 6, 0.0)
    region = [l for l in body if (l["page"], l["y"]) < end]
    return region, {line_key(l) for l in region}


def cells_of(region: list[dict]) -> list[list[str]]:
    """Ячейки таблицы: запись начинается там, где начинается первый столбец.

    Внутри ячейки строки идут вплотную (~14 pt), между записями промежуток
    шире. Первая ячейка первого столбца — шапка; на следующих страницах шапка
    повторяется и отбрасывается по совпадению строк. Строки над первой записью
    страницы продолжают ячейку предыдущей записи: так ячейка, разрезанная
    границей страницы, склеивается обратно, а страница без записей первого
    столбца целиком продолжает последнюю запись.
    """
    pages: list[dict] = []
    for line in region:
        if not pages or pages[-1]["page"] != line["page"]:
            pages.append({"page": line["page"], "lines": []})
        pages[-1]["lines"].append(line)

    ncols = len(COL_X)
    header: list[list[str]] = [[] for _ in range(ncols)]
    header_texts: set[str] = set()
    rows: list[dict] = []

    def starts_of(lines: list[dict]) -> list[float]:
        starts: list[float] = []
        last_y: float | None = None
        for line in lines:
            if column_of(line["x"]) != 0:
                continue
            if last_y is None or line["y"] - last_y > CELL_GAP:
                starts.append(line["y"])
            last_y = line["y"]
        return starts

    for page in pages:
        lines = page["lines"]
        starts = starts_of(lines)
        if not starts:
            if rows:                       # страница целиком продолжает запись
                for line in lines:
                    if line["text"] not in header_texts:
                        rows[-1]["cells"][column_of(line["x"])].append(line)
            continue
        col0_lines = [l for l in lines if column_of(l["x"]) == 0]
        if len(starts) == 1 and header_texts and all(
                l["text"] in header_texts for l in col0_lines):
            if rows:                       # только повтор шапки: записи нет
                for line in lines:
                    if line["text"] not in header_texts:
                        rows[-1]["cells"][column_of(line["x"])].append(line)
            continue
        top = starts[1] if len(starts) > 1 else starts[0]     # вторая запись — данные
        above = [l for l in lines if l["y"] < top - 2]
        if not header_texts:
            for line in above:
                header[column_of(line["x"])].append(line)
                header_texts.add(line["text"])
        else:
            for line in above:
                if line["text"] in header_texts:
                    continue                       # повтор шапки
                if rows:
                    rows[-1]["cells"][column_of(line["x"])].append(line)
        for y in starts:
            if y < top - 2:
                continue
            rows.append({"y": y, "page": page["page"],
                         "cells": [[] for _ in range(ncols)]})
        for line in lines:
            if line["y"] < top - 2:
                continue
            pos = None
            for i, row in enumerate(rows):
                if row["page"] < line["page"] or (
                        row["page"] == line["page"] and row["y"] <= line["y"] + 2):
                    pos = i
            if pos is not None:
                rows[pos]["cells"][column_of(line["x"])].append(line)

    table = [[join_lines(header[i]) for i in range(ncols)]]
    for row in rows:
        table.append([join_lines(row["cells"][i]) for i in range(ncols)])
    return table


# -------------------------------------------------------------------- разметка

def vlabel_kind(text: str) -> str:
    for key, names in VLABELS.items():
        if text in names:
            return key
    return ""


def label_kind(text: str) -> str:
    probe = text.rstrip(":").strip()
    probe = re.sub(r"\s*\(.*?\)\s*$", "", probe)
    for kind, names in LABELS.items():
        for name in names:
            if probe == name or probe.startswith(name + " "):
                return kind
    return ""


def tokenize(lang: str) -> list[dict]:
    """Поток элементов издания: заголовки, подписи, пункты списка, строки."""
    lines = read_lines(lang)
    skip: set = set()
    for kind in ("manuscripts", "concordance"):
        _, keys = table_region(lines, kind)
        skip |= keys
    lines = [l for l in lines if line_key(l) not in skip]

    tokens: list[dict] = []
    prev: dict | None = None
    for line in lines:
        text, x = line["text"], line["x"]
        tok = dict(line, kind="text")

        close = prev is not None and prev["page"] == line["page"] and \
            line["y"] - prev.get("last_y", prev["y"]) <= NEW_HEAD
        # у заголовков межстрочный интервал крупнее (20.5 pt против 20)
        close_head = prev is not None and prev["page"] == line["page"] and \
            line["y"] - prev.get("last_y", prev["y"]) <= NEW_HEAD * 1.15
        if line["size"] >= 15.5 and x < 95:
            if close_head and prev["kind"] == "title":
                prev["text"] += " " + text
                prev["last_y"] = line["y"]
                continue
            tok["kind"] = "title"
        elif line["size"] >= 13.5 and x < 95:
            if close_head and prev["kind"] == "h2":
                prev["text"] += " " + text
                prev["last_y"] = line["y"]
                continue
            tok["kind"] = "h2"
        elif close and prev["kind"] in ("title", "h2", "h3") and text[:1].islower():
            prev["text"] += " " + text
            prev["last_y"] = line["y"]
            continue
        elif text in PROLOGUE_HEAD:
            tok["kind"] = "h2"
        elif VERSE_HEAD.match(text) and x < 95:
            tok["kind"] = "vhead"
            tok["verse"] = VERSE_HEAD.match(text).group(1)
        elif vlabel_kind(text) and x < 95:
            tok["kind"] = "vlabel"
            tok["key"] = vlabel_kind(text)
        elif NUM_HEAD.match(text) and x < 95:
            if close and prev["kind"] == "h3":
                prev["text"] += " " + text
                prev["last_y"] = line["y"]
                continue
            tok["kind"] = "h3"
        elif text in ("Итоговый хронологический вывод", "Conclusion",
                      "The Final Chronological Conclusion"):
            tok["kind"] = "h3"
        elif text.startswith(("Завершение раздела", "Completion of section",
                              "End of Section")):
            tok["kind"] = "h3"
        elif label_kind(text) and x < 95:
            tok["kind"] = "label"
            tok["key"] = label_kind(text)
            tok["label"] = text.rstrip(":").strip()      # подпись как в издании
        elif text == "•":
            tok["kind"] = "bullet"
            tok["level"] = 1
        elif text in ("–", "—") and x >= 115:
            tok["kind"] = "bullet"
            tok["level"] = 2
        elif NUMBERED.match(text) and x < 100:
            tok["kind"] = "num"
            tok["num"] = int(text[:-1])
        tokens.append(tok)
        prev = tok
    return tokens


# --------------------------------------------------------------- сборка блоков

DASH = re.compile(r"\s+—\s+")
VERSE_NUM = re.compile(r"^(\d+(?:\.\d+)?(?:cd|ab)?)\.\s+")


def split_pairs(text: str) -> tuple[str, list[list[str]]]:
    """Разбор «слово (грамматика) — значение; …» на пары для таблицы страницы.

    Точка с запятой разделяет пары только вне скобок: внутри скобок издание
    само перечисляет значения через «;», и такие пояснения должны остаться при
    своём слове.
    """
    match = VERSE_NUM.match(text)
    title = match.group(1) if match else ""
    body = VERSE_NUM.sub("", text)
    items: list[str] = []
    depth, start = 0, 0
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
    for item in (p.strip() for p in items):
        if not item:
            continue
        depth, cut = 0, -1
        for i, char in enumerate(item):
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and char == "—" and item[i - 1] == " " and item[i + 1] == " ":
                cut = i
                break
        if cut < 0:
            pairs.append([item, ""])
        else:
            pairs.append([item[:cut].strip(), item[cut + 1:].strip()])
    return title, pairs


def words_block(label: str, groups: list[list[dict]], lang: str) -> dict:
    """Пословный разбор: каждая группа строк — разбор одного стиха."""
    texts = [join_lines(group) for group in groups]
    parsed = [split_pairs(text) for text in texts]
    words = {"ru": "Стих ", "en": "Verse "}[lang]
    titles = [words + title if title else "" for title, _ in parsed]
    block: dict = {"type": "words", "label": label, "paragraphs": texts}
    if all(pairs for _, pairs in parsed):
        block["groups"] = [pairs for _, pairs in parsed]
        if any(titles):
            block["titles"] = titles
    return block


class Builder:
    """Линейный разбор издания: абзацы, карточки стихов, списки, подписи.

    У издания три уровня разметки, и каждый собирается своим приёмом:

    * карточка стиха — подпись «Стих 34», строка-подзаголовок и три
      транслитерации (деванагари, IAST, кириллица);
    * список — пункты «•» или нумерованные; подпись списка («Аппарат
      разночтений по рукописям») стоит перед ним отдельной строкой;
    * подпись с содержимым — «Пословный разбор», «Буквальный перевод»,
      «Литературный перевод»: пункты внутри становятся отдельными абзацами
      (в русском томе это абзацы, в английском — пункты списка).
    """

    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.blocks: list[dict] = []
        self.para: list[dict] = []
        self.caption: dict | None = None      # открытая строка-подзаголовок стиха
        self.card: dict | None = None
        self.label: dict | None = None        # {"key", "label", "items": [[строка]]}
        self.inline: dict | None = None       # «Деванагари: …» внутри статьи
        self.items: list[dict] = []
        self.ordered = False
        self.start = 1
        self.level = 1
        self.list_label: str | None = None
        self.pending: dict | None = None
        self.last: dict | None = None

    # --- сбросы
    def flush_para(self) -> None:
        if self.para:
            self.blocks.append({"type": "p", "text": join_lines(self.para)})
            self.para = []

    def flush_card(self) -> None:
        if self.card is not None and self.card["parts"]:
            # строки стиха — типографские переносы издания: стих склеивается в
            # одну строку, иначе на странице он разъедется по строкам PDF
            parts = [dict(part, lines=[join_lines(part["lines"])])
                     for part in self.card["parts"] if part["lines"]]
            if parts:
                self.blocks.append({"type": "verse_card", "verses": self.card["verses"],
                                    "sections": parts})
        self.card = None
        self.caption = None

    def flush_list(self) -> None:
        if self.items:
            block: dict = {"type": "list", "ordered": self.ordered, "items": self.items}
            if self.ordered and self.start > 1:
                block["start"] = self.start
            if self.list_label:
                block["label"] = self.list_label
            self.blocks.append(block)
        self.items = []
        self.ordered = False
        self.start = 1
        self.level = 1
        self.list_label = None

    def flush_label(self) -> None:
        if self.label is None:
            return
        kind, lab = self.label["key"], self.label["label"]
        groups = [g for g in self.label["items"] if g]
        if kind == "words":
            self.blocks.append(words_block(lab, groups, self.label["lang"]))
        elif kind in ("literal", "literary"):
            self.blocks.append({"type": "prose", "key": kind, "label": lab,
                                "paragraphs": [join_lines(g) for g in groups]})
        else:
            self.blocks.append({"type": "p", "text": join_lines(
                [line for g in groups for line in g])})
        self.label = None

    def flush_inline(self) -> None:
        if self.inline is None:
            return
        if not self.inline["lines"]:
            self.inline = None
            return
        text = join_lines(self.inline["lines"])
        if self.inline["type"] == "deva":
            self.blocks.append({"type": "deva", "lines": [text]})
        else:
            self.blocks.append({"type": "p", "text": text})
        self.inline = None

    def flush_all(self) -> None:
        self.flush_para()
        self.flush_list()
        self.flush_label()
        self.flush_inline()
        self.flush_card()
        self.pending = None

    # --- разбор
    def feed(self, tok: dict) -> None:
        kind = tok["kind"]
        gap = None
        if self.last is not None and self.last["page"] == tok["page"]:
            gap = tok["y"] - self.last["y"]

        if kind in ("title", "h2", "h3"):
            self.flush_all()
            self.blocks.append({"type": kind, "text": tok["text"]})
        elif kind == "vhead":
            self.flush_all()
            self.blocks.append({"type": "h4", "text": tok["text"]})
            self.card = {"verses": tok["verse"], "parts": []}
            self.caption = None
        elif kind == "vlabel":
            self.flush_para()
            self.flush_list()
            self.flush_label()
            self.flush_inline()
            if self.card is None:
                self.card = {"verses": "", "parts": []}
            self.card["parts"].append({"type": "verse", "key": tok["key"], "lines": []})
            self.caption = None
        elif kind == "label":
            self.flush_para()
            self.flush_card()
            self.flush_list()
            self.flush_inline()
            self.flush_label()
            if tok["key"] in ("apparatus", "parallels", "commentary"):
                self.list_label = tok["label"]
                self.ordered = tok["key"] == "commentary"
                self.start = 1
            else:
                self.label = {"key": tok["key"], "label": tok["label"],
                              "items": [[]], "lang": self.lang}
            self.caption = None
        elif kind in ("bullet", "num"):
            self.flush_para()
            self.flush_card()
            self.flush_inline()
            if self.label is not None:             # пункт внутри подписи
                self.label["items"].append([])
                self.pending = None
            else:
                self.pending = {"kind": kind, "level": tok.get("level", 1),
                                "num": tok.get("num", 0)}
        else:
            self.text(tok, gap)
        self.last = tok

    def text(self, tok: dict, gap: float | None) -> None:
        text = tok["text"]

        match = INLINE_LABEL.match(text)
        if match and not self.items:
            self.flush_para()
            self.flush_card()
            self.flush_label()
            self.flush_inline()
            name, rest = match.group(1), match.group(2)
            if name in DEVA_NAMES:      # деванагари набирается своим шрифтом
                self.inline = {"type": "deva",
                               "lines": [dict(tok, text=rest)] if rest else []}
            else:                       # подпись «IAST: …» остаётся в тексте
                self.inline = {"type": "p", "lines": [tok]}
            return

        if self.caption is not None and (gap is None or gap <= NEW_PARA):
            self.caption["text"] = self.caption["text"] + " " + text
            return

        if self.pending is not None:
            kind = self.pending["kind"]
            level = self.pending.get("level", 1)
            ordered = kind == "num"
            # список продолжается, пока не меняется вид или уровень пункта
            if self.items and (self.ordered != ordered or self.level != level):
                self.flush_list()
            if not self.items:
                self.ordered = ordered
                self.level = level
                self.start = self.pending["num"] or 1
            item: dict = {"html": "", "lines": [tok]}
            if self.pending.get("level", 1) > 1:
                item["level"] = self.pending["level"]
            self.items.append(item)
            self.pending = None
            return

        if self.items:
            if gap is not None and gap > NEW_PARA:
                self.flush_list()
            else:
                self.items[-1]["lines"].append(tok)
                return

        if self.label is not None:
            if not self.label["items"]:
                self.label["items"].append([])
            self.label["items"][-1].append(tok)
            return

        if self.inline is not None and (gap is None or gap <= NEW_PARA):
            self.inline["lines"].append(tok)
            return

        if self.card is not None and self.card["parts"] and (
                self.card["parts"][-1]["lines"] or tok["x"] < 95):
            self.card["parts"][-1]["lines"].append(tok)
            return

        if self.para and gap is not None and gap > NEW_PARA:
            self.flush_para()

        if not self.para and self.card is not None:
            self.caption = {"type": "p", "text": text}   # строка под «Стих 34»
            self.blocks.append(self.caption)
            return

        self.para.append(tok)


def expand_stars(blocks: list[dict]) -> list[dict]:
    """Перечисление внутри абзаца («…: * одно; * другое; * третье»).

    Разметка осталась от исходного документа: звёздочки не текст, а знак
    пункта. Слова не меняются — только вид: список вместо сплошного абзаца.
    """
    out: list[dict] = []
    for block in blocks:
        text = block.get("text", "")
        if "*" not in text:
            out.append(block)
            continue
        parts = [part.strip() for part in re.split(r"\s\*\s+", text)]
        if len(parts) < 3:
            out.append(block)
            continue
        head, items = parts[0], [part for part in parts[1:] if part]
        out.append({"type": block["type"], "text": head})
        out.append({"type": "list", "ordered": False,
                    "items": [{"html": escaped(item)} for item in items]})
    return out


def build_blocks(tokens: list[dict], lang: str) -> list[dict]:
    builder = Builder(lang)
    for tok in tokens:
        builder.feed(tok)
    builder.flush_all()
    for block in builder.blocks:
        if block["type"] == "list":
            for item in block["items"]:
                item["html"] = escaped(join_lines(item.pop("lines")))
    blocks: list[dict] = []
    for block in builder.blocks:
        if block["type"] == "list":
            extra: list[dict] = []
            for item in block["items"]:
                split = split_quote(item["html"])
                if split:
                    item["html"], rest = split
                    extra.extend(rest)
                else:
                    item["html"] = markup(item["html"])
            blocks.append(block)
            blocks.extend(extra)
        elif "text" in block and any(bad in block["text"] for bad, _ in MARKUP):
            block = {"type": block["type"], "html": markup(escaped(block.pop("text")))}
            blocks.append(block)
        else:
            blocks.append(block)
    builder.blocks = expand_stars(blocks)
    return [b for b in builder.blocks
            if not (b["type"] == "verse_card" and not b["sections"])
            and not (b["type"] == "list" and not b["items"])]


# -------------------------------------------------------------------- разделы

SECTION_KEYS = {
    "prologue": PROLOGUE_HEAD,
    "contents": HEADINGS["contents"],
    "apparatus": HEADINGS["apparatus"],
    "manuscripts": HEADINGS["manuscripts"],
    "dating": HEADINGS["dating"],
    "excursus": HEADINGS["excursus"],
    "concordance": HEADINGS["concordance"],
    "conclusions": HEADINGS["conclusions"],
}


def section_kind(heading: str) -> str:
    """Куда идёт раздел издания: страница сайта и ключ āсаны."""
    body = re.sub(r"^\d+\.\s*", "", heading).strip()
    for key, (ru, en) in POSE_HEADS.items():
        for head in (ru, en):
            if heading.startswith(head) or body.startswith(re.sub(r"^\d+\.\s*", "", head)):
                return "pose:" + key
    low = heading.lower()
    for key, names in SECTION_KEYS.items():
        for name in names:
            if low.startswith(name.lower()):
                return key
    return ""


def split_sections(blocks: list[dict]) -> dict[str, list[dict]]:
    """Разделы издания по заголовкам; всё до первого заголовка — шапка."""
    parts: dict[str, list[dict]] = {"front": []}
    current = "front"
    for block in blocks:
        if block["type"] == "h2":
            kind = section_kind(block["text"]) or "other"
            current = kind
            n = 2
            while current in parts:       # раздел с тем же ключом второй раз
                current = kind + ":" + str(n)
                n += 1
            parts.setdefault(current, [])
        parts[current].append(block)
    return parts


def take(parts: dict, key: str) -> tuple[str, list[dict]]:
    """(заголовок раздела, его блоки без заголовка)."""
    blocks = parts.get(key, [])
    if not blocks:
        raise SystemExit("в издании не найден раздел: " + key)
    if blocks[0]["type"] not in ("h2", "h3"):
        raise SystemExit("раздел без заголовка: " + key)
    return blocks[0]["text"], blocks[1:]


def as_subhead(label: str) -> dict:
    return {"type": "subhead", "label": label}


def pose_head(heading: str) -> tuple[str, str]:
    """«1. Падмāсана — поза лотоса» → («Падмāсана», «поза лотоса»)."""
    body = re.sub(r"^\d+\.\s*", "", heading).strip()
    name, _, gloss = body.partition(" — ")
    return name.strip(), gloss.strip()


VERSE_RANGE = re.compile(r"^(?:Стихи|Стих|Verses|Verse):\s*([^()]+?)\s*(?:\(|$)")


def verses_of(blocks: list[dict]) -> str:
    for block in blocks:
        text = block.get("text") or ""
        match = VERSE_RANGE.match(text)
        if match:
            return match.group(1).strip()
    return ""


def build(lang: str) -> dict:
    lines = read_lines(lang)
    blocks = build_blocks(tokenize(lang), lang)
    parts = split_sections(blocks)

    manuscripts = cells_of(table_region(lines, "manuscripts")[0])
    concordance = cells_of(table_region(lines, "concordance")[0])

    apparatus_head, apparatus = take(parts, "apparatus")
    manuscripts_head, _ = take(parts, "manuscripts")
    dating_head, dating = take(parts, "dating")
    excursus_head, excursus = take(parts, "excursus")
    concordance_head, concordance_rest = take(parts, "concordance")
    conclusions_head, conclusions = take(parts, "conclusions")
    _, prologue = take(parts, "prologue")

    poses: dict[str, dict] = {}
    for key in POSE_HEADS:
        heading, body = take(parts, "pose:" + key)
        name, gloss = pose_head(heading)
        poses[key] = {"heading": heading, "name": name, "gloss": gloss,
                      "verses": verses_of(body), "blocks": body}

    return {
        "about": parts["front"] + [as_subhead(parts["contents"][0]["text"])]
                 + parts["contents"][1:],
        "prologue": [as_subhead(PROLOGUE_HEAD[0] if lang == "ru" else PROLOGUE_HEAD[1])]
                    + prologue,
        "dating": {
            "title": dating_head,
            "blocks": dating + [{"type": "h3", "text": excursus_head}] + excursus,
        },
        "appendix": [as_subhead(apparatus_head)] + apparatus
                    + [as_subhead(manuscripts_head),
                       {"type": "table", "rows": manuscripts}],
        "notes": [as_subhead(concordance_head)] + concordance_rest
                 + [{"type": "table", "rows": concordance},
                    as_subhead(conclusions_head)] + conclusions,
        "poses": poses,
    }


# ------------------------------------------------------------------ сборка данных

POSE_ORDER = ("padmasana", "shavasana", "viparitakarani")
POSE_IAST = {
    "padmasana": "Padmāsana",
    "shavasana": "Śavāsana",
    "viparitakarani": "Viparītakaraṇī",
}
TITLE = {"ru": "Даттāтрея-йога-ш́āстра", "en": "Dattātreyayogaśāstra"}
ASANAS_TITLE = {"ru": "Āсаны «Даттāтрея-йога-ш́āстры»",
                "en": "The āsanas of the Dattātreyayogaśāstra"}
NOTES_TITLE = {"ru": "Конкорданс и выводы", "en": "Concordance and conclusions"}

# Короткая датировка под названием позы. Формулировки — цитаты издания: сводка
# (§ «Итоговый хронологический вывод» / «Conclusion») и границы, названные в
# разделах 1 и 2 статьи о датировке.
DATING_SUMMARY = {
    "label": {"ru": "На чём основано (по словам самого издания)",
              "en": "Basis (in the edition's own words)"},
    "items": [
        {
            "who": {"ru": "Дж. Маллинсон, критическое издание 2024 · «Итоговый хронологический вывод»",
                    "en": "J. Mallinson, critical edition 2024 · “Conclusion”"},
            "when": {"ru": "«около 1200–1250 гг. н. э. (начало XIII века)»",
                     "en": "“circa 1200 CE (early 13th century)”"},
            "work": {"ru": "«Совокупность филологических, палеографических и исторических свидетельств фиксирует дату создания «Даттāтрея-йога-ш́āстры» около 1200–1250 гг. н. э.»",
                     "en": "“The convergence of philological, stemmatic, and historical evidence firmly dates the composition of the Dattātreyayogaśāstra to circa 1200 CE.”"},
        },
        {
            "who": {"ru": "Верхняя граница (terminus ante quem) · раздел 1 статьи о датировке",
                    "en": "Upper bound (terminus ante quem) · section 1 of the dating study"},
            "when": {"ru": "не позднее 1363 г. н. э.", "en": "not later than 1363 CE"},
            "work": {"ru": "«Ш́āрн̇гадхара-паддхати» цитирует стих 35 дословно (стихи 4376 и 4435) и воспроизводит стихи 131–145.",
                     "en": "The Śārṅgadharapaddhati quotes verse 35 verbatim (verses 4376 and 4435) and reproduces verses 131–145."},
        },
        {
            "who": {"ru": "Нижняя граница (terminus post quem) · раздел 2 статьи о датировке",
                    "en": "Lower bound (terminus post quem) · section 2 of the dating study"},
            "when": {"ru": "ок. 1150–1200 гг. н. э.", "en": "c. 1150–1200 CE"},
            "work": {"ru": "Рецепция «Амр̣тасиддхи» (XI–XII вв.) и четырёхчастной схемы «Амараугха-прабодхи» (XII в.).",
                     "en": "Reception of the Amṛtasiddhi (11th–12th c.) and of the fourfold scheme of the Amaraughaprabodha (12th c.)."},
        },
    ],
}


def payload(ru: dict, en: dict) -> dict:
    poses = []
    for number, key in enumerate(POSE_ORDER, start=1):
        ru_pose, en_pose = ru["poses"][key], en["poses"][key]
        poses.append({
            "key": key,
            "iast": POSE_IAST[key],
            "number": number,
            "name": {"ru": ru_pose["name"], "en": en_pose["name"]},
            "gloss": {"ru": ru_pose["gloss"], "en": en_pose["gloss"]},
            "verses": {"ru": ru_pose["verses"], "en": en_pose["verses"]},
            "text": {"ru": ru_pose["blocks"], "en": en_pose["blocks"]},
        })
    return {
        "id": "dattatreyayogasastra",
        "title": TITLE,
        "asanasTitle": ASANAS_TITLE,
        "notesTitle": NOTES_TITLE,
        "about": {"ru": ru["about"], "en": en["about"]},
        "prologue": {"ru": ru["prologue"], "en": en["prologue"]},
        "dating": {"ru": ru["dating"], "en": en["dating"]},
        "datingSummary": DATING_SUMMARY,
        "appendix": {"ru": ru["appendix"], "en": en["appendix"]},
        "notes": {"ru": ru["notes"], "en": en["notes"]},
        "closing": {"ru": [], "en": []},
        "poses": poses,
    }


# --------------------------------------------------------------------- проверка

def strings_of(node, out: list[str]) -> None:
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, list):
        for item in node:
            strings_of(item, out)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key in ("type", "key", "level", "start", "ordered"):
                continue
            strings_of(value, out)


def squash(text: str) -> str:
    """Только буквы и цифры: сверка не зависит от переносов и разметки."""
    return "".join(ch for ch in text
                   if ch.isalnum() or "\u0900" <= ch <= "\u097f").lower()


def coverage(lang: str, data: dict) -> tuple[int, list[str]]:
    """Каждая содержательная строка издания должна быть в данных."""
    strings: list[str] = []
    strings_of(data, strings)
    blob = squash("".join(strings))
    missing: list[str] = []
    for line in read_lines(lang):
        text = line["text"].rstrip(":").strip()
        if len(text) < 24 or line["x"] >= TABLE_XMIN:
            continue
        # у строки «Деванагари: <стих>» подпись снята: стих лежит в блоке deva
        probe = re.sub(r"^(Деванагари|Devanagari|Devanāgarī):\s*", "", text)
        if squash(probe)[:40] not in blob:
            missing.append(text[:80])
    return len(missing), missing


def check(data: dict) -> None:
    """Сверки, без которых данные молча разъедутся с изданием."""
    for lang in ("ru", "en"):
        count, missing = coverage(lang, data)
        print(f"  {lang}: строк вне данных — {count}")
        for line in missing[:10]:
            print("     не найдено:", line)
    for lang in ("ru", "en"):
        for section in ("appendix", "notes"):
            tables = [b for b in data[section][lang] if b["type"] == "table"]
            if len(tables) != 1:
                raise SystemExit(f"{lang}/{section}: таблиц {len(tables)}, ждали одну")
            print(f"  {lang}/{section}: таблица {len(tables[0]['rows'])} × "
                  f"{len(tables[0]['rows'][0])}")
        for pose in data["poses"]:
            kinds = [b["type"] for b in pose["text"][lang]]
            if kinds.count("verse_card") == 0 or kinds.count("words") != 1:
                raise SystemExit(f"{lang}/{pose['key']}: разметка не собралась")
        strings: list[str] = []
        strings_of(data, strings)
        blob = "\n".join(strings)
        for broken, _ in FIX:
            if broken in blob:
                raise SystemExit(f"{lang}: не склеено «{broken}»")


def main() -> None:
    data = payload(build("ru"), build("en"))
    check(data)
    data = diacritics.fix_document(data)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    size = OUT.stat().st_size / 1024
    print(f"записано: {OUT.relative_to(ROOT)} · {size:.0f} КБ · "
          f"āсан {len(data['poses'])}")


if __name__ == "__main__":
    main()
