# -*- coding: utf-8 -*-
"""Build data/vasishtha-samhita.json from the two source PDFs.

Sources (in sources/):
  * "Васишт̣ха-сам̣хитā. Āсаны (Йога-кāн̣д̣а, гл. 1, ст. 67–82).pdf"
  * "Vasiṣṭha Saṃhitā. Āsanas (Yoga Kāṇḍa, ch. 1, vv. 67–82).pdf"

Text is copied from the PDFs; the script only decides where one block ends and
the next begins (headings, paragraphs, quotations, lists, tables, verses).
"""
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

from common import (Block, assemble_paragraphs, clean, looks_like_list,
                    merge_runs, page_items, para_html, runs_html, split_bullets)

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "sources"

PDFS = {
    "ru": "Васишт̣ха-сам̣хитā. Āсаны (Йога-кāн̣д̣а, гл. 1, ст. 67–82).pdf",
    "en": "Vasiṣṭha Saṃhitā. Āsanas (Yoga Kāṇḍa, ch. 1, vv. 67–82).pdf",
}

LABELS = {
    "ru": {
        "Деванāгарӣ": ("verse", "deva"),
        "Деванагари": ("verse", "deva"),
        "IAST": ("verse", "iast"),
        "Кириллическая транслитерация": ("verse", "cyr"),
        "Пословный разбор": ("words", "words"),
        "Буквальный перевод": ("prose", "literal"),
        "Литературный перевод": ("prose", "literary"),
        "Примечание": ("note", "note"),
    },
    "en": {
        "Devanāgarī": ("verse", "deva"),
        "Devanagari": ("verse", "deva"),
        "IAST": ("verse", "iast"),
        "Cyrillic transliteration": ("verse", "cyr"),
        "Word-by-word analysis": ("words", "words"),
        "Literal translation": ("prose", "literal"),
        "Literary translation": ("prose", "literary"),
        "Note": ("note", "note"),
    },
}

LABEL_BY_KEY = {
    "ru": {"deva": "Деванāгарӣ", "iast": "IAST",
           "cyr": "Кириллическая транслитерация"},
    "en": {"deva": "Devanāgarī", "iast": "IAST",
           "cyr": "Cyrillic transliteration"},
}

ASANA_HEAD = {"ru": "Āсаны", "en": "Āsanas"}
DATING_HEAD = {"ru": "Введение. Датировка", "en": "Introduction. The Dating"}
ABOUT_HEAD = {"ru": "О тексте и цели документа", "en": "About the Text and the Purpose"}
INTRO_VERSE = {"ru": "Вводный стих", "en": "Introductory verse"}

# "1. Свастикāсана («Поза свастики», «Благая поза»)" / "1. Svastikāsana (“...”)."
# group 3 keeps the parenthetical exactly as printed in the source.
POSE_HEAD_RE = re.compile(
    r"^(\d{1,2})\.\s+(.+?)\s*[\(（](.+)[\)）]$", re.S)

POSES = [
    (("svastika",), "svastikasana"),
    (("gomukha",), "gomukhasana"),
    (("padma",), "padmasana"),
    (("vira",), "virasana"),
    (("simha",), "simhasana"),
    (("mayura",), "mayurasana"),
    (("kukkuta",), "kukkutasana"),
    (("bhadra",), "bhadrasana"),
    (("kurma",), "kurmasana"),
    (("mukta",), "muktasana"),
]

CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ӣ": "i", "ӯ": "u", "ѣ": "e", "ѳ": "f", "ѵ": "i",
}

COMBINING = set("\u093e\u093f\u0940\u0941\u0942\u0943\u0944\u0945\u0946\u0947"
                "\u0948\u0949\u094a\u094b\u094c\u094d\u0951\u0952\u0953"
                "\u0954\u0962\u0963\u0902\u0903")


