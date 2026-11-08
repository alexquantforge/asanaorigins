#!/usr/bin/env python3
"""Сборка data/matsyendra-samhita.json из двух томов о третьей пат̣але.

Источник — русский и английский тома одной статьи: пятнадцать āсан третьей
пат̣алы «Матсйендра-сам̣хитā» по изданию Дебабраты Сеншармы (Калькутта, 1994).
Скрипт ничего не сочиняет: он раскладывает текст томов по полям сайта и
проверяет, что раскладка сошлась.

Структура тома:

    заглавие, автор, «Предисловие», «Издание и рукописи», «О тексте и нумерации»
                                            → раздел «О трактате»
    «Датировка»                             → статья «Датировка» + короткая сводка
    «Вступление (стихи 1–2)»                → «Вступление»
    1. Вӣрāсана … 15. Вр̣шабхāсана            → пятнадцать страниц āсан
    «Приложение. Заключительные стихи (36–46)» → «Приложение»
    «Примечания к чтениям рукописи»         → «Примечания»

Имена āсан берутся из списка в предисловии: это единственное место, где том
сам пишет их с полной диакритикой (в заголовках разделов диакритика местами
опущена — «Kurmāsana», «Garuāsana»). Расхождение заголовка и списка
печатается, а не замалчивается.

Запуск:  python3 tools/extract_matsyendra.py [--check]
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
import script_mix  # noqa: E402  (одно слово — один алфавит)

# Буквы-двойники: в томах встречаются опечатки набора, когда внутри
# кириллического слова набрана латинская буква («кучe», «камаṭӣ»). Карта
# tools/script_mix.py чинит только буквы с диакритикой, поэтому простые
# двойники перечислены здесь и каждая замена печатается.
HOMOGLYPHS = {"a": "а", "c": "с", "e": "е", "k": "к", "o": "о", "p": "р",
              "t": "т", "x": "х", "y": "у", "ṭ": "т\u0323", "ī": "ӣ",
              "ā": "а\u0304", "ṃ": "м\u0323", "ḥ": "х\u0323"}


def unmix(token: str) -> str:
    """Заменить латинские двойники кириллицей; незнакомые — оставить."""
    out = []
    for ch in token:
        out.append(HOMOGLYPHS.get(ch, ch) if "a" <= ch.lower() <= "z"
                   or ch in "āīūṛṃḥṭḍṇśṣḷ" else ch)
    return "".join(out)


def fix_word(token: str) -> str:
    fixed = unmix(token)
    if scan(fixed):
        raise SystemExit(f"не удалось развести алфавиты в слове: {token!r}")
    return fixed


def fix_text(text: str) -> str:
    """Смешанные слова в строке → одноалфавитные."""
    out = []
    pos = 0
    for match in re.finditer(r"\S+", text):
        out.append(text[pos:match.start()])
        word = match.group(0)
        out.append(fix_word(word) if scan(word) else word)
        pos = match.end()
    out.append(text[pos:])
    return "".join(out)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "matsyendra-samhita.json"

PDF = {
    "ru": ROOT / "sources" / "Матсйендра-сам̣хитā. Третья пат̣ала (RU).pdf",
    "en": ROOT / "sources" / "Matsyendrasaṃhitā. Chapter Three (EN).pdf",
}

LABELS = {
    "ru": {
        "deva": "Деванāгарӣ", "iast": "IAST",
        "cyr": "Кириллическая транслитерация",
        "words": "Пословный разбор", "literal": "Буквальный перевод",
        "literary": "Литературный перевод", "trans": "Перевод",
        "note": "Примечание:", "byline": "Автор:",
        "chapter": "Вступление", "appendixWord": "Приложение",
        "notes": "Примечания к чтениям рукописи",
    },
    "en": {
        "deva": "Devanāgarī", "iast": "IAST",
        "cyr": "Cyrillic transliteration",
        "words": "Word-by-word analysis", "literal": "Literal translation",
        "literary": "Literary translation", "trans": "Translation",
        "note": "Note:", "byline": "Author:",
        "chapter": "Introduction", "appendixWord": "Application",
        "notes": "Notes on manuscript readings",
    },
}

VERSE_KEYS = ("deva", "iast", "cyr")
PARA_KEYS = ("words", "literal", "literary", "trans")

# подзаголовки предисловия; «Датировка» выносится в отдельную статью
SUBHEADS = {
    "ru": ["Предисловие", "Издание и рукописи", "Датировка",
           "О тексте и нумерации"],
    "en": ["Preface", "The edition and its manuscript sources", "Dating",
           "Text and numbering"],
}
DATING = {"ru": "Датировка", "en": "Dating"}

# колонтитул заключительной страницы; заглавие тома под него не подходит
FOOTER = re.compile(r"^(Матсйендра-сам̣хитā · III пат̣ала ·|Matsyendra Saṃhitā · III Paṭala ·)$")

# пометка конца стиха: «॥ ३ ॥», «|| 36 ||», «|| 18a ||»
VERSE_END = re.compile(r"[॥|]{1,2}\s*[0-9०-९]{1,2}[a-zA-Z\u0430-\u044f]?\s*[॥|]{1,2}$")
# обрывок, состоящий только из пометки: так номер стиха переезжает на новую строку
VERSE_TAIL = re.compile(r"^[॥|\s0-9०-९abа]+$")


def ends_sentence(line: str) -> bool:
    """Кончилось ли предложение: по нему видно, оборван ли абзац на странице."""
    tail = line.rstrip()
    # пометка конца стиха «॥ ३ ॥», «|| 36 ||» закрывает стих
    if VERSE_END.search(tail):
        return True
    # «(?)» — знак неясного чтения, а не конец фразы
    if tail.endswith(("(?)", "( ? )")):
        return False
    # одинокое «||» — номер стиха перешёл на следующую строку
    if re.search(r"[॥|]$", tail):
        return False
    tail = tail.rstrip("»”’)]")
    # «A. D.» на странице рвётся после «A.»
    if re.search(r"(?:^|\s)[A-ZА-Я]\.$", tail):
        return True
    if tail.endswith(("…", ",", ";", ":", "«", "-", "(")):
        return False
    return bool(re.search(r"[.!?]$", tail))


# Короткая сводка датировки. Каждая цитата проверяется на присутствие в томе:
# если фрагмент не найден дословно, сборка останавливается.
DATING_SUMMARY = {
    "label": {"ru": "На чём основано (по словам самого тома)",
              "en": "Basis (in the volume’s own words)"},
    "items": [
        {
            "who": {"ru": "Дебабрата Сеншарма о рукописи, «введение, с. 1»",
                    "en": "Debabrata Sensharma on the manuscript, “introduction, p. 1”"},
            "when": {"ru": "1900 год эры Викрама или 1858 год н. э.",
                     "en": "1900 of the Vikram era or 1858 CE"},
            "whenNote": {"ru": "какое из двух чисел имел в виду редактор, по этой фразе "
                               "установить нельзя: соответствие календарей в ней "
                               "противоречиво",
                         "en": "which of the two numbers the editor meant cannot be "
                               "established from this sentence: the conversion in it is "
                               "inconsistent"},
            "work": {
                "ru": "“The ms bears no date but on paleographic examination the date for "
                      "writing the ms appears to be about 1900 Vikram era corresponding to "
                      "1858 A. D.”",
                "en": "“The ms bears no date but on paleographic examination the date for "
                      "writing the ms appears to be about 1900 Vikram era corresponding to "
                      "1858 A. D.”"},
        },
        {
            "who": {"ru": "Историографический диапазон датировки Матсйендранāтха, "
                          "«введение, с. 9»",
                    "en": "The range of scholarly opinions on Matsyendranātha, "
                          "“introduction, p. 9”"},
            "when": {"ru": "V–XIII вв. н. э.", "en": "the 5th to the 13th century CE"},
            "work": {
                "ru": "“The upper limit of his time is fifth century A. D. and lowest "
                      "limit is sometime in the thirteenth century A. D.”",
                "en": "“The upper limit of his time is fifth century A. D. and lowest "
                      "limit is sometime in the thirteenth century A. D.”"},
        },
        {
            "who": {"ru": "Собственное предположение редактора, с. 26",
                    "en": "The editor’s own conclusion, p. 26"},
            "when": {"ru": "V–VI вв. н. э.", "en": "the 5th or 6th century CE"},
            "whenNote": {"ru": "это мнение редактора, а не установленный исторический факт",
                         "en": "the editor’s interpretation, not an established historical "
                               "conclusion"},
            "work": {
                "ru": "“Matsyendranātha therefore probably flourished in 5th or 6th century "
                      "A. D. and lived for 400 years or so in the physical body and taught "
                      "Yoga to Gorakṣanātha in the 10th century A. D.”",
                "en": "“Matsyendranātha therefore probably flourished in 5th or 6th century "
                      "A. D. and lived for 400 years or so in the physical body and taught "
                      "Yoga to Gorakṣanātha in the 10th century A. D.”"},
        },
        {
            "who": {"ru": "Описание критического издания Чабы Киша (IFP / EFEO, 2021), "
                          "в которое входит третья глава",
                    "en": "Description of Csaba Kiss’s critical edition (IFP / EFEO, 2021), "
                          "which includes chapter 3"},
            "when": {"ru": "предположительно XIII век", "en": "perhaps the thirteenth century"},
            "whenNote": {"ru": "сохранилось в пяти свидетелях XIX века",
                         "en": "surviving in five nineteenth-century witnesses"},
            "work": {
                "ru": "“This volume presents the first critical edition, along with an "
                      "English translation, of the core chapters of a Sanskrit work of "
                      "perhaps the thirteenth century surviving in five nineteenth-century "
                      "witnesses”",
                "en": "“This volume presents the first critical edition, along with an "
                      "English translation, of the core chapters of a Sanskrit work of "
                      "perhaps the thirteenth century surviving in five nineteenth-century "
                      "witnesses”"},
        },
    ],
}

# Последняя строка примечаний: в двух томах она разная (русский том говорит об
# издании 1994 года, английский — о рукописной транскрипции). Печатается как есть.
CLOSING = {
    "ru": "Перевод и пословный разбор выполнены по тексту III пат̣алы в издании "
          "Сеншармы 1994 года.",
    "en": "The translation and word-by-word analysis are based on the handwritten "
          "transcription of Paṭala III of the Matsyendra Saṃhitā.",
}


def clean_pages(path: Path) -> list[str]:
    """Строки тома подряд; пустая строка сохранена — она разделяет абзацы."""
    lines: list[str] = []
    for page in pymupdf.open(path):
        for raw in page.get_text().split("\n"):
            s = raw.strip()
            if s.isdigit() or FOOTER.match(s):
                continue
            lines.append(s)
    return lines


def page_blocks(path: Path) -> list[tuple[int, list[str]]]:
    """Абзацы тома так, как их выделяет сам PDF: метка, заголовок, абзац.

    Разбиение по пустым строкам здесь не годится: в примечаниях абзацы идут
    подряд без пустых строк, а страница рвёт абзац посередине.
    """
    out: list[tuple[int, list[str]]] = []
    for num, page in enumerate(pymupdf.open(path)):
        for block in page.get_text("blocks"):
            lines = [l.strip() for l in block[4].split("\n") if l.strip()]
            lines = [l for l in lines if not FOOTER.match(l) and not l.isdigit()]
            if lines:
                out.append((num, lines))
    return out


def walk(lang: str) -> list[dict]:
    """Блоки в порядке тома: раздел, подзаголовок, метка, абзац."""
    lab = LABELS[lang]
    label_of = {lab[k]: k for k in VERSE_KEYS + PARA_KEYS}
    blocks: list[dict] = []
    cur = {"kind": "front", "head": [], "blocks": []}
    blocks.append(cur)
    expected = 1
    label: str | None = None

    def add(key: str, lines: list[str], new_page: bool = False) -> None:
        """Абзац под текущей меткой.

        Метка в PDF стоит отдельным блоком и действует до следующей метки:
        у позы из двух стихов «Пословный разбор» идёт двумя абзацами подряд.
        Абзац, оборванный на странице, остаётся одним абзацем.
        """
        nonlocal label
        if key == "p" and label:
            key = label
        same = [i for i, b in enumerate(cur["blocks"]) if b["key"] == key]
        if same:
            i = same[-1]
            target = cur["blocks"][i]
            tail = join_lines(target["lines"], deva=(key == "deva"))
            if VERSE_END.search(tail):
                # стих закрыт: обрывок пометки ниже относится уже к другому
                cur["blocks"].append({"key": key, "lines": list(lines)})
                return
            if VERSE_TAIL.match(" ".join(lines)) and i == len(cur["blocks"]) - 1:
                # «||» или «23 ||» на отдельной строке — это хвост стиха выше
                target["lines"].extend(lines)
                return
            # «A. D.» на странице рвётся на «…A.» и «D.”»: это один абзац
            if re.search(r"(?:^|\s)[A-ZА-Я]\.$", tail.rstrip(" »”’)]")) \
                    and re.match(r"^[A-ZА-Я]\.", lines[0]):
                target["lines"].extend(lines)
                return
            if not ends_sentence(tail):
                target["lines"].extend(lines)
                return
            # «… (introduction, p.» + «9): …» — ссылка разорвана на номер
            if re.match(r"^\d+\)", lines[0]):
                target["lines"].extend(lines)
                return
            # на границе страницы абзац может продолжиться с цифры — так новый
            # абзац не начинается
            if new_page and i == len(cur["blocks"]) - 1 \
                    and re.match(r"^[)]", lines[0]):
                target["lines"].extend(lines)
                return
        cur["blocks"].append({"key": key, "lines": list(lines)})

    prev_page = -1
    for page, lines in page_blocks(PDF[lang]):
        new_page = page != prev_page
        prev_page = page
        first = lines[0]
        # заглавие тома — первый блок
        if not blocks[0]["head"] and cur is blocks[0]:
            cur["head"] = [first]
            lines = lines[1:]
            if not lines:
                continue
            first = lines[0]

        head_key = None
        if first.startswith(lab["chapter"]):
            head_key = "intro"
        elif first.startswith(lab["appendixWord"]):
            head_key = "appendix"
        elif first.startswith(lab["notes"]):
            head_key = "notes"
        else:
            m = re.match(r"^(\d{1,2})\.\s+\S", first)
            if m and int(m.group(1)) == expected:
                head_key = "pose"
        if head_key:
            if head_key == "pose":
                expected += 1
            cur = {"kind": head_key, "head": [first], "blocks": []}
            blocks.append(cur)
            label = None
            if len(lines) > 1:
                add("p", lines[1:], new_page)
            continue

        if first in SUBHEADS[lang] and cur["kind"] in ("front", "subhead"):
            cur = {"kind": "subhead", "head": [first], "blocks": []}
            blocks.append(cur)
            label = None
            if len(lines) > 1:
                add("p", lines[1:], new_page)
            continue

        if first in label_of:
            label = label_of[first]
            if len(lines) > 1:
                cur["blocks"].append({"key": label, "lines": lines[1:]})
            continue
        if first.startswith(lab["note"]):
            add("note", [first[len(lab["note"]):].strip()] + lines[1:])
            continue
        if first.startswith(lab["byline"]):
            cur["blocks"].append({"key": "byline", "lines": [first]})
            continue

        add("p", lines, new_page)
    return blocks


def join_lines(lines: list[str], deva: bool = False) -> str:
    """Склеить перенесённые строки абзаца.

    Деванāгарӣ склеивается без пробела, если строка оборвана на огласовке или
    вираме: там разрыв прошёл внутри слова, а не по пробелу.
    """
    out = ""
    for line in lines:
        if not out:
            out = line
            continue
        if deva and unicodedata.category(out[-1]) in ("Mn", "Mc"):
            out += line
        elif out.endswith("-") and len(out) > 1 and not out[-2].isspace():
            # перенос внутри слова: «сама-» + «грӣва»
            out += line
        else:
            out += " " + line
    return re.sub(r"\s+", " ", out).strip()


def paragraphs(blocks: list[dict], key: str) -> list[str]:
    return [join_lines(b["lines"], deva=(key == "deva"))
            for b in blocks if b["key"] == key]


def split_verses(blocks: list[dict]) -> list[dict]:
    """Стих = деванāгарӣ + IAST + кириллица (+ «Перевод», если он есть)."""
    out: list[dict] = []
    cur: dict | None = None

    def close() -> None:
        nonlocal cur
        if cur:
            out.append(cur)
            cur = None

    for b in blocks:
        key = b["key"]
        if key in VERSE_KEYS:
            if key == "deva":
                close()
            cur = cur or {}
            cur[key] = join_lines(b["lines"], deva=(key == "deva"))
            if key == "cyr":
                cur["num"] = verse_number(cur)
                close()
        elif key == "trans":
            # «Перевод» стоит после стиха, а не внутри тройки
            if cur is None:
                if out and "trans" not in out[-1]:
                    out[-1]["trans"] = join_lines(b["lines"])
                continue
            cur["trans"] = join_lines(b["lines"])
            close()
        elif key == "p":
            close()  # абзац между стихами закрывает предыдущий стих
    close()
    return out


DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
NUM = re.compile(r"\|\|\s*(\d{1,2}|[०-९]{1,2})\s*"
                 r"([a-zA-Z\u0430-\u044f\u0410-\u042f])?\s*\|")


def verse_number(t: dict) -> str:
    """Номер стиха. В русском томе «18а» набрано кириллицей — приводим к 18a."""
    for key in ("iast", "cyr", "deva"):
        m = NUM.search(t.get(key, ""))
        if m:
            letter = (m.group(2) or "").lower()
            if letter in ("а", "А".lower()):
                letter = "a"
            return m.group(1).translate(DEVANAGARI_DIGITS) + letter
    raise SystemExit(f"у стиха не найден номер: {t.get('iast') or t.get('cyr') or t.get('deva')!r}")


def verse_cards(triples: list[dict], lang: str) -> list[dict]:
    out: list[dict] = []
    for t in triples:
        out.append({"type": "verse_card", "verses": t.get("num", ""), "sections": [
            {"type": "verse", "key": k, "lines": [t[k]]}
            for k in VERSE_KEYS if t.get(k)
        ]})
        if t.get("trans"):
            out.append({"type": "prose", "key": "trans",
                        "label": LABELS[lang]["trans"],
                        "paragraphs": [t["trans"]]})
    return out


def leading_paragraphs(blocks: list[dict], lang: str) -> list[dict]:
    """Абзацы перед стихами; абзац после стихов означал бы промах разбора."""
    out: list[dict] = []
    seen_verse = False
    for b in blocks:
        if b["key"] in VERSE_KEYS or b["key"] == "trans":
            seen_verse = True
        elif b["key"] == "p":
            if seen_verse:
                raise SystemExit(f"абзац после стихов ({lang}): {b['lines'][0][:60]!r}")
            out.append({"type": "p", "text": join_lines(b["lines"])})
    return out


def prose_blocks(blocks: list[dict], lang: str, keys: tuple[str, ...]) -> list[dict]:
    out: list[dict] = []
    for key in keys:
        got = paragraphs(blocks, key)
        if not got:
            continue
        if key == "words":
            out.append({"type": "words", "key": "words",
                        "label": LABELS[lang]["words"], "paragraphs": got})
        else:
            out.append({"type": "prose", "key": key,
                        "label": LABELS[lang].get(key, LABELS[lang]["trans"]),
                        "paragraphs": got})
    return out


def preface_names(lang: str) -> list[str]:
    """Список āсан из предисловия — с полной диакритикой, как в томе."""
    text = " ".join(clean_pages(PDF[lang]))
    starts = {"en": "The postures are ", "ru": "Ниже описаны: "}
    ends = {"en": ". The chapter closes", "ru": ". Затем следуют"}
    i = text.find(starts[lang])
    j = text.find(ends[lang], i)
    if i < 0 or j < 0:
        raise SystemExit(f"не найден список āсан в предисловии ({lang})")
    chunk = text[i + len(starts[lang]):j]
    chunk = re.sub(r"\s*\((?:possibly|возможно,)[^)]*\)", "", chunk)
    chunk = re.sub(r"\s+(?:and|и)\s+", ", ", chunk)
    return [p.strip().rstrip(".") for p in chunk.split(",") if p.strip()]


def split_head(line: str) -> tuple[int, str, str]:
    """«1. Вӣрāсана («Поза героя»)» → (1, «Вӣрāсана», «Поза героя»)."""
    m = re.match(r"^(\d{1,2})\.\s+(.*)$", line)
    if not m:
        raise SystemExit(f"не разобрать заголовок позы: {line!r}")
    num, rest = int(m.group(1)), m.group(2).strip()
    cut = min([i for i in (rest.find("("), rest.find("«")) if i >= 0] or [len(rest)])
    name, tail = rest[:cut].strip(), rest[cut:].strip()
    if tail.startswith("(") and tail.endswith(")"):
        tail = tail[1:-1].strip()
    elif tail.startswith("«") and tail.endswith("»"):
        pass
    else:
        tail = tail
    # кавычки вокруг пояснения не нужны: страница ставит пояснение отдельной строкой
    if len(tail) > 2 and tail[0] in "«“" and tail[-1] in "»”":
        tail = tail[1:-1].strip()
    return num, name, tail


SLUG = {"ā": "a", "ī": "i", "ū": "u", "ṛ": "ri", "ṝ": "ri", "ḷ": "l", "ḹ": "l",
        "ṅ": "n", "ñ": "n", "ṭ": "t", "ḍ": "d", "ṇ": "n", "ś": "sh", "ṣ": "sh",
        "ṃ": "m", "ḥ": "h", "’": "", "‘": "", "–": "-", "—": "-"}


def slugify(name: str) -> str:
    """Латинский сегмент адреса: одинаковый для русского и английского тома."""
    s = unicodedata.normalize("NFC", name).lower()
    for a, b in SLUG.items():
        s = s.replace(a, b)
    return "".join(ch for ch in s if ch.isascii() and ch.isalnum())


def json_texts(node, out: list[str]) -> list[str]:
    """Весь текст, который попал в данные (для проверки «ничего не потеряно»)."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("key", "type", "id", "iast", "number"):
                continue
            json_texts(v, out)
    elif isinstance(node, list):
        for v in node:
            json_texts(v, out)
    elif isinstance(node, str):
        out.append(node)
    return out


