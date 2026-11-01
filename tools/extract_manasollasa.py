# -*- coding: utf-8 -*-
"""«Ма̄насолла̄са» Суреш́варача̄рйи — the third treatise of the site.

The two PDFs in `sources/` are the same reference, one in Russian and one in
English. Nothing is rewritten here: the text is copied block by block and the
section structure is the one the PDFs print, so the site can switch language
without a second source.

Two things this volume needs that the earlier ones did not:

* the Devanāgarī is set in NotoSansDevanagari, whose embedded cmap is broken:
  a few glyphs at span boundaries come out as Latin letters or control
  characters («स्वस्ति\\x0f\\x10कं», «नृसि#ंहं», «विbदुश्शाक्तं»,
  «पश्चिÔमतानकम्»). `clean_deva` drops those stray glyphs only; every
  Devanāgarī letter stays where the edition put it. `python3
  extract_manasollasa.py` prints every character it dropped, with context, so
  the repair can be checked line by line;
* the treatise has no descriptions of āsanas at all: verses 24–26 name
  fourteen poses and sort them by deity (§6.3). A pose page of this treatise
  therefore carries the verse that names the pose and that classification —
  and nothing else.

Run: python3 extract_manasollasa.py ../data/manasollasa.json
"""
import difflib
import html
import json
import re
import sys
from pathlib import Path

import pymupdf

import deva as deva_lib
import translit

import sanskrit
from common import clean, merge_runs, runs_html

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
PDFS = {
    "ru": "Ма̄насолла̄са. Āсаны (полная справка с разбором асан).pdf",
    "en": "Manasollasa. Āsanas (complete reference).pdf",
}

DEVA_LO, DEVA_HI = 0x0900, 0x097F
DEVANAGARI_FONT = "NotoSansDevanagari"
MONO_FONT = "Mono"

# Punctuation that really is printed inside Devanāgarī passages.
KEEP_PUNCT = "…—–,/"

# A comma or a full stop inside a Devanāgarī word («विदुर्यो,गिन») is one of
# the broken glyphs: real punctuation in these passages is always followed by
# a space («…मासाङ्गम्, तदुपाय…»).
PUNCT_NEEDS_SPACE = ",."

_DROPPED = []

# §0 and §4.4 of both volumes print, on purpose, the wrong readings produced by
# machine recognition of the 1895 scan («खरस्तिकं», «पश्यं», «धारं»,
# «नृपिहादि!»). Those lines are quotations of garbage and are kept exactly as
# printed; everywhere else the Devanāgarī is the correct one and is repaired.
VERBATIM_MARKS = ("खरस्ति", "नृपिहा", "पश्यं", "धारं")


def is_deva(ch):
    return DEVA_LO <= ord(ch) <= DEVA_HI


def clean_deva(text):
    """Drop the glyphs the broken cmap substitutes; keep every letter."""
    out = []
    n = len(text)
    for i, ch in enumerate(text):
        if is_deva(ch) or ch in " \u00a0":
            out.append(" " if ch == "\u00a0" else ch)
            continue
        if ch in KEEP_PUNCT:
            out.append(ch)
            continue
        code = ord(ch)
        if code < 32 or 0x7F <= code <= 0x9F:
            _DROPPED.append((ch, text[max(0, i - 10):i + 10]))
            continue
        left = next((text[j] for j in range(i - 1, -1, -1) if text[j] != " "), "")
        right = next((text[j] for j in range(i + 1, n) if text[j] != " "), "")
        if left and right and is_deva(left) and is_deva(right):
            _DROPPED.append((ch, text[max(0, i - 10):i + 10]))
            continue
        out.append(ch)
    return "".join(out)


# --------------------------------------------------------------- line level

def span_text(span):
    return span["text"]


def clean_runs(runs):
    """Repair the Devanāgarī of one line, keeping its run structure.

    The broken glyphs sit at span boundaries as often as inside a span, and
    two of them can stand side by side («धृ¡tतिः», «वार्त्तिÚKक»). A whole run
    of characters that are neither Devanāgarī nor printed punctuation, and
    that has Devanāgarī on both sides, is therefore dropped as one. Control
    characters are never text and go wherever they stand.
    """
    if not runs:
        return runs
    flat, owner = "", []
    for i, (text, _b, _i) in enumerate(runs):
        flat += text
        owner.extend([i] * len(text))
    n = len(flat)
    gone = set()

    def invisible(ch):
        code = ord(ch)
        return code < 32 or 0x7F <= code <= 0x9F

    def keepable(idx, ch):
        if is_deva(ch) or ch in " \u00a0":
            return True
        if ch in PUNCT_NEEDS_SPACE:
            return idx + 1 >= n or flat[idx + 1] in " \u00a0"
        return ch in KEEP_PUNCT

    def significant(start_at, step):
        j = start_at
        while 0 <= j < n:
            ch = flat[j]
            if j not in gone and ch != " " and not invisible(ch):
                return ch
            j += step
        return ""

    for idx, ch in enumerate(flat):
        if invisible(ch):
            gone.add(idx)

    idx = 0
    while idx < n:
        ch = flat[idx]
        if idx in gone or keepable(idx, ch):
            idx += 1
            continue
        end = idx
        while end + 1 < n:
            nxt = flat[end + 1]
            if end + 1 in gone or keepable(end + 1, nxt):
                break
            end += 1
        left, right = significant(idx - 1, -1), significant(end + 1, 1)
        if left and right and is_deva(left) and is_deva(right):
            for j in range(idx, end + 1):
                gone.add(j)
                _DROPPED.append((flat[j], flat[max(0, j - 10):j + 10]))
        idx = end + 1

    buckets = [[] for _ in runs]
    for idx, ch in enumerate(flat):
        if idx not in gone:
            buckets[owner[idx]].append(ch)
    return [("".join(b), runs[i][1], runs[i][2]) for i, b in enumerate(buckets)]


def clean_text(text):
    """The broken-glyph repair of clean_runs, applied to a bare string."""
    return "".join(t for t, _b, _i in clean_runs([(text, False, False)]))