def fold(text):
    """Lower-case ASCII approximation; used only to pick the shared key."""
    text = text.lower()
    text = "".join(CYR.get(ch, ch) for ch in text)
    for a, b in (("ā", "a"), ("ī", "i"), ("ū", "u"), ("ṃ", "m"), ("ṁ", "m"),
                 ("ṭ", "t"), ("ḍ", "d"), ("ṇ", "n"), ("ś", "s"), ("ṣ", "s"),
                 ("ṛ", "r"), ("ṅ", "n"), ("ñ", "n"), ("ḷ", "l")):
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def pose_key(title):
    folded = fold(title)
    for stems, key in POSES:
        for stem in stems:
            if folded.startswith(stem):
                return key
    return None


DEVA_DIGITS = {ord(d): str(i) for i, d in enumerate("०१२३४५६७८९")}


def verse_numbers(sections):
    """Verse numbers printed at the end of the Devanāgarī lines (॥ ६८ ॥)."""
    nums = []
    for sec in sections:
        if sec.get("type") != "verse_card":
            continue
        for part in sec["sections"]:
            if part["key"] != "deva":
                continue
            for line in part["lines"]:
                m = re.search(r"॥\s*([०-९]+)\s*॥\s*$", line)
                if m and m.group(1).translate(DEVA_DIGITS) not in nums:
                    nums.append(m.group(1).translate(DEVA_DIGITS))
    if not nums:
        return ""
    return nums[0] if len(nums) == 1 else "%s–%s" % (nums[0], nums[-1])


def word_pairs(text):
    """Split a word-by-word line into (term, gloss) pairs, verbatim.

    Only the separators are interpreted: entries are separated by ";" (and by
    a spaced dash), brackets are shielded so an inner ";" or dash cannot split
    an entry.
    """
    store = []

    def shield(match):
        store.append(match.group(0))
        return "\x00%d\x00" % (len(store) - 1)

    def unshield(value):
        return re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], value)

    shielded = re.sub(r"\[[^\]]*\]", shield, text)
    shielded = re.sub(r"\([^)]*\)", shield, shielded)
    parts = re.split(r";\s*", shielded)
    pairs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        bits = re.split(r"\s[-\u2013\u2014]\s", part, maxsplit=1)
        head = bits[0]
        tail = bits[1] if len(bits) > 1 else ""
        if tail and head.strip():
            pairs.append([clean(unshield(head)), clean(unshield(tail))])
        elif pairs:
            pairs[-1][1] = clean(pairs[-1][1] + " " + unshield(part))
        else:
            pairs.append(["", clean(unshield(part))])
    return pairs


def join_verse_lines(lines):
    """Re-join wrapped PDF lines into verse lines (danda marks the end)."""
    out, cur = [], ""
    for raw in lines:
        piece = clean(raw)
        if not piece:
            continue
        if cur and piece[:1] in COMBINING:
            cur += piece
        elif cur:
            cur += " " + piece
        else:
            cur = piece
        if cur.endswith("॥") or re.search(r"॥\s*\d*\s*॥?\s*$", cur):
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return [re.sub(r"\s+", " ", l) for l in out]