def lost_lines(data: dict, lang: str) -> list[str]:
    """Строки тома, которых нет в данных ни одной подстрокой."""
    haystack = re.sub(r"\s+", " ", " ".join(json_texts(data, [])))
    labels = set(LABELS[lang].values())
    heads = {SUBHEADS[lang][0], SUBHEADS[lang][1], SUBHEADS[lang][2],
             SUBHEADS[lang][3], DATING[lang]}
    lab = LABELS[lang]
    lost = []
    prev_page = -1
    for page, lines in page_blocks(PDF[lang]):
        new_page = page != prev_page
        prev_page = page
        first = lines[0]
        if first in labels or first in heads or first in VERSE_HEAD_HEADS(lang):
            lines = lines[1:]
        for line in lines:
            probe = re.sub(r"\s+", " ", line).strip()
            # заглавия разделов и āсан берутся из предисловия, а не из строки
            if re.match(r"^\d{1,2}\.\s", probe) or probe in heads:
                continue
            for prefix in (lab["note"], lab["byline"]):
                if probe.startswith(prefix):
                    probe = probe[len(prefix):].strip()
            if len(probe) > 3 and probe not in haystack:
                lost.append(probe)
    return lost


def VERSE_HEAD_HEADS(lang: str) -> set[str]:
    return {LABELS[lang]["chapter"], LABELS[lang]["appendixWord"],
            LABELS[lang]["notes"], LABELS[lang]["trans"]}


