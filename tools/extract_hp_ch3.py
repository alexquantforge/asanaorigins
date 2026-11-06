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


# Как называть тексты, на которые ссылается аппарат. Сокращений на странице
# не остаётся: «DYŚ» читатель не обязан знать, а «Даттāтрея-йога-ш́āстра» —
# знает каждый, кто открыл эту позу.
WORKS = {
    "DYŚ": {"ru": "Даттāтрея-йога-ш́āстра", "en": "Dattātreyayogaśāstra"},
    "DYS": {"ru": "Даттāтрея-йога-ш́āстра", "en": "Dattātreyayogaśāstra"},
    "HRĀ": {"ru": "Хат̣харатнāвали", "en": "Haṭharatnāvalī"},
    "YCM": {"ru": "Йогачинтāман̣и", "en": "Yogacintāmaṇi"},
    "YBhD": {"ru": "Йуктабхавадева", "en": "Yuktabhavadeva"},
    "HSC": {"ru": "Хат̣хасан̇кетачандрикā", "en": "Haṭhasaṅketacandrikā"},
    "VM": {"ru": "Вивека-мāртан̣д̣а", "en": "Vivekamārtaṇḍa"},
    "ŚS": {"ru": "Ш́ива-сам̣хитā", "en": "Śivasaṃhitā"},
    "VS": {"ru": "Васишт̣ха-сам̣хитā", "en": "Vasiṣṭha Saṃhitā"},
    "YY": {"ru": "Йога-йāджн̃авалкйа", "en": "Yogayājñānvalkya"},
    "HTK": {"ru": "Хат̣хататтвакаумудӣ", "en": "Haṭhatattvakaumudī"},
    "ŚP": {"ru": "Ш́āрн̇гадхара-паддхати", "en": "Śārṅgadharapaddhati"},
    "HP": {"ru": "Хат̣хапрадӣпикā", "en": "Haṭhapradīpikā"},
    "ХП": {"ru": "Хат̣хапрадӣпикā", "en": "Haṭhapradīpikā"},
}
WORK_RE = re.compile(r"(?<![A-Za-zА-Яа-я])(%s)(?![A-Za-zА-Яа-я])" % "|".join(
    sorted(map(re.escape, WORKS), key=len, reverse=True)))


def quoted(text: str, lang: str) -> str:
    return f"“{text}”" if lang == "en" else f"«{text}»"


def names(signs: list[str], table: dict[str, str], lang: str) -> str:
    out = []
    for sign in signs:
        full = table.get(sign)
        if not full:
            raise SystemExit(f"условный знак «{sign}» не найден в таблице рукописей")
        out.append(full)
    if lang == "en":
        return ", ".join(out) if len(out) < 3 else ", ".join(out[:-1]) + ", and " + out[-1]
    return "; ".join(out)


def works(signs: list[str], lang: str) -> str:
    """«HRĀ YBhD» → ««Хат̣харатнāвали» и «Йуктабхавадеве»»."""
    names_ = [quoted(WORKS[s][lang], lang) for s in signs]
    if lang == "en":
        return names_[0] if len(names_) == 1 else ", ".join(names_[:-1]) + " and " + names_[-1]
    return names_[0] if len(names_) == 1 else ", ".join(names_[:-1]) + " и " + names_[-1]


def side(text: str, lang: str, table: dict[str, str], default: str) -> str:
    """Одна половина строки аппарата: «кто» и «что у него стоит».

    В издании запись выглядит как «чтение ] варианты», где варианты бывают
    и в рукописях (δ1ζ2 …), и в других текстах (HRĀ, YCM …), а «v.l.» значит
    «вариант чтения». Здесь из неё делается обычная фраза.
    """
    codes = WORK_RE.findall(text)
    variant = "v.l." in text
    body = WORK_RE.sub("", text).replace("v.l.", "").replace("om.", "").strip(" ,;")
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return ""
    who = works(codes, lang) if codes else default
    tail = ""
    if variant:
        tail = " (variant reading)" if lang == "en" else " (вариант чтения)"
    if lang == "en":
        return f"In {who} — “{body}”{tail}."
    return f"В {who} — «{body}»{tail}."