class Doc:
    def __init__(self, lang):
        self.lang = lang
        self.labels = LABELS[lang]
        self.items = []
        doc = pymupdf.open(PDF_DIR / PDFS[lang])
        for page in doc:
            self.items.extend(page_items(page))

        self.title = ""
        self.about = {"title": "", "blocks": []}
        self.dating = {"title": "", "blocks": []}
        self.prologue = []
        self.poses = []
        self.asana_title = ""

        self.state = "title"
        self.target = self.about["blocks"]
        self.pose = None
        self.card = None      # current verse card
        self.mode = None      # ("verse", key, section) | ("words"|"prose"|"note", section)
        self.buf = []         # pending paragraph blocks (about / dating)
        self.last_quote = None  # previous block, to join wrapped quotation lines
        self.last_block = None  # previous body block (to join wrapped lines)
        body = [it["block"] for it in self.items if it["kind"] == "block"]
        self.left = min((b.x0 for b in body if b.x0 > 60), default=90.0)
        self.right = max((b.x1_last for b in body), default=505.0)

    # ------------------------------------------------------------- utilities
    def _flush(self):
        self.last_quote = None
        if not self.buf:
            return
        for para in assemble_paragraphs(self.buf):
            html = para_html(para)
            if html:
                self.target.append({"type": "p", "html": html})
        self.buf = []

    def _close_mode(self, assemble=True):
        """Turn the pending block run of the current section into paragraphs."""
        if not self.mode:
            return
        kind, sec = self.mode
        if kind == "verse":
            sec["lines"] = join_verse_lines(sec.pop("_lines"))
            m = re.search(r"॥\s*([०-९]+)\s*॥\s*$", " ".join(sec["lines"]))
            if m:
                sec["verses"] = m.group(1).translate(DEVA_DIGITS)
        elif kind == "words":
            groups = []
            paras = []
            for para in assemble_paragraphs(sec.pop("_blocks")):
                html = para_html(para)
                if not html:
                    continue
                paras.append(html)
                pairs = word_pairs(html)
                if pairs:
                    groups.append(pairs)
            sec["paragraphs"] = paras
            sec["groups"] = groups
        elif assemble and sec.get("_blocks"):
            sec["paragraphs"] = [para_html(p)
                                 for p in assemble_paragraphs(sec.pop("_blocks"))]
        elif "_blocks" in sec:
            sec.pop("_blocks")
        self.mode = None

    def _sink(self):
        if self.pose is not None:
            return self.pose["sections"]
        return self.prologue

    # ------------------------------------------------------------------ walk
    def parse(self):
        for item in self.items:
            if item["kind"] == "table":
                if self.state in ("about", "dating"):
                    self._flush()
                    last = self.target[-1] if self.target else None
                    if (last and last["type"] == "table"
                            and item["page"] == last.get("_page", -2) + 1
                            and item["y"] < 170):
                        last["rows"].extend(item["rows"])   # table split by a page break
                    else:
                        self.target.append({"type": "table", "rows": item["rows"],
                                            "_page": item["page"],
                                            "_cols": item.get("cols", [])})
                continue

            blk: Block = item["block"]
            text = blk.text
            if not text:
                continue

            # a table may spill its last row past the page break
            last = self.target[-1] if self.target else None
            if (last and last["type"] == "table" and last.get("_cols")
                    and item["page"] == last.get("_page", -2) + 1
                    and blk.y0 < 100 and blk.size < 12 and blk.bold < 0.9):
                cx = (blk.x0 + blk.x1_last) / 2
                for idx, (c0, c1) in enumerate(last["_cols"]):
                    if c0 - 2 <= cx <= c1 + 2:
                        row = last["rows"][-1]
                        while len(row) <= idx:
                            row.append("")
                        row[idx] = (row[idx] + " " + text).strip()
                        break
                continue

            if blk.size >= 12.9:
                self._heading(blk)
                continue

            is_heading = (blk.bold > 0.95 and blk.x0 < 112 and len(text) < 150
                          and not looks_like_list(blk))
            if self.state in ("title", "about", "dating"):
                if self.state == "title":
                    self.state = "about"
                    self.target = self.about["blocks"]
                if is_heading and blk.size >= 12.4:
                    self._flush()
                    self.target.append({"type": "h2", "html": self._inline(blk)})
                    continue
                if is_heading:
                    self._flush()
                    level = "h4" if re.match(r"^\d{1,2}\.\d{1,2}\.", text) else "h3"
                    self.target.append({"type": level, "html": self._inline(blk)})
                    continue
                self._body(blk)
                continue

            if self.state == "asanas":
                self._asanas(blk)
                continue

        self._flush()
        self._close_mode()
        return self

    @staticmethod
    def _inline(blk):
        return runs_html(merge_runs([tuple(r) for l in blk.lines for r in l.runs]))

    def _heading(self, blk):
        text = blk.text
        self._flush()
        self._close_mode()
        if self.state == "title":
            if not self.title:
                self.title = text
                return
            self.state = "about"
            self.target = self.about["blocks"]
        if text.startswith(DATING_HEAD[self.lang]):
            self.state = "dating"
            self.target = self.dating["blocks"]
            self.dating["title"] = text
            self.pose = None
            return
        if text.startswith(ABOUT_HEAD[self.lang]):
            self.state = "about"
            self.target = self.about["blocks"]
            self.about["title"] = text
            self.pose = None
            return
        if text.startswith(ASANA_HEAD[self.lang]):
            self.state = "asanas"
            self.pose = None
            self.asana_title = blk.lines[0].text if blk.lines else text
            # the section opener may share a block with the first subheading
            for line in blk.lines[1:]:
                if line.text:
                    self.prologue.append({"type": "subhead", "label": line.text})
            return
        if self.state == "asanas":
            m = POSE_HEAD_RE.match(text)
            if m:
                self.pose = {
                    "number": int(m.group(1)),
                    "title": clean(m.group(2)),
                    "gloss": clean(m.group(3)),
                    "key": pose_key(m.group(2)),
                    "sections": [],
                }
                self.poses.append(self.pose)
                self.card = None
                return
            if text.startswith(INTRO_VERSE[self.lang]):
                self.pose = None
                self.prologue.append({"type": "subhead", "label": text})
                return
        # any other large heading: keep it as a section title
        if self.state in ("about", "dating"):
            self.target.append({"type": "h2", "html": self._inline(blk)})

    def _is_indent(self, blk):
        """A line indented past the block margin (a wrapped line, not a new one)."""
        return self.left + 12 <= blk.x0 <= self.left + 90

    def _joins_previous(self, blk):
        """True when `blk` is the wrapped tail of the previous body block."""
        prev = self.last_block
        if prev is None or not self._is_indent(blk):
            return False
        if prev.page == blk.page:
            return blk.y0 - prev.y1 <= 6.0
        if blk.page == prev.page + 1:
            # a run may continue over a page break: the last line then either
            # reaches the right margin or stops before a full stop
            tail = prev.text[-1:]
            return prev.x1_last >= self.right - 20 or tail not in ".!?:;»”"

    def _continues_sentence(self, blk):
        """A line at the left margin that still belongs to the previous block.

        Numbered references such as "… nn. 8 and 10." look like list items; they
        only continue the running text when the previous line stops mid-sentence.
        """
        prev = self.last_block
        if prev is None or prev.page != blk.page:
            return False
        if blk.y0 - prev.y1 > 6.0:
            return False
        tail = prev.text[-1:]
        return bool(tail) and tail not in ".!?:;»”"
        return False

    def _append_wrapped(self, blk):
        if not self.target:
            return False
        last = self.target[-1]
        html = blk.html()
        if not html:
            return True
        if last["type"] == "list" and last["items"]:
            last["items"][-1]["html"] = last["items"][-1]["html"] + " " + html
        elif last["type"] == "p":
            last["html"] = last["html"] + " " + html
        elif last["type"] == "quote" and last["paragraphs"]:
            last["paragraphs"][-1] = last["paragraphs"][-1] + " " + html
        else:
            return False
        return True

    def _body(self, blk):
        """Paragraphs, bullet lists and quotations of the article sections."""
        if self.state == "title":
            self.state = "about"
            self.target = self.about["blocks"]
            self.about["title"] = self.about["title"] or blk.text

        joins = self._joins_previous(blk)
        if (self._is_numbered(blk) and not self._is_indent(blk)
                and self._continues_sentence(blk)):
            joins = True        # "… nn. 8 and 10." — a reference, not a new item
        if (joins and not looks_like_list(blk)
                and (not self._is_numbered(blk) or self._continues_sentence(blk))):
            self._flush()
            if self._append_wrapped(blk):
                self.last_block = blk
                return

        if looks_like_list(blk):
            self.last_block = blk
            lead_html, items = split_bullets(blk, base=self.left)
            self._flush()
            if lead_html:
                self.target.append({"type": "p", "html": lead_html})
            if items:
                if self.target and self.target[-1]["type"] == "list":
                    self.target[-1]["items"].extend(items)
                else:
                    self.target.append({"type": "list", "items": items})
            return

        if blk.x0 >= 114 and blk.italic > 0.5:
            self._flush()
            html = blk.html()
            prev = self.last_quote
            same_run = (prev is not None and prev.page == blk.page
                        and blk.y0 - prev.y1 <= 8)
            last = self.target[-1] if self.target else None
            if last and last["type"] == "quote":
                if same_run:
                    last["paragraphs"][-1] = last["paragraphs"][-1] + " " + html
                else:
                    last["paragraphs"].append(html)
            else:
                self.target.append({"type": "quote", "paragraphs": [html]})
            self.last_quote = blk
            self.last_block = blk
            return
        self.last_quote = None

        if self._is_numbered(blk):
            self._flush()   # a numbered item always starts a new paragraph
        self.buf.append(blk)
        self.last_block = blk

    @staticmethod
    def _is_numbered(blk):
        return bool(re.match(r"^\d{1,2}\.[^\d]", blk.text))

    def _asanas(self, blk):
        text = blk.text
        label = text.rstrip(":").strip()
        if label in self.labels and blk.bold > 0.6 and len(text) < 60:
            typ, key = self.labels[label]
            if typ == "verse":
                if key == "deva" or self.card is None:
                    self._close_mode()
                    self.card = {"type": "verse_card", "sections": []}
                    self._sink().append(self.card)
                sec = {"type": "verse", "key": key,
                       "label": LABEL_BY_KEY[self.lang][key], "_lines": []}
                self.card["sections"].append(sec)
                self._close_mode()
                self.mode = ("verse", sec)
                return
            self._close_mode()
            sec = {"type": typ, "key": key, "label": label, "paragraphs": []}
            if typ in ("words", "note"):
                sec.pop("paragraphs")
                sec["_blocks"] = []
            else:
                sec.pop("paragraphs")
                sec["_blocks"] = []
            self._sink().append(sec)
            self.mode = (typ, sec)
            return

        if self.mode is None:
            sec = {"type": "prose", "key": None, "label": "", "_blocks": [blk]}
            self._sink().append(sec)
            self.mode = ("prose", sec)
            return
        kind, sec = self.mode
        if kind == "verse":
            sec["_lines"].extend(l.text for l in blk.lines)
        else:
            sec.setdefault("_blocks", []).append(blk)

    # ---------------------------------------------------------------- summary
    def summary(self):
        tables = [b for b in self.dating["blocks"] if b["type"] == "table"]
        if not tables:
            return {"header": [], "items": []}
        header = [clean(c) for c in tables[0]["rows"][0]]
        items = []

        def add(rows):
            for row in rows:
                cells = [clean(c) for c in row]
                if len(cells) < 2 or not cells[0] or not cells[1]:
                    continue
                item = {"when": cells[0], "who": cells[1]}
                if len(cells) > 2 and cells[2]:
                    item["basis"] = cells[2]
                items.append(item)

        # the table may be split over a page break: later tables continue it
        add(tables[0]["rows"][1:])
        for extra in tables[1:]:
            add(extra["rows"])
        return {"header": header, "items": items}