def missing_quotes(data: dict, lang: str) -> list[str]:
    """Цитаты сводки, которых нет в томе дословно."""
    haystack = re.sub(r"\s+", " ", " ".join(clean_pages(PDF[lang])))
    bad = []
    for item in data["items"]:
        for field in ("work", "when"):
            text = item[field][lang]
            if "“" not in text and lang:
                continue
            for q in re.findall(r"“([^”]+)”", text) or [text]:
                if re.sub(r"\s+", " ", q).strip() not in haystack:
                    bad.append(q[:60])
    return bad


# ------------------------------------------------------------------ сборка

def build() -> dict:
    parsed = {lang: walk(lang) for lang in ("ru", "en")}

    def of(lang: str, kind: str) -> list[dict]:
        return [b for b in parsed[lang] if b["kind"] == kind]

    if len(of("ru", "pose")) != len(of("en", "pose")):
        raise SystemExit("русский и английский тома дали разное число поз")

    names = {lang: preface_names(lang) for lang in ("ru", "en")}
    for lang in ("ru", "en"):
        if len(names[lang]) != len(of(lang, "pose")):
            raise SystemExit(f"список имён в предисловии ({lang}) не совпал с числом поз")
    if len(names["ru"]) != len(names["en"]):
        raise SystemExit("списки имён в двух томах разной длины")

    poses = []
    for i, (pr, pe) in enumerate(zip(of("ru", "pose"), of("en", "pose"))):
        num_ru, head_ru, gloss_ru = split_head(pr["head"][0])
        num_en, head_en, gloss_en = split_head(pe["head"][0])
        if num_ru != num_en or num_ru != i + 1:
            raise SystemExit(f"порядок поз не совпал на {i + 1}-й")
        for lang, head in (("ru", head_ru), ("en", head_en)):
            if head != names[lang][i]:
                print(f"  заголовок → имя из предисловия ({lang}, поза {num_ru}): "
                      f"«{head}» → «{names[lang][i]}»")
        triples = {lang: split_verses(of(lang, "pose")[i]["blocks"])
                   for lang in ("ru", "en")}
        if not triples["ru"] or len(triples["ru"]) != len(triples["en"]):
            raise SystemExit(f"{names['en'][i]}: число стихов в двух томах разное")
        if any(not t.get("num") for t in triples["ru"] + triples["en"]):
            raise SystemExit(f"{names['en'][i]}: у стиха не найден номер")

        text = {}
        for lang in ("ru", "en"):
            src = of(lang, "pose")[i]["blocks"]
            v = [t["num"] for t in triples[lang]]
            head = ("Стихи: " if lang == "ru" else "Verses: ") + ", ".join(v)
            text[lang] = [{"type": "p", "text": head}]
            text[lang] += verse_cards(triples[lang], lang)
            text[lang] += prose_blocks(src, lang, PARA_KEYS)
            notes = paragraphs(src, "note")
            if notes:
                text[lang].append({"type": "p", "text": " ".join(notes)})

        poses.append({
            "key": slugify(names["en"][i]),
            "iast": names["en"][i],
            "number": num_ru,
            "name": {lang: names[lang][i] for lang in ("ru", "en")},
            "gloss": {"ru": gloss_ru, "en": gloss_en},
            "verses": {lang: ", ".join(t["num"] for t in triples[lang])
                       for lang in ("ru", "en")},
            "text": text,
        })
    keys = [p["key"] for p in poses]
    if len(set(keys)) != len(keys):
        raise SystemExit("повторяющиеся латинские ключи поз")

    def about(lang: str, want_dating: bool) -> list[dict]:
        """Предисловие тома по порядку, с выносом «Датировки» в отдельную статью."""
        out: list[dict] = []
        for block in parsed[lang]:
            if block["kind"] == "front":
                title = block["head"][0]
                if not want_dating:
                    out.append({"type": "title", "text": title})
                for b in block["blocks"]:
                    if b["key"] == "byline":
                        if not want_dating:
                            out.append({"type": "byline", "text": b["lines"][0]})
                    else:
                        if not want_dating:
                            out += [{"type": "p", "text": t}
                                    for t in paragraphs([b], b["key"])]
            elif block["kind"] == "subhead":
                label = block["head"][0]
                dating = label == DATING[lang]
                if dating != want_dating:
                    continue
                if not want_dating:
                    out.append({"type": "subhead", "label": label})
                out += [{"type": "p", "text": t}
                        for t in paragraphs(block["blocks"], "p")]
        return out

    def prologue(lang: str) -> list[dict]:
        src = of(lang, "intro")
        if not src:
            return []
        blocks = src[0]["blocks"]
        lead = leading_paragraphs(blocks, lang)
        out = [{"type": "subhead", "label": src[0]["head"][0]}]
        out += lead
        out += verse_cards(split_verses(blocks), lang)
        out += prose_blocks(blocks, lang, ("words", "literal", "literary"))
        notes = paragraphs(blocks, "note")
        if notes:
            out.append({"type": "p", "text": " ".join(notes)})
        return out

    def appendix(lang: str) -> list[dict]:
        src = of(lang, "appendix")
        if not src:
            return []
        sec = src[0]
        out = [{"type": "subhead", "label": sec["head"][0]}]
        out += leading_paragraphs(sec["blocks"], lang)
        out += verse_cards(split_verses(sec["blocks"]), lang)
        return out

    def notes(lang: str) -> list[dict]:
        src = of(lang, "notes")
        if not src:
            return []
        return [{"type": "p", "text": t} for t in paragraphs(src[0]["blocks"], "p")]

    data = {
        "id": "matsyendra-samhita",
        "title": {"ru": "Матсйендра-сам̣хитā", "en": "Matsyendrasaṃhitā"},
        "asanasTitle": {"ru": "Āсаны третьей пат̣алы",
                        "en": "The āsanas of the third paṭala"},
        "notesTitle": {"ru": "Примечания к чтениям рукописи",
                       "en": "Notes on manuscript readings"},
        "about": {lang: about(lang, False) for lang in ("ru", "en")},
        "prologue": {lang: prologue(lang) for lang in ("ru", "en")},
        "dating": {lang: {"title": out, "blocks": about(lang, True)}
                   for lang, out in (("ru", "Датировка «Матсйендра-сам̣хитā»"),
                                     ("en", "Dating of the Matsyendrasaṃhitā"))},
        "datingSummary": DATING_SUMMARY,
        "appendix": {lang: appendix(lang) for lang in ("ru", "en")},
        "notes": {lang: notes(lang) for lang in ("ru", "en")},
        "closing": {lang: [CLOSING[lang]] for lang in ("ru", "en")},
        "poses": poses,
    }

    for lang in ("ru", "en"):
        lost = lost_lines(data, lang)
        if lost:
            raise SystemExit(f"в данные не попали {len(lost)} строк ({lang}):\n  "
                             + "\n  ".join(lost[:12]))
        bad = missing_quotes(DATING_SUMMARY, lang)
        if bad:
            raise SystemExit(f"цитаты сводки не найдены в томе ({lang}): {bad}")
        if CLOSING[lang] not in re.sub(r"\s+", " ", " ".join(clean_pages(PDF[lang]))):
            raise SystemExit(f"заключительная строка не найдена в томе ({lang})")
    return data


