#!/usr/bin/env python3
"""Сборка data/hathatattvakaumudi.json из двух PDF 7-й главы «Хат̣хататтвакаумудӣ».

Источник — критическое издание главы 7 (RU) и его английская версия (EN).
Скрипт ничего не сочиняет: он раскладывает текст издания по полям сайта
(стихи, пословный разбор, переводы, комментарий) и проверяет, что каждая
строка исходника попала в данные.

Структура издания:

    РАЗДЕЛ I. ИСТОРИКО-ФИЛОЛОГИЧЕСКОЕ ВВЕДЕНИЕ
        1.1 … 1.4            → страница «О трактате» (1.2 — датировка)
    РАЗДЕЛ II. КРИТИЧЕСКИЙ РАЗБОР (шлоки 1–4)
        ВВОДНАЯ ЧАСТЬ        → страница «Вступление»
    РАЗДЕЛ II.1. ПЯТНАДЦАТЬ ĀСАН (шлоки 5–45)
        1 … 15               → по странице на āсану
    РАЗДЕЛ III. СВОДНАЯ ТАБЛИЦА
        таблица              → приложение

Каждый стих разобран одинаково: деванагари, IAST, кириллица, пословный
грамматический разбор, дословный перевод, литературный перевод и
текстологический комментарий. Эти блоки и становятся разделами страницы.

Запуск:  .venv/bin/python tools/extract_hathatattvakaumudi.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hathatattvakaumudi.json"

PDF = {
    "ru": ROOT / "sources" / "Hathatattvakaumudi_Chapter_7_Critical_Edition_RU.pdf",
    "en": ROOT / "sources" / "Hathatattvakaumudi_Chapter_7_Critical_Edition_EN.pdf",
}

# Подписи блоков в издании. В английской версии кириллической транслитерации
# нет — там её не печатают.
LABELS = {
    "ru": {
        "deva": r"^Деванагари( \(шлока .*\))?$",
        "iast": r"^IAST( \(verse \d+\))?$",
        "cyr": r"^Кириллическая транслитерация \(с диакритикой(, шлока [\d–]+)?\)$",
        "words": r"^Пословный грамматический разбор( \(шлока \d+\))?$",
        "literal": r"^Дословный перевод( \(шлоки [\d–]+\))?$",
        "literary": r"^Литературный перевод( \(шлоки [\d–]+\))?$",
        "comment": r"^Текстологический комментарий и критический аппарат$",
    },
    "en": {
        "deva": r"^Devanāgarī( \(Verse .*\))?$",
        "iast": r"^IAST( \('?[Vv]erse \d+\))?$",
        "cyr": None,
        "words": r"^Word-by-Word Grammatical Analysis( \('?[Vv]erse \d+\))?$",
        "literal": r"^Literal Translation( \(Verses? [\d–]+\))?$",
        "literary": r"^Literary Translation( \(Verses? [\d–]+\))?$",
        "comment": r"^Textological Commentary and Critical Apparatus$",
    },
}

PART = re.compile(r"^(РАЗДЕЛ|SECTION)\s+([IVX]+)(\.\d+)?\.")
HEADING_START = re.compile(r"^(РАЗДЕЛ|SECTION|Шлока|Verse|\d+\.)")
VERSE_HEAD = re.compile(r"^(Шлока|Verse)\s+(\d+)\s*:")
NUM_HEAD = re.compile(r"^(\d+\.\d+(?:\.\d+)?)\.?\s")
NUM_ITEM = re.compile(r"^(\d+)\.\s+(.*)$")
POSE_HEAD = re.compile(r"^(\d+)\.\s+(.+?)\s*\((.+)\)$")

# Позы главы 7 и ключи сайта: ключ один для всех трактатов, по нему страница
# асаны собирает описания из всех памятников, где она названа.
POSES = [
    ("dhanurasana", "ДХАНУРĀСАНА", "DHANURĀSANA"),
    ("kukkutasana", "КУККУТ̣ĀСАНА", "KUKKUṬĀSANA"),
    ("matsyendrapitha", "МАТСЙЕНДРАПӢТ̣ХА", "MATSYENDRAPĪṬHA"),
    ("mayurasana", "МАЙӮРĀСАНА", "MAYŪRĀSANA"),
    ("shavasana", "Ш́АВĀСАНА", "ŚAVĀSANA"),
    ("simhasana", "СИМ̣ХĀСАНА", "SIṂHĀSANA"),
    ("bhadrasana", "БХАДРĀСАНА", "BHADRĀSANA"),
    ("virasana", "ВӢРĀСАНА", "VĪRĀSANA"),
    ("kurmasana", "КӮРМĀСАНА", "KŪRMĀSANA"),
    ("prasaritasana", "ПРАСĀРИТĀСАНА", "PRASĀRITĀSANA"),
    ("padmasana", "ПАДМĀСАНА", "PADMĀSANA"),
    ("baddhapadmasana", "БАДДХАПАДМĀСАНА", "BADDHAPADMĀSANA"),
    ("siddhasana", "СИДДХĀСАНА", "SIDDHĀSANA"),
    ("pashchimatana", "ПАШ́ЧИМАТĀНĀСАНА", "PAŚCIMATĀNĀSANA"),
    ("svastikasana", "СВАСТИКĀСАНА", "SVASTIKĀSANA"),
]

POSE_BY_NUM = {i + 1: POSES[i] for i in range(len(POSES))}

# Разрыв строки иногда попадает внутрь слова (узкая колонка таблицы,
# выключка по формату). Такие склейки перечислены явно: если исходник
# перестанет их давать, скрипт об этом скажет в проверке покрытия.
GLUE = [
    ("Текстологичес", "кое", "Текстологическое"),
    ("биомеханичес", "кая", "биомеханическая"),
    ("Патофизиолог", "ический", "Патофизиологический"),
    ("терапевтическ", "ий", "терапевтический"),
    ("пищеварительног", "о", "пищеварительного"),
    ("Haṭhasaṅketacan", "drikā", "Haṭhasaṅketacandrikā"),
    ("Textological", "significance", "Textological significance"),
    ("Pathophysiolo", "gical", "Pathophysiological"),
    ("Biomechani", "cal", "Biomechanical"),
    ("Baddhapadmāsa", "na", "Baddhapadmāsana"),
    ("Баддхападмāсан", "а", "Баддхападмāсана"),
    ("Paścimatānāsan", "a", "Paścimatānāsana"),
    ("Паш́чиматāнāсан", "а", "Паш́чиматāнāсана"),
]

WARNINGS: list[str] = []


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u200b", "")).strip()


def escaped(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------ чтение PDF

def read_lines(lang: str) -> list[dict]:
    """Строки PDF с координатами: по ним видно, где заголовок, где список."""
    doc = pymupdf.open(PDF[lang])
    out = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = [s for s in line.get("spans", []) if s["text"].strip()]
                if not spans:
                    continue
                text = norm(join_spans(line["spans"]))
                if not text:
                    continue
                out.append({
                    "page": pno + 1,
                    "x": round(line["bbox"][0], 1),
                    "y": round(line["bbox"][1], 1),
                    "text": text,
                    "size": max(round(s["size"], 1) for s in spans),
                    "bold": all("Bold" in s["font"] for s in spans),
                })
    return out


# Выключка по формату вставляет в стихотворные строки растянутые пробелы.
# Иногда такой пробел попадает внутрь слова — он стоит сразу после «ш́»,
# потому что там обрывается участок набора с диакритикой. Такой пробел не
# пробел: слова в стихе разделены иначе (сверено с деванагари).
ACUTE_SHA = "ш\u0301"


def join_spans(spans: list[dict]) -> str:
    out = ""
    for i, span in enumerate(spans):
        text = span["text"]
        width = span["bbox"][2] - span["bbox"][0]
        if not text.strip() and width >= 4.5 and out.endswith(ACUTE_SHA):
            continue
        out += text
    return out


def label_of(text: str, lang: str) -> str | None:
    for key, pat in LABELS[lang].items():
        if pat and re.match(pat, text):
            return key
    return None


def tokens_of(lang: str) -> list[dict]:
    out = []
    for ln in read_lines(lang):
        text = ln["text"]
        tok = dict(ln)
        lab = label_of(text, lang)
        if text.startswith("●"):
            tok["kind"] = "bullet"
            tok["text"] = norm(text.lstrip("●"))
        elif PART.match(text) and ln["bold"] and ln["size"] >= 11.9:
            tok["kind"] = "subpart" if PART.match(text).group(3) else "part"
        elif lab:
            tok["kind"] = "label"
            tok["label"] = lab
        elif ln["size"] <= 9:
            tok["kind"] = "table"
        elif ln["bold"] and ln["size"] >= 11.9:
            tok["kind"] = "h2"
        elif ln["bold"] and ln["size"] >= 10.9:
            tok["kind"] = "h3"
        elif ln["x"] >= 65 and NUM_ITEM.match(text) and not ln["bold"]:
            tok["kind"] = "num"
        elif ln["x"] >= 65:
            tok["kind"] = "verse"
        else:
            tok["kind"] = "para"
        out.append(tok)
    return out


def merge_headings(tokens: list[dict]) -> list[dict]:
    """Заголовок, перешедший на вторую строку, склеивается в один."""
    out: list[dict] = []
    for tok in tokens:
        prev = out[-1] if out else None
        if (prev is not None and prev["kind"] in ("part", "subpart", "h2", "h3")
                and tok["kind"] in ("h2", "h3")
                and tok["bold"] and abs(tok["size"] - prev["size"]) < 0.3
                and not HEADING_START.match(tok["text"])):
            prev["text"] = prev["text"] + " " + tok["text"]
            continue
        out.append(tok)
    return out


def split_parts(tokens: list[dict]) -> list[dict]:
    parts: list[dict] = []
    cur = None
    sub = None
    for tok in tokens:
        if tok["kind"] == "part":
            cur = {"title": tok["text"], "tokens": [], "subparts": []}
            parts.append(cur)
            sub = None
        elif tok["kind"] == "subpart" and cur is not None:
            sub = {"title": tok["text"], "tokens": []}
            cur["subparts"].append(sub)
        elif sub is not None:
            sub["tokens"].append(tok)
        elif cur is not None:
            cur["tokens"].append(tok)
    return parts


def poser_head(tok: dict) -> bool:
    if tok["kind"] != "h3":
        return False
    m = POSE_HEAD.match(tok["text"])
    return bool(m and re.search(r"(ШЛОК|VERSE)", m.group(3), re.I))


def join_glued(left: str, right: str) -> str:
    """Склеивает обрывки ячейки: обычный пробел или известная склейка."""
    if not left:
        return right
    if not right:
        return left
    for tail, head, whole in GLUE:
        if left.endswith(tail) and right.startswith(head):
            return left[: -len(tail)] + whole + right[len(head):]
    return f"{left} {right}".strip()


# ------------------------------------------------------------------- таблицы

def table_groups(lang: str) -> list[dict]:
    """Таблицы издания, склеенные по страницам.

    Каждая страница даёт свой кусок; куски одной таблицы идут подряд, а на
    следующей странице повторяется шапка. Ячейки собираются из слов, попавших
    в их пределы, — иначе текст колонок перемешивается между строками.
    """
    doc = pymupdf.open(PDF[lang])
    pieces = []
    for pno, page in enumerate(doc):
        words = page.get_text("words")
        spans = [(sp["bbox"], "Bold" in sp["font"])
                 for block in page.get_text("dict")["blocks"]
                 for line in block.get("lines", []) for sp in line["spans"] if sp["text"].strip()]
        for table in page.find_tables().tables:
            rows = []
            for row in table.rows:
                cells = [cell_text(words, spans, box) for box in row.cells]
                ys = [w[1] for w in words
                      if any(c and c[0] - 1 <= (w[0] + w[2]) / 2 <= c[2] + 1
                             and c[1] - 1 <= (w[1] + w[3]) / 2 <= c[3] + 1
                             for c in row.cells if c)]
                rows.append({"y": min(ys) if ys else 0.0, "cells": cells})
            rows = [r for r in rows if any(c["text"].strip() for c in r["cells"])]
            if rows:
                pieces.append({"page": pno + 1, "rows": rows})
    groups: list[dict] = []
    for piece in pieces:
        if groups and piece["page"] - groups[-1]["page"] <= 1:
            groups[-1]["rows"].extend(piece["rows"])
            groups[-1]["page"] = piece["page"]
        else:
            groups.append({"page": piece["page"], "rows": list(piece["rows"])})
    return groups


def cell_text(words: list, spans: list, box) -> dict:
    if not box:
        return {"text": "", "bold": False}
    x0, y0, x1, y1 = box
    inside = [w for w in words
              if x0 - 1 <= (w[0] + w[2]) / 2 <= x1 + 1 and y0 - 1 <= (w[1] + w[3]) / 2 <= y1 + 1]
    inside.sort(key=lambda w: (round(w[1], 1), w[0]))
    lines: list[list[str]] = []
    for w in inside:
        if lines and abs(w[1] - lines[-1][0]) < 3:
            lines[-1][1].append(w[4])
        else:
            lines.append([w[1], [w[4]]])
    text = ""
    for _, parts in lines:
        text = join_glued(text, " ".join(parts))
    first = inside[0] if inside else None
    bold = False
    if first:
        cx, cy = (first[0] + first[2]) / 2, (first[1] + first[3]) / 2
        for (sx0, sy0, sx1, sy1), is_bold in spans:
            if sx0 - 1 <= cx <= sx1 + 1 and sy0 - 1 <= cy <= sy1 + 1:
                bold = is_bold
                break
    return {"text": norm(text), "bold": bold}


def table_rows_of(group: dict) -> list[list[dict]]:
    """Записи таблицы: строки с общим малым интервалом — одна запись.

    В издании запись отделена от следующей чуть большим интервалом
    (около 18 pt против 11 pt внутри записи), и это единственный признак,
    который не ломается на переносах ячеек.
    """
    records: list[list[dict]] = []
    prev_y = None
    for row in group["rows"]:
        gap = row["y"] - prev_y if prev_y is not None else 0
        if not records or gap > 15:
            records.append([dict(c) for c in row["cells"]])
        else:
            records[-1] = [{"text": join_glued(a["text"], b["text"]), "bold": a["bold"]}
                           for a, b in zip(records[-1], row["cells"])]
        prev_y = row["y"]
    return records


def tables_of(lang: str) -> tuple[list[list[str]], list[list[str]]]:
    """(таблица рукописей, сводная таблица āсан) как они напечатаны."""
    groups = table_groups(lang)
    if len(groups) < 2:
        raise SystemExit(f"{lang}: не найдены обе таблицы издания")
    out = []
    for group in groups[:2]:
        records = table_rows_of(group)
        head = [c["text"] for c in records[0]]
        body = [[c["text"] for c in rec] for rec in records[1:]]
        # шапка, повторённая на следующей странице, не остаётся записью
        if body and body[0] == head:
            body = body[1:]
        # запись, у которой пусты первые две колонки, — продолжение предыдущей
        merged: list[list[str]] = []
        for row in body:
            if merged and not row[0].strip() and not row[1].strip():
                merged[-1] = [join_glued(a, b) for a, b in zip(merged[-1], row)]
            else:
                merged.append(list(row))
        body = merged
        out.append([head] + body)
    return out[0], out[1]


def blocks_of(tokens: list[dict], part_title: str) -> list[dict]:
    blocks: list[dict] = [{"type": "h2", "text": part_title}]
    para: list[str] = []
    items: list[dict] = []
    ordered = False
    prev: dict | None = None

    def flush_para():
        nonlocal para
        if para:
            blocks.append({"type": "p", "text": join_text(para)})
            para = []

    def flush_list():
        nonlocal items, ordered
        if items:
            blocks.append({"type": "list", "ordered": ordered,
                           "items": [dict(it, html=escaped(it["html"])) for it in items]})
        items = []
        ordered = False

    for tok in tokens:
        kind = tok["kind"]
        if kind == "bullet":
            flush_para()
            if items and ordered:
                flush_list()
            ordered = False
            items.append({"html": tok["text"], "level": 1})
        elif kind == "num":
            flush_para()
            if items and not ordered:
                flush_list()
            ordered = True
            m = NUM_ITEM.match(tok["text"])
            items.append({"html": m.group(2) if m else tok["text"], "level": 1})
        elif kind in ("h2", "h3"):
            flush_para()
            flush_list()
            blocks.append({"type": "h3" if kind == "h2" else "h4", "text": tok["text"]})
        elif kind == "table":
            continue
        elif kind == "label":
            continue
        else:
            if items and prev and prev["page"] == tok["page"] and tok["y"] - prev["y"] < 18:
                items[-1]["html"] = (items[-1]["html"] + " " + tok["text"]).strip()
            else:
                flush_list()
                if para and prev and (prev["page"] != tok["page"] or tok["y"] - prev["y"] > 18):
                    flush_para()
                para.append(tok["text"])
        prev = tok
    flush_para()
    flush_list()
    return blocks


def join_text(parts: list[str]) -> str:
    text = ""
    for part in parts:
        text = join_glued(text, part) if text else part
    return text


# -------------------------------------------------------------- стихи и āсаны

def verse_number(tok: dict) -> str:
    m = re.search(r"(?:шлока|стих)\s+(\d+)", tok["text"]) or \
        re.search(r"[Vv]erse\s+(\d+)", tok["text"])
    return m.group(1) if m else ""


def sections_of(tokens: list[dict], fallback: str = "") -> list[dict]:
    """Тело одной единицы (стих или āсана) → разделы страницы."""
    out: list[dict] = []
    card: dict | None = None
    mode: str | None = None
    label_text = ""
    buf: list[str] = []
    items: list[dict] = []
    prev: dict | None = None

    def flush_card():
        nonlocal card
        if card and card["sections"]:
            out.append({"type": "verse_card", "verses": card["num"], "sections": card["sections"]})
        card = None

    def flush_mode():
        nonlocal buf, items, mode, label_text
        if mode in ("literal", "literary") and buf:
            out.append({
                "type": "prose",
                "key": mode,
                "label": label_text,
                "paragraphs": paragraphs(buf),
            })
        elif mode == "words" and items:
            out.append({
                "type": "words",
                "key": "words",
                "label": label_text,
                "groups": [[pair_of(it["lines"]) for it in items]],
            })
        elif mode == "comment" and items:
            out.append({"type": "label", "label": label_text})
            out.append({"type": "list", "items": [
                {"html": escaped(join_text(it["lines"])), "level": 1} for it in items
            ]})
        buf = []
        items = []
        mode = None
        label_text = ""

    for tok in tokens:
        if tok["kind"] == "label" and tok["label"] in ("deva", "iast", "cyr"):
            flush_mode()
            # «Кириллическая транслитерация (с диакритикой)» идёт без номера
            # шлоки: это тот же стих, что и карточка над ней
            num = verse_number(tok) or (card["num"] if card else "") or fallback
            if card is None or card["num"] != num:
                flush_card()
                card = {"num": num, "sections": []}
            card["sections"].append({
                "type": "verse",
                "key": tok["label"],
                "label": re.sub(r" \((шлока|verse) [^)]*\)$", "", tok["text"], flags=re.I),
                "lines": [],
            })
            prev = tok
            continue
        if card and tok["kind"] == "verse" and not mode:
            card["sections"][-1]["lines"].append(tok["text"])
            prev = tok
            continue
        if card and tok["kind"] in ("para", "num", "h3") and not mode:
            flush_card()
        if tok["kind"] == "label":
            flush_mode()
            flush_card()
            mode = {"words": "words", "literal": "literal",
                    "literary": "literary", "comment": "comment"}[tok["label"]]
            label_text = tok["text"]
            prev = tok
            continue
        if mode == "words" or mode == "comment":
            if tok["kind"] == "bullet":
                items.append({"lines": [tok["text"]]})
            elif items:
                items[-1]["lines"].append(tok["text"])
            prev = tok
            continue
        if mode in ("literal", "literary"):
            buf.append(tok["text"])
            prev = tok
            continue
        if tok["kind"] in ("para", "num"):
            out.append({"type": "p", "text": tok["text"]})
        prev = tok
    flush_card()
    flush_mode()
    return out


def paragraphs(lines: list[str]) -> list[str]:
    return [join_text(lines)] if lines else []


def pair_of(lines: list[str]) -> list[str]:
    """Один пункт разбора: «слово [основа] — грамматика — значение»."""
    text = join_text(lines)
    head, sep, tail = text.partition(" — ")
    return [head.strip(" ;"), tail.strip()] if sep else ["", text]


def units_of(tokens: list[dict], head_test) -> list[dict]:
    units = []
    cur = {"head": None, "tokens": []}
    for tok in tokens:
        if head_test(tok):
            units.append(cur)
            cur = {"head": tok["text"], "tokens": []}
        else:
            cur["tokens"].append(tok)
    units.append(cur)
    return [u for u in units if u["head"] or u["tokens"]]


def pose_from(unit: dict, lang: str) -> dict | None:
    m = POSE_HEAD.match(unit["head"])
    if not m:
        return None
    num = int(m.group(1))
    key, name_ru, name_iast = POSE_BY_NUM[num]
    # «1. ДХАНУРĀСАНА (DHANURĀSANA, ШЛОКА 5)» — кириллица снаружи, IAST внутри;
    # «1. DHANURĀSANA (BOW POSE, VERSE 5)» — наоборот: IAST снаружи, английское
    # имя внутри. Шлоки стоят после запятой в скобках.
    outer = m.group(2)
    inner = m.group(3)
    bits = [b.strip() for b in inner.split(",")]
    verses = inner.split(",", 1)[1] if "," in inner else ""
    verses = re.sub(r"(ШЛОК[АИ]|VERSES?)\s+", "", verses, flags=re.I).strip(" ,)")
    iast = titlecase(bits[0] if lang == "ru" else outer)
    name = titlecase(outer) if lang == "ru" \
        else " ".join(w.capitalize() for w in bits[0].split())
    return {
        "key": key,
        "iast": iast,
        "number": num,
        "name": name,
        "gloss": "",
        "verses": verses,
        "sections": sections_of(unit["tokens"], verses),
    }


def titlecase(name: str) -> str:
    return " / ".join(p.strip().capitalize() for p in name.split("/"))


# ------------------------------------------------------------------ датировка

# Короткие строки датировки: только то, что авторы издания говорят о дате,
# их же словами. Полная статья (§1.2) остаётся на странице асаны целиком.
DATING_SUMMARY = {
    "ru": {
        "label": "Кто как датирует (по §1.2 издания)",
        "items": [
            {
                "who": "М. Л. Гхароте, М. Венката Редди",
                "when": "1700–1750 гг. н. э.",
                "work": "Вывод издания: «Трактат был создан в период между 1700 и 1750 гг. н. э. "
                        "(первая половина XVIII века)». Нижняя граница — цитаты из «Хат̣харатнāвалӣ» "
                        "(ок. 1670–1695), верхняя — рукопись MS. No. 4235 с датой 1789 г.",
            },
            {
                "who": "Джейсон Бёрч",
                "when": "первая половина XVIII столетия",
                "work": "Дату текста отдельно не называет: относит жанр «энциклопедизма», к которому "
                        "принадлежит «Хат̣хататтвакаумудӣ», к первой половине XVIII века и Вāрāн̣асӣ.",
            },
            {
                "who": "Гудрун Бюнеманн",
                "when": "дата не названа",
                "work": "Говорит о месте главы 7 в истории перечней āсан: канонический костяк из 15 āсан "
                        "переосмыслен терапевтически, «перед бурным расцветом более обширных перечней āсан "
                        "(84 и более) в конце XVIII — начале XIX века».",
            },
            {
                "who": "Марк Синглтон",
                "when": "XVIII век",
                "work": "Дату текста отдельно не называет: объясняет фигуру Сундарадевы условиями "
                        "«космополитического Вāрāн̣аси XVIII века».",
            },
        ],
    },
    "en": {
        "label": "Who dates it how (per §1.2 of the edition)",
        "items": [
            {
                "who": "M. L. Gharote, M. Venkata Reddy",
                "when": "1700–1750 CE",
                "work": "The edition's conclusion: “The treatise was composed between 1700 and 1750 CE "
                        "(the first half of the 18th century)”. The lower bound is its citations of the "
                        "Haṭharatnāvalī (c. 1670–1695); the upper bound is MS. No. 4235, dated 1789.",
            },
            {
                "who": "Jason Birch",
                "when": "first half of the 18th century",
                "work": "Gives no separate date for the text: places the “age of encyclopaedism” to which "
                        "the Haṭhatattvakaumudī belongs in the first half of the 18th century and in Vārāṇasī.",
            },
            {
                "who": "Gudrun Bühnemann",
                "when": "no date given",
                "work": "Discusses the place of chapter 7 in the history of āsana lists: the canonical "
                        "fifteen are recast therapeutically, “before the flowering of longer lists of āsanas "
                        "(84 and more) in the late 18th and early 19th centuries”.",
            },
            {
                "who": "Mark Singleton",
                "when": "18th century",
                "work": "Gives no separate date for the text: explains Sundaradeva's figure by the conditions "
                        "of “cosmopolitan 18th-century Vārāṇasī”.",
            },
        ],
    },
}


# --------------------------------------------------------------------- сборка

def grouped(summary: dict) -> dict:
    """Сводка датировки: один заголовок на группу, а не подпись к каждой строке."""
    return {"groups": [{"title": summary.get("label"), "items": summary.get("items", [])}]}


def build(lang: str) -> dict:
    tokens = tokens_of(lang)
    parts = split_parts(merge_headings(tokens))
    if len(parts) < 3:
        raise SystemExit(f"{lang}: ожидалось три раздела, найдено {len(parts)}")
    intro, chapter, summary = parts[0], parts[1], parts[2]
    poses_part = chapter["subparts"][0] if chapter["subparts"] else {"tokens": []}

    # §1.2 — датировка: она живёт отдельной статьёй, а не внутри «О трактате»
    all_blocks = blocks_of(intro["tokens"], intro["title"])
    about, dating, in_dating = [], [], False
    for block in all_blocks:
        if block.get("type") in ("h3", "h4"):
            m = NUM_HEAD.match(block.get("text", ""))
            if m:
                in_dating = m.group(1) == "1.2"
            if in_dating:
                dating.append(block)
                continue
        (dating if in_dating else about).append(block)

    manuscripts, poses_table = tables_of(lang)

    # таблица рукописей стоит в §1.3.7 — вставляем её туда, а не в конец главы
    for i, block in enumerate(about):
        if block.get("type") in ("h3", "h4") and "1.3.7" in block.get("text", ""):
            j = i + 1
            while j < len(about) and about[j].get("type") not in ("h3", "h4"):
                j += 1
            about.insert(j, {"type": "table", "rows": manuscripts})
            break

    pose_units = [u for u in units_of(poses_part["tokens"], poser_head) if u["head"]]

    # титул издания: имя памятника и строка главы — дословно с первой страницы
    head = [t["text"] for t in tokens[:4] if t["size"] >= 14]
    about = ([{"type": "title", "text": head[0]}] if head else []) + \
            ([{"type": "byline", "text": head[1]}] if len(head) > 1 else []) + about

    return {
        "about": about,
        "dating": [b for b in dating if b.get("type") not in ("h3", "h4")],
        "chapter_title": chapter["title"],
        "chapter": units_of(chapter["tokens"], lambda t: bool(
            t["kind"] == "h3" and VERSE_HEAD.match(t["text"]))),
        "poses": [pose_from(u, lang) for u in pose_units],
        "summary_title": summary["title"],
        "summary_text": summary["tokens"],
        "summary_table": poses_table,
    }


def chapter_sections(data: dict) -> list[dict]:
    out = [{"type": "subhead", "label": data["chapter_title"]}]
    for unit in data["chapter"]:
        if not unit["head"]:
            continue
        out.append({"type": "subhead", "label": unit["head"]})
        out.extend(sections_of(unit["tokens"]))
    return out


def appendix_sections(data: dict) -> list[dict]:
    """Раздел III: сводная таблица āсан главы."""
    out = [{"type": "subhead", "label": data["summary_title"]}]
    lead = [t["text"] for t in data["summary_text"] if t["kind"] in ("para", "num")
            and len(t["text"]) > 40]
    for text in lead[:2]:
        out.append({"type": "p", "text": text})
    out.append({"type": "table", "rows": data["summary_table"]})
    return out


DATING_TITLE = {
    "ru": "1.2. Проблема датировки текста: аргументы и научная дискуссия",
    "en": "1.2. The Chronological Problem: Scholarly Arguments and Dating Debate",
}


def strings_of(payload) -> str:
    """Все строки данных одной лентой; пункты разбора склеиваются как в издании."""
    out: list[str] = []

    def walk(node):
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            # пары «слово — разбор» лежат в words.groups; у datingSummary тоже
            # есть ключ groups, но там группы — словари, а не пары
            pairs = node.get("groups")
            pairs = pairs if isinstance(pairs, list) and pairs and \
                all(isinstance(g, list) for g in pairs) else None
            if pairs:
                for group in pairs:
                    for term, gloss in group:
                        out.append(f"{term} — {gloss}")
            for key, value in node.items():
                if key != "groups" or not pairs:
                    walk(value)

    walk(payload)
    return "\n".join(out)


def coverage(lang: str, payload: dict) -> tuple[int, list[str]]:
    """Проверка: каждая содержательная строка исходника попала в данные."""
    blob = strings_of(payload)
    missing = []
    for tok in tokens_of(lang):
        if tok["kind"] not in ("para", "num", "bullet", "verse", "table"):
            continue
        text = norm(re.sub(r"^\d+\.\s+", "", tok["text"]))
        if len(text) < 30:
            continue
        probe = text[:44]
        if probe not in blob:
            missing.append(text[:80])
    return len(missing), missing


def main() -> None:
    data_ru = build("ru")
    data_en = build("en")

    poses = []
    for ru_pose, en_pose in zip(data_ru["poses"], data_en["poses"]):
        if ru_pose["key"] != en_pose["key"]:
            print("  ! ключи расходятся:", ru_pose["key"], en_pose["key"])
        poses.append({
            "key": ru_pose["key"],
            # IAST общий для двух языков; в английском томе имя печатается
            # полнее («SIṂHĀSANA / YOGASIṂHĀSANA»), его и берём
            "iast": max(ru_pose["iast"], en_pose["iast"], key=len),
            "number": ru_pose["number"],
            "name": {"ru": ru_pose["name"], "en": en_pose["name"]},
            "gloss": {"ru": ru_pose["gloss"], "en": en_pose["gloss"]},
            "verses": {"ru": ru_pose["verses"], "en": en_pose["verses"]},
            "text": {"ru": ru_pose["sections"], "en": en_pose["sections"]},
        })

    data = {
        "id": "hathatattvakaumudi",
        "chapter": "7",
        "title": {"ru": "Хат̣хататтвакаумудӣ", "en": "Haṭhatattvakaumudī"},
        "about": {"ru": data_ru["about"], "en": data_en["about"]},
        "dating": {
            "ru": {"title": DATING_TITLE["ru"], "blocks": data_ru["dating"]},
            "en": {"title": DATING_TITLE["en"], "blocks": data_en["dating"]},
        },
        "datingSummary": {k: grouped(v) for k, v in DATING_SUMMARY.items()},
        "prologue": {"ru": chapter_sections(data_ru), "en": chapter_sections(data_en)},
        "appendix": {"ru": appendix_sections(data_ru), "en": appendix_sections(data_en)},
        "notes": {"ru": [], "en": []},
        "poses": poses,
    }

    for lang in ("ru", "en"):
        count, missing = coverage(lang, data)
        print(f"  {lang}: āсан {len(data['poses'])} · строк вне данных: {count}")
        for line in missing[:6]:
            print("     не найдено:", line)

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("записано:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