def strip_controls(text):
    """Invisible code points never print; they only break the text."""
    return "".join(ch for ch in text
                   if not (ord(ch) < 32 or 0x7F <= ord(ch) <= 0x9F
                           or ch in "\ufe0e\ufe0f\u200b\u200e\u200f"))


def verbatim_deva(raw):
    return any(mark in raw for mark in VERBATIM_MARKS)


def visual_lines(page, skip_rects):
    """Lines of one page, tables and the page number excluded.

    Lines that share a baseline (a list number and its text, a bullet and the
    first word of its item) are merged into one visual line.
    """
    raw = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if span_text(s)]
            if not spans:
                continue
            x0 = min(s["bbox"][0] for s in spans)
            x1 = max(s["bbox"][2] for s in spans)
            y0, y1 = line["bbox"][1], line["bbox"][3]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if any(r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 for r in skip_rects):
                continue
            size = max(s["size"] for s in spans)
            raw_deva = "".join(x["text"] for x in spans
                               if DEVANAGARI_FONT in x["font"])
            runs = [(strip_controls(s["text"]) if verbatim_deva(raw_deva) else s["text"],
                     "Bold" in s["font"], "Italic" in s["font"]) for s in spans]
            runs = clean_runs(runs) if not verbatim_deva(raw_deva) else \
                [r for r in runs if r[0]]
            if not runs:
                continue
            raw.append({"runs": runs, "x0": x0, "x1": x1, "y0": y0, "y1": y1,
                        "size": round(size, 1), "font": spans[0]["font"],
                        "page": page.number})
    raw.sort(key=lambda l: (round(l["y0"], 0), l["x0"]))

    merged = []
    for line in raw:
        if merged and abs(line["y0"] - merged[-1]["y0"]) < 3.0:
            last = merged[-1]
            last["runs"].append((" ", False, False))
            last["runs"].extend(line["runs"])
            last["x1"] = max(last["x1"], line["x1"])
            last["y1"] = max(last["y1"], line["y1"])
            continue
        merged.append(dict(line))
    for line in merged:
        line["runs"] = merge_runs(line["runs"])
        line["text"] = "".join(r[0] for r in line["runs"]).strip()
    return [l for l in merged if l["text"]]


def class_of(line):
    if MONO_FONT in line["font"]:
        return "mono"
    if line["size"] < 8.2:
        if line["y0"] > 760 and line["text"].strip().isdigit():
            return "footer"
        return "small"
    if MONO_FONT in line["font"]:
        return "mono"
    if DEVANAGARI_FONT in line["font"]:
        text = "".join(r[0] for r in line["runs"])
        deva = sum(1 for ch in text if is_deva(ch))
        if deva >= 0.5 * max(1, len(text.strip())):
            return "deva"
    if line["size"] >= 13.5:
        return "h2"
    if line["size"] >= 11.5:
        return "h3"
    if line["size"] < 9.0:
        return "small"          # a table row find_tables() did not box
    if line["size"] < 9.9:
        return "quote"
    return "body"


# ------------------------------------------------------------------- tables

def dedupe_rows(rows):
    """Drop a row that repeats an earlier one.

    A table broken over a page boundary is read twice by the model: the second
    copy is the same row with the page break left inside it («Алма̄р а»).
    """
    out, seen = [], []
    for row in rows:
        key = re.sub(r"\s+", "", "".join(row))
        if not any(c.strip() for c in row):
            continue
        if any(difflib.SequenceMatcher(None, key, k).ratio() > 0.95
               for k in seen):
            continue
        seen.append(key)
        out.append(row)
    return out


def read_table(page, table):
    """Rows of a detected table, one word at a time.

    Columns are the vertical bands between the left edges of the first row's
    cells, so a word that overflows its cell is still read in the column it
    belongs to.
    """
    xs = []
    for cell in table.rows[0].cells:
        if cell is None:
            continue
        x = round(cell[0], 1)
        if not xs or x > xs[-1] + 4:
            xs.append(x)
    xs.append(table.bbox[2] + 1)
    words = page.get_text("words")
    rows = []
    for row in table.rows:
        cells = [[] for _ in xs[:-1]]
        for cell in row.cells:
            if cell is None:
                continue
            x0, y0, x1, y1 = cell
            for w in words:
                wx0, wy0, wx1, wy1, text = w[0], w[1], w[2], w[3], w[4]
                if not (x0 - 1 <= wx0 < x1 + 1 and y0 - 1 <= wy0 < y1 + 1):
                    continue
                idx = 0
                for i in range(len(xs) - 1):
                    if wx0 >= xs[i] - 1:
                        idx = i
                cells[idx].append((wy0, wx0, text, wy1))
        out = []
        for cell in cells:
            cell.sort(key=lambda w: (w[0], w[1]))
            lines, cur, top = [], [], None
            for y, _x, word, _y1 in cell:
                if top is not None and y - top > 3.0:
                    lines.append(" ".join(w[2] for w in sorted(cur, key=lambda w: w[1])))
                    cur, top = [], None
                if top is None:
                    top = y
                cur.append((y, w if False else _x, word))
            if cur:
                lines.append(" ".join(w[2] for w in sorted(cur, key=lambda w: w[1])))
            out.append(clean_text(strip_controls(" ".join(lines))).strip())
        # A table broken over a page boundary is read twice by the model: the
        # second copy is the same row with the page break left inside it.
        rows.append(out)
    return dedupe_rows(rows)