def about_blocks(doc):
    """The about page as the site expects it: document title, section head, text."""
    blocks = [{"type": "title", "html": doc.title}]
    if doc.about["title"]:
        blocks.append({"type": "h2", "html": doc.about["title"]})
    blocks.extend(doc.about["blocks"])
    return blocks


def dating_summary(ru, en):
    """Short dating rows, pairwise from the two PDFs (no text added)."""
    import html as htmllib

    a, b = ru.summary(), en.summary()
    label = {"ru": a["header"][2] if len(a["header"]) > 2 else "",
             "en": b["header"][2] if len(b["header"]) > 2 else ""}
    items = []
    for i, row in enumerate(a["items"]):
        other = b["items"][i] if i < len(b["items"]) else row
        items.append({
            "when": {"ru": htmllib.unescape(row["when"]),
                     "en": htmllib.unescape(other["when"])},
            "who": {"ru": htmllib.unescape(row["who"]),
                    "en": htmllib.unescape(other["who"])},
            "work": {"ru": htmllib.unescape(row.get("basis", "")),
                     "en": htmllib.unescape(other.get("basis", ""))},
        })
    return {"label": {"ru": htmllib.unescape(label["ru"]),
                      "en": htmllib.unescape(label["en"])},
            "items": items}


def main():
    docs = {lang: Doc(lang).parse() for lang in ("ru", "en")}
    ru, en = docs["ru"], docs["en"]
    assert len(ru.poses) == len(en.poses) == 10, (len(ru.poses), len(en.poses))
    for a, b in zip(ru.poses, en.poses):
        assert a["key"] == b["key"], (a["title"], b["title"])

    for lang in ("ru", "en"):
        for b in docs[lang].dating["blocks"]:
            b.pop("_page", None)
            b.pop("_cols", None)

    data = {
        "id": "vasishtha-samhita",
        "chapter": "1",
        "title": {"ru": ru.title, "en": en.title},
        "asanasTitle": {"ru": ru.asana_title, "en": en.asana_title},
        "about": {"ru": about_blocks(ru), "en": about_blocks(en)},
        "dating": {
            "ru": {"title": ru.dating["title"], "blocks": ru.dating["blocks"],
                   "summary": ru.summary()},
            "en": {"title": en.dating["title"], "blocks": en.dating["blocks"],
                   "summary": en.summary()},
        },
        "datingSummary": dating_summary(ru, en),
        "prologue": {"ru": ru.prologue, "en": en.prologue},
        "appendix": {"ru": [], "en": []},
        "notes": {"ru": [], "en": []},
        "closing": {"ru": [], "en": []},
        "poses": [],
    }
    for pose in ru.poses + en.poses:
        for sec in pose["sections"]:
            if sec.get("type") != "verse_card":
                continue
            for part in sec["sections"]:
                if part.get("verses"):
                    sec["verses"] = part["verses"]
                    break

    for idx, (a, b) in enumerate(zip(ru.poses, en.poses)):
        data["poses"].append({
            "key": a["key"],
            "iast": b["title"],
            "number": idx + 1,
            "name": {"ru": a["title"], "en": b["title"]},
            "gloss": {"ru": a["gloss"], "en": b["gloss"]},
            "verses": {"ru": verse_numbers(a["sections"]),
                       "en": verse_numbers(b["sections"])},
            "text": {"ru": a["sections"], "en": b["sections"]},
        })
    return data, docs


