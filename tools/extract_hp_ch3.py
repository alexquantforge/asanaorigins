# -*- coding: utf-8 -*-
"""Третья глава «Хат̣хапрадӣпики»: Випарӣта-каран̣ӣ (стихи 3.73–3.77).

Собрание сайта строилось по двум PDF, и в них была только глава 1. Позу
Випарӣта-каран̣ӣ «Хат̣хапрадӣпикā» описывает в главе 3, поэтому на странице
этой позы ссылки другого трактата («HP 3.79–82») оставались без ответа:
читатель не видел ни самого стиха, ни рукописей.

Текст главы 3 списан с цифрового критического издания
(yoga.ames.ox.ac.uk/hp/reader/edition/) в tools/hp_ch3_raw.json, здесь он
только перекладывается в ту же форму блоков, что и остальные главы:

* деванагари и IAST — как напечатаны (издание кое-где набирает слово слитно,
  потому что от него идёт ссылка на аппарат; это не наша склейка);
* кириллическая транслитерация — tools/translit.py, буква в букву;
* аппарат («Разночтения по рукописям») — рassуждения издания переписаны в те же
  фразы, что и в главе 1: «В издании — «…» (так в: …). Ещё «…» — так в: …»,
  а условные знаки рукописей (α1, ζ2, πω …) заменены полными названиями из
  таблицы «Что это за рукописи», которая уже лежит в данных главы 1.
  Если какой-то знак в таблице не найдётся, сборка падает: лучше остановиться,
  чем напечатать «α1» без расшифровки.

Запуск:  python3 tools/extract_hp_ch3.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from translit import translit  # noqa: E402

RAW = ROOT / "tools" / "hp_ch3_raw.json"
HP = ROOT / "data" / "hathapradipika.json"
OUT = ROOT / "data" / "hathapradipika-ch3.json"

GREEK = {
    "α": "альфа", "β": "бета", "γ": "гамма", "δ": "дельта", "ε": "эпсилон",
    "ζ": "дзета", "η": "эта", "θ": "тета", "π": "пи", "χ": "хи",
}

SIGLUM = re.compile(r"(?P<letter>[αβγδεζηθπχ])(?P<tail>\d+|ω)?")
TAIL = re.compile(r"(?:[αβγδεζηθπχ](?:\d+|ω)?)+\s*$")


def sigla_names() -> dict[str, str]:
    """Условный знак → полное название рукописи (из таблицы главы 1)."""
    doc = json.loads(HP.read_text(encoding="utf-8"))
    table = None
    for lang in ("ru", "en"):
        for block in doc["appendix"][lang]:
            if block.get("type") == "table" and len(block["rows"][0]) == 3:
                table = block["rows"]
                break
        if table:
            break
    if not table:
        raise SystemExit("в данных главы 1 нет таблицы «Что это за рукописи»")

    out: dict[str, str] = {}
    for row in table[1:]:
        key = row[0].strip("«» ")
        # «альфа-1» → α1; «пи-омега» → πω; «хи» → χ
        name, _, tail = key.partition("-")
        letter = {v: k for k, v in GREEK.items()}.get(name)
        if not letter:
            continue
        sign = letter + (("ω" if tail == "омега" else tail) if tail else "")
        out[sign] = row[1].strip()
    return out


def split_sigla(text: str) -> tuple[str, list[str]]:
    """«ūrdhvanābhir ε1π1» → («ūrdhvanābhir», [«ε1», «π1»])."""
    m = TAIL.search(text)
    if not m:
        return text.strip(), []
    tail = text[m.start():].strip()
    signs = [s.group(0) for s in SIGLUM.finditer(tail)]
    return text[:m.start()].strip(), signs


def names(signs: list[str], table: dict[str, str], lang: str) -> str:
    out = []
    for sign in signs:
        full = table.get(sign)
        if not full:
            raise SystemExit(f"условный знак «{sign}» не найден в таблице рукописей")
        out.append(full)
    sep = ", " if lang == "en" else "; "
    return sep.join(out)


def expand(line: str, table: dict[str, str], lang: str) -> str:
    """Строка аппарата издания → фраза на языке страницы."""
    lemma_raw, _, rest = line.partition("|")
    lemma_sigla_raw, _, variants_raw = rest.partition("|")
    cett = "_cett." in lemma_raw
    lemma = lemma_raw.replace("_cett.", "").strip()
    lemma = re.sub(r"\s*incl\.\s*(.+)$", "", lemma).strip()
    incl = re.search(r"incl\.\s*(\S+)", lemma_raw)
    lemma_sigla = [s.group(0) for s in SIGLUM.finditer(lemma_sigla_raw)]

    chunks = [c.strip() for c in variants_raw.split(",") if c.strip()] if variants_raw.strip() else []
    parts: list[str] = []

    # «pāda c ] om. δ1ζ2» — целого полустишия в этих рукописях нет
    if lemma.startswith("pāda") and chunks and chunks[0].startswith("om."):
        part = lemma.split()[-1]
        who = names([s.group(0) for s in SIGLUM.finditer(" ".join(chunks))], table, lang)
        if lang == "en":
            parts.append(f"Quarter {part} is absent in: {who}.")
        else:
            parts.append(f"Полустишие {part} отсутствует в: {who}.")
        return " ".join(parts)

    if lemma_sigla:
        who = names(lemma_sigla, table, lang)
        if lang == "en":
            parts.append(f"In the edition — “{lemma}” (so in: {who}).")
        else:
            parts.append(f"В издании — «{lemma}» (так в: {who}).")
    elif cett:
        if incl:
            extra = names([s.group(0) for s in SIGLUM.finditer(incl.group(1))], table, lang)
            if lang == "en":
                parts.append(f"In the edition — “{lemma}” (so in all the manuscripts, including {extra}).")
            else:
                parts.append(f"В издании — «{lemma}» (так во всех рукописях, включая {extra}).")
        elif lang == "en":
            parts.append(f"In the edition — “{lemma}” (so in all the manuscripts except those listed here).")
        else:
            parts.append(f"В издании — «{lemma}» (так во всех рукописях, кроме перечисленных ниже).")
    else:
        if lang == "en":
            parts.append(f"Reading checked: “{lemma}”.")
        else:
            parts.append(f"Проверяемое чтение — «{lemma}».")

    for chunk in chunks:
        if chunk.startswith("om."):
            who = names([s.group(0) for s in SIGLUM.finditer(chunk)], table, lang)
            parts.append(f"Нет в: {who}." if lang == "ru" else f"Absent in: {who}.")
            continue
        reading, signs = split_sigla(chunk)
        if not signs:
            parts.append(f"Ещё «{reading}»." if lang == "ru" else f"Also “{reading}”.")
            continue
        who = names(signs, table, lang)
        if lang == "en":
            parts.append(f"Also “{reading}” — so in: {who}.")
        else:
            parts.append(f"Ещё «{reading}» — так в: {who}.")
    return " ".join(parts)


def build(lang: str, raw: dict, table: dict[str, str]) -> list[dict]:
    labels = {
        "ru": {"verse": "Стих", "edition": "Перевод издания (английский)",
               "metre": "Метр", "readings": "Разночтения по рукописям",
               "sources": "Источники", "testimonia": "Свидетели",
               "testimonia_readings": "Разночтения в других текстах"},
        "en": {"verse": "Verse", "edition": "Edition translation (English)",
               "metre": "Metre", "readings": "Readings in the manuscripts",
               "sources": "Sources", "testimonia": "Testimonia",
               "testimonia_readings": "Readings in other texts"},
    }[lang]
    blocks: list[dict] = [
        {"type": "p", "text": raw["pose"]["intro"][lang]},
        {"type": "p", "text": raw["vulgate"]["note"][lang]},
    ]
    for verse in raw["verses"]:
        num = verse["number"]
        blocks.append({"type": "h4", "text": f'{labels["verse"]} {num}'})
        blocks.append({
            "type": "verse_card",
            "verses": "",
            "sections": [
                {"type": "verse", "key": "deva",
                 "label": "Деванагари" if lang == "ru" else "Devanagari",
                 "lines": verse["deva"]},
                {"type": "verse", "key": "iast", "label": "IAST", "lines": verse["iast"]},
                {"type": "verse", "key": "cyr",
                 "label": "Кириллическая транслитерация" if lang == "ru"
                          else "Cyrillic transliteration",
                 "lines": [translit(line) for line in verse["iast"]]},
            ],
        })
        blocks.append({"type": "prose", "key": "edition", "label": labels["edition"],
                       "paragraphs": [verse["translation"]]})
        if verse.get("metre"):
            blocks.append({"type": "prose", "key": "metre", "label": labels["metre"],
                           "paragraphs": [verse["metre"]]})
        items = [{"html": expand(line, table, lang)} for line in verse["readings"]]
        blocks.append({"type": "list", "ordered": False, "label": labels["readings"],
                       "items": items})
        if verse.get("sources"):
            paragraphs = [verse["sources"]]
            paragraphs.extend(verse.get("sources_readings", []))
            blocks.append({"type": "prose", "key": "sources", "label": labels["sources"],
                           "paragraphs": paragraphs})
        if verse.get("testimonia"):
            blocks.append({"type": "prose", "key": "testimonia",
                           "label": labels["testimonia"],
                           "paragraphs": [verse["testimonia"]]})
            for row in verse.get("testimonia_readings", []):
                blocks.append({"type": "p", "text": row})
    return blocks


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    table = sigla_names()

    texts = {lang: build(lang, raw, table) for lang in ("ru", "en")}
    doc = {
        "id": "hathapradipika-ch3",
        "title": {
            "ru": "«Хат̣хапрадӣпикā», глава 3: Випарӣта-каран̣ӣ",
            "en": "Haṭhapradīpikā, chapter 3: Viparītakaraṇī",
        },
        "source": raw["source"],
        "vulgate": raw["vulgate"],
        "poses": [{
            "key": raw["pose"]["key"],
            "number": 1,
            "name": raw["pose"]["name"],
            "gloss": raw["pose"]["gloss"],
            "verses": raw["pose"]["verses"],
            "text": texts,
        }],
    }

    if "--check" in sys.argv:
        if not OUT.exists():
            raise SystemExit(f"нет файла {OUT.relative_to(ROOT)}")
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if old != doc:
            raise SystemExit(f"{OUT.relative_to(ROOT)} отстал от tools/hp_ch3_raw.json")
        print(f"{OUT.relative_to(ROOT)}: совпадает с источником")
        return

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {OUT.stat().st_size} байт, "
          f"{len(doc['poses'][0]['text']['ru'])} блоков")


if __name__ == "__main__":
    main()