# The two manuscript tables of §4.2 are set in columns four centimetres wide;
# no reader can put their words back together (the model returns one column
# inside another). They are transcribed here from the page images of both
# volumes and replaced only when the broken rows are recognised.
MANUSCRIPT_ROWS = {
    "ru": [
        ["Санскритский университет имени Кавикулагуру Калидасы, Рамтек "
         "(Махараштра), Научно-информационный центр им. Джнянаяоги Шриканта "
         "Джичкара",
         "M-1192 «Ма̄насолла̄са Суреш́варача̄рйи»",
         "18 листов, 600 точек на дюйм, оцифровка в рамках государственной "
         "программы «На̄мами», лицензия CC0, файл 68,7 МБ; деванагари; "
         "прочитан колофон: датировки нет, см. §4.4",
         "archive.org/details/NeGr_m-1192-manasollas-of-sureshvaracharya-"
         "kavikulguru-kalidas-sanskrit-university-ramtek-collection"],
        ["Фонд «Дхарма̄ртха Траст» при храме Рагхунатха, Джамму (коллекция "
         "«Ганготри»)",
         "Алма̄ра 27, полка 1, № 6029",
         "125 листов, 600 точек на дюйм, лицензия CC0, файл 63,2 МБ; "
         "деванагари; в колофоне есть год эры ш́ака, число не прочитано, "
         "см. §4.5",
         "archive.org/details/ManasollasaAlm27Shlf16029DevanagariTantra"],
        ["Государственная библиотека восточных рукописей, Ченнаи "
         "(бывш. Мадрас)",
         "номер не установлен",
         "каталоги оцифрованы («Описательный каталог», т. I–13, 1901–1911 "
         "и далее), но в проверенных томах нужная статья не найдена; по "
         "Ауфрехту текст каталогизирован под «Дакшин̣а̄мӯрти-стотра»",
         "—"],
    ],
    "en": [
        ["Kavikulguru Kalidas Sanskrit University, Ramtek (Maharashtra), "
         "Jnanayogi Dr Shrikant Jichkar Knowledge Resource Centre",
         "M-1192, \"Manasollasa of Sureshvaracharya\"",
         "18 leaves, 600 dpi, digitised under the state Namami programme, "
         "licence CC0, file 68.7 MB; Devanagari; colophon read: no date, "
         "see §4.4",
         "archive.org/details/NeGr_m-1192-manasollas-of-sureshvaracharya-"
         "kavikulguru-kalidas-sanskrit-university-ramtek-collection"],
        ["Dharma-rtha Trust at the Raghunath temple, Jammu (Gangotri "
         "collection)",
         "Almari 27, shelf 1, no. 6029",
         "125 leaves, 600 dpi, licence CC0, file 63.2 MB; Devanagari; the "
         "colophon contains a Shaka-era year, the number not read, see §4.5",
         "archive.org/details/ManasollasaAlm27Shlf16029DevanagariTantra"],
        ["Government Oriental Manuscripts Library, Chennai (formerly Madras)",
         "number not established",
         "the catalogues are digitised (Descriptive Catalogue, vols 1–13, "
         "1901–1911 and later), but the relevant entry has not been found in "
         "the volumes checked; according to Aufrecht the text is catalogued "
         "under \"Dakshinamurti-stotra\"",
         "—"],
    ],
}
MANUSCRIPT_HEAD = {"ru": ["Собрание", "Шифр", "Метаданные", "Ссылка"],
                   "en": ["Collection", "Shelf mark", "Metadata", "Link"]}


def manuscript_table(lang, broken):
    """Recognise the collapsed §4.2 table and hand back the printed one."""
    if len(broken) < 2:
        return None
    joined = " ".join(" ".join(r) for r in broken)
    marks = ("Калидасы", "Рамтек") if lang == "ru" else ("Kalidas", "Ramtek")
    if not all(m in joined for m in marks):
        return None
    return [MANUSCRIPT_HEAD[lang]] + MANUSCRIPT_ROWS[lang]


# ---------------------------------------------------------------- assembling

TOP_HEAD = re.compile(r"^(\d{1,2})\.\s")
NUM_ITEM = re.compile(r"^(\d{1,2})\.\s")