def coverage(data, docs):
    def flatten(obj, acc):
        if isinstance(obj, str):
            acc.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                flatten(v, acc)
        elif isinstance(obj, list):
            for v in obj:
                flatten(v, acc)
        return acc

    blob = " \n ".join(flatten(data, []))
    blob = html.unescape(re.sub(r"<[^>]+>", " ", blob))
    blob = re.sub(r"\s+", "", blob)
    report = {}
    for lang in ("ru", "en"):
        missing = []
        for item in docs[lang].items:
            if item["kind"] == "table":
                continue
            for line in item["block"].lines:
                raw = clean(line.text)
                if POSE_HEAD_RE.match(raw) or raw.startswith(ASANA_HEAD[lang]):
                    continue  # headings are rebuilt from their parts
                probe = re.sub(r"\s+", "", raw)[:40].lstrip("●")
                if probe and probe not in blob:
                    missing.append(line.text)
        report[lang] = missing
    return report


if __name__ == "__main__":
    data, docs = main()
    with open(sys.argv[1], "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    for lang in ("ru", "en"):
        print(lang, "| title:", data["title"][lang][:60])
        print("   about blocks:", len(data["about"][lang]),
              "| dating blocks:", len(data["dating"][lang]["blocks"]),
              "| prologue:", len(data["prologue"][lang]))
        types = {}
        for b in data["dating"][lang]["blocks"]:
            types[b["type"]] = types.get(b["type"], 0) + 1
        print("   dating block types:", types)
    print("summary rows:", len(data["dating"]["ru"]["summary"]["items"]))
    for item in data["dating"]["ru"]["summary"]["items"]:
        print("   ", item["when"], "|", item["who"][:65])
    for pose in data["poses"]:
        kinds = []
        for sec in pose["text"]["ru"]:
            if sec["type"] == "verse_card":
                kinds.append("card(%d)" % len(sec["sections"]))
            else:
                kinds.append(sec["type"])
        print(pose["number"], pose["key"], "|", pose["name"]["ru"], "|", " ".join(kinds))
    rep = coverage(data, docs)
    for lang in ("ru", "en"):
        print(lang, "lines missing:", len(rep[lang]))
        for line in rep[lang][:15]:
            print("   !", line[:110])
