# -*- coding: utf-8 -*-
"""«Дхармапутрикā», глава 2, из двух томов — русского и английского.

Тома — полный перевод главы об āсанах (Āсанапракаран̣ам, стихи 1–17)
по публикации Кристель Баруа в блоге AyurYog (19 января 2017 года),
с добавленными в этих томах глоссами, буквальным переводом,
восстановленным деванāгарӣ и примечаниями. Стихи в томах есть,
поэтому на сайте они есть: деванāгарӣ, IAST, кириллица тома,
пословный разбор, оба перевода и примечания.

Кириллица тома сверяется с текстом PDF. Долгую ā том печатает
кириллической «а» с макроном; карта сайта пишет её латинской «ā».
Сборщик переводит знак в форму карты (так же делает tools/diacritics.py)
и оставляет об этом примечание: отступление названо, а не спрятано.

Запуск:  python3 tools/extract_dharmaputrika.py [--check]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from translit import translit  # noqa: E402
from diacritics import fix_document  # noqa: E402

EN_PDF = ROOT / "sources" / "Dharmaputrikā. Chapter 2. Āsanaprakaraṇam.pdf"
RU_PDF = ROOT / "sources" / "Дхармапутрикā. Глава 2. Āсанапракаран̣ам.pdf"
OUT = ROOT / "data" / "dharmaputrika.json"

POSE_KEYS = {
    1: "padmasana",
    2: "svastikasana",
    3: "pithasana",
    4: "sthalasana",
    5: "anjalikasana",
    6: "ardhacandrasana",
    7: "dandasana",
    8: "sarvatobhadrasana",
}

# Сводка таблицы датировки. Строки сверены с томом дословно
# (verify_summary); одна русская ячейка разорвана границей страницы,
# и проверяются обе её половины.
SUMMARY = {
    "en": {
        "heads": ["Claim", "Status", "Source"],
        "rows": [
            ["Text existed by 24 May 1069 CE (NAK 3–393 contains it and is dated to that day)",
             "Documented fact",
             "De Simini 2016, p. 252 and n. 49 [S2]"],
            ['"Composed in the 10th century at the latest"',
             "Statement of the source publication, quoted as such",
             "Barois 2017 [S1]"],
            ['"An 11th century manuscript is preserved in Calcutta"',
             "Statement of the source publication; the manuscript is not identified there, and is not identified here either",
             "Barois 2017 [S1]"],
            ["G 4077 (Calcutta, 1036 CE), the earliest dated corpus MS identified so far, lacks the Dharmaputrikā",
             "Documented fact",
             "De Simini 2016, p. 243 n. 28; p. 251 n. 44 [S2]"],
            ["Composition as early as the 7th century",
             "Hypothesis (textual parallels)",
             "Barois 2020, pp. 20–21 [S3]"],
            ["Posture chapter precedes Hemacandra's Yogaśāstra (12th c.) by ≥2 centuries",
             "Statement of the source publication",
             "Barois 2017 [S1]"],
        ],
    },
    "ru": {
        "heads": ["Утверждение", "Статус", "Источник"],
        "rows": [
            ["Текст существовал к 24 мая 1069 г. н. э. (NAK 3–393 содержит его и датирована этим днём)",
             "Документированный факт",
             "De Simini 2016, с. 252 и прим. 49 [S2]"],
            ["«Составлена не позднее X века»",
             "Утверждение исходной публикации, приведено как таковое",
             "Barois 2017 [S1]"],
            ["«В Калькутте хранится рукопись XI века»",
             "Утверждение исходной публикации; рукопись там не идентифицирована, и здесь она тоже не идентифицируется",
             "Barois 2017 [S1]"],
            ["G 4077 (Калькутта, 1036 г. н. э.), самая ранняя из выявленных датированных рукописей корпуса, не содержит «Дхармапутрикā»",
             "Документированный факт",
             "De Simini 2016, с. 243 прим. 28; с. 251 прим. 44 [S2]"],
            ["Составление уже в VII веке",
             "Гипотеза (текстовые параллели)",
             "Barois 2020, с. 20–21 [S3]"],
            ["Глава о позах предшествует «Йогаш́āстра» Хемачандры (XII в.) не менее чем на два века",
             "Утверждение исходной публикации",
             "Barois 2017 [S1]"],
        ],
    },
}

# Половина ячейки, которую линейный текст PDF разрывает ссылкой [S1].
SUMMARY_SPLIT = (
    "Утверждение исходной публикации; рукопись там не идентифицирована, и",
    "здесь она тоже не идентифицируется",
)

# Примечание сайта о знаке, который том печатает иначе. Это не цитата:
# цитата после перевода знака в форму карты стала бы самопротиворечивой.
MAP_NOTE = {
    "ru": (
        "Том печатает долгую гласную карты — латинскую «ā» внутри "
        "кириллического слова — как кириллическую «а» с комбинируемым "
        "макроном. Том сам называет это единственным отступлением от карты "
        "проекта. На сайте стоит форма карты, та же, что в остальных трактатах."
    ),
    "en": (
        "The Russian volume prints the long vowel of the project map — Latin "
        "“ā” inside a Cyrillic word — as Cyrillic “а” with a combining macron. "
        "The volume itself calls this its only departure from the project map. "
        "The site uses the map’s form, the same one as in the other treatises."
    ),
}

MARKER_RE = re.compile(
    r"^(?:Devanagari|Деванагари|IAST|Транслитерация \(кириллица\)|"
    r"Word-for-word Analysis|Пословный разбор|"
    r"Verse \d+|Стих \d+|"
    r"Literal Translation|Буквальный перевод|"
    r"Literary Translation.*|Литературный перевод.*|"
    r"Notes|Примечания|Translation|Перевод|Colophon|Колофон)$"
)
H3_RE = re.compile(r"^(?:\d+\.\s|\([a-cа-в]\)\s)")
VERSE_END_RE = re.compile(r"(?:\|\|\s*\d+\s*\|\||॥\s*[०-९0-9]+\s*॥)\s*$")
SUMMARY_HEAD_RE = re.compile(r"^(?:5\.\s+Summary|5\.\s+Сводка)")


def clean(text: str) -> str:
    text = text.replace("\u200b", "").replace("\u00ad", "").replace("\ufeff", "")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def canon(text: str) -> str:
    """Знаки карты: кириллическая «а» с макроном → латинская ā, как в diacritics.py."""
    text = clean(text)
    for src, dst in (
        ("а\u0304", "ā"), ("А\u0304", "Ā"),
        ("a\u0304", "ā"), ("A\u0304", "Ā"),
        ("у\u0304", "ӯ"), ("У\u0304", "Ӯ"),
        ("я\u0304", "йā"),
        ("ı\u0304", "ī"),
        ("ш\u0323", "ш"), ("Ш\u0323", "Ш"),
        ("r\u0325", "ṛ"),
    ):
        text = text.replace(src, dst)
    return unicodedata.normalize("NFC", text)


def squash(text: str) -> str:
    return re.sub(r"\s+", "", canon(text))


def join_lines(lines: list[str]) -> str:
    """Склеить строки абзаца. Незакрытый адрес склеивается без пробела."""
    out = ""
    for line in lines:
        line = clean(line)
        if not line:
            continue
        if not out:
            out = line
            continue
        unclosed_url = out.count("<") > out.count(">")
        unclosed_code = out.count("`") % 2 == 1
        if unclosed_url or unclosed_code:
            out += line
        else:
            out += " " + line
    return canon(out)


def pdf_flat(path: Path) -> str:
    import pymupdf
    doc = pymupdf.open(path)
    parts = []
    for page in doc:
        parts.append(page.get_text())
    return re.sub(r"\s+", " ", canon("\n".join(parts)))


def present(fragment: str, flat: str, gap: int = 0) -> bool:
    """Фрагмент есть в томе. gap > 0 — слова могут быть разнесены границей колонки.

    Первое вхождение первого слова может быть из другого абзаца, поэтому
    при разрыве ищется следующее.
    """
    frag = canon(fragment)
    if not frag:
        return True
    if gap <= 0:
        return squash(frag) in squash(flat)
    collapsed = re.sub(r"\s+", " ", canon(flat))
    words = frag.split()
    start = 0
    while True:
        found = collapsed.find(words[0], start)
        if found < 0:
            return False
        pos = found + len(words[0])
        ok = True
        for word in words[1:]:
            nxt = collapsed.find(word, pos)
            if nxt < 0 or nxt - pos > gap:
                ok = False
                break
            pos = nxt + len(word)
        if ok:
            return True
        start = found + 1


def line_kind(line: dict) -> str | None:
    text = canon(line["text"])
    if line["deva"]:
        return None
    if line["size"] >= 12.5:
        return "h2"
    if line["bold"] and MARKER_RE.match(text):
        return "marker"
    if line["bold"] and H3_RE.match(text) and len(text) < 160:
        return "h3"
    return None


def is_verse_line(line: dict) -> bool:
    text = line["text"]
    if line["deva"]:
        return True
    if line["italic"] and ("|" in text or "।" in text or "॥" in text):
        return True
    if VERSE_END_RE.search(text) or text.endswith("|") or text.endswith("।"):
        return True
    return False


def events_of(path: Path) -> list[dict]:
    import pymupdf
    doc = pymupdf.open(path)
    events = []
    for pi, page in enumerate(doc):
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            lines = []
            for raw in block["lines"]:
                if raw["bbox"][1] > 745:
                    continue
                spans = raw["spans"]
                text = clean("".join(s["text"] for s in spans))
                if not text or re.fullmatch(r"\d+", text):
                    continue
                meaningful = [s for s in spans if s["text"].strip()]
                lines.append({
                    "text": text,
                    "bold": bool(meaningful) and all("Bold" in s["font"] for s in meaningful),
                    "italic": any("Italic" in s["font"] for s in spans),
                    "deva": any("\u0900" <= c <= "\u097F" for c in text),
                    "size": max(s["size"] for s in spans),
                    "page": pi + 1,
                })
            if not lines:
                continue
            i = 0
            while i < len(lines):
                kind = line_kind(lines[i])
                text = canon(lines[i]["text"])
                # Неполный заголовок («(б) … (1069») не отрывается от продолжения.
                if kind == "h3" and sentence_complete(text) and text.count("(") == text.count(")"):
                    events.append({"kind": kind, "text": text, "page": pi + 1})
                    i += 1
                    continue
                if kind not in ("h2", "marker"):
                    break
                events.append({"kind": kind, "text": text, "page": pi + 1})
                i += 1
            rest = lines[i:]
            if not rest:
                continue
            if all(is_verse_line(line) for line in rest):
                for line in rest:
                    events.append({
                        "kind": "verse",
                        "text": canon(line["text"]),
                        "deva": line["deva"],
                        "page": pi + 1,
                    })
                continue
            text = join_lines([line["text"] for line in rest])
            if "●" in text:
                parts = re.split(r"\s*●\s*", text)
                if parts[0].strip():
                    events.append({"kind": "p", "text": canon(parts[0]), "page": pi + 1})
                for part in parts[1:]:
                    part = canon(part)
                    if part:
                        events.append({"kind": "bullet", "text": part, "page": pi + 1})
            else:
                events.append({"kind": "p", "text": text, "page": pi + 1})
    return events


def sentence_complete(text: str) -> bool:
    """Абзац договорён. Точка с запятой и запятая — разрыв строки, не конец."""
    t = text.rstrip()
    if not t:
        return True
    if t[-1] in ".!?»\"”)]।॥:":
        return True
    if t.endswith("||"):
        return True
    if re.search(r"\[\s*S\d+\s*\]\s*$", t):
        return True
    if re.search(r"\|\|\s*\d+\s*\|\|\s*$", t):
        return True
    return False


def join_continuations(events: list[dict]) -> list[dict]:
    """Склеивает абзац, который PDF разорвал границей страницы.

    Признак разрыва — незакрытая фраза, а не новая строка: «составлена не» /
    «позднее», «(De» / «Simini», «ча — и;» / «йатнатах̣ — усердно».
    """
    out = []
    for event in events:
        if (out and out[-1]["kind"] in ("p", "bullet") and event["kind"] == "p"
                and not sentence_complete(out[-1]["text"])):
            out[-1]["text"] = canon(out[-1]["text"] + " " + event["text"])
            out[-1]["joined"] = True
            continue
        out.append(event)
    return out


def split_sections(events: list[dict]) -> list[dict]:
    """Режет поток по заголовкам размера главы. Сводку-таблицу не тащит абзацами."""
    sections = []
    current = {"title": "", "events": []}
    skipping_table = False
    for event in events:
        if event["kind"] == "h2":
            if current["title"] or current["events"]:
                sections.append(current)
            current = {"title": event["text"], "events": []}
            skipping_table = False
            continue
        if SUMMARY_HEAD_RE.match(event["text"]):
            current["events"].append({"kind": "summary", "text": event["text"], "page": event["page"]})
            skipping_table = True
            continue
        if skipping_table:
            continue
        current["events"].append(event)
    if current["title"] or current["events"]:
        sections.append(current)
    return sections


def section_by(sections: list[dict], pattern: str) -> dict:
    regex = re.compile(pattern)
    found = [s for s in sections if regex.search(s["title"])]
    if len(found) != 1:
        titles = [s["title"] for s in sections]
        raise SystemExit("раздел %r не найден однозначно: %s" % (pattern, titles))
    return found[0]


def paras_of(section: dict) -> list[str]:
    return [e["text"] for e in section["events"] if e["kind"] == "p" and e["text"]]


def section_blocks(section: dict, lang: str) -> list[dict]:
    """Абзацы раздела и заголовки пунктов, которые иначе отрываются от текста."""
    blocks = []
    buf = []

    def flush():
        if buf:
            blocks.extend(blocks_of(buf, lang))
            buf.clear()

    for event in section["events"]:
        if event["kind"] == "h3":
            flush()
            blocks.append({"type": "h3", "text": event["text"]})
        elif event["kind"] == "p" and event["text"]:
            buf.append(event["text"])
    flush()
    return blocks


def tidy_text(text: str) -> list[dict]:
    """Чинит то, что склейка строк PDF портит, не меняя слов тома.

    Строка «Источник:» в шапке и таблица знаков, которую двухколонный набор
    слил в одну строку, — не новые слова, а разметка. Противоречивая фраза
    про ā появляется только после перевода знака в форму карты; вместо неё
    стоит примечание, которое называет отступление.
    """
    for sep in (" Источник:", " Source:"):
        if sep in text:
            head, tail = text.split(sep, 1)
            if "." not in head and len(head) < 140:
                return [{"type": "p", "text": head.strip()},
                        {"type": "p", "text": sep.strip() + tail}]
    if text.startswith("Кириллица IAST Кириллица"):
        if "Три места, где латиница сохранена намеренно" in text:
            return [{"type": "h3", "text": "Три места, где латиница сохранена намеренно"}]
        return []
    if text.startswith("Соответствия (диакритика"):
        return []
    bad = "Единственное отступление, согласованное отдельно:"
    if bad in text:
        kept = text.split(bad)[0].strip()
        return [{"type": "p", "text": kept}] if kept else []
    return [{"type": "p", "text": text}]


def blocks_of(paragraphs: list[str], lang: str) -> list[dict]:
    blocks = []
    for text in paragraphs:
        if not text:
            continue
        if lang == "ru" and text.startswith("Оригинал (EN):"):
            blocks.append({
                "type": "prose",
                "key": "orig",
                "label": "Оригинал (EN)",
                "paragraphs": [text.split(":", 1)[1].strip()],
            })
            continue
        # Короткий заголовок пункта — целиком, без продолжения фразы.
        if H3_RE.match(text) and len(text) < 180 and ". " not in text[:-1] and " — " not in text:
            blocks.append({"type": "h3", "text": text})
            continue
        if text.startswith(("«", '"', "“")) and text.endswith(("»", '"', "”", "».", '".', "”.", ").")):
            blocks.append({"type": "quote", "paragraphs": [html_escape(text)]})
            continue
        for piece in tidy_text(text):
            if piece["type"] == "p" and piece["text"].startswith(("«", '"', "“")) and piece["text"].endswith(("»", '"', "”", "».", '".', ").")):
                blocks.append({"type": "quote", "paragraphs": [html_escape(piece["text"])]})
            else:
                blocks.append(piece)
    return blocks


def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse_pairs(text: str) -> list[list[str]]:
    text = text.lstrip("●").strip()
    pairs = []
    for part in re.split(r";\s*", text):
        part = part.strip().rstrip(".")
        if not part:
            continue
        if " — " not in part:
            raise SystemExit("в пословном разборе нет тире: %s" % part[:80])
        term, gloss = part.split(" — ", 1)
        pairs.append([canon(term.strip()), canon(gloss.strip())])
    if not pairs:
        raise SystemExit("пустой пословный разбор")
    return pairs


def group_verses(lines: list[str]) -> list[list[str]]:
    groups = []
    buf: list[str] = []
    for line in lines:
        buf.append(line)
        if VERSE_END_RE.search(line) or (len(lines) == 1):
            groups.append(buf)
            buf = []
    if buf:
        groups.append(buf)
    return groups


def verse_number(lines: list[str]) -> str:
    joined = " ".join(lines)
    match = re.search(r"\|\|\s*(\d+)\s*\|\|", joined)
    if match:
        return match.group(1)
    match = re.search(r"॥\s*([०-९]+)\s*॥", joined)
    if match:
        digits = str.maketrans("०१२३४५६७८९", "0123456789")
        return match.group(1).translate(digits)
    return ""


def parse_verse_section(en: dict, ru: dict) -> dict:
    """Один раздел (вступление, поза или колофон) из двух томов."""
    def take(section, kind_set):
        return [e for e in section["events"] if e["kind"] in kind_set]

    en_deva = [e["text"] for e in en["events"] if e["kind"] == "verse" and e.get("deva")]
    ru_deva = [e["text"] for e in ru["events"] if e["kind"] == "verse" and e.get("deva")]
    if [squash(x) for x in en_deva] != [squash(x) for x in ru_deva]:
        raise SystemExit("деванāгарӣ двух томов разошлось в «%s»" % en["title"])
    en_iast = [e["text"] for e in en["events"] if e["kind"] == "verse" and not e.get("deva")]
    ru_cyr = [e["text"] for e in ru["events"] if e["kind"] == "verse" and not e.get("deva")]
    if len(en_deva) != len(en_iast) or len(en_deva) != len(ru_cyr):
        raise SystemExit(
            "строки не сошлись в «%s»: deva %d, iast %d, cyr %d"
            % (en["title"], len(en_deva), len(en_iast), len(ru_cyr))
        )

    def words_of(section):
        groups = []
        title = ""
        mode = None
        for event in section["events"]:
            if event["kind"] == "marker":
                text = event["text"]
                if text in ("Word-for-word Analysis", "Пословный разбор"):
                    mode = "words"
                elif text in ("Literal Translation", "Буквальный перевод",
                              "Notes", "Примечания", "Translation", "Перевод") \
                        or text.startswith("Literary") or text.startswith("Литературный"):
                    mode = None
                elif mode == "words" and re.match(
                        r"^(?:Verse|Стих) \d+$|^(?:Colophon|Колофон)$", text):
                    title = text
                continue
            if mode == "words" and event["kind"] == "bullet":
                groups.append({"title": title, "pairs": parse_pairs(event["text"])})
                title = ""
        return groups

    en_words = words_of(en)
    ru_words = words_of(ru)
    deva_groups = group_verses(en_deva)
    iast_groups = group_verses(en_iast)
    cyr_groups = group_verses(ru_cyr)
    if not (len(deva_groups) == len(iast_groups) == len(cyr_groups)):
        raise SystemExit("стихи не сошлись в «%s»" % en["title"])
    if en_words and len(en_words) != len(deva_groups):
        raise SystemExit(
            "пословный разбор не покрывает стихи в «%s»: стихов %d, групп %d"
            % (en["title"], len(deva_groups), len(en_words))
        )
    if len(en_words) != len(ru_words):
        raise SystemExit("число групп разбора разное в «%s»" % en["title"])

    def prose(section, labels):
        mode = None
        out = {"literal": [], "literary": [], "translation": [], "notes": []}
        label_found = {}
        for event in section["events"]:
            if event["kind"] == "marker":
                text = event["text"]
                if text in ("Literal Translation", "Буквальный перевод"):
                    mode = "literal"
                    label_found["literal"] = text
                elif text.startswith("Literary") or text.startswith("Литературный"):
                    mode = "literary"
                    label_found["literary"] = text
                elif text in ("Translation", "Перевод"):
                    mode = "translation"
                    label_found["translation"] = text
                elif text in ("Notes", "Примечания"):
                    mode = "notes"
                else:
                    mode = None
                continue
            if mode in ("literal", "literary", "translation") and event["kind"] == "p":
                out[mode].append(event["text"])
            elif mode == "notes" and event["kind"] in ("bullet", "p"):
                out["notes"].append(event["text"])
        out["labels"] = label_found
        return out

    en_prose = prose(en, None)
    ru_prose = prose(ru, None)
    cards = []
    for deva, iast, cyr in zip(deva_groups, iast_groups, cyr_groups):
        number = verse_number(iast) or verse_number(deva)
        cards.append({
            "number": number,
            "deva": deva,
            "iast": iast,
            "cyr": cyr,
        })
    return {
        "title_en": en["title"],
        "title_ru": ru["title"],
        "cards": cards,
        "words_en": en_words,
        "words_ru": ru_words,
        "en": en_prose,
        "ru": ru_prose,
    }


def verse_blocks(parsed: dict, lang: str) -> list[dict]:
    words = parsed["words_" + lang]
    prose = parsed[lang]
    blocks = []
    for index, card in enumerate(parsed["cards"]):
        blocks.append({
            "type": "verse_card",
            "verses": card["number"],
            "sections": [
                {
                    "type": "verse",
                    "key": "deva",
                    "label": "Деванāгарӣ" if lang == "ru" else "Devanāgarī",
                    "lines": card["deva"],
                },
                {
                    "type": "verse",
                    "key": "iast",
                    "label": "IAST",
                    "lines": card["iast"],
                },
                {
                    "type": "verse",
                    "key": "cyr",
                    "label": "Кириллическая транслитерация" if lang == "ru" else "Cyrillic transliteration",
                    "lines": card["cyr"],
                },
            ],
        })
    if words:
        blocks.append({
            "type": "words",
            "label": "Пословный разбор" if lang == "ru" else "Word-for-word Analysis",
            "titles": [g["title"] for g in words],
            "groups": [g["pairs"] for g in words],
        })
    for key, fallback in (
        ("literal", "Буквальный перевод" if lang == "ru" else "Literal Translation"),
        ("literary", "Литературный перевод" if lang == "ru" else "Literary Translation"),
        ("translation", "Перевод" if lang == "ru" else "Translation"),
    ):
        if prose[key]:
            blocks.append({
                "type": "prose",
                "key": key if key != "translation" else "translation",
                "label": prose["labels"].get(key, fallback),
                "paragraphs": prose[key],
            })
    if prose["notes"]:
        blocks.append({"type": "note", "paragraphs": prose["notes"]})
    return blocks


def pose_meta(title_en: str, title_ru: str) -> dict:
    match = re.match(r"^(\d+)\.\s+(\S+)\s+—\s+(.+?)\s+\(verses?\s+([^)]+)\)$", title_en)
    if not match:
        raise SystemExit("не разобран заголовок позы: %s" % title_en)
    number, iast, gloss_en, verses = match.groups()
    ru = re.match(r"^(\d+)\.\s+(\S+)\s+—\s+(.+?)\s+\(стих(?:и)?\s+([^)]+)\)$", title_ru)
    if not ru:
        raise SystemExit("не разобран русский заголовок позы: %s" % title_ru)
    return {
        "number": int(number),
        "key": POSE_KEYS[int(number)],
        "iast": iast,
        "name_en": iast,
        "name_ru": ru.group(2),
        "gloss_en": gloss_en,
        "gloss_ru": ru.group(3),
        "verses": verses.replace("–", "–"),
    }


def find_paragraph(paragraphs: list[str], needle: str) -> str:
    for text in paragraphs:
        if needle in text:
            return text
    raise SystemExit("в томе нет фразы: %s" % needle)


def dating_summary() -> dict:
    def items(lang, indexes):
        out = []
        for index in indexes:
            claim, status, source = SUMMARY[lang]["rows"][index]
            out.append({
                "who": claim,
                "when": status,
                "work": source,
            })
        return out

    return {
        "note": {
            "ru": "Никаких суждений о точности исходной публикации здесь не выносится.",
            "en": "No judgment is passed here on the accuracy of the source publication.",
        },
        "groups": [
            {
                "title": {"ru": "Документированный факт", "en": "Documented fact"},
                "label": {"ru": "Источник", "en": "Source"},
                "items": [
                    {"who": {lang: SUMMARY[lang]["rows"][0][0]},
                     "when": {lang: SUMMARY[lang]["rows"][0][1]},
                     "work": {lang: SUMMARY[lang]["rows"][0][2]}}
                    for lang in ()
                ] or None,
            }
        ],
    }


def bilingual_items(indexes: list[int]) -> list[dict]:
    items = []
    for index in indexes:
        item = {"who": {}, "when": {}, "work": {}}
        for lang in ("ru", "en"):
            claim, status, source = SUMMARY[lang]["rows"][index]
            item["who"][lang] = claim
            item["when"][lang] = status
            item["work"][lang] = source
        items.append(item)
    return items


def build_summary() -> dict:
    return {
        "note": {
            "ru": "Никаких суждений о точности исходной публикации здесь не выносится.",
            "en": "No judgement is passed on the accuracy of the source publication.",
        },
        "note2": {
            "ru": "Важно: дата «VII век» — это гипотеза Баруа, основанная на текстовых параллелях, а не дата рукописи. Ссылаться на неё следует как на её предположение, а не как на установленный факт.",
            "en": "Important: the \"seventh century\" date is Barois's hypothesis based on textual parallels, not a manuscript date. It should be cited as her suggestion, not as an established fact.",
        },
        "groups": [
            {
                "title": {"ru": "Документированный факт", "en": "Documented fact"},
                "label": {"ru": "Источник", "en": "Source"},
                "items": bilingual_items([0, 3]),
            },
            {
                "title": {"ru": "Утверждение исходной публикации", "en": "Statement of the source publication"},
                "label": {"ru": "Источник", "en": "Source"},
                "items": bilingual_items([1, 2, 5]),
            },
            {
                "title": {"ru": "Гипотеза (текстовые параллели)", "en": "Hypothesis (textual parallels)"},
                "label": {"ru": "Источник", "en": "Source"},
                "items": bilingual_items([4]),
            },
        ],
    }


def build() -> dict:
    en_sections = split_sections(join_continuations(events_of(EN_PDF)))
    ru_sections = split_sections(join_continuations(events_of(RU_PDF)))

    opening = parse_verse_section(
        section_by(en_sections, r"^Opening Instruction"),
        section_by(ru_sections, r"^Вступительное наставление"),
    )
    poses_parsed = []
    for number in range(1, 9):
        en = section_by(en_sections, r"^%d\. " % number)
        ru = section_by(ru_sections, r"^%d\. " % number)
        parsed = parse_verse_section(en, ru)
        parsed["meta"] = pose_meta(en["title"], ru["title"])
        poses_parsed.append(parsed)
    colophon = parse_verse_section(
        section_by(en_sections, r"^Colophon$"),
        section_by(ru_sections, r"^Колофон$"),
    )

    en_intro = section_by(en_sections, r"^Introduction")
    ru_intro = section_by(ru_sections, r"^Введение")
    en_dating = section_by(en_sections, r"^Dating of the Text")
    ru_dating = section_by(ru_sections, r"^Датировка текста")
    en_translator = section_by(en_sections, r"^Translator")
    ru_translator = section_by(ru_sections, r"^Примечание переводчицы")
    en_general = section_by(en_sections, r"^General Notes")
    ru_general = section_by(ru_sections, r"^Общие замечания")
    en_refs = section_by(en_sections, r"^References")
    ru_refs = section_by(ru_sections, r"^Библиография")
    ru_map = section_by(ru_sections, r"^Карта транслитерации")

    front_en = [s for s in en_sections if s["title"] in ("The Dharmaputrikā", "Chapter 2 — Āsanaprakaraṇam (\"The Section on the Postures\")")]
    front_ru = [s for s in ru_sections if s["title"] in ("Дхармапутрикā", "Глава 2 — Āсанапракаран̣ам («Раздел о позах»)")]

    def about(lang, front, intro, dating):
        blocks = [
            {"type": "title", "text": "Дхармапутрикā" if lang == "ru" else "The Dharmaputrikā"},
            {"type": "byline", "text": (
                "Глава 2 — Āсанапракаран̣ам («Раздел о позах»)"
                if lang == "ru" else
                "Chapter 2 — Āsanaprakaraṇam (“The Section on the Postures”)"
            )},
        ]
        for section in front:
            for text in paras_of(section):
                blocks.extend(tidy_text(text))
        blocks.append({"type": "h2", "text": intro["title"]})
        blocks.extend(section_blocks(intro, lang))
        blocks.append({"type": "h2", "text": dating["title"]})
        blocks.extend(section_blocks(dating, lang))
        blocks.append({
            "type": "table",
            "label": "5. Сводка по датировке (что можно и чего нельзя утверждать)" if lang == "ru"
            else "5. Summary of the dating (what can and cannot be asserted)",
            "rows": [SUMMARY[lang]["heads"]] + SUMMARY[lang]["rows"],
        })
        return blocks

    def dating_blocks(lang, dating):
        blocks = section_blocks(dating, lang)
        blocks.append({
            "type": "table",
            "label": "5. Сводка по датировке (что можно и чего нельзя утверждать)" if lang == "ru"
            else "5. Summary of the dating (what can and cannot be asserted)",
            "rows": [SUMMARY[lang]["heads"]] + SUMMARY[lang]["rows"],
        })
        return blocks

    def notes(lang, colophon_blocks, translator, general, mapping):
        blocks = [{"type": "subhead", "label": "Колофон" if lang == "ru" else "Colophon"}]
        blocks.extend(colophon_blocks)
        blocks.append({"type": "subhead", "label": translator["title"]})
        blocks.extend(section_blocks(translator, lang))
        blocks.append({"type": "subhead", "label": general["title"]})
        blocks.extend(section_blocks(general, lang))
        if mapping is not None:
            blocks.append({"type": "subhead", "label": mapping["title"]})
            blocks.extend(section_blocks(mapping, lang))
        blocks.append({"type": "note", "paragraphs": [MAP_NOTE[lang]]})
        return blocks

    def appendix(lang, refs):
        return [
            {"type": "subhead", "label": refs["title"]},
            *section_blocks(refs, lang),
        ]

    poses = []
    for parsed in poses_parsed:
        meta = parsed["meta"]
        poses.append({
            "key": meta["key"],
            "iast": meta["iast"],
            "number": meta["number"],
            "name": {"ru": meta["name_ru"], "en": meta["name_en"]},
            "gloss": {"ru": meta["gloss_ru"], "en": meta["gloss_en"]},
            "verses": {"ru": meta["verses"], "en": meta["verses"]},
            "text": {
                "ru": verse_blocks(parsed, "ru"),
                "en": verse_blocks(parsed, "en"),
            },
        })

    data = {
        "id": "dharmaputrika",
        "chapter": "2",
        "title": {
            "ru": "Дхармапутрикā. Глава 2. Āсанапракаран̣ам",
            "en": "Dharmaputrikā. Chapter 2. Āsanaprakaraṇam",
        },
        "asanasTitle": {
            "ru": "Вступительное наставление и перечень восьми поз (стихи 1–4)",
            "en": "Opening Instruction and the List of the Eight Postures (verses 1–4)",
        },
        "notesTitle": {"ru": "Примечания", "en": "Notes"},
        "about": {
            "ru": about("ru", front_ru, ru_intro, ru_dating),
            "en": about("en", front_en, en_intro, en_dating),
        },
        "dating": {
            "ru": {
                "title": ru_dating["title"],
                "blocks": dating_blocks("ru", ru_dating),
            },
            "en": {
                "title": en_dating["title"],
                "blocks": dating_blocks("en", en_dating),
            },
        },
        "datingSummary": build_summary(),
        "prologue": {
            "ru": [{"type": "subhead", "label": opening["title_ru"]}] + verse_blocks(opening, "ru"),
            "en": [{"type": "subhead", "label": opening["title_en"]}] + verse_blocks(opening, "en"),
        },
        "appendix": {
            "ru": appendix("ru", ru_refs),
            "en": appendix("en", en_refs),
        },
        "notes": {
            "ru": notes("ru", verse_blocks(colophon, "ru"), ru_translator, ru_general, ru_map),
            "en": notes("en", verse_blocks(colophon, "en"), en_translator, en_general, None),
        },
        "poses": poses,
        "_parsed": {
            "opening": opening,
            "poses": poses_parsed,
            "colophon": colophon,
        },
    }
    return data


def verify(data: dict, en_flat: str, ru_flat: str) -> None:
    missing = []

    def check(fragment, flat, where, gap=0):
        if fragment.startswith(MAP_NOTE["ru"][:24]) or fragment.startswith(MAP_NOTE["en"][:24]):
            return
        if not present(fragment, flat, gap=gap):
            missing.append("%s: %s" % (where, fragment[:90]))

    for lang, flat in (("en", en_flat), ("ru", ru_flat)):
        for row in SUMMARY[lang]["rows"]:
            for cell in row:
                gap = 80 if cell.startswith("Утверждение исходной публикации; рукопись") else 0
                check(cell, flat, "сводка %s" % lang, gap=gap)
        for head in SUMMARY[lang]["heads"]:
            check(head, flat, "шапка %s" % lang)
    for half in SUMMARY_SPLIT:
        check(half, ru_flat, "сводка ru, половина")

    parsed = data["_parsed"]
    for piece in [parsed["opening"], parsed["colophon"], *parsed["poses"]]:
        for card in piece["cards"]:
            for line in card["deva"]:
                check(line, en_flat, "дева " + piece["title_en"])
                check(line, ru_flat, "дева ru " + piece["title_ru"])
            for line in card["iast"]:
                check(line, en_flat, "iast " + piece["title_en"])
            for line in card["cyr"]:
                check(line, ru_flat, "кириллица " + piece["title_ru"])
        for lang, flat in (("en", en_flat), ("ru", ru_flat)):
            for group in piece["words_" + lang]:
                for term, gloss in group["pairs"]:
                    check(term, flat, "термин " + piece["title_" + lang])
                    check(gloss, flat, "глосса " + piece["title_" + lang])
            for key in ("literal", "literary", "translation", "notes"):
                for text in piece[lang][key]:
                    check(text, flat, key + " " + piece["title_" + lang])

    for lang, flat, about in (
        ("en", en_flat, data["about"]["en"]),
        ("ru", ru_flat, data["about"]["ru"]),
    ):
        for block in about:
            if block.get("type") == "p":
                check(block["text"], flat, "о трактате " + lang)
            elif block.get("type") == "quote":
                raw = block["paragraphs"][0].replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
                check(raw, flat, "цитата " + lang)
            elif block.get("type") == "prose":
                for text in block["paragraphs"]:
                    check(text, flat, "проза " + lang)

    # Фразы короткой датировки — из тома, не из пересказа.
    check(data["datingSummary"]["note"]["ru"], ru_flat, "note ru")
    check(data["datingSummary"]["note"]["en"], en_flat, "note en")
    check(data["datingSummary"]["note2"]["ru"], ru_flat, "note2 ru")
    check(data["datingSummary"]["note2"]["en"], en_flat, "note2 en")

    if missing:
        raise SystemExit("в томе не найдено %d фрагментов:\n%s" % (len(missing), "\n".join(missing[:30])))


def translit_report(data: dict) -> list[str]:
    """Буквы кириллицы тома против карты. Расхождение печатается, том не переписывается."""
    diffs = []
    pieces = [data["_parsed"]["opening"], data["_parsed"]["colophon"], *data["_parsed"]["poses"]]
    for piece in pieces:
        for card in piece["cards"]:
            for iast_lines, cyr_lines in zip(
                group_verses([" ".join(card["iast"])]),
                group_verses([" ".join(card["cyr"])]),
            ):
                pass
            iast = " ".join(card["iast"])
            cyr = " ".join(card["cyr"])
            expected = translit(iast)
            def letters(text):
                return re.sub(r"[^0-9A-Za-z\u0400-\u04FF\u0300-\u036fāĀ]+", "", text)
            if letters(expected) != letters(cyr):
                diffs.append("%s: карта %s | том %s" % (piece["title_en"], expected, cyr))
    return diffs


def public_data(data: dict) -> dict:
    out = {key: value for key, value in data.items() if key != "_parsed"}
    return out


def main() -> None:
    data = build()
    en_flat = pdf_flat(EN_PDF)
    ru_flat = pdf_flat(RU_PDF)
    verify(data, en_flat, ru_flat)
    diffs = translit_report(data)
    payload = fix_document(public_data(data))
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            raise SystemExit("data/dharmaputrika.json разошёлся с томами — пересоберите без --check")
        print("совпадает с томами: поз %d, стихов вступления %d" % (
            len(payload["poses"]),
            sum(1 for b in payload["prologue"]["ru"] if b.get("type") == "verse_card"),
        ))
        return
    OUT.write_text(text, encoding="utf-8")
    verses = sum(len(p["text"]["ru"]) for p in payload["poses"])
    print("записан %s" % OUT.name)
    print("поз: %d" % len(payload["poses"]))
    print("блоков на страницах поз (ru): %d" % verses)
    print("кириллица против карты, расхождений букв: %d" % len(diffs))
    for line in diffs:
        print("  " + line)


if __name__ == "__main__":
    main()