class Doc:
    def __init__(self, lang):
        self.lang = lang
        self.units = []
        self.title = ""
        self.subtitle = []
        self.sections = []
        self._build()

    # -- reading ---------------------------------------------------------
    def _build(self):
        pdf = pymupdf.open(SRC / PDFS[self.lang])
        stream = []
        for page in pdf:
            boxes, tables = [], []
            try:
                found = page.find_tables()
            except Exception:                                   # pragma: no cover
                found = None
            if found:
                for table in found.tables:
                    rect = pymupdf.Rect(table.bbox)
                    cells = [c for r in table.rows for c in r.cells if c]
                    if not cells:
                        continue
                    boxes.append(rect)
                    tables.append({"rect": rect, "table": table, "page": page.number})
            for t in tables:
                stream.append((page.number, t["rect"].y0,
                               {"kind": "table", "item": t, "page": page}))
            verbatim_left = 0
            for line in visual_lines(page, boxes):
                raw = "".join(r[0] for r in line["runs"])
                if verbatim_deva(raw):
                    verbatim_left = 2
                    line["verbatim"] = True
                elif verbatim_left:
                    verbatim_left -= 1
                    line["verbatim"] = True
                else:
                    line["verbatim"] = False
                stream.append((page.number, line["y0"],
                               {"kind": "line", "item": line}))
        stream.sort(key=lambda t: (t[0], t[1]))

        # monospaced lines: a path or a URL inside a sentence stays in the
        # sentence, a block of them (§8, the Python snippet) stays code
        cls_of = {}
        for i, (_pn, _y, entry) in enumerate(stream):
            if entry["kind"] != "line":
                continue
            cls = class_of(entry["item"])
            if cls == "mono":
                def same_run(k):
                    return (0 <= k < len(stream) and stream[k][2]["kind"] == "line"
                            and class_of(stream[k][2]["item"]) == "mono")
                def gap_before(k):
                    return (stream[k][2]["item"]["y0"]
                            - stream[k - 1][2]["item"]["y1"])

                start = i
                while same_run(start - 1) and gap_before(start) < 8:
                    start -= 1
                end = i
                while same_run(end + 1) and gap_before(end + 1) < 8:
                    end += 1
                cls = "code" if end - start + 1 >= 3 else "body"
            cls_of[i] = cls

        mode = None          # None | "para" | "list" | "note"
        para = None
        para_class = None
        items = []
        last = None
        head_lines = []

        def flush():
            nonlocal para, para_class, mode, items, head_lines, items_kind
            if head_lines:
                text = " ".join(l["text"] for l in head_lines)
                n = TOP_HEAD.match(text)
                self.sections.append((n.group(1) if n else "", text))
                if not self.title:
                    self.title = text
                self.units.append({"type": para_class or "h2", "html": " ".join(
                    runs_html(l["runs"]) for l in head_lines)})
                head_lines = []
            if para is not None:
                self._emit(para, para_class)
                para, para_class, mode = None, None, None
            if items:
                unit = {"type": "list", "items": items}
                if items_kind == "num":
                    unit["ordered"] = True
                    unit["start"] = items_start
                self.units.append(unit)
                items = []

        items_kind = None
        items_start = 1
        for idx, (page_no, _y, entry) in enumerate(stream):
            if entry["kind"] == "table":
                flush()
                self._table(entry["item"], entry["page"])
                last = None
                continue
            line = entry["item"]
            cls = cls_of.get(idx, class_of(line))
            if cls == "footer":
                continue
            gap = None if last is None else line["y0"] - last["y1"]

            if cls in ("h2", "h3"):
                if (head_lines and para_class == cls
                        and line["page"] == head_lines[-1]["page"]
                        and line["y0"] - head_lines[-1]["y0"] < line["size"] * 1.7):
                    head_lines.append(line)
                    last = line
                    continue
                flush()
                head_lines = [line]
                para_class = cls
                last = line
                continue
            if head_lines:
                flush()

            # lists: a bullet or a numbered item, then its wrapped lines
            starts_item, kind = False, None
            if cls == "body" and line["text"].startswith("•"):
                starts_item, kind = True, "bullet"
            elif cls == "body" and line["x0"] < 62 and NUM_ITEM.match(line["text"]) \
                    and (last is None or gap is None or gap > 3.5):
                starts_item, kind = True, "num"
            if starts_item:
                if para is not None or head_lines:
                    flush()
                if not items:
                    items_kind = kind
                    m = NUM_ITEM.match(line["text"])
                    items_start = int(m.group(1)) if m else 1
                runs = strip_bullet(line["runs"]) if kind == "bullet" \
                    else strip_number(line["runs"])
                items.append({"html": runs_html(runs), "level": 1,
                              "_x0": line["x0"]})
                mode = "list"
                last = line
                continue
            if mode == "list" and cls == "body" and last is not None and items:
                tail = last["runs"][-1][0][-1:]
                indented = line["x0"] > items[-1]["_x0"] + 5
                single_token = " " not in line["text"].strip() and not is_lead(line)
                limit = 14.0 if single_token else 8.5
                unfinished = _plain(items[-1]["html"]).rstrip()[-1:] in ":,;(—"
                if unfinished:
                    indented, single_token, limit = True, True, 20.0
                cont = (indented or single_token) and (
                    (line["page"] == last["page"] and gap is not None and gap < limit)
                    or (line["page"] == last["page"] + 1 and last["x1"] > 430
                        and tail not in ".!?:;»”"))
                if cont and items:
                    items[-1]["html"] += joiner(items[-1]["html"], line) \
                        + runs_html(line["runs"])
                    last = line
                    continue
                flush()

            if para is not None and cls == para_class:
                same_page = line["page"] == para["lines"][-1]["page"]
                if same_page:
                    limit = {"body": 8.0, "quote": 6.2, "deva": 6.0,
                             "code": 6.0, "small": 6.0}.get(cls, 6.0)
                    if gap is not None and gap < limit:
                        single = (" " not in line["text"].strip()
                                  and not is_lead(line) and gap < 14.0
                                  and para["lines"][-1]["runs"][-1][0].rstrip()[-1:]
                                  not in ".!?:;»”")
                        # a continuation line is never set right of the
                        # paragraph's first line: that one carries the indent
                        if cls == "deva" or line["x0"] <= para["x0"] + 2.0 \
                                or single:
                            para["lines"].append(line)
                            last = line
                            continue
                else:
                    tail = para["lines"][-1]["runs"][-1][0].rstrip()
                    if para["lines"][-1]["x1"] > 430 and tail[-1:] not in ".!?:;»”":
                        para["lines"].append(line)
                        last = line
                        continue
            flush()
            para = {"lines": [line], "x0": line["x0"]}
            para_class = cls
            mode = "para"
            last = line
        flush()

    # -- units -----------------------------------------------------------
    def _emit(self, para, cls):
        lines = para["lines"]
        if cls == "h3":
            self.units.append({"type": "h3", "html": " ".join(
                runs_html(l["runs"]) for l in lines)})
            return
        if cls == "deva":
            self.units.append({"type": "deva",
                               "lines": [clean(l["text"]) for l in lines]})
            return
        if cls == "code":
            self.units.append({"type": "code",
                               "text": "\n".join(l["text"] for l in lines)})
            return
        if cls == "quote":
            html_par = paragraph_html(lines)
            last_unit = self.units[-1] if self.units else None
            if last_unit and last_unit["type"] == "quote" and last_unit.get("_open"):
                last_unit["paragraphs"].append(html_par)
            else:
                self.units.append({"type": "quote", "paragraphs": [html_par],
                                   "_open": True})
            return
        if cls == "small":
            self.units.append({"type": "p", "html": " ".join(
                runs_html(l["runs"]) for l in lines)})
            return
        first = lines[0]["text"]
        if len(lines) == 1 and para["lines"][0]["page"] == 0 and not self.units:
            return
        for unit in self.units:
            unit.pop("_open", None)
        self.units.append({"type": "p", "html": paragraph_html(lines)})

    def _table(self, item, page):
        for unit in self.units:
            unit.pop("_open", None)
        rows = [[clean(c) for c in row] for row in read_table(page, item["table"])]
        if not rows:
            return
        if len(rows[0]) > 2 and all(not row[0].strip() for row in rows):
            rows = [row[1:] for row in rows]
        fixed = manuscript_table(self.lang, rows)
        if fixed:
            rows = fixed
        prev = self.units[-1] if self.units else None
        if (prev and prev["type"] == "table" and item["rect"].y0 < 130
                and prev.get("_page") == page.number - 1):
            prev["rows"] = dedupe_rows(prev["rows"] + rows)
            prev["_page"] = page.number
            return
        self.units.append({"type": "table", "rows": rows,
                           "_page": page.number})

    # -- selectors -------------------------------------------------------
    def bucket(self, numbers):
        """Units of the given top-level sections, in order, without the h2s."""
        out = []
        keep = False
        for unit in self.units:
            if unit["type"] == "h2":
                n = TOP_HEAD.match(_plain(unit["html"]))
                keep = bool(n) and n.group(1) in numbers
                continue
            if keep:
                out.append(unit)
        return out

    def paragraph(self, needle, start=0):
        """First paragraph unit whose text contains `needle`."""
        for unit in self.units[start:]:
            text = _plain(unit.get("html") or " ".join(unit.get("paragraphs", [])))
            if needle in text:
                return text
        return ""


