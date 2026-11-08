#!/usr/bin/env python3
"""Сборка data/yoga-kaustubha.json из двух томов статьи о «Йога-каустубхе».

Источник — русский и английский тома одной работы: восемьдесят четыре āсаны
печатного руководства на гуджарати «Йога-каустубха» (составители Натхурāма
Пӣтāм̣бараджӣ Рāвал̣а и Вайджанāтха Мотӣрāмаджӣ Бхат̣т̣а; печатные страницы
55–73). Скрипт ничего не сочиняет: он раскладывает текст томов по полям сайта и
проверяет, что раскладка сошлась.

Тома присланы тремя частями каждый (по 10 МБ на часть); сборка читает склеенный
файл — тот же самый текст в том же порядке, без правок.

Структура тома:

    заглавие, «О тексте»                        → раздел «О трактате»
    «Начало раздела об āсанах»                  → страница главы
    «Āsana 1 — Сиддхāсана» … «Āsana 84 — …»     → восемьдесят четыре страницы
    «Заключение», «Печатный источник»,
    «Издания и рукописи»                        → раздел «О трактате»

У каждой āсаны том даёт до одиннадцати полей: печатный источник, гуджарати,
IAST, кириллицу, пословный разбор, перевод, при наличии — дополнительный
пассаж, примечание печатного издания, традиционный эффект (каждое из трёх —
гуджарати, IAST, кириллица и перевод) и текстологическое примечание.

Запуск:  python3 tools/extract_yoga_kaustubha.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_mix import scan  # noqa: E402  (проверка «одно слово — один алфавит»)
from extract_matsyendra import slugify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "yoga-kaustubha.json"

PDF = {
    "ru": ROOT / "sources" / "Йога-каустубха — восемьдесят четыре āсаны (RU).pdf",
    "en": ROOT / "sources" / "Yoga Kaustubha — the Eighty-Four Āsanas (EN).pdf",
}

# Метки полей — так, как они напечатаны в томе. Порядок важен: «Дополнительный
# пассаж — транслитерация (IAST)» начинается с «Дополнительный пассаж».
LABELS = {
    "en": [
        ("addgu", "Additional passage — Gujarati (normalised transcription)"),
        ("addiast", "Additional passage transliteration (IAST)"),
        ("addcyr", "Additional passage transliteration (Cyrillic)"),
        ("addtr", "Additional passage — English"),
        ("fgu", "Printed footnote — Gujarati"),
        ("fiast", "Printed footnote transliteration (IAST)"),
        ("fcyr", "Printed footnote transliteration (Cyrillic)"),
        ("ftr", "Printed footnote — English"),
        ("effgu", "Traditional effect — Gujarati (normalised transcription)"),
        ("effiast", "Effect transliteration (IAST)"),
        ("effcyr", "Effect transliteration (Cyrillic)"),
        ("efftr", "Traditional effect — English"),
        ("wbaA", "Word-by-word analysis (Aṅguṣṭhāsana)"),
        ("wbaU", "Word-by-word analysis (Utkaṭāsana)"),
        ("trA", "English translation (Aṅguṣṭhāsana)"),
        ("trU", "English translation (Utkaṭāsana)"),
        ("ps", "Printed source"),
        ("gu", "Gujarati"),
        ("iast", "Transliteration (IAST)"),
        ("cyr", "Cyrillic transliteration"),
        ("wba", "Word-by-word analysis"),
        ("tr", "English translation"),
        ("tn", "Textual note"),
        ("par", "Printed parallel"),
    ],
    "ru": [
        ("addgu", "Дополнительный пассаж — гуджарати (нормализованная запись)"),
        ("addiast", "Дополнительный пассаж — транслитерация (IAST)"),
        ("addcyr", "Дополнительный пассаж — кириллическая транслитерация"),
        ("addtr", "Дополнительный пассаж — перевод"),
        ("fgu", "Примечание печатного издания — гуджарати"),
        ("fiast", "Примечание печатного издания — транслитерация (IAST)"),
        ("fcyr", "Примечание печатного издания — кириллическая транслитерация"),
        ("ftr", "Примечание печатного издания — перевод"),
        ("effgu", "Традиционный эффект — гуджарати (нормализованная запись)"),
        ("effiast", "Эффект — транслитерация (IAST)"),
        ("effcyr", "Эффект — кириллическая транслитерация"),
        ("efftr", "Традиционный эффект — перевод"),
        ("wbaA", "Пословный разбор (Ан̇гушт̣хāсана)"),
        ("wbaU", "Пословный разбор (Уткат̣āсана)"),
        ("trA", "Перевод (Ан̇гушт̣хāсана)"),
        ("trU", "Перевод (Уткат̣āсана)"),
        ("ps", "Печатный источник"),
        ("gu", "Гуджарати"),
        ("iast", "Транслитерация (IAST)"),
        ("cyr", "Кириллическая транслитерация"),
        ("wba", "Пословный разбор"),
        ("tr", "Перевод"),
        ("tn", "Текстологическое примечание"),
        ("par", "Параллельный печатный текст"),
    ],
}

# Заголовки статьи. «О тексте» и «Начало раздела» открывают страницы, остальные
# стоят после последней āсаны.
HEADS = {
    "en": {
        "about": "About the text",
        "chapter": "Opening of the section on āsanas",
        "tail": ["Conclusion", "Printed source", "Printed editions and manuscripts"],
    },
    "ru": {
        "about": "О тексте",
        "chapter": "Начало раздела об āсанах",
        "tail": ["Заключение", "Печатный источник", "Издания и рукописи"],
    },
}

POSE_HEAD = {
    "en": re.compile(r"^Āsana (\d+) — (.+)$"),
    "ru": re.compile(r"^Āсана (\d+) — (.+)$"),
}

VERSE_KEYS = ("gu", "iast", "cyr")

# Латинский адрес āсаны. Общий для всех трактатов сайта: если поза уже есть в
# других памятниках, берётся её прежний адрес. Расхождение печатается.
KEY_OVERRIDES = {
    # «Паш́чиматāна» здесь — та же поза, что «Паш́чимоттāна̄сана» в остальных
    # трактатах: имя сокращено на одно слог, адрес общий.
    "Paścimatāna": "pashchimatana",
    # «Матсйендра̄сана» на сайте стоит под адресом matsyendrapitha
    "Matsyendrāsana": "matsyendrapitha",
    # «Дханушāсана» — вариант «Дханурāсаны» (dhanus / dhanur)
    "Dhanuṣāsana": "dhanurasana",
    # «Уттāна кӯрмāсана» — то же имя, что «Уттāнакӯрмāсана» других трактатов
    "Uttāna kūrmāsana": "uttanakurmaka",
}

# подпись группы перед стихом-цитатой (гуджарати, IAST, кириллица)
GROUP_LABEL = {
    ("ru", "add"): "Дополнительный пассаж",
    ("en", "add"): "Additional passage",
    ("ru", "f"): "Примечание печатного издания",
    ("en", "f"): "Printed footnote",
    ("ru", "eff"): "Традиционный эффект",
    ("en", "eff"): "Traditional effect",
}

GROUP_KEYS = ("add", "f", "eff")

# Подписи вкладок под стихом: гуджарати, IAST, кириллица.
VERSE_LABEL = {
    "ru": {"gu": "Гуджарати", "iast": "Транслитерация (IAST)",
           "cyr": "Кириллическая транслитерация"},
    "en": {"gu": "Gujarati", "iast": "Transliteration (IAST)",
           "cyr": "Cyrillic transliteration"},
}


def verse_tab(lang: str, key: str) -> str:
    """«effgu» → подпись вкладки «Гуджарати»."""
    for prefix in GROUP_KEYS:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    return VERSE_LABEL[lang][key]


def group_prefix(key: str) -> str | None:
    """«effgu» → «eff», «fgu» → «f»; «fgu» не «f» ловится по порядку."""
    for prefix in GROUP_KEYS:
        if key.startswith(prefix):
            return prefix
    return None


# --------------------------------------------------------------- чтение тома

def blocks_of(lang: str) -> list[str]:
    """Абзацы тома подряд, как их выделяет сам PDF."""
    out: list[str] = []
    for page in pymupdf.open(PDF[lang]):
        for block in page.get_text("blocks"):
            text = re.sub(r"\s+", " ", block[4].replace("\n", " ")).strip()
            # перенос строки после тире: «56– 74» → «56–74»
            text = re.sub(r"(?<=\d)\s*([–—-])\s*(?=\d)", r"\1", text)
            if text:
                out.append(text)
    return out


def ends_sentence(text: str) -> bool:
    return bool(re.search(r"[.!?…”»)]$", text.rstrip()))


def match_label(lang: str, text: str):
    """Начало абзаца — метка поля? Тогда (ключ, метка, остаток)."""
    for key, label in LABELS[lang]:
        if text.startswith(label + ":"):
            return key, label, text[len(label) + 1:].strip()
    return None


# --------------------------------------------------------------- разбор тома

def parse(lang: str) -> dict:
    """Том по порядку: абзацы статьи, глава и восемьдесят четыре āсаны."""
    blocks = blocks_of(lang)
    head = HEADS[lang]
    pose_head = POSE_HEAD[lang]

    about: list[str] = []            # абзацы «О тексте»
    chapter: list[str] = []          # абзацы «Начала раздела»
    tail: list[tuple[str, list[str]]] = []   # (заголовок, абзацы)
    poses: list[dict] = []

    where = None                     # "about" | "chapter" | "tail" | "pose"
    field: dict | None = None
    last_para: list[str] | None = None

    def add_para(text: str) -> None:
        """Абзац статьи: оборванный на странице абзац продолжается."""
        nonlocal last_para
        target = about if where == "about" else chapter
        if where == "tail":
            target = tail[-1][1]
        if last_para is not None and not ends_sentence(target[-1]):
            # перенос строки после тире: «56–» + «74» = «56–74»
            if target[-1].rstrip().endswith(("–", "—", "-")):
                target[-1] = target[-1].rstrip() + text
            else:
                target[-1] += " " + text
            return
        target.append(text)
        last_para = target

    for text in blocks:
        if text == head["about"]:
            where, field, last_para = "about", None, None
            continue
        if text == head["chapter"]:
            where, field, last_para = "chapter", None, None
            continue
        if text in head["tail"]:
            where, field = "tail", None
            tail.append((text, []))
            last_para = None
            continue
        m = pose_head.match(text)
        if m:
            where, last_para = "pose", None
            field = None
            poses.append({"num": int(m.group(1)), "title": m.group(2).strip(), "fields": []})
            continue

        if where == "pose":
            label = match_label(lang, text)
            if label:
                key, name, rest = label
                field = {"key": key, "label": name, "text": rest}
                poses[-1]["fields"].append(field)
            elif field is not None:
                field["text"] = (field["text"] + " " + text).strip()
            else:
                raise SystemExit(f"текст вне поля ({lang}): {text[:60]!r}")
            continue

        if where is None:
            if text.startswith("Yoga Kaustubha") or text.startswith("Йога-каустубха"):
                about.append(text)      # заглавие статьи
                last_para = None
                continue
            raise SystemExit(f"текст до первого заголовка ({lang}): {text[:60]!r}")
        add_para(text)

    if len(poses) != 84:
        raise SystemExit(f"в томе {lang} не 84 āсаны, а {len(poses)}")
    return {"about": about, "chapter": chapter, "tail": tail, "poses": poses}


# ------------------------------------------------------------------ страницы

def page_of(field: dict) -> str:
    """«стр. 55–56 (…» → «55–56»; «p. 55–56 (…» → «55–56»."""
    m = re.search(r"\b(?:стр\.|p\.)\s*(\d+(?:\s*[–-]\s*\d+)?)", field["text"])
    if not m:
        raise SystemExit(f"не найден номер страницы: {field['text'][:60]!r}")
    return re.sub(r"\s*[–-]\s*", "–", m.group(1))


def sections(fields: list[dict], lang: str) -> list[dict]:
    """Страница āсаны: поля тома в том же порядке, что и в томе.

    Гуджарати, IAST и кириллица идут одной цитатой (вкладки), как в остальных
    трактатах сайта; группы «дополнительный пассаж», «примечание печатного
    издания» и «традиционный эффект» получают свою подпись.
    """
    out: list[dict] = []
    index = 0
    while index < len(fields):
        field = fields[index]
        key = field["key"]

        if key in VERSE_KEYS:
            block = []
            while index < len(fields) and fields[index]["key"] in VERSE_KEYS:
                got = fields[index]
                block.append({"type": "verse", "key": got["key"],
                              "label": verse_tab(lang, got["key"]),
                              "lines": [got["text"]]})
                index += 1
            out.extend(block)
            continue

        prefix = group_prefix(key)
        if prefix is not None:
            keys = {prefix + "gu", prefix + "iast", prefix + "cyr", prefix + "tr"}
            parts = []
            while index < len(fields) and fields[index]["key"] in keys:
                parts.append(fields[index])
                index += 1
            out.append({"type": "label", "label": GROUP_LABEL[(lang, prefix)]})
            for part in parts:
                if part["key"] == prefix + "tr":
                    out.append({"type": "prose", "key": prefix + "tr",
                                "label": part["label"],
                                "paragraphs": [part["text"]]})
                else:
                    out.append({"type": "verse", "key": part["key"],
                                "label": verse_tab(lang, part["key"]),
                                "lines": [part["text"]]})
            continue

        if key == "ps":
            out.append({"type": "p", "text": field["label"] + ": " + field["text"]})
        elif key.startswith("wba"):
            out.append({"type": "words", "key": "words", "label": field["label"],
                        "paragraphs": [field["text"]]})
        elif key.startswith("tr"):
            out.append({"type": "prose", "key": key, "label": field["label"],
                        "paragraphs": [field["text"]]})
        elif key in ("tn", "par"):
            # подпись печатается заголовком раздела, как в самом томе
            out.append({"type": "prose", "key": key, "label": field["label"],
                        "paragraphs": [field["text"]]})
        else:
            raise SystemExit(f"неизвестное поле ({lang}): {field['label']!r}")
        index += 1
    return out


# ------------------------------------------------------------------ сборка

def build() -> dict:
    parsed = {lang: parse(lang) for lang in ("ru", "en")}
    nums = {lang: [p["num"] for p in parsed[lang]["poses"]] for lang in ("ru", "en")}
    if nums["ru"] != nums["en"] or nums["ru"] != list(range(1, 85)):
        raise SystemExit("нумерация āсан в двух томах разошлась")

    poses = []
    for pr, pe in zip(parsed["ru"]["poses"], parsed["en"]["poses"]):
        for lang, pose in (("ru", pr), ("en", pe)):
            keys = [f["key"] for f in pose["fields"]]
            for want in ("ps", "gu", "iast", "cyr"):
                if want not in keys:
                    raise SystemExit(f'āсана {pose["num"]}: в томе {lang} нет поля {want}')
        if [f["key"] for f in pr["fields"]] != [f["key"] for f in pe["fields"]]:
            raise SystemExit(f'āсана {pr["num"]}: поля двух томов разошлись')

        en_title = pe["title"]
        key = KEY_OVERRIDES.get(en_title) or slugify(en_title.split(" / ")[0])
        if key != slugify(en_title.split(" / ")[0]):
            print(f'  адрес: «{en_title}» → {key} (как у той же позы в других трактатах)')
        page_en = page_of(pe["fields"][0])
        page_ru = page_of(pr["fields"][0])
        poses.append({
            "key": key,
            "iast": en_title,
            "number": pr["num"],
            "name": {"ru": pr["title"], "en": en_title},
            "gloss": {"ru": "", "en": ""},
            "verses": {"ru": "стр. " + page_ru, "en": "p. " + page_en},
            "text": {"ru": sections(pr["fields"], "ru"),
                     "en": sections(pe["fields"], "en")},
        })
    keys = [p["key"] for p in poses]
    if len(set(keys)) != len(keys):
        raise SystemExit("повторяющиеся латинские ключи āсан")

    return {
        "id": "yoga-kaustubha",
        "title": {"ru": "Йога-каустубха", "en": "Yoga Kaustubha"},
        "prologue": {
            "ru": [{"type": "subhead", "label": HEADS["ru"]["chapter"]}] +
                  [{"type": "p", "text": t} for t in parsed["ru"]["chapter"]],
            "en": [{"type": "subhead", "label": HEADS["en"]["chapter"]}] +
                  [{"type": "p", "text": t} for t in parsed["en"]["chapter"]],
        },
        "about": {lang: about_sections(lang, parsed[lang]) for lang in ("ru", "en")},
        "datingSummary": dating_summary(parsed),
        "poses": poses,
    }


def about_sections(lang: str, parsed: dict) -> list[dict]:
    """«О трактате»: заглавие, «О тексте», затем концовка тома по разделам."""
    out: list[dict] = [{"type": "title", "text": parsed["about"][0]}]
    out.append({"type": "subhead", "label": HEADS[lang]["about"]})
    out += [{"type": "p", "text": t} for t in parsed["about"][1:]]
    for head, paragraphs in parsed["tail"]:
        out.append({"type": "subhead", "label": head})
        out += [{"type": "p", "text": t} for t in paragraphs]
    return out


# Пересчёт эр — не текст тома, а арифметика сайта. Он стоит последней строкой
# сводки и подписан как наш расчёт: иначе читатель принял бы его за слова
# издания. Оба года на титульном листе дают один и тот же промежуток, потому что
# ш́ака и сам̣ват начинают год одновременно (весной): ш́ака + 78, сам̣ват − 57 —
# 1889 год для месяцев от начала года до декабря; + 79 и − 56 — 1890 для
# января–февраля, когда эра уже перешла в следующий год, а григорианский ещё нет.
ERA_ARITHMETIC = {
    "ru": (
        "Пересчёт по эрам — это наш расчёт, а не слова тома. "
        "Ш́ака 1811: 1811 + 78 = 1889 для месяцев от начала года до декабря и "
        "1811 + 79 = 1890 для января–февраля. "
        "Сам̣ват 1946: 1946 − 57 = 1889 и 1946 − 56 = 1890 — при том же начале "
        "года; в Гуджарате обычен викрама-сам̣ват со счётом от чаитры, но том "
        "этого не уточняет. "
        "Обе даты дают один и тот же промежуток, март 1889 — март 1890, и "
        "расходятся ровно на 135 лет, как и сами эры: титульный лист сам себе не "
        "противоречит. Но ни месяца, ни дня на нём нет, поэтому один год "
        "назвать нельзя."
    ),
    "en": (
        "The conversion is our arithmetic, not the volume’s words. "
        "Śaka 1811: 1811 + 78 = 1889 for the months from the start of the year "
        "to December, and 1811 + 79 = 1890 for January–February. "
        "Saṃvat 1946: 1946 − 57 = 1889 and 1946 − 56 = 1890, assuming the same "
        "start of the year; in Gujarat the Vikrama saṃvat counted from Caitra is "
        "the usual reckoning, but the volume does not say so. "
        "Both dates give the same span, March 1889 to March 1890, and differ by "
        "exactly 135 years, as the eras themselves do: the title page does not "
        "contradict itself. But neither month nor day is printed on it, so no "
        "single year can be named."
    ),
}


def dating_summary(parsed: dict) -> dict:
    """Короткая сводка датировки: что стоит на титульном листе.

    Том не приравнивает эти годы к григорианскому; сводка говорит то же самое и
    цитирует том дословно — цитата проверяется при сборке. Пересчёт эр стоит
    отдельной строкой и подписан как расчёт сайта, а не как слова тома.
    """
    def sentence(lang: str, start: str) -> str:
        for text in parsed[lang]["about"]:
            if text.startswith(start):
                return text
        raise SystemExit(f"в томе ({lang}) не найден абзац «{start}»")

    return {
        "label": {"ru": "На чём основана дата (по словам самого тома)",
                  "en": "Basis of the date (in the volume’s own words)"},
        "items": [
            {
                "who": {"ru": "Титульный лист издания",
                        "en": "The title page of the edition"},
                "when": {"ru": "ш́ака 1811; сам̣ват 1946",
                         "en": "Śaka 1811; Saṃvat 1946"},
                "whenNote": {"ru": "к григорианскому году не приравниваются",
                             "en": "not equated with a Gregorian year"},
                "work": {
                    "ru": sentence("ru", "На титульном листе указаны"),
                    "en": sentence("en", "The title page gives"),
                },
            },
        ],
        "note2": ERA_ARITHMETIC,
    }


# ------------------------------------------------------------------ проверки

def check_era_arithmetic() -> None:
    """Каждое «a ± b = c» в примечании должно быть верным, и разница эр — 135.

    Примечание — проза, поэтому числа проверяются разбором самой строки: если
    кто-нибудь поправит текст и ошибётся в счёте, сборка остановится.
    """
    for lang, text in ERA_ARITHMETIC.items():
        found = re.findall(r"(\d{4}) ([+\u2212-]) (\d{1,2}) = (\d{4})", text)
        if len(found) < 4:
            raise SystemExit(f"в примечании о пересчёте эр мало примеров ({lang}): "
                             f"{len(found)}")
        for left, sign, right, result in found:
            value = int(left) + int(right) if sign == "+" else int(left) - int(right)
            if value != int(result):
                raise SystemExit(f"пересчёт неверен ({lang}): {left} {sign} {right} "
                                 f"≠ {result}")
        # разница эр, о которой говорит примечание
        gap = 1946 - 1811
        if gap != 135 or str(gap) not in text:
            raise SystemExit(f"разница эр не 135 лет ({lang}): {gap}")


def json_texts(node, out: list[str]) -> list[str]:
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
    for text in blocks_of(lang):
        probe = text
        if probe in labels or probe in HEADS[lang]["tail"] \
                or probe in (HEADS[lang]["about"], HEADS[lang]["chapter"]):
            continue
        if POSE_HEAD[lang].match(probe):
            continue
        label = match_label(lang, probe)
        if label:
            probe = label[2]
        if len(probe) > 3 and re.sub(r"\s+", " ", probe) not in haystack:
            lost.append(probe)
    return lost


def main() -> int:
    check_era_arithmetic()
    data = build()

    for lang in ("ru", "en"):
        lost = lost_lines(data, lang)
        if lost:
            raise SystemExit(f"в данные не попали {len(lost)} строк ({lang}):\n  "
                             + "\n  ".join(lost[:12]))
    bad = scan(" ".join(json_texts(data, [])))
    if bad:
        raise SystemExit(f"слова из двух алфавитов: {bad[:5]}")

    haystack = {}
    for lang in ("ru", "en"):
        parts = (json_texts(data["about"][lang], [])
                 + json_texts(data["prologue"][lang], [])
                 + [t for pose in data["poses"] for t in json_texts(pose["text"][lang], [])])
        haystack[lang] = re.sub(r"\s+", " ", " ".join(parts))
    for item in data["datingSummary"]["items"]:
        for lang in ("ru", "en"):
            quote = re.sub(r"\s+", " ", item["work"][lang])
            if quote not in haystack[lang]:
                raise SystemExit(f"цитата сводки не найдена в томе ({lang}): {quote[:60]}")

    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if have != text:
            print("data/yoga-kaustubha.json расходится с томами: пересоберите")
            return 1
        print("data/yoga-kaustubha.json совпадает с томами")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f'поз: {len(data["poses"])} → {OUT.relative_to(ROOT)} '
          f'({len(text.encode("utf-8"))} байт)')
    for pose in data["poses"][:5] + data["poses"][-3:]:
        print(f'  {pose["number"]:2d}. {pose["name"]["ru"]:32s} {pose["key"]:26s} '
              f'{pose["verses"]["ru"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
