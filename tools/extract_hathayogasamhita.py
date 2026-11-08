#!/usr/bin/env python3
"""Сборка data/hathayogasamhita.json из двух томов девятого трактата.

Источник — русский и английский тома одной работы: глава 2 «Āsana-prakaraṇa»
«Хат̣хайогасам̣хитā» (XVII в.) в издании на хинди «Śrī Bhārata Dharma
Mahāmaṇḍala» (Vārāṇasī, под редакцией Yogirāja Svāmī Jñānānanda Ji Mahārāja).
Скрипт ничего не сочиняет: он раскладывает текст томов по полям сайта и
проверяет, что раскладка сошлась.

Структура тома:

    заглавие, «Введение», «Утерянное звено», «Сходство текстов»,
    «Структура перевода»                    → раздел «О трактате»
    «Глава 2. Āsana-prakaraṇa»              → «Глава» (раздел об āсанах)
    стихи 2.1–2.11 (определение, число, место практики, список)  → «Глава»
    стихи 2.12–2.52 — тридцать три āсаны    → тридцать три страницы āсан
    «Заключение», «Источник»                → раздел «О трактате»

Каждый стих в томе разобран шестью полями: деванāгарӣ, комментарий на хинди
(деванāгарӣ), IAST, кириллическая транслитерация, пословный разбор, перевод и
перевод комментария на хинди. Поля идут в томе под своими метками; скрипт
читает их по меткам, а не по числу строк, поэтому стих из двух шлок остаётся
одной карточкой — ровно так, как его печатает том.

Адреса āсан (латинский сегмент) — общая нумерация сайта: если поза уже есть в
других трактатах, берётся её прежний адрес (Matsyendrāsana → matsyendrapitha,
Uttānakūrmāsana → uttanakurmaka, Paścimottānāsana / Ugrāsana → pashchimatana,
Mṛtāsana / Śavāsana → shavasana); остальные получают адрес из своего имени.
Расхождение печатается, а не замалчивается.

Запуск:  python3 tools/extract_hathayogasamhita.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_mix import scan  # noqa: E402  (проверка «одно слово — один алфавит»)
import diacritics  # noqa: E402  (диакритика терминов и названий поз)
from deva import to_iast  # noqa: E402  (деванāгарӣ → IAST, для сверки переносов)
# та же карта латинских сегментов адреса, что и у восьмого трактата
from extract_matsyendra import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hathayogasamhita.json"

PDF = {
    "ru": ROOT / "sources" / "Хат̣хайогасам̣хитā. Глава 2. Āсана-пракаран̣а (RU).pdf",
    "en": ROOT / "sources" / "Haṭhayogasaṃhitā. Chapter 2. The Āsana Section (EN).pdf",
}

# Метки полей — так, как они напечатаны в томе. Порядок разбора — от длинной
# метки к короткой: «Перевод комментария на хинди» начинается с «Перевод»,
# «English translation of the Hindi commentary» — с «English».
LABELS = {
    "ru": [
        ("devanote", "Примечание к санскриту"),
        ("commenttrans", "Перевод комментария на хинди"),
        ("hindicomment", "Комментарий на хинди (исправленный)"),
        ("words", "Пословный разбор"),
        ("deva", "Devanagari"),
        ("iast", "IAST"),
        ("cyr", "Cyrillic"),
        ("trans", "Перевод"),
        ("note", "Примечание"),
    ],
    "en": [
        ("commenttrans", "English translation of the Hindi commentary"),
        ("hindicomment", "Hindi commentary (corrected text)"),
        ("devanote", "Note on Sanskrit"),
        ("deva", "Sanskrit (Devanāgarī)"),
        ("words", "Word-by-word analysis"),
        ("cyr", "Cyrillic transliteration"),
        ("iast", "IAST"),
        ("trans", "Translation"),
        ("note", "Note"),
    ],
}

VERSE_KEYS = ("deva", "iast", "cyr")

# Подзаголовки статьи: с них начинается раздел «О трактате».
SUBHEADS = {
    "ru": ["Введение",
           "«Утерянное звено»: Исследование Джейсона Бёрча",
           "Сходство текстов и уникальность используемого издания",
           "Структура перевода",
           "Заключение"],
    "en": ["Introduction",
           "The Missing Link: Jason Birch’s Research",
           "Textual Similarities and the Edition Used",
           "Organisation of the Translation",
           "Conclusion",
           "Source"],
}

# Заголовок главы: с него начинается раздел об āсанах.
CHAPTER = {
    "ru": re.compile(r"^Глава 2\.\s"),
    "en": re.compile(r"^Chapter 2:\s"),
}

# Заголовок стиха: «Стих 2.12-13 (Сиддха̄сана)», «Verse 2.14 — Svastikāsana».
VERSE_HEAD = {
    "ru": re.compile(r"^Стих 2\.(?P<num>\d+(?:-\d+)?)\s*\((?P<title>.+)\)$"),
    "en": re.compile(r"^Verse 2\.(?P<num>\d+(?:-\d+)?)\s+—\s+(?P<title>.+)$"),
}

# Стихи 2.1–2.11 — не āсаны: определение, число, место практики, перечень.
NON_POSE = 6

# Позы, у которых на сайте уже есть страница под другим адресом.
KEY_OVERRIDES = {
    "Matsyendrāsana": "matsyendrapitha",
    "Uttānakūrmāsana": "uttanakurmaka",
    "Paścimottānāsana / Ugrāsana": "pashchimatana",
    "Mṛtāsana / Śavāsana": "shavasana",
}

# Просвет между строками внутри абзаца и между абзацами в этих томах не
# пересекается (внутри — до 4,2 пт, между — от 8,1 пт), поэтому порог разделяет
# их без догадок.
PARA_GAP = 7.0

# Строка деванāгарӣ, оборванная посреди слова, не доходит до правого края:
# в этих томах такие строки кончаются левее 400 пт, набранные — у 500–525 пт.
SHORT_LINE = 400.0

ZERO_WIDTH = "\u200b\u200c\u200d\ufeff"


# --------------------------------------------------------------- чтение тома

def stream(lang: str) -> list[dict]:
    """Строки тома по порядку с просветом до предыдущей строки (в пунктах)."""
    items: list[dict] = []
    for page in pymupdf.open(PDF[lang]):
        prev = None
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"])
                for ch in ZERO_WIDTH:
                    text = text.replace(ch, "")
                text = text.strip()
                if not text:
                    continue
                gap = None if prev is None else line["bbox"][1] - prev
                items.append({"page": page.number, "t": text, "gap": gap,
                              "x2": line["bbox"][2]})
                prev = line["bbox"][3]
    return items


def match_label(lang: str, text: str):
    """Метка поля в начале строки → (ключ, остаток строки)."""
    for key, label in LABELS[lang]:
        if not text.startswith(label):
            continue
        rest = text[len(label):]
        if rest and not rest.startswith(":"):
            continue
        return key, rest.lstrip(":").strip()
    return None


def ends_sentence(line: str) -> bool:
    """Закончилась ли фраза: по этому видно, оборван ли абзац на странице."""
    tail = line.rstrip().rstrip("»”’)")
    return bool(re.search(r"[.!?…]$", tail))


# --------------------------------------------------------------- разбор тома

def parse(lang: str) -> dict:
    items = stream(lang)
    groups: list[dict] = []
    blocks: list[dict] = []            # «О трактате»: абзацы и подзаголовки
    chapter = None
    cur: dict | None = None
    field: dict | None = None
    para: list[str] | None = None

    def flush_para() -> None:
        nonlocal para
        if para:
            blocks.append({"type": "p", "text": re.sub(r"\s+", " ", " ".join(para))})
            para = None

    for it in items:
        text, gap = it["t"], it["gap"]

        head = VERSE_HEAD[lang].match(text)
        if head:
            flush_para()
            field = None
            # номер стиха печатается так, как он стоит в томе: 2.12-13
            cur = {"num": "2." + head.group("num"), "title": head.group("title").strip(),
                   "fields": []}
            groups.append(cur)
            continue

        if CHAPTER[lang].match(text):
            flush_para()
            field = None
            cur = None
            chapter = text
            continue

        if text in SUBHEADS[lang]:
            flush_para()
            field = None
            cur = None
            blocks.append({"type": "subhead", "label": text})
            continue

        label = match_label(lang, text)
        if label and cur is not None:
            flush_para()
            key, rest = label
            field = {"key": key,
                     "lines": [{"t": rest, "x2": it["x2"]}] if rest else []}
            cur["fields"].append(field)
            continue

        if cur is not None and field is not None:
            field["lines"].append({"t": text, "x2": it["x2"]})
            continue

        # абзац статьи: границу задаёт просвет, начало страницы или метка
        # списка (пункты списка набраны вплотную, просвет их не разделяет)
        new_para = para is None
        if text.startswith("●") or re.match(r"^\d+\.\s", text):
            new_para = True
        if text.startswith("●") or re.match(r"^\d+\.\s", text):
            pass
        elif para is not None and gap is not None and gap > PARA_GAP:
            new_para = True
        elif para is not None and gap is None and ends_sentence(para[-1]):
            new_para = True
        if new_para:
            flush_para()
            para = [text]
        else:
            para.append(text)
    flush_para()

    if chapter is None:
        raise SystemExit(f"не найден заголовок главы ({lang})")
    return {"chapter": chapter, "groups": groups, "blocks": blocks}


# --------------------------------------------------- склейка строк в абзац

def join_plain(lines: list[dict]) -> str:
    return re.sub(r"\s+", " ", " ".join(line["t"] for line in lines)).strip()


SEPARATORS = re.compile(r"[\s|,;:।॥—–()\[\]«»“”\"'!?.]+")
RAW_TEXT: dict[str, str] = {}


def word_set(text: str) -> set[str]:
    """Слова текста — для проверки «есть ли это слово отдельным словом»."""
    return {w for w in SEPARATORS.split(text) if w}


def starts_with_mark(text: str) -> bool:
    """Строка начинается со знака огласовки: слово так начинаться не может."""
    return bool(text) and unicodedata.category(text[0]) in ("Mn", "Mc")


def join_deva(lines: list[dict], refs: dict, where: str) -> str:
    """Склеить строки деванāгарӣ, решая каждый перенос.

    В деванāгарӣ нет подсказки, где кончилось слово: перенос может пройти внутри
    слова («त्रयस्त्रिं | शन्मर्त्यलोके»), а может — по пробелу («…चायतं |
    सम्यग्गोमय…»). Решение принимается по признакам, в таком порядке:

    0. строка начинается со знака огласовки — слово так начинаться не может,
       значит перенос прошёл внутри слова;
    1. по IAST того же стиха: склейка верна, если слитое слово есть в IAST
       отдельным словом, а раздельное — нет;
    2. по другому тому: та же фраза набрана там независимо, и слово ищется
       в нём (комментарий на хинди IAST не имеет, зато есть во втором томе);
       односложные обрывки словом не считаются — они и сами могут быть
       обрывом;
    3. по набору: строка, оборванная посреди слова, кончается коротко и без
       дан̣д̣ы; набранная доходит до правого края или кончается знаком.

    Каждое решение печатается, чтобы его было видно.
    """
    iast = refs["iast"]
    other = refs["other"]
    out = lines[0]["t"]
    for prev, nxt in zip(lines, lines[1:]):
        text = nxt["t"]
        words = out.split()
        w1 = words[-1] if words else ""
        w2 = text.split()[0]
        rule = None
        if starts_with_mark(w2):
            rule = "знак огласовки"
        else:
            glued, apart = to_iast(w1 + w2), to_iast(w2)
            if glued and glued in iast and apart not in iast:
                rule = "IAST"
            elif apart and apart in iast and glued not in iast:
                out += " " + text
                continue
            elif len(w2) > 1 and (w1 + w2) in other and w2 not in other:
                rule = "другой том"
            elif len(w2) > 1 and w2 in other:
                out += " " + text
                continue
        if rule is None:
            tail = prev["t"].rstrip()
            if prev["x2"] < SHORT_LINE and not re.search(r"[।॥,.!?;:»)\]-]$", tail):
                rule = "набор строки"
        if rule:
            out += text
            print(f'  перенос внутри слова по признаку «{rule}» ({where}): '
                  f'«{w1}» + «{w2}…»')
        else:
            out += " " + text
    return re.sub(r"\s+", " ", out).strip()


def fields_of(group: dict, lang: str, other_lang: str) -> dict:
    """Поля стиха: ключ → одна строка текста."""
    raw = {f["key"]: f["lines"] for f in group["fields"]}
    iast = join_plain(raw.get("iast", []))
    refs = {"iast": word_set(iast), "other": word_set(RAW_TEXT[other_lang])}
    out = {}
    for key, lines in raw.items():
        # деванāгарӣ в томе дважды: стих и комментарий на хинди
        if key in ("deva", "hindicomment"):
            out[key] = join_deva(lines, refs, f'{lang} {group["num"]}')
        else:
            out[key] = join_plain(lines)
    return out


# ------------------------------------------------------------------ проверки

def json_texts(node, out: list[str]) -> list[str]:
    """Весь текст, который попал в данные (для проверки «ничего не потеряно»)."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("key", "type", "id", "iast", "number"):
                continue
            json_texts(value, out)
    elif isinstance(node, list):
        for value in node:
            json_texts(value, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def lost_lines(data: dict, lang: str) -> list[str]:
    """Строки тома, которых нет в данных ни одной подстрокой."""
    haystack = re.sub(r"\s+", " ", " ".join(json_texts(data, [])))
    labels = {label for _, label in LABELS[lang]}
    lost = []
    for it in stream(lang):
        probe = it["t"]
        if probe in labels or probe in SUBHEADS[lang]:
            continue
        if VERSE_HEAD[lang].match(probe) or CHAPTER[lang].match(probe):
            continue
        for _, label in LABELS[lang]:
            if probe.startswith(label):
                probe = probe[len(label):].lstrip(":").strip()
        # метка списка (● или «1.») снята при сборке, строка проверяется без неё
        probe = re.sub(r"^(?:●|\d+\.)\s*", "", probe)
        if len(probe) > 3 and re.sub(r"\s+", " ", probe) not in haystack:
            lost.append(probe)
    return lost


def compare_with_iast(groups: list[dict]) -> list[str]:
    """Сверка деванāгарӣ с IAST того же стиха — по словам, без диакритики."""
    def norm(word: str) -> str:
        word = word.replace("—", " ").replace("–", " ")
        return re.sub(r"[^a-zāīūṛṃḥṭḍṇśṣṅñ]", "", word.lower())

    bad: list[str] = []
    for group in groups:
        iast = group["fields"].get("iast", "")
        deva = group["fields"].get("deva", "")
        if not iast or not deva:
            continue
        a = {norm(w) for w in re.split(r"[\s|]+", to_iast(deva)) if norm(w)}
        b = {norm(w) for w in re.split(r"[\s|]+", iast) if norm(w)}
        diff = a - b
        if diff:
            bad.append(f'{group["num"]}: ' + ", ".join(sorted(diff)[:6]))
    return bad


# ------------------------------------------------------------------ сборка

ABOUT_TITLES = {"ru": "О трактате", "en": "About the treatise"}


def list_blocks(blocks: list[dict]) -> list[dict]:
    """Строки «●» и «1.» → настоящие списки, остальное остаётся абзацами."""
    out: list[dict] = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if block["type"] == "p" and block["text"].startswith("●"):
            items = []
            while i < len(blocks) and blocks[i]["type"] == "p" \
                    and blocks[i]["text"].startswith("●"):
                items.append(blocks[i]["text"].lstrip("●").strip())
                i += 1
            out.append({"type": "list", "items": items})
            continue
        if block["type"] == "p" and re.match(r"^\d+\.\s", block["text"]):
            items = []
            while i < len(blocks) and blocks[i]["type"] == "p" \
                    and re.match(r"^\d+\.\s", blocks[i]["text"]):
                items.append(re.sub(r"^\d+\.\s*", "", blocks[i]["text"]))
                i += 1
            out.append({"type": "list", "ordered": True, "items": items})
            continue
        out.append(block)
        i += 1
    return out


def verse_card(group: dict, fields: dict, lang: str) -> dict:
    return {"type": "verse_card", "verses": group["num"], "sections": [
        {"type": "verse", "key": key, "lines": [fields[key]]}
        for key in VERSE_KEYS if fields.get(key)
    ]}


def prose(kind: str, key: str, label: str, text: str) -> dict:
    return {"type": kind, "key": key, "label": label, "paragraphs": [text]}


def group_sections(group: dict, fields: dict, lang: str, with_verses: bool) -> list[dict]:
    """Стих так, как его читает страница сайта: карточка, разборы, переводы."""
    label_of = dict(LABELS[lang])
    sections: list[dict] = []
    if with_verses:
        # так же, как в других трактатах: строка со стихами, затем карточка
        head = ("Стихи: " if lang == "ru" else "Verses: ") + group["num"]
        sections.append({"type": "p", "text": head})
        sections.append(verse_card(group, fields, lang))
    for field in group["fields"]:
        key = field["key"]
        if key in VERSE_KEYS or not fields.get(key):
            continue
        if key == "hindicomment":
            sections.append({"type": "label", "label": label_of[key]})
            sections.append({"type": "deva", "key": "deva",
                             "lines": [fields[key]]})
        elif key in ("devanote", "note"):
            sections.append({"type": "note", "paragraphs": [fields[key]]})
        elif key == "words":
            sections.append(prose("words", "words", label_of[key], fields[key]))
        elif key in ("trans", "commenttrans"):
            sections.append(prose("prose", key, label_of[key], fields[key]))
    return sections


def build() -> dict:
    for lang in ("ru", "en"):
        RAW_TEXT[lang] = " ".join(item["t"] for item in stream(lang))
    parsed = {lang: parse(lang) for lang in ("ru", "en")}
    for lang in ("ru", "en"):
        if len(parsed[lang]["groups"]) != 39:
            raise SystemExit(f"в томе {lang} не 39 разобранных стихов, а "
                             f"{len(parsed[lang]['groups'])}")

    nums = {lang: [g["num"] for g in parsed[lang]["groups"]] for lang in ("ru", "en")}
    if nums["ru"] != nums["en"]:
        raise SystemExit("нумерация стихов в двух томах разошлась")

    # все стихи вместе с разобранными полями: часть из них — глава об āсанах
    resolved = []
    for gr, ge in zip(parsed["ru"]["groups"], parsed["en"]["groups"]):
        fr, fe = fields_of(gr, "ru", "en"), fields_of(ge, "en", "ru")
        for lang, fields in (("ru", fr), ("en", fe)):
            for key in VERSE_KEYS + ("words", "trans"):
                if not fields.get(key):
                    raise SystemExit(f'стих {gr["num"]}: в томе {lang} нет поля {key}')
        gr["fields_resolved"], ge["fields_resolved"] = fr, fe
        resolved.append((gr, ge, fr, fe))

    poses = []
    for index, (gr, ge, fr, fe) in enumerate(resolved[NON_POSE:]):
        name = {"ru": gr["title"], "en": ge["title"]}
        key = KEY_OVERRIDES.get(name["en"]) or slugify(name["en"].split(" / ")[0])
        text = {lang: group_sections(gr if lang == "ru" else ge, fields, lang, True)
                for lang, fields in (("ru", fr), ("en", fe))}
        poses.append({
            "key": key,
            "iast": name["en"],
            "number": index + 1,
            "name": name,
            "gloss": {"ru": "", "en": ""},
            "verses": {"ru": gr["num"], "en": ge["num"]},
            "text": text,
        })
    keys = [pose["key"] for pose in poses]
    if len(keys) != 33:
        raise SystemExit(f"āсан в главе не тридцать три, а {len(keys)}")
    if len(set(keys)) != len(keys):
        raise SystemExit("повторяющиеся латинские ключи āсан")

    # первые шесть разобранных стихов — не āсаны, а глава о них
    prologue = {}
    for lang, groups in (("ru", parsed["ru"]["groups"]),
                         ("en", parsed["en"]["groups"])):
        out = [{"type": "subhead", "label": parsed[lang]["chapter"]}]
        for group in groups[:NON_POSE]:
            fields = group["fields_resolved"]
            out.append({"type": "label", "label": head_label(group, lang)})
            out += group_sections(group, fields, lang, True)
        prologue[lang] = out

    about = {}
    about_blocks = {}
    for lang in ("ru", "en"):
        blocks = list_blocks(parsed[lang]["blocks"])
        title = blocks[0]
        if title["type"] != "p":
            raise SystemExit(f"первый блок статьи — не заглавие ({lang})")
        about_blocks[lang] = blocks
        about[lang] = [{"type": "title", "text": title["text"]}] + blocks[1:]

    data = {
        "id": "hathayogasamhita",
        "title": {"ru": "Хат̣хайогасам̣хитā", "en": "Haṭhayogasaṃhitā"},
        "prologue": prologue,
        "about": about,
        "datingSummary": dating_summary(about_blocks),
        "poses": poses,
    }
    data["_comparison"] = [{"num": gr["num"], "fields": fr} for gr, _, fr, _ in resolved]
    data["_comparison"] += [{"num": ge["num"], "fields": fe} for _, ge, _, fe in resolved]
    return data


def head_label(group: dict, lang: str) -> str:
    """Заголовок стиха так, как он напечатан в томе."""
    if lang == "ru":
        return f'Стих {group["num"]} ({group["title"]})'
    return f'Verse {group["num"]} — {group["title"]}'


def dating_summary(about: dict) -> dict:
    """Короткая сводка датировки — только словами самих томов.

    Отдельной статьи о датировке в этих томах нет; дата стоит в заглавии работы
    и в описании рукописи у Джейсона Бёрча. Обе опоры переносятся сюда дословно.
    """
    def find_paragraph(lang: str, start: str) -> str:
        for block in about[lang]:
            if block["type"] == "p" and block["text"].startswith(start):
                return block["text"]
        raise SystemExit(f"в статье ({lang}) не найден абзац «{start}»")

    return {
        "label": {"ru": "На чём основана дата (по словам самого тома)",
                  "en": "Basis of the date (in the volume’s own words)"},
        "items": [
            {
                "who": {"ru": "Заглавие работы",
                        "en": "The title of the work"},
                "when": {"ru": "XVII век", "en": "the 17th century"},
                "whenNote": {"ru": "дата стоит в самом заглавии статьи",
                             "en": "the date stands in the title of the article itself"},
                "work": {
                    "ru": "«Haṭhayogasaṃhitā» (XVII в.): Вероятный прототип «Gheraṇḍasaṃhitā»",
                    "en": "The Haṭhayogasaṃhitā (17th Century): A Probable Precursor "
                          "to the Gheraṇḍasaṃhitā",
                },
            },
            {
                "who": {"ru": "Джейсон Бёрч, «Haṭhayoga’s Floruit on the Eve of "
                              "Colonialism» (2020)",
                        "en": "Jason Birch, “Haṭhayoga’s Floruit on the Eve of "
                              "Colonialism” (2020), p. 458, note 17"},
                "when": {"ru": "манускрипт XVII века",
                         "en": "a seventeenth-century manuscript"},
                "whenNote": {"ru": "текст предшествует «Gheraṇḍasaṃhitā»; в статье она "
                                   "отнесена к XVIII веку",
                             "en": "the text predates the Gheraṇḍasaṃhitā; the article "
                                   "places that work in the eighteenth century"},
                "work": {
                    "ru": find_paragraph("ru", "Современный индолог"),
                    "en": find_paragraph("en", "In “Haṭhayoga’s Floruit"),
                },
            },
        ],
    }


def main() -> int:
    data = build()
    comparison = data.pop("_comparison")

    for lang in ("ru", "en"):
        lost = lost_lines(data, lang)
        if lost:
            raise SystemExit(f"в данные не попали {len(lost)} строк ({lang}):\n  "
                             + "\n  ".join(lost[:12]))
    bad = scan(" ".join(json_texts(data, [])))
    if bad:
        raise SystemExit(f"слова из двух алфавитов: {bad[:5]}")
    quotes = []
    for item in data["datingSummary"]["items"]:
        for lang in ("ru", "en"):
            quotes.append((lang, item["work"][lang]))
    haystack = {lang: re.sub(r"\s+", " ", " ".join(
        block.get("text", "") for block in data["about"][lang])) for lang in ("ru", "en")}
    titles = {"ru": data["about"]["ru"][0]["text"], "en": data["about"]["en"][0]["text"]}
    for lang, quote in quotes:
        text = re.sub(r"\s+", " ", quote)
        if text not in haystack[lang] and text not in titles[lang]:
            raise SystemExit(f"цитата сводки не найдена в томе ({lang}): {quote[:60]}")

    # диакритика в терминах и названиях поз — по карте проекта
    data = diacritics.fix_document(data)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if have != text:
            print("data/hathayogasamhita.json расходится с томами: пересоберите")
            return 1
        print("data/hathayogasamhita.json совпадает с томами")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f'поз: {len(data["poses"])} → {OUT.relative_to(ROOT)} '
          f'({len(text.encode("utf-8"))} байт)')
    for pose in data["poses"]:
        print(f'  {pose["number"]:2d}. {pose["name"]["ru"]:32s} {pose["key"]:22s} '
              f'стихи {pose["verses"]["ru"]}')
    bad = compare_with_iast(comparison)
    if bad:
        print("сверка деванāгарӣ с IAST (различия чтения):")
        for line in bad:
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