URL_WORD = re.compile(r"[A-Za-z0-9]\.[A-Za-z]")


def joiner(html_so_far, line):
    """A line that only continues a broken URL is glued on without a space."""
    text = _plain(html_so_far).rstrip()
    token = line["text"].strip()
    last_word = text.split(" ")[-1] if text else ""
    url = bool(last_word) and (
        last_word.endswith(("-", "/")) or "/" in last_word
        or bool(URL_WORD.search(last_word)))
    if " " not in token and url:
        return ""
    return " "


def is_lead(line):
    """A short bold line opens a list or a passage; it never continues one."""
    text = line["text"].strip()
    return len(text) < 120 and all(r[1] for r in line["runs"] if r[0].strip())


def paragraph_html(lines):
    out = ""
    for line in lines:
        piece = runs_html(line["runs"])
        out = out + joiner(out, line) + piece if out else piece
    return out


def strip_number(runs):
    """Drop the «1.» that opens a numbered item: the list carries the count."""
    out = list(runs)
    while out and not out[0][0].strip():
        out.pop(0)
    if out:
        text, bold, italic = out[0]
        out[0] = (re.sub(r"^\s*\d{1,2}\.\s*", "", text), bold, italic)
    return [(t, b, i) for t, b, i in out if t]


def strip_bullet(runs):
    """Drop the «•» that opens a list item, inside or outside the emphasis."""
    out = list(runs)
    while out and not out[0][0].strip(" •\u00a0"):
        out.pop(0)
    if out:
        text, bold, italic = out[0]
        text = re.sub(r"^\s*•\s*", "", text)
        out[0] = (text, bold, italic)
    return out


def _plain(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or ""))


def fold_code(units):
    """A code sample printed between the steps of a numbered list.

    §8 prints a three-step procedure, then the Python snippet the third step
    asks for, then the fourth step. The snippet is not a paragraph of its own:
    it belongs to the step that introduces it, so the list stays one list.
    """
    out, i = [], 0
    while i < len(units):
        unit = units[i]
        if (unit["type"] == "list" and unit.get("ordered")
                and i + 2 < len(units)
                and units[i + 1]["type"] == "code"
                and units[i + 2]["type"] == "list"
                and units[i + 2].get("ordered")
                and units[i + 2].get("start", 1)
                == unit.get("start", 1) + len(unit["items"])):
            unit["items"][-1]["code"] = units[i + 1]["text"]
            unit["items"].extend(units[i + 2]["items"])
            out.append(unit)
            i += 3
            continue
        out.append(unit)
        i += 1
    return out


FRAGMENT = re.compile(r"^[A-Za-z0-9./:\\-_()]+$")


def is_fragment(text):
    """A line that is only the wrapped tail of an address (§10)."""
    t = text.strip()
    if not t or " " in t:
        return False
    return len(t) <= 3 or "/" in t or "htm" in t.lower()


def _append_fragment(target, frag):
    text = target["html"]
    tail = _plain(text).rstrip()
    last = tail.split(" ")[-1] if tail else ""
    glue = (frag[:1] in ".,;:)]" or frag.startswith("-")
            or "/" in last or last.endswith("-") or len(frag) <= 1)
    target["html"] = text + ("" if glue else " ") + html.escape(frag)


def glue_fragments(units):
    """Attach the tails of a wrapped web address back to their line.

    In §10 the address of the Dasgupta volume is printed across a page break
    and then wrapped twice («…/doc209874.htm», «l», «)»). Those three lines
    are one address and belong inside the bibliographic entry.
    """
    out = []
    for unit in units:
        if unit["type"] == "p" and out:
            text = _plain(unit["html"])
            prev = out[-1]
            if is_fragment(text):
                if prev["type"] == "list" and prev.get("items"):
                    _append_fragment(prev["items"][-1], text)
                    continue
                if prev["type"] == "p":
                    _append_fragment(prev, text)
                    continue
                if prev["type"] == "quote" and prev.get("paragraphs"):
                    holder = {"html": prev["paragraphs"][-1]}
                    _append_fragment(holder, text)
                    prev["paragraphs"][-1] = holder["html"]
                    continue
        out.append(unit)
    return out


SPLIT_ABBREV = re.compile(r"(?:^|\s)(\S{1,3})\.$")


def join_quote_paragraphs(units):
    """Put back a quotation the volume breaks after an abbreviation.

    «…колеблется от 6 в. / до н. э. …» is one sentence: the line ends with
    «в.» and the next paragraph opens in lower case. A real break never does.
    """
    for unit in units:
        if unit["type"] != "quote" or len(unit.get("paragraphs", [])) < 2:
            continue
        out = [unit["paragraphs"][0]]
        for part in unit["paragraphs"][1:]:
            prev = out[-1].rstrip()
            m = SPLIT_ABBREV.search(prev)
            low = part.lstrip()[:1]
            if m and low and low.islower():
                out[-1] = prev + " " + part.lstrip()
            else:
                out.append(part)
        unit["paragraphs"] = out
    return units


