#!/usr/bin/env python3
"""Сборка data/sharngadharapaddhati.json из двух PDF о «Ш́āрн̇гадхара-паддхати».

Источник — русский и английский тома одного исследования антологии
Ш́āрн̇гадхары (1363 г. н. э.). Скрипт ничего не сочиняет: он раскладывает текст
издания по полям сайта и проверяет, что каждая строка исходника попала в
данные.

Структура издания:

    шапка (титул, выходные данные)  → страница «О трактате»
    Аннотация                       → страница «О трактате»
    ЧАСТЬ I.  Датировка (1363 г.)   → статья «Датировка», §1–5
    ЧАСТЬ II. Корпус āсан           → страница «Вступление»
        1. Стих 4375                → вступление
        2–3. Стихи 4376, 4377       → страница Падмāсаны
        4–6. Стихи 4428–4434        → вступление
        7. Стих 4435                → страница Падмāсаны (повторение)
        8. Стих 4436                → страница Ардхāсаны
        9. Стих 4437                → страница Сиддхāсаны
    ЧАСТЬ III. Сравнительная таблица и вывод → страница «Приложение»

В издании три позы получают собственные страницы: Падмāсана, Ардхāсана и
Сиддхāсана. Остальные стихи части II (место для сиденья, общие правила,
перечень поз, биомеханика) остаются на странице «Вступление», как и в
издании — это не описания отдельных āсан.

Запуск:  .venv/bin/python tools/extract_sharngadhara.py
"""

from __future__ import annotations

import sharngadhara_refs as refs   # раздел «Рукописи и издания» — не из PDF

import json
import re
import unicodedata
from pathlib import Path

import pymupdf

import diacritics  # диакритика терминов и названий поз

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sharngadharapaddhati.json"

PDF = {
    "ru": ROOT / "sources" / "Ш́āрн̇гадхара-паддхати (1363 г. н. э.).pdf",
    "en": ROOT / "sources" / "Śārṅgadharapaddhati (1363 CE).pdf",
}

# Позы, у которых в издании есть собственное описание (стихи 4376–4377, 4435,
# 4436, 4437). Ключ один для всех трактатов сайта.
POSES = [
    ("padmasana", "падмāсан", "padmāsan"),
    ("ardhasana", "ардхāсан", "ardhāsan"),
    ("siddhasana", "сиддхāсан", "siddhāsan"),
]

# Подписи блоков внутри стиха. В части I они отдельными абзацами с двоеточием,
# в части II — первым словом пункта списка; после нормализации совпадают.
LABELS = [
    (("деванагари", "devanāgarī", "devanagari"), "deva"),
    (("iast", "iast transliteration"), "iast"),
    (("кириллица", "cyrillic"), "cyr"),
    (("пословный разбор", "word-by-word analysis"), "words"),
    (("буквальный перевод", "literal translation", "translation"), "literal"),
    (("литературный перевод", "literary translation"), "literary"),
    (("текстологическое примечание", "textual note"), "note"),
    (("размер", "metre", "meter"), "metre"),
]

# Строка, перешедшая на вторую строку, склеивается обратно. Пары собраны по
# фактическим разрывам в обоих томах: проверка покрытия сообщит, если исходник
# перестанет их давать.
GLUE = [
    ("«Даттāтрея-йог", "а-ш́āстра»", "«Даттāтрея-йога-ш́āстра»"),
    ("«Хат̣ха-йога-пр", "адӣпикā»", "«Хат̣ха-йога-прадӣпикā»"),
    ("Хронологическ", "ий", "Хронологический"),
    ("Самостоятельн", "ый", "Самостоятельный"),
    ("терапевтически", "х", "терапевтических"),
    ("Випарӣта-кара", "н̣ӣ", "Випарӣта-каран̣ӣ"),
    ("Dattātreyayogaś", "āstra", "Dattātreyayogaśāstra"),
    ("Śārṅgadharapa", "ddhati", "Śārṅgadharapaddhati"),
]