def expand(line: str, table: dict[str, str], lang: str) -> str:
    """Строка аппарата издания → фраза без единого сокращения."""
    lemma_raw, _, rest = line.partition("|")
    lemma_sigla_raw, _, variants_raw = rest.partition("|")
    cett = "_cett." in lemma_raw
    incl = re.search(r"incl\.\s*(\S+)", lemma_raw)
    lemma = lemma_raw.replace("_cett.", "").strip()
    lemma = re.sub(r"\s*incl\.\s*(.+)$", "", lemma).strip()
    lemma_sigla = [s.group(0) for s in SIGLUM.finditer(lemma_sigla_raw)]
    chunks = [c.strip() for c in variants_raw.split(",") if c.strip()] if variants_raw.strip() else []

    # «pāda c ] om. δ1ζ2» — целого полустишия в этих рукописях нет
    if lemma.startswith("pāda") and chunks and chunks[0].startswith("om."):
        part = lemma.split()[-1]
        who = names([s.group(0) for s in SIGLUM.finditer(" ".join(chunks))], table, lang)
        return (f"Quarter {part} is absent in: {who}." if lang == "en"
                else f"Полустишие {part} отсутствует в: {who}.")

    parts: list[str] = []
    if lemma_sigla:
        who = names(lemma_sigla, table, lang)
        parts.append(f"In the edition — “{lemma}” (so in: {who})." if lang == "en"
                     else f"В издании — «{lemma}» (так в: {who}).")
    elif lemma_raw.strip() == "" or cett:
        if incl:
            extra = names([s.group(0) for s in SIGLUM.finditer(incl.group(1))], table, lang)
            parts.append(f"In the edition — “{lemma}” (so in all the manuscripts, including {extra})."
                         if lang == "en" else
                         f"В издании — «{lemma}» (так во всех рукописях, включая {extra}).")
        elif lang == "en":
            parts.append(f"In the edition — “{lemma}” (so in all the manuscripts except those listed below).")
        else:
            parts.append(f"В издании — «{lemma}» (так во всех рукописях, кроме перечисленных ниже).")
    else:
        parts.append(f"Reading checked: “{lemma}”." if lang == "en"
                     else f"Проверяемое чтение — «{lemma}».")

    for chunk in chunks:
        if chunk.startswith("om."):
            who = names([s.group(0) for s in SIGLUM.finditer(chunk)], table, lang)
            parts.append(f"Absent in: {who}." if lang == "en" else f"Нет в: {who}.")
            continue
        codes = WORK_RE.findall(chunk)
        if codes:
            parts.append(side(chunk, lang, table, default="the edition" if lang == "en" else "издании"))
            continue
        reading, signs = split_sigla(chunk)
        if not signs:
            parts.append(f"Also “{reading}”." if lang == "en" else f"Ещё «{reading}».")
            continue
        who = names(signs, table, lang)
        parts.append(f"Also “{reading}” — so in: {who}." if lang == "en"
                     else f"Ещё «{reading}» — так в: {who}.")
    return " ".join(parts)


FOLIO = re.compile(r"\bf\.\s?(\d+)\s?([rv])?")
ATTRIB = re.compile(r"\(attrib\.\s*([^)]+)\)")


def plain(text: str, lang: str) -> str:
    """Убрать сокращения из готовой строки источника (свидетели, источники).

    «Yogacintāmaṇi f. 78r (attrib. Dattātreya)» превращается в
    ««Йогачинтāман̣и», лист 78, лицевая сторона (приписывается Даттāтрее)»:
    ни одной буквы не добавлено, только раскрыто то, что стояло за знаками.
    """
    def folio(m):
        num, side = m.group(1), m.group(2)
        if lang == "en":
            return f"f. {num}" if not side else (
                f"f. {num}, recto" if side == "r" else f"f. {num}, verso")
        return f"лист {num}" + ("" if not side else
                                 (", лицевая сторона" if side == "r" else ", оборотная сторона"))

    def attrib(m):
        return f"(attributed to {m.group(1)})" if lang == "en" else f"(приписывается {m.group(1)})"

    text = FOLIO.sub(folio, text)
    text = ATTRIB.sub(attrib, text)
    text = WORK_RE.sub(lambda m: quoted(WORKS[m.group(1)][lang], lang), text)
    return text