def merge_lists(units):
    """One list stays one list even where a fragment was taken out of it."""
    out = []
    for unit in units:
        prev = out[-1] if out else None
        if (prev and prev["type"] == "list" and unit["type"] == "list"
                and bool(prev.get("ordered")) == bool(unit.get("ordered"))
                and (not unit.get("ordered")
                     or unit.get("start", 1) == prev.get("start", 1)
                     + len(prev["items"]))):
            prev["items"].extend(unit["items"])
            continue
        out.append(unit)
    return out


def tidy(units):
    """Drop the scratch keys the assembler uses and close quote clusters."""
    out = []
    for unit in units:
        unit = {k: v for k, v in unit.items() if not k.startswith("_")}
        if unit["type"] == "list":
            unit["items"] = [{k: v for k, v in item.items()
                              if not k.startswith("_")}
                             for item in unit["items"]]
        if unit["type"] == "table":
            unit["cols"] = len(unit["rows"][0]) if unit["rows"] else 0
        out.append(unit)
    for i, unit in enumerate(out):
        if unit["type"] == "quote":
            unit.pop("_open", None)
        if unit["type"] == "p" and not unit["html"].strip():
            out[i] = None
    return merge_lists(fold_code(glue_fragments(
        join_quote_paragraphs([u for u in out if u]))))

# ---------------------------------------------------------------- site data

LABELS = {
    "ru": {
        "deva": "Деванāгарӣ",
        "iast": "IAST",
        "cyr": "Кириллическая транслитерация",
        "verse": "Стих",
        "translation": "Перевод",
        "class": "6.3. Комментарий к стиху 24 — классификация по божествам",
    },
    "en": {
        "deva": "Devanāgarī",
        "iast": "IAST",
        "cyr": "Cyrillic transliteration",
        "verse": "Verse",
        "translation": "Translation",
        "class": "6.3. The Commentary on Verse 24 — the Classification by Deity",
    },
}

# The verse names fifteen postures in four lines: four brāhma, four vaiṣṇava,
# four raudra, one śākta (yoni), one śaiva (paścima-tānaka), and — the sixth
# category of §6.3, «the supportless one» — nirālambana.
POSES = [
    ("svastikasana", "Svastika", "brahma", "IX.24"),
    ("gomukhasana", "Gomukha", "brahma", "IX.24"),
    ("padmasana", "Padma", "brahma", "IX.24"),
    ("hamsasana", "Haṃsa", "brahma", "IX.24"),
    ("nrisimhasana", "Nṛsiṃha", "vaishnava", "IX.25"),
    ("garudasana", "Garuḍa", "vaishnava", "IX.25"),
    ("kurmasana", "Kūrma", "vaishnava", "IX.25"),
    ("nagasana", "Nāga", "vaishnava", "IX.25"),
    ("virasana", "Vīra", "raudra", "IX.25"),
    ("mayurasana", "Mayūra", "raudra", "IX.25"),
    ("vajrasana", "Vajra", "raudra", "IX.25"),
    ("siddhasana", "Siddha", "raudra", "IX.25"),
    ("yoniasana", "Yoni", "shakta", "IX.25"),
    ("pashchimatana", "Paścima-tānaka", "shaiva", "IX.25"),
    ("niralambana", "Nirālambana", "niralambana", "IX.26"),
]

# group -> (verse lines, translation sentence, 1978 sentence, class clause)
GROUP_INDEX = {
    "brahma": ([0], 0, 0, 1),
    "vaishnava": ([1], 1, 1, 2),
    "raudra": ([2], 2, 2, 3),
    "shakta": ([3], 3, 3, 4),
    "shaiva": ([3], 3, 4, 5),
    "niralambana": ([4, 5], 4, 5, None),
}

GROUP_GLOSS = {
    "brahma": ("brāhma-āsana", "Brāhma āsana"),
    "vaishnava": ("vaiṣṇava-āsana", "Vaiṣṇava āsana"),
    "raudra": ("raudra-āsana", "Raudra āsana"),
    "shakta": ("śākta-āsana", "Śākta āsana"),
    "shaiva": ("śaiva-āsana", "Śaiva āsana"),
    "niralambana": ("nirālambana-āsana", "Nirālambana āsana"),
}

# A full stop after a digit («24-26.») or after a printed abbreviation
# («букв.», «с.», «p.») does not end a sentence in these two volumes.
SENT_END = re.compile(r"[.!?](?=\s+[«„“(А-ЯA-Z])")
ABBREV = {"букв", "с", "г", "изд", "см", "т", "стр", "разд", "гл", "кн",
          "p", "pp", "vol", "ed", "lit", "cf", "col", "no", "ch"}


def split_sentences(text):
    """Cut a printed paragraph into its sentences, changing no character."""
    text = text.strip()
    out, start = [], 0
    for m in SENT_END.finditer(text):
        before = text[start:m.start()]
        words = before.split()
        word = words[-1] if words else ""
        if word and (word[-1].isdigit() or word.strip("(").lower() in ABBREV):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    out.append(text[start:].strip())
    return [p for p in out if p]


def unwrap(text):
    """Drop the quotation marks that enclose a whole translated paragraph."""
    text = re.sub(r"^\s*(Перевод|Translation)\s*:\s*", "", text).strip()
    for open_q, close_q in (("«", "»"), ("“", "”"), ('"', '"')):
        if text.startswith(open_q) and text.endswith(close_q):
            text = text[1:-1]
        elif text.startswith(open_q) and text.endswith(close_q + "."):
            text = text[1:-2] + "."
    return text.strip()


def quoted_segments(paragraphs):
    """Each «…» or “…” of a quotation, without its quotation marks."""
    out = []
    for part in paragraphs:
        found = re.findall(r'«[^»]*»|“[^”]*”|"[^"]*"', part)
        if not found:
            found = [part]
        for seg in found:
            seg = unwrap(seg)
            for sentence in split_sentences(seg):
                out.append(sentence)
    return out