PART_HEAD = re.compile(r"^(ЧАСТЬ|PART)\s+[IVX]+\.")
POSED_HEAD = re.compile(
    r"^\d+\.\s+(?:(?:Стих(?:и)?|Verse(?:s)?)\s+[\d.–]+|.*?)\s*:")
VERSE_HEAD = re.compile(
    r"^(?:\d+\.\s*)?(?:Стих(?:и)?|Verse(?:s)?)\s+(\d+(?:\.\d+)?"
    r"(?:\s*[–-]\s*\d+)?)\s*:")
NEW_PARA = 20.0          # интервал между абзацами (внутри строки ~14.4)
MATH_FONTS = ("CambriaMath", "CambriaMath-Italic")


# ------------------------------------------------------------------ чтение PDF

def norm(text: str) -> str:
    text = text.replace("\u200b", "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def read_lines(lang: str) -> list[dict]:
    """Строки издания подряд, с координатами, начертанием и шрифтом."""
    doc = pymupdf.open(PDF[lang])
    out: list[dict] = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                spans = line["spans"]
                text = norm("".join(s["text"] for s in spans))
                if not text:
                    continue
                weight = sum(len(s["text"]) for s in spans if s["text"].strip())
                bold_chars = sum(len(s["text"]) for s in spans
                                 if s["font"].startswith("Type3"))
                out.append({
                    "text": text,
                    "page": pno + 1,
                    "y": line["bbox"][1],
                    "x": line["bbox"][0],
                    "size": round(max(s["size"] for s in spans), 1),
                    "bold": weight > 0 and bold_chars / weight >= 0.85,
                    "deva": any("Mangal" in s["font"] for s in spans),
                    "math": any(s["font"].startswith(MATH_FONTS) for s in spans),
                })
    return out


def merge_wrapped(lines: list[dict]) -> list[dict]:
    """Заголовок, перешедший на вторую строку, склеивается в один.

    Продолжение узнаётся по тому же начертанию и по началу с маленькой буквы
    или с «(»/«гг.»/«Э.)»: новый заголовок так не начинается.
    """
    out: list[dict] = []
    for line in lines:
        prev = out[-1] if out else None
        if (prev is not None and prev["bold"] and line["bold"]
                and prev["size"] == line["size"] and prev["x"] < 80
                and not prev["text"].endswith(":")
                and not re.match(r"^(\d+\.|ЧАСТЬ|PART|РАЗДЕЛ|SECTION|Аннотация|"
                                 r"Abstract|Conclusion|Итоговый)", line["text"])):
            prev["text"] = prev["text"] + " " + line["text"]
            continue
        out.append(dict(line))
    return out


# ------------------------------------------------------------- разметка строк

def label_kind(text: str) -> str:
    """Какому полю сайта соответствует подпись блока («Деванагари:» и т. п.)."""
    key = text.rstrip(":").strip().lower()
    key = re.sub(r"\s*\(.*?\)\s*$", "", key)
    for names, kind in LABELS:
        for name in names:
            if key == name or key.startswith(name + " "):
                return kind
    return ""


def tokenize(lang: str) -> list[dict]:
    """Поток элементов: заголовки, подписи, пункты списка, строки текста."""
    tokens: list[dict] = []
    _, skip = build_table(lang)
    lines = [l for l in read_lines(lang)
             if line_key(l["page"], l["x"], l["y"]) not in skip]
    for line in merge_wrapped(lines):
        text, x = line["text"], line["x"]
        tok = dict(line, kind="text")
        if text in ("•", "–", "-") or (text.startswith("•") and len(text) <= 2):
            tok["kind"] = "bullet"
            tok["level"] = 2 if x >= 115 else 1
            tokens.append(tok)
            continue
        if re.match(r"^\d+\.$", text) and x < 100:
            tok["kind"] = "num"
            tokens.append(tok)
            continue
        if line["bold"] and line["size"] >= 15 and x < 80:
            tok["kind"] = "title"
            tokens.append(tok)
            continue
        if PART_HEAD.match(text) and line["bold"]:
            tok["kind"] = "part"
            tokens.append(tok)
            continue
        # полужирная строка внутри абзаца — не заголовок: она начинается со
        # строчной буквы и продолжает перечисление
        if line["bold"] and x < 80 and not text[:1].islower():
            tok["kind"] = "h"
            tokens.append(tok)
            continue
        m = VERSE_HEAD.match(text)
        if m and not line["bold"]:
            tok["kind"] = "vhead"
            tok["verse"] = m.group(1)
            tokens.append(tok)
            continue
        if text in ("Деванагари", "IAST", "Кириллица", "Devanāgarī", "Cyrillic") and x < 80:
            tok["kind"] = "vlabel"
            tok["label"] = text
            tok["key"] = label_kind(text)
            tokens.append(tok)
            continue
        if line["math"]:
            tok["kind"] = "math"
            tokens.append(tok)
            continue
        # подпись отдельным абзацем (часть I) — с отступом, но не в пункте
        # списка: там подпись стоит в начале пункта (x ≈ 108) и остаётся текстом
        if line["bold"] and text.endswith(":") and 88 <= x <= 100:
            tok["kind"] = "label"
            tok["label"] = text.rstrip(":").strip()
            tok["key"] = label_kind(text)
            tokens.append(tok)
            continue
        tokens.append(tok)
    return tokens


# ------------------------------------------------------------------- склейки

def join_glued(text: str, part: str) -> str:
    """Склейка строки с разрывом внутри слова (см. GLUE)."""
    if not text:
        return part
    for tail, head, whole in GLUE:
        if text.endswith(tail) and part.startswith(head):
            return text[: -len(tail)] + whole + part[len(head):]
    return text + " " + part


def join_text(parts: list[str]) -> str:
    text = ""
    for part in parts:
        text = join_glued(text, part)
    return text


def escaped(text: str) -> str:
    """Текст для поля html: знаки разметки не должны ломать страницу."""
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------- сборка блоков

def split_label(text: str) -> tuple[str, str, str]:
    """«Пословный разбор (падавибхāга): purā (…)» → (вид, подпись, остаток)."""
    prefix, sep, rest = text.partition(":")
    if not sep:
        return "", "", text
    kind = label_kind(prefix + ":")
    return kind, prefix.strip(), rest.strip()


def build_blocks(tokens: list[dict]) -> list[dict]:
    blocks: list[dict] = []
    para: list[str] = []
    items: list[dict] = []
    ordered = False
    label: dict | None = None      # открытый блок «подпись + строки»
    card: dict | None = None       # открытая карточка стиха
    card_lines: list[str] = []     # строки текущей части карточки
    pending: dict | None = None    # объявленный пункт списка, ещё без текста
    last: dict | None = None
    just_opened = True

    def flush_para():
        nonlocal para
        if para:
            blocks.append({"type": "p", "text": join_text(para)})
            para = []

    def flush_list():
        nonlocal items, ordered
        if items:
            blocks.append({"type": "list", "ordered": ordered, "items": items})
        items = []
        ordered = False

    def flush_label():
        nonlocal label
        if label is not None:
            kind, lines = label["key"], label["lines"]
            text = join_text(lines)
            if kind == "words":
                blocks.append(words_block(label["label"], text))
            elif kind in ("literal", "literary"):
                blocks.append({"type": "prose", "key": kind, "label": label["label"],
                               "paragraphs": paragraphs(lines)})
            elif kind == "note":
                blocks.append({"type": "note", "paragraphs": paragraphs(lines)})
            elif kind == "metre":
                blocks.append({"type": "p", "text": label["label"] + ": " + text})
            else:
                blocks.append({"type": "p", "text": text})
        label = None

    def flush_card_part():
        nonlocal card_lines
        if card is not None and card.get("pending") is not None:
            part = card["pending"]
            part["lines"] = list(card_lines)
            card["parts"].append(part)
            card["pending"] = None
        card_lines = []

    def flush_card():
        nonlocal card
        flush_card_part()
        if card is not None and card["parts"]:
            blocks.append({"type": "verse_card", "verses": card["verses"],
                           "sections": card["parts"]})
        card = None

    def flush_all():
        nonlocal pending
        flush_para()
        flush_list()
        flush_label()
        flush_card()
        pending = None

    for tok in tokens:
        kind = tok["kind"]
        gap = None
        if last is not None and last["page"] == tok["page"]:
            gap = tok["y"] - last["y"]

        if kind == "title":
            flush_all()
            blocks.append({"type": "title", "text": tok["text"]})
        elif kind in ("part", "h"):
            flush_all()
            blocks.append({"type": "h2" if kind == "part" else "h3", "text": tok["text"]})
        elif kind == "vhead":
            flush_all()
            blocks.append({"type": "h4", "text": tok["text"], "verse": tok["verse"]})
            card = {"verses": tok["verse"], "parts": [], "pending": None}
        elif kind == "vlabel":
            flush_para()
            flush_list()
            flush_label()
            flush_card_part()
            if card is None:
                card = {"verses": "", "parts": [], "pending": None}
            card["pending"] = {"type": "verse", "key": tok["key"],
                               "label": tok["label"], "lines": []}
        elif kind == "label":
            flush_para()
            flush_list()
            flush_card()
            flush_label()
            label = {"key": tok["key"] or "text", "label": tok["label"], "lines": []}
        elif kind in ("bullet", "num"):
            flush_para()
            flush_card()
            flush_label()
            pending = {"kind": kind, "level": tok.get("level", 1)}
        elif kind == "math":
            flush_all()
            blocks.append({"type": "quote", "paragraphs": [escaped(tok["text"])]})
        else:  # строка текста
            if pending is not None:
                # пункт списка может оказаться подписью раздела страницы
                label_kind_of, prefix, rest = split_label(tok["text"])
                if label_kind_of:
                    flush_para()
                    flush_list()
                    flush_card()
                    label = {"key": label_kind_of, "label": prefix,
                             "lines": [rest] if rest else []}
                    pending = None
                    last, just_opened = tok, False
                    continue
                ord_flag = pending["kind"] == "num"
                if items and ordered != ord_flag:
                    flush_list()
                ordered = ord_flag
                items.append({"html": "", "level": pending["level"],
                              "lines": [tok["text"]]})
                pending = None
                last, just_opened = tok, False
                continue
            if items:
                if not just_opened and gap is not None and gap > NEW_PARA:
                    flush_list()
                else:
                    items[-1]["lines"].append(tok["text"])
                    last, just_opened = tok, False
                    continue
            if card is not None and card.get("pending") is not None and (
                    just_opened or gap is None or gap <= NEW_PARA):
                card_lines.append(tok["text"])
            elif label is not None and (just_opened or gap is None or gap <= NEW_PARA):
                label["lines"].append(tok["text"])
            else:
                if card_lines:
                    flush_card_part()
                if label is not None:
                    flush_label()
                if para and gap is not None and gap > NEW_PARA:
                    flush_para()
                para.append(tok["text"])
        just_opened = kind in ("bullet", "num", "vlabel", "label", "vhead")
        last = tok

    flush_all()
    for blk in blocks:
        if blk["type"] == "list":
            for item in blk["items"]:
                item["html"] = escaped(join_text(item.pop("lines")))
    # карточка без разбора (заголовок стиха без текста) на страницу не нужна
    return [b for b in blocks if not (b["type"] == "verse_card" and not b["sections"])]


def paragraphs(lines: list[str]) -> list[str]:
    """Абзацы внутри подписи: строки склеиваются, пустая строка — граница."""
    out: list[str] = []
    buf: list[str] = []
    for line in lines:
        if not line.strip():
            if buf:
                out.append(join_text(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        out.append(join_text(buf))
    return out


# ------------------------------------------------------------------- таблица

COL_X = [113.0, 212.0, 311.0, 410.0]


def column_of(x: float) -> int:
    best, dist = 0, 1e9
    for i, cx in enumerate(COL_X):
        if abs(x - cx) < dist:
            best, dist = i, abs(x - cx)
    return best


HEADER_WORDS = ("Параметр", "Feature")


def table_lines(lang: str) -> list[dict]:
    """Строки издания с сохранением пробелов: по ним собираются ячейки."""
    doc = pymupdf.open(PDF[lang])
    out: list[dict] = []
    for pno, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block.get("lines", []):
                raw = "".join(s["text"] for s in line["spans"])
                raw = re.sub(r"[ \t]+", " ", raw.replace("\u200b", "").replace("\xa0", " "))
                if not raw.strip():
                    continue
                out.append({"page": pno + 1,
                            "y": round(line["bbox"][1], 1),
                            "x": round(line["bbox"][0], 1),
                            "piece": raw})
    return out


def line_key(page: int, x: float, y: float) -> tuple[int, float, float]:
    return (page, round(x, 1), round(y, 1))


def build_table(lang: str) -> tuple[list[list[str]], set]:
    """Сравнительная таблица части III: шапка и четыре записи, четыре столбца.

    Ячейки собираются по столбцам. Строка начинается там, где первый столбец
    уходит вниз больше чем на строку; повтор шапки на следующей странице
    отбрасывается. Строки издания, занятые таблицей, помечаются, чтобы не
    попасть в текст страницы.
    """
    lines = table_lines(lang)
    head = next((l for l in lines
                 if l["x"] < 200 and l["piece"].strip() in HEADER_WORDS), None)
    if head is None:
        return [], set()

    pages = [head["page"]]
    pages += sorted({l["page"] for l in lines
                     if l["page"] > head["page"] and l["x"] < 200
                     and l["piece"].strip() in HEADER_WORDS})
    top = min(l["y"] for l in lines
              if l["page"] == head["page"] and l["x"] >= 105
              and head["y"] - 45 <= l["y"] <= head["y"])

    region: list[dict] = []
    for i, page in enumerate(pages):
        cells = [l for l in lines if l["page"] == page and l["x"] >= 105]
        if i == 0:
            cells = [l for l in cells if l["y"] >= top - 2]
        else:
            repeat = next((l for l in cells
                           if l["x"] < 200 and l["piece"].strip() in HEADER_WORDS), None)
            after = repeat["y"] if repeat else 0.0
            # ячейки повтора шапки стоят над её первым столбцом
            cells = [l for l in cells if l["y"] > after]
            body = [l["y"] for l in lines
                    if l["page"] == page and l["x"] < 105 and l["y"] > after + 10]
            cut = min(body) if body else float("inf")
            cells = [l for l in cells if l["y"] < cut]
        region.extend(cells)
    region.sort(key=lambda l: (l["page"], l["y"], l["x"]))

    starts: list[tuple[int, float]] = [(head["page"], top)]
    last: tuple[int, float] | None = None
    for l in region:
        if column_of(l["x"]) != 0 or l["piece"].strip() in HEADER_WORDS:
            continue
        if last is not None and last[0] == l["page"] and l["y"] - last[1] <= 16:
            last = (l["page"], l["y"])       # продолжение ячейки первого столбца
            continue
        starts.append((l["page"], l["y"]))
        last = (l["page"], l["y"])

    rows: list[list[list[str]]] = [[[] for _ in COL_X] for _ in starts]
    for l in region:
        pos = None
        for i, (page, y) in enumerate(starts):
            if (l["page"], l["y"]) < (page, y - 2):
                break
            pos = i
        if pos is not None:
            rows[pos][column_of(l["x"])].append(l["piece"])

    table = [[norm("".join(cell)) for cell in row] for row in rows]
    keys = {line_key(l["page"], l["x"], l["y"]) for l in region}
    return table, keys


# -------------------------------------------------------------------- разделы

WORD_RE = re.compile(r"\w+")


def words_of(text: str) -> list[str]:
    """Слова текста: знаки и пробелы не считаются (для сверки разбора)."""
    return WORD_RE.findall(unicodedata.normalize("NFC", text))


def word_groups(text: str) -> list[list[str]]:
    """Пословный разбор → пары [термин, перевод] для таблицы на странице.

    Издание пишет разбор подряд: «слово (перевод)», разделяя пары знаками «/»,
    «//», «;» и метками конца стиха («5 //»). Знаки — не слова: в таблицу идут
    только пары, а `words_of()` ниже убеждается, что ни одно слово разбора не
    потерялось и не переставилось.
    """
    pairs: list[list[str]] = []
    i, n, start = 0, len(text), 0
    while i < n:
        if text[i] == "(":
            depth, j = 0, i
            while j < n:
                if text[j] == "(":
                    depth += 1
                elif text[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:
                break
            pairs.append([text[start:i].strip(), text[i + 1:j].strip()])
            i, start = j + 1, j + 1
            continue
        i += 1
    tail = text[start:].strip()
    if tail:
        pairs.append([tail, ""])

    out: list[list[str]] = []
    for term, gloss in pairs:
        term = re.sub(r"^(?://|/)", "", term).strip()
        term = re.sub(r"^;", "", term).strip()
        term = re.sub(r";$", "", term).strip()
        if not re.search(r"\w", term):
            continue                    # «/», «//», «;», «5 //» — знаки, не слово
        out.append([term, gloss])
    return out


def words_block(label: str, text: str) -> dict:
    block = {"type": "words", "label": label,
             "paragraphs": [text] if text else []}
    if text:
        groups = word_groups(text)
        left = " ".join(t + " " + g for t, g in groups)
        if words_of(left) != words_of(text):
            raise ValueError("пословный разбор не совпал с текстом издания: " + text[:80])
        # та же форма, что у остальных трактатов: список групп, а в группе —
        # пары «слово → значение». Разбор одного стиха — одна группа.
        if len(groups) >= 2:
            block["groups"] = [groups]
    return block


def split_parts(blocks: list[dict]) -> dict[str, list[dict]]:
    """Разделы издания: до части I, часть I, часть II, часть III."""
    parts: dict[str, list[dict]] = {"front": [], "one": [], "two": [], "three": []}
    current = "front"
    for block in blocks:
        if block["type"] == "h2":
            upper = block["text"].upper()
            # III проверяется первой: «ЧАСТЬ III» начинается и с «ЧАСТЬ II»
            if re.match(r"^(ЧАСТЬ|PART)\s+III\b", upper):
                current = "three"
            elif re.match(r"^(ЧАСТЬ|PART)\s+II\b", upper):
                current = "two"
            elif re.match(r"^(ЧАСТЬ|PART)\s+I\b", upper):
                current = "one"
        parts[current].append(block)
    return parts


def pose_of(heading: str) -> str:
    low = unicodedata.normalize("NFC", heading).lower()
    for key, ru_stem, en_stem in POSES:
        if ru_stem in low or en_stem in low:
            return key
    return ""


def pose_name(heading: str, lang: str) -> tuple[str, str]:
    """(IAST-имя, отображаемое имя) из заголовка стиха."""
    body = re.sub(r"^\d+\.\s*", "", heading)
    body = re.sub(r"^(?:Стих(?:и)?|Verse(?:s)?)\s+[\d.–]+\s*:\s*", "", body)
    m = re.match(r"^(.+?)\s*\((.+)\)\s*$", body)
    outer = (m.group(1) if m else body).strip()
    inner = (m.group(2) if m else "").strip()
    if lang == "ru":
        # «Падмāсана (Padmāsana — Поза лотоса)»: кириллица снаружи
        iast = inner.split("—")[0].strip() if inner else outer
        return iast, outer
    # «Padmāsana (The Lotus Posture)»: IAST снаружи
    return outer, inner or outer


def collect_poses(part_two: list[dict], lang: str) -> tuple[list[dict], list[dict]]:
    """Стихи с описанием отдельной āсаны уходят на её страницу."""
    units: list[dict] = []
    current = None
    for block in part_two:
        if block["type"] == "h4":
            current = {"heading": block["text"], "blocks": [], "key": pose_of(block["text"])}
            units.append(current)
            continue
        if block["type"] in ("h2", "h3"):
            current = None
        if current is not None:
            current["blocks"].append(block)
        else:
            units_rest = None
    # карта «ключ → блоки в порядке издания»
    poses: dict[str, dict] = {}
    order: list[str] = []
    rest: list[dict] = []
    current = None
    for block in part_two:
        if block["type"] == "h4":
            current = block
            key = pose_of(block["text"])
            if key:
                if key not in poses:
                    iast, name = pose_name(block["text"], lang)
                    poses[key] = {"key": key, "iast": iast, "name": name,
                                  "headings": [], "blocks": [], "verses": []}
                    order.append(key)
                poses[key]["headings"].append(block["text"])
                poses[key]["verses"].append(block.get("verse", ""))
                poses[key]["blocks"].append({"type": "h4", "text": block["text"]})
            else:
                rest.append(block)
            continue
        if block["type"] in ("h2", "h3"):
            current = None
            rest.append(block)
            continue
        if current is not None and pose_of(current["text"]):
            poses[pose_of(current["text"])]["blocks"].append(block)
        else:
            rest.append(block)
    return [poses[k] for k in order], rest


DEVANAGARI = re.compile(r"[\u0900-\u097f]")


def hoist_notes(blocks: list[dict]) -> list[dict]:
    """Приписка после стиха — примечание, а не строка транслитерации.

    В издании после строфы 4435 стоит пояснение в скобках; в карточке стиха
    ему не место, поэтому оно выносится отдельным примечанием сразу за ней.
    """
    out: list[dict] = []
    for block in blocks:
        if block["type"] != "verse_card":
            out.append(block)
            continue
        notes: list[str] = []
        for part in block["sections"]:
            keep: list[str] = []
            taking = False      # пояснение в скобках занимает несколько строк
            for line in part["lines"]:
                if taking:
                    notes.append(line)
                    if line.rstrip().endswith(")"):
                        taking = False
                    continue
                if keep and line.startswith("(") and not DEVANAGARI.search(line):
                    notes.append(line)
                    taking = not line.rstrip().endswith(")")
                    continue
                keep.append(line)
            part["lines"] = keep
        block["sections"] = [p for p in block["sections"] if p["lines"]]
        if block["sections"]:
            out.append(block)
        if notes:
            out.append({"type": "note", "paragraphs": paragraphs(notes)})
    return out


def build(lang: str) -> dict:
    blocks = build_blocks(tokenize(lang))
    parts = split_parts(blocks)
    table, _ = build_table(lang)

    # шапка издания: титул, выходные данные, аннотация
    front = list(parts["front"])
    if front and front[0]["type"] == "title":
        if len(front) > 1 and front[1]["type"] == "p":
            # «Автор-составитель антологии: …» — строка под титулом
            front[1] = {"type": "byline", "text": front[1]["text"]}

    # часть I — статья о датировке: заголовок части, затем §1–5
    one = list(parts["one"])
    dating_title = one[0]["text"] if one and one[0]["type"] == "h2" else ""
    dating = [b for b in one[1:]] if dating_title else one

    # часть II — корпус: āсаны с собственным описанием отдельно
    two = [{"type": "subhead", "label": b["text"]}
           if b["type"] == "h2" and re.match(r"^(ЧАСТЬ|PART)\s+II\b", b["text"].upper())
           else b for b in parts["two"]]
    poses, rest_two = collect_poses(two, lang)

    # часть III — сравнительная таблица и вывод
    three = list(parts["three"])
    appendix: list[dict] = []
    for block in three:
        if block["type"] == "h2":
            appendix.append({"type": "subhead", "label": block["text"]})
            appendix.append({"type": "table", "rows": table})
            continue
        appendix.append(block)

    return {
        "about": hoist_notes(front),
        "dating": hoist_notes(dating),
        "dating_title": dating_title,
        "chapter": hoist_notes(rest_two),
        "appendix": hoist_notes(appendix),
        "poses": [dict(p, blocks=hoist_notes(p["blocks"])) for p in poses],
    }


# --------------------------------------------------------------------- проверка

def strings_of(payload) -> str:
    out: list[str] = []

    def walk(node):
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key, value in node.items():
                if key in ("type", "key", "level"):
                    continue
                walk(value)

    walk(payload)
    return "\n".join(out)


def coverage(lang: str, payload: dict) -> tuple[int, list[str]]:
    """Каждая содержательная строка исходника должна быть в данных."""
    blob = strings_of(payload)
    missing: list[str] = []
    for line in read_lines(lang):
        text = norm(line["text"]).rstrip(":").strip()
        if len(text) < 24:
            continue
        probe = text[:40]
        if probe in blob:
            continue
        # строки таблицы собираются по ячейкам, а не подряд
        if line["x"] >= 100:
            continue
        missing.append(text[:80])
    return len(missing), missing


def main() -> None:
    data_ru = build("ru")
    data_en = build("en")

    poses = []
    keys_en = {p["key"]: p for p in data_en["poses"]}
    for number, ru_pose in enumerate(data_ru["poses"], start=1):
        en_pose = keys_en[ru_pose["key"]]
        poses.append({
            "key": ru_pose["key"],
            "heading": {lang: p["headings"][0] for lang, p in
                        (("ru", ru_pose), ("en", en_pose))},
            "iast": ru_pose["iast"],
            "number": number,
            "name": {"ru": ru_pose["name"], "en": en_pose["name"]},
            "gloss": {"ru": "", "en": ""},
            "verses": {"ru": ", ".join(ru_pose["verses"]),
                       "en": ", ".join(en_pose["verses"])},
            "text": {"ru": ru_pose["blocks"], "en": en_pose["blocks"]},
        })

    data = {
        "id": "sharngadharapaddhati",
        "chapter": "157–158",
        "title": {"ru": "Ш́āрн̇гадхара-паддхати", "en": "Śārṅgadharapaddhati"},
        "about": {"ru": data_ru["about"], "en": data_en["about"]},
        "dating": {
            "ru": {"title": data_ru["dating_title"], "blocks": data_ru["dating"]},
            "en": {"title": data_en["dating_title"], "blocks": data_en["dating"]},
        },
        "prologue": {"ru": data_ru["chapter"], "en": data_en["chapter"]},
        "appendix": {"ru": data_ru["appendix"], "en": data_en["appendix"]},
        "notesTitle": refs.TITLE,
        "notes": {"ru": refs.RU, "en": refs.EN},
        "poses": poses,
    }

    for lang in ("ru", "en"):
        count, missing = coverage(lang, data)
        print(f"  {lang}: āсан {len(data['poses'])} · строк вне данных: {count}")
        for line in missing[:8]:
            print("     не найдено:", line)

    data = diacritics.fix_document(data)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("записано:", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