def unify_script(node, trail: str = "") -> list[str]:
    """Слово не может быть наполовину кириллицей, наполовину латиницей.

    В томах встречаются опечатки набора («кучe» с латинской e, «камаṭӣ» с
    латинской ṭ). Правка идёт по общей карте проекта — tools/script_mix.py, —
    и каждая замена печатается, чтобы её было видно.
    """
    changes: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            changes += unify_script(v, trail + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            changes += unify_script(v, trail + f"[{i}]")
    elif isinstance(node, str):
        hits = scan(node)
        if hits:
            fixed = fix_text(node)
            changes.append(f"  {trail}: {hits[0][0]!r} → "
                           f"{fix_text(hits[0][0])!r}")
            return changes + [fixed]  # последний элемент — новое значение
    return changes


def apply_script_fix(node, trail: str = "") -> list[str]:
    """Пройти данные и заменить смешанные слова (список правок — в отчёт)."""
    found: list[str] = []
    if isinstance(node, dict):
        for k in list(node.keys()):
            found += apply_script_fix(node[k], trail + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, (dict, list)):
                found += apply_script_fix(v, trail + f"[{i}]")
            elif isinstance(v, str) and scan(v):
                hit = scan(v)[0][0]
                node[i] = fix_text(v)
                found.append(f"  {trail}[{i}]: {hit!r} → {fix_text(hit)!r}")
    elif isinstance(node, str):
        pass
    return found


def main() -> int:
    data = build()
    fixes = apply_script_fix(data)
    for line in fixes:
        print("смешанное слово исправлено:" + line)
    # диакритика в терминах и названиях поз — по карте проекта
    data = script_mix.fix_value(data)   # одно слово — один алфавит
    data = diacritics.fix_document(data)
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if have != text:
            print("data/matsyendra-samhita.json расходится с томами: пересоберите")
            return 1
        print("data/matsyendra-samhita.json совпадает с томами")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f'поз: {len(data["poses"])} → {OUT.relative_to(ROOT)} '
          f'({len(text.encode("utf-8"))} байт)')
    for p in data["poses"]:
        print(f'  {p["number"]:2d}. {p["name"]["ru"]:24s} {p["iast"]:16s} '
              f'{p["key"]:16s} стихи {p["verses"]["ru"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