def cross_reference(line: str, lang: str, table: dict[str, str]) -> str:
    """Строка сверки с другим текстом: «чтение ] чтение DYŚ v.l.»."""
    lemma_raw, _, rest = line.partition("|")
    lemma, _, variants = lemma_raw.partition("]")
    lemma = lemma.strip()
    variants = variants.strip()
    parts = []
    if lemma:
        parts.append(f"In the edition — “{lemma}”." if lang == "en" else f"В издании — «{lemma}».")
    # разбираем правую часть по запятым, каждая — своё чтение
    for chunk in [c.strip() for c in _split_variants(variants) if c.strip()]:
        codes = WORK_RE.findall(chunk)
        variant = "v.l." in chunk
        body = WORK_RE.sub("", chunk).replace("v.l.", "").strip(" ,;")
        if not body:
            continue
        tail = " (variant reading)" if variant and lang == "en" else (" (вариант чтения)" if variant else "")
        if codes:
            who = works(codes, lang)
            parts.append(f"In {who} — “{body}”{tail}." if lang == "en"
                         else f"В {who} — «{body}»{tail}.")
        else:
            parts.append(f"Also “{body}”{tail}." if lang == "en" else f"Ещё «{body}»{tail}.")
    return " ".join(parts)


def _split_variants(text: str) -> list[str]:
    """Запятая разделяет варианты, но «f. 78r, 79v» — это один шифр."""
    out, buf = [], ""
    for piece in text.split(","):
        if re.match(r"^\s*\d", piece) and buf:
            buf += "," + piece
            continue
        if buf:
            out.append(buf)
        buf = piece
    if buf:
        out.append(buf)
    return out


def build(lang: str, raw: dict, table: dict[str, str]) -> list[dict]:
    labels = {
        "ru": {"verse": "Стих", "edition": "Перевод издания (английский)",
               "metre": "Метр", "readings": "Разночтения по рукописям",
               "own": "По-русски (наш подстрочник)", "words": "Пословный разбор",
               "literal": "Буквальный перевод", "literary": "Литературный перевод",
               "sources": "Источники", "testimonia": "Свидетели",
               "testimonia_readings": "Разночтения в других текстах"},
        "en": {"verse": "Verse", "edition": "Edition translation (English)",
               "metre": "Metre", "readings": "Readings in the manuscripts",
               "own": "Our rendering", "words": "Word-by-word analysis",
               "literal": "Literal translation", "literary": "Literary translation",
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
        if verse.get("own"):
            blocks.append({"type": "prose", "key": "own", "label": labels["own"],
                           "paragraphs": [verse["own"][lang]]})
        if verse.get("metre"):
            blocks.append({"type": "prose", "key": "metre", "label": labels["metre"],
                           "paragraphs": [verse["metre"]]})
        items = [{"html": expand(line, table, lang)} for line in verse["readings"]]
        blocks.append({"type": "list", "ordered": False, "label": labels["readings"],
                       "items": items})
        if verse.get("sources"):
            lead = plain(verse["sources"], lang)
            if lang == "en":
                lead = "Source text: " + lead + "."
            else:
                lead = "Текст-источник: " + lead + "."
            paragraphs = [lead]
            paragraphs.extend(cross_reference(row, lang, table)
                              for row in verse.get("sources_readings", []))
            blocks.append({"type": "prose", "key": "sources", "label": labels["sources"],
                           "paragraphs": paragraphs})
        if verse.get("testimonia"):
            blocks.append({"type": "prose", "key": "testimonia",
                           "label": labels["testimonia"],
                           "paragraphs": [plain(verse["testimonia"], lang)]})
            for row in verse.get("testimonia_readings", []):
                blocks.append({"type": "p", "text": cross_reference(row, lang, table)})

    # пословный разбор, буквальный и литературный переводы — в конце раздела,
    # как во всех остальных позах: сначала все стихи, потом разбор
    groups = []
    titles = []
    for verse in raw["verses"]:
        titles.append(f'{labels["verse"]} {verse["number"]}')
        if lang == "ru":
            groups.append([[translit(word), gloss] for word, gloss in verse["words"]["ru"]])
        else:
            groups.append([[word, gloss] for word, gloss in verse["words"]["en"]])
    blocks.append({"type": "words", "label": labels["words"], "groups": groups,
                   "titles": titles})
    blocks.append({"type": "prose", "key": "literal", "label": labels["literal"],
                   "paragraphs": [raw["pose"]["literal"][lang]]})
    blocks.append({"type": "prose", "key": "literary", "label": labels["literary"],
                   "paragraphs": [raw["pose"]["literary"][lang]]})
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