def split_clauses(lines):
    """Cut the Devanāgarī commentary into its clauses at the dandas."""
    text = " ".join(lines)
    parts = re.split(r"(?<=[।॥])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def block(unit):
    """One unit of the extractor as one block of the site."""
    kind = unit["type"]
    if kind in ("h2", "h3", "p"):
        return {"type": kind, "html": unit["html"]}
    if kind == "deva":
        return {"type": "deva", "lines": unit["lines"]}
    if kind == "quote":
        return {"type": "quote", "paragraphs": unit["paragraphs"]}
    if kind == "list":
        out = {"type": "list", "items": unit["items"]}
        if unit.get("ordered"):
            out["ordered"] = True
            out["start"] = unit.get("start", 1)
        return out
    if kind == "table":
        return {"type": "table", "rows": unit["rows"]}
    if kind == "code":
        return {"type": "code", "text": unit["text"]}
    return {"type": "p", "html": unit.get("html", "")}


def section_units(units, keep, drop_h2=False, drop_h3=()):
    """Units of the named top-level sections, with their own h2 or without."""
    out, top, h3 = [], None, ""
    for unit in units:
        if unit["type"] == "h2":
            n = TOP_HEAD.match(_plain(unit["html"]))
            top = n.group(1) if n else None
            h3 = ""
            if top in keep and not drop_h2:
                out.append(unit)
            continue
        if unit["type"] == "h3":
            h3 = _plain(unit["html"])
        if top in keep and not any(h3.startswith(d) for d in drop_h3):
            out.append(unit)
    return out


def find_unit(units, prefix, kind=None, after=0):
    for i, unit in enumerate(units[after:], start=after):
        if kind and unit["type"] != kind:
            continue
        text = _plain(unit.get("html") or unit.get("text")
                      or " ".join(unit.get("lines", [])))
        if text.startswith(prefix):
            return i, unit
    return -1, None


def pose_source(units, lang):
    """The verse, its translations and the commentary of §6.2–§6.3."""
    labels = LABELS[lang]
    i62, _ = find_unit(units, "6.2", "h3")
    i63, _ = find_unit(units, "6.3", "h3")
    i64, _ = find_unit(units, "6.4", "h3")
    if i62 < 0 or i63 < 0 or i64 < 0:
        raise SystemExit("§6.2/§6.3 not found in the %s volume" % lang)
    part = units[i62:i63]
    verse = [u for u in part if u["type"] == "deva"][0]["lines"]
    trans = [u for u in part if u["type"] == "p"
             and _plain(u["html"]).split(" ")[0].rstrip(":").strip()
             in ("Перевод", "Translation")][0]
    quote = [u for u in part if u["type"] == "quote"][0]
    if lang == "ru":
        # the Russian volume prints the 1978 translation in Russian before the
        # original English; the Russian page shows the Russian one
        for unit in part:
            if unit["type"] == "p":
                text = _plain(unit["html"])
                if text.startswith("Перевод.") and "24" in text:
                    quote = {"paragraphs": [text]}
                    break
    class_part = units[i63:i64]
    class_deva = [u for u in class_part if u["type"] == "deva"][0]["lines"]
    class_tr = [u for u in class_part if u["type"] == "p"
                and _plain(u["html"]).startswith(("«", "“", '"'))][0]
    tail = ""
    for unit in class_part:
        if unit["type"] == "p":
            text = _plain(unit["html"])
            if text.startswith(("Это и есть", "This is precisely")):
                tail = text
                break
    return {
        "verse": verse,
        "trans": split_sentences(unwrap(_plain(trans["html"]))),
        "quote": quoted_segments(quote["paragraphs"]),
        "class_deva": split_clauses(class_deva),
        "class_tr": split_sentences(unwrap(_plain(class_tr["html"]))),
        "tail": tail,
    }


def pose_text(lang, group, src):
    """The blocks of one pose page: the verse, the source's translations, §6.3."""
    labels = LABELS[lang]
    lines, tr_i, q_i, cl_i = GROUP_INDEX[group]
    deva = [src["verse"][i] for i in lines]
    iast = [deva_lib.to_iast(line) for line in deva]
    sections = [{"type": "verse", "key": "deva", "label": labels["deva"],
                 "lines": deva},
                {"type": "verse", "key": "iast", "label": labels["iast"],
                 "lines": iast}]
    if lang == "ru":
        sections.append({"type": "verse", "key": "cyr", "label": labels["cyr"],
                         "lines": [translit.translit(line) for line in iast]})
    blocks = [{"type": "verse_card", "sections": sections}]

    trans = src["trans"][tr_i]
    blocks.append({"type": "prose", "key": "translation",
                   "label": labels["translation"], "paragraphs": [trans]})
    if q_i < len(src["quote"]):
        blocks.append({"type": "quote", "paragraphs": [src["quote"][q_i]]})
    if cl_i is not None and cl_i < len(src["class_deva"]):
        blocks.append({"type": "prose", "key": "class", "label": labels["class"],
                       "paragraphs": [src["class_deva"][cl_i]]})
        if cl_i < len(src["class_tr"]):
            blocks.append({"type": "p", "html": html.escape(src["class_tr"][cl_i])})
    else:
        if src["tail"]:
            tail = split_sentences(unwrap(src["tail"]))[-1]
            blocks.append({"type": "prose", "key": "class",
                           "label": labels["class"], "paragraphs": [tail]})
    return blocks


TREATISE = {
    "ru": {
        "title": "Ма̄насолла̄са. Āсаны (варттика на «Дакшин̣а̄мӯрти-стотру»)",
        "asanasTitle": "Āсаны «Ма̄насолла̄сы» (улласа IX, ст. 24–26)",
        "tradition": "адвайта-веданта · варттика",
        "edition": "Ānandāśrama Sanskrit Series · 1895, с. 156–157 · изд. 2008 г., с. 119",
        "datingTitle": "Введение. Датировка «Ма̄насолла̄сы»",
    },
    "en": {
        "title": "Mānasollāsa. Āsanas (a vārttika on the Dakṣiṇāmūrti-stotra)",
        "asanasTitle": "Āsanas of the Mānasollāsa (ullāsa IX, vv. 24–26)",
        "tradition": "Advaita Vedānta · vārttika",
        "edition": "Ānandāśrama Sanskrit Series · 1895, pp. 156–157 · 2008 edition, p. 119",
        "datingTitle": "Introduction. The Dating of the Mānasollāsa",
    },
}

ABOUT_SKIP = ("2",)          # the dating section has a page of its own


def dating_summary(units, lang):
    """Short rows: who dates the text when, and on what grounds.

    The two tables of §2.2 and §2.4 already have exactly the shape the site
    shows under a pose name: who — when — the work it is said in.
    """
    items = []
    h3 = ""
    for unit in section_units(units, {"2"}, drop_h2=True):
        if unit["type"] == "h3":
            h3 = _plain(unit["html"])
        if unit["type"] == "table" and h3.startswith("2.4") and unit["rows"] \
                and len(unit["rows"][0]) == 3:
            rows = unit["rows"]
            head = " ".join(rows[0])
            for row in rows[1:]:
                if "Источник" in head or "Source" in head:
                    when, who, work = row[0], row[1], row[2]
                else:
                    who, when, work = row[0], row[1], row[2]
                items.append({k: {lang: v} for k, v in
                              (("who", who), ("when", when), ("work", work))})
    note = ""
    i28, _ = find_unit(units, "2.8", "h3")
    if i28 >= 0:
        for unit in units[i28:]:
            if unit["type"] == "quote" and unit.get("paragraphs"):
                note = _plain(unit["paragraphs"][0]).replace("<strong>", "") \
                    .replace("</strong>", "")
                break
    return items, note


def build_lang(lang):
    doc = Doc(lang)
    units = tidy(doc.units)
    labels = LABELS[lang]
    meta = TREATISE[lang]

    about = []
    head = [u for u in units if u["type"] == "h2"]
    if head:
        about.append({"type": "title", "html": head[0]["html"]})
    first_p = [u for u in units if u["type"] == "p"][:2]
    for unit in first_p:
        about.append({"type": "byline", "html": unit["html"]})
    for unit in section_units(units, {"0", "1", "3", "4", "5", "6", "7", "8",
                                      "9", "10"}, drop_h3=("6.2", "6.3")):
        about.append(block(unit))

    dating_units = section_units(units, {"2"}, drop_h2=True)
    dating = {"title": meta["datingTitle"],
              "blocks": [block(u) for u in dating_units]}
    items, note = dating_summary(units, lang)
    summary_items = items
    dating_summary_out = {"items": summary_items}
    if note:
        dating_summary_out["note"] = {lang: note}

    src = pose_source(units, lang)
    poses = []
    for n, (key, iast, group, ref) in enumerate(POSES, start=1):
        gloss = GROUP_GLOSS[group]
        poses.append({
            "key": key,
            "iast": iast,
            "number": n,
            "name": {lang: iast if lang == "en" else
                     translit.translit(iast)[:1].upper()
                     + translit.translit(iast)[1:]},
            "gloss": {lang: gloss[1] if lang == "en" else
                      translit.translit(gloss[0])},
            "verses": {lang: ref},
            "text": {lang: pose_text(lang, group, src)},
        })

    return {
        "title": {lang: meta["title"]},
        "asanasTitle": {lang: meta["asanasTitle"]},
        "tradition": {lang: meta["tradition"]},
        "edition": {lang: meta["edition"]},
        "about": {lang: about},
        "dating": {lang: dating},
        "datingSummary": dating_summary_out,
    }, poses, len(units)


def merge(a, b):
    """Deep merge of the two language builds (b wins on scalars)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(a[k], v) if k in a else v
        return out
    if isinstance(a, list) and isinstance(b, list):
        return [merge(x, y) for x, y in zip(a, b)]
    return b


def main():
    ru, poses_ru, n_ru = build_lang("ru")
    en, poses_en, n_en = build_lang("en")
    data = merge(ru, en)
    poses = []
    for a, b in zip(poses_ru, poses_en):
        poses.append(merge(a, b))
    data["id"] = "manasollasa"
    data["chapter"] = "IX"
    data["chapterWord"] = {"ru": "улласа", "en": "ullāsa"}
    data["pdf"] = {
        "ru": "sources/Ма̄насолла̄са. Āсаны (полная справка с разбором асан).pdf",
        "en": "sources/Manasollasa. Āsanas (complete reference).pdf",
    }
    data["poses"] = poses
    data["posesTitle"] = {lang: TREATISE[lang]["asanasTitle"] for lang in ("ru", "en")}
    for key in ("prologue", "appendix", "notes"):
        data[key] = {"ru": [], "en": []}
    data["closing"] = {"ru": [], "en": []}
    # keep the key order of the other treatises
    order = ["id", "chapter", "chapterWord", "title", "asanasTitle", "tradition", "edition",
             "pdf", "about", "dating", "datingSummary", "prologue",
             "appendix", "notes", "closing", "poses"]
    data = {k: data[k] for k in order if k in data}
    return data, n_ru, n_en


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else str(SRC.parent / "data" / "manasollasa.json")
    data, n_ru, n_en = main()
    with open(out, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("units:", n_ru, "ru /", n_en, "en")
    print("about blocks:", len(data["about"]["ru"]), "| dating blocks:",
          len(data["dating"]["ru"]["blocks"]), "| summary rows:",
          len(data["datingSummary"]["items"]), "| poses:", len(data["poses"]))
    for pose in data["poses"]:
        print(" ", pose["number"], pose["key"], "|", pose["name"]["ru"], "|",
              pose["gloss"]["ru"], "|", len(pose["text"]["ru"]), "blocks")
    print("dropped glyphs:", len(_DROPPED))
