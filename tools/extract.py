# -*- coding: utf-8 -*-
"""Build the site's JSON data from the two source PDFs.

The PDFs are "Описание асан из XXXI главы Ахирбудхнья-самхиты"
(translation and word-by-word analysis by Alexander Vijaya) and its English
counterpart.  This script copies text verbatim out of the PDFs and only splits
it into structural blocks (verses, word-by-word lists, prose sections, notes).
No wording is added, removed or reordered.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

ZWSP = "\u200b"

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "sources"

RUNNING = {"ru": "АХИРБУДХНЬЯ-САМХИТА", "en": "AHIRBUDHNYA-SAṂHITĀ"}

LABELS = {
    "ru": {
        "Деванагари": ("verse", "deva"),
        "IAST": ("verse", "iast"),
        "Кириллическая транслитерация": ("verse", "cyr"),
        "Пословный разбор": ("words", "words"),
        "Буквальный перевод": ("prose", "literal"),
        "Литературный перевод": ("prose", "literary"),
        "Перевод": ("prose", "translation"),
    },
    "en": {
        "Devanāgarī": ("verse", "deva"),
        "IAST": ("verse", "iast"),
        "Cyrillic transliteration": ("verse", "cyr"),
        "Word-by-word analysis": ("words", "words"),
        "Literal translation": ("prose", "literal"),
        "Literary translation": ("prose", "literary"),
        "Translation": ("prose", "translation"),
    },
}

NOTE = {"ru": "Примечание", "en": "Note"}
COLOPHON = {"ru": "Колофон", "en": "Colophon"}
PROLOGUE_TITLE = {"ru": "Вступление и перечень асан", "en": "Opening and List of Āsanas"}
LIST_TITLE = {"ru": "Перечень, стихи 31–32", "en": "List, verses 31–32"}
APPENDIX = {"ru": "Приложение. Переход к пранаяме и конец главы",
            "en": "Appendix. Transition to Prāṇāyāma and the End of the Chapter"}
NOTES_HEAD = {"ru": "Примечания к чтениям", "en": "Notes on Readings"}
REPORT_HEAD = {"ru": "Главные асаны XXXI главы", "en": "The Principal Āsanas of Chapter XXXI"}
DATING_HEAD = {"ru": "О датировке и предполагаемом месте создания",
               "en": "Dating and Probable Place of Composition"}
CLOSING = {"ru": "Перевод и пословный разбор выполнены",
           "en": "This translation and word-by-word analysis"}
TITLE_TAIL = {"ru": "санскритский текст и перевод", "en": "Sanskrit Text and Translation"}

HEAD_RE = re.compile(r"^(\d{1,2})\.\s+(.+?)\s*\((«.+?»|“.+?”)\)\s*[—-]\s*(.+)$", re.S)
NOTE_RE = re.compile(r"^\d{1,2}\.\s*")


def clean(s: str) -> str:
    s = s.replace(ZWSP, "").replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def pdf_blocks(doc, lang):
    out = []
    for pi, page in enumerate(doc):
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            lines, heading = [], False
            for line in b["lines"]:
                buf = ""
                for span in line["spans"]:
                    if span["font"].startswith("NotoSans-Bold") and span["size"] > 12.5:
                        heading = True
                    buf += span["text"]
                lines.append(buf)
            txt = clean("\n".join(lines))
            if not txt or RUNNING[lang] in txt or re.fullmatch(r"\d{1,3}", txt):
                continue
            ys = [ln["bbox"][1] for ln in b["lines"]]
            out.append({"page": pi, "text": txt, "heading": heading,
                        "top": ys[0], "last": ys[-1]})
    return out


def group_paragraphs(raw):
    """Join consecutive line-blocks into paragraphs.

    A new paragraph starts when the vertical step between two lines is clearly
    larger than the normal leading, or when the page changes.
    """
    paras, cur, prev = [], "", None
    for b in raw:
        gap = b["top"] - prev["last"] if prev and prev["page"] == b["page"] else None
        if cur and gap is not None and gap >= 21:
            paras.append(cur)
            cur = ""
        cur = (cur + " " + b["text"]).strip() if cur else b["text"]
        prev = b
    if cur:
        paras.append(cur)
    return [clean(x) for x in paras]


def word_pairs(text):
    """Split the word-by-word analysis into (term, gloss) pairs.

    This is a structural split only: the strings themselves are untouched.
    Bracketed editorial notes may contain ';' or '.', so they are shielded
    while the text is being split.
    """
    store = []

    def shield(match):
        store.append(match.group(0))
        return "\x00%d\x00" % (len(store) - 1)

    shielded = re.sub(r"\[[^\]]*\]", shield, text)
    parts = re.split(r";\s*|(?<=\.)\s+(?=[\[A-Za-z])", shielded)

    def unshield(value):
        return re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], value)

    def is_term(value):
        value = unshield(value).strip()
        if not value or re.search(r"[А-Яа-яЁё]", value):
            return False
        return bool(re.search(r"[A-Za-zĀ-žḀ-ỿ]", value))

    pairs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        head, sep, tail = part.partition(" — ")
        if sep and is_term(head):
            pairs.append([clean(unshield(head)), clean(unshield(tail))])
        elif pairs:
            pairs[-1][1] = clean(pairs[-1][1] + " " + unshield(part))
        else:
            pairs.append(["", clean(unshield(part))])
    return pairs


def to_sections(secs):
    out = []
    for s in secs:
        t = s["type"]
        if t == "verse":
            out.append({"type": "verse", "key": s["key"], "label": s["label"],
                        "lines": [clean(x) for x in s["lines"] if clean(x)]})
        elif t == "words":
            text = " ".join(s["paragraphs"])
            out.append({"type": "words", "label": s["label"], "text": text,
                        "pairs": word_pairs(text)})
        elif t in ("prose", "note", "p"):
            item = {"type": t, "label": s.get("label") or "",
                    "paragraphs": s["paragraphs"]}
            if s.get("key"):
                item["key"] = s["key"]
            out.append(item)
        elif t == "subhead":
            out.append({"type": "subhead", "label": s["label"]})
    return out


class Doc:
    def __init__(self, lang):
        self.lang = lang
        name = ("Ahirbudhnya_samhita_asanas.pdf" if lang == "ru"
                else "Ahirbudhnya_samhita_asanas_en.pdf")
        self.blocks = pdf_blocks(pymupdf.open(PDF_DIR / name), lang)
        self.labels = LABELS[lang]
        self.prologue, self.poses, self.appendix = [], [], []
        self.notes, self.closing, self.about = [], [], []
        self.dating = {"title": DATING_HEAD[lang], "blocks": []}
        self.notes_title = NOTES_HEAD[lang]

    # ------------------------------------------------------------------ utils
    def _new(self, typ, **kw):
        sec = {"type": typ, "raw": [], **kw}
        return sec

    def _flush(self, coll):
        for sec in coll:
            if sec.get("raw"):
                sec["paragraphs"] = group_paragraphs(sec.pop("raw"))
            elif "raw" in sec:
                sec.pop("raw")
        for p in self.poses:
            pass

    # ------------------------------------------------------------------ parse
    def parse(self):
        bs = self.blocks
        state, pose = "title", None
        target = self.prologue
        i = 0
        while i < len(bs):
            b = bs[i]
            t = b["text"]

            if b["page"] <= 2:
                i += 1
                continue

            if t.startswith(NOTES_HEAD[self.lang]):
                self.notes_title = t
                state = "notes"
                i += 1
                continue

            if state == "notes":
                if t.startswith(CLOSING[self.lang]):
                    self.closing.append(t)
                elif NOTE_RE.match(t):
                    self.notes.append(self._new("note", label=t.split(":")[0].strip()))
                    self.notes[-1]["raw"].append(b)
                elif self.notes:
                    self.notes[-1]["raw"].append(b)
                i += 1
                continue

            if t.startswith(APPENDIX[self.lang]):
                state, pose = "appendix", None
                target = self.appendix
                target.append({"type": "subhead", "label": APPENDIX[self.lang]})
                rest = clean(t[len(APPENDIX[self.lang]):])
                if rest:
                    target.append(self._new("p"))
                    target[-1]["raw"].append({**b, "text": rest})
                i += 1
                continue

            if state == "title":
                if t.startswith(REPORT_HEAD[self.lang]) or t == TITLE_TAIL[self.lang]:
                    i += 1
                    continue
                state = "prologue"

            m = HEAD_RE.match(t)
            if m:
                pose = {"number": int(m.group(1)), "title": clean(m.group(2)),
                        "gloss": m.group(3), "verses": clean(m.group(4)),
                        "sections": []}
                self.poses.append(pose)
                state, target = "pose", pose["sections"]
                i += 1
                continue

            if t.startswith(NOTE[self.lang]):
                target.append(self._new("note", label=t.split(":")[0].strip()))
                target[-1]["raw"].append(b)
                i += 1
                continue

            if t in COLOPHON.values():
                target.append({"type": "subhead", "label": t})
                if i + 1 < len(bs) and not HEAD_RE.match(bs[i + 1]["text"]):
                    target.append({"type": "verse", "key": "deva", "label": t,
                                   "lines": bs[i + 1]["text"].split("\n")})
                    i += 2
                else:
                    i += 1
                continue

            if t in self.labels:
                typ, key = self.labels[t]
                if typ == "verse":
                    sec = {"type": "verse", "key": key, "label": t, "lines": []}
                elif typ == "words":
                    sec = self._new("words", label=t)
                else:
                    sec = self._new("prose", key=key, label=t)
                target.append(sec)
                i += 1
                while i < len(bs):
                    nb = bs[i]
                    ntext = nb["text"]
                    if (ntext in self.labels or ntext.startswith(NOTE[self.lang])
                            or ntext in COLOPHON.values() or HEAD_RE.match(ntext)
                            or ntext in (PROLOGUE_TITLE[self.lang], LIST_TITLE[self.lang])
                            or ntext.startswith(APPENDIX[self.lang])
                            or ntext.startswith(NOTES_HEAD[self.lang]) or nb["heading"]):
                        break
                    if typ == "verse":
                        sec["lines"].extend(x for x in ntext.split("\n") if clean(x))
                    else:
                        sec["raw"].append(nb)
                    i += 1
                continue

            if t in (PROLOGUE_TITLE[self.lang], LIST_TITLE[self.lang]) or b["heading"]:
                if state in ("prologue", "appendix"):
                    target.append({"type": "subhead", "label": t.rstrip(".")})
                i += 1
                continue

            if target and target[-1]["type"] in ("prose", "note", "p"):
                target[-1]["raw"].append(b)
            else:
                target.append(self._new("p"))
                target[-1]["raw"].append(b)
            i += 1

        for coll in (self.prologue, self.appendix):
            self._flush(coll)
        for p in self.poses:
            self._flush(p["sections"])
        self._flush(self.notes)
        self.closing = [" ".join(self.closing)] if self.closing else []
        return self

    def parse_about(self):
        raw = [b for b in self.blocks if b["page"] <= 2]
        out = []
        for b in raw:
            t = b["text"]
            if b["heading"]:
                if not out:
                    out.append({"type": "title", "text": t, "_src": b})
                elif out[-1]["type"] == "title" and out[-1]["_src"]["page"] == b["page"] \
                        and b["top"] - out[-1]["_src"]["last"] < 40:
                    out[-1]["text"] += " " + t
                    out[-1]["_src"] = b
                else:
                    out.append({"type": "h2", "text": t, "_src": b})
            elif t.startswith(("Автор:", "Author:")):
                out.append({"type": "byline", "text": t, "_src": b})
            else:
                out.append({"type": "p", "text": t, "_src": b})

        # join wrapped lines into paragraphs
        merged = []
        for item in out:
            prev = merged[-1] if merged else None
            if prev and prev["type"] == item["type"] == "p":
                gap = (item["_src"]["top"] - prev["_src"]["last"]
                       if prev["_src"]["page"] == item["_src"]["page"] else None)
                if gap is None or gap < 21:
                    prev["text"] += " " + item["text"]
                    prev["_src"] = item["_src"]
                    continue
            merged.append(item)

        # the sources block is a bullet list: split the running text on bullets
        for idx, item in enumerate(merged):
            if (item["type"] == "h2" and item["text"] in ("Источники", "Sources")
                    and idx + 1 < len(merged)):
                rest = " ".join(x["text"] for x in merged[idx + 1:])
                items = [clean(x) for x in re.split(r"●\s*", rest) if clean(x)]
                merged = merged[:idx + 1] + [{"type": "list", "items": items}]
                break

        for m in merged:
            m.pop("_src", None)
        self.about = merged
        self._split_dating()
        return self

    def _split_dating(self):
        """Pull the dating section out of the article (verbatim, uncut).

        The section stays in `about` as well: the article keeps all of its
        paragraphs, this is only a convenient pointer for the pose pages.
        """
        head = DATING_HEAD[self.lang]
        start = next((i for i, b in enumerate(self.about)
                      if b["type"] == "h2" and b["text"] == head), None)
        if start is None:
            self.dating = {"title": head, "blocks": []}
            return
        end = next((i for i in range(start + 1, len(self.about))
                    if self.about[i]["type"] == "h2"), len(self.about))
        body = self.about[start + 1:end]
        for item in body:
            if item["type"] == "p":
                item["type"] = "p"
        self.dating = {
            "title": head,
            "blocks": [dict(b) for b in body],
            "continues": [b["text"] for b in self.about[end:end + 1]
                          if b["type"] == "h2"] or [],
        }


POSE_KEYS = [
    "cakrasana", "padmasana", "kurmasana", "mayurasana", "kukkutasana",
    "virasana", "svastikasana", "bhadrasana", "simhasana", "muktasana",
    "gomukhasana",
]
POSE_IAST = [
    "cakrāsanam", "padmāsanam", "kūrmāsanam", "māyūrāsanam", "kukkuṭāsanam",
    "vīrāsanam", "svastikam", "bhadrāsanam", "siṃhāsanam", "muktāsanam",
    "gomukham",
]


def main():
    docs = {lang: Doc(lang).parse().parse_about() for lang in ("ru", "en")}
    ru, en = docs["ru"], docs["en"]
    assert len(ru.poses) == len(en.poses) == 11, (len(ru.poses), len(en.poses))

    treat = {
        "id": "ahirbudhnya-samhita",
        "chapter": "XXXI",
        "about": {lang: docs[lang].about for lang in docs},
        "prologue": {lang: to_sections(docs[lang].prologue) for lang in docs},
        "appendix": {lang: to_sections(docs[lang].appendix) for lang in docs},
        "notes": {lang: to_sections(docs[lang].notes) for lang in docs},
        "notesTitle": {lang: docs[lang].notes_title for lang in docs},
        "closing": {lang: docs[lang].closing for lang in docs},
        "dating": {lang: docs[lang].dating for lang in docs},
        "poses": [],
    }
    for idx, key in enumerate(POSE_KEYS):
        p_ru, p_en = ru.poses[idx], en.poses[idx]
        assert p_ru["number"] == p_en["number"] == idx + 1
        treat["poses"].append({
            "key": key, "iast": POSE_IAST[idx], "number": idx + 1,
            "name": {"ru": p_ru["title"], "en": p_en["title"]},
            "gloss": {"ru": p_ru["gloss"], "en": p_en["gloss"]},
            "verses": {"ru": p_ru["verses"], "en": p_en["verses"]},
            "text": {"ru": to_sections(p_ru["sections"]),
                     "en": to_sections(p_en["sections"])},
        })
    return treat, docs


def coverage(doc, treat):
    """Check that every block of the PDF is present in the extracted data."""
    def texts(obj):
        acc = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "pairs":
                    acc.append(" ".join(x for pair in v for x in pair))
                elif k in ("lines", "paragraphs"):
                    acc.extend(v)
                elif isinstance(v, (dict, list)):
                    acc.append(texts(v))
                elif isinstance(v, str) and k in ("text", "label"):
                    acc.append(v)
        elif isinstance(obj, list):
            for v in obj:
                acc.append(texts(v))
        return " \n ".join(a for a in acc if a)

    blob = texts(treat)
    blob = clean(blob)
    missing = []
    for b in doc.blocks:
        for line in b["text"].split("\n"):
            line = clean(line)
            if not line:
                continue
            probe = clean(line)[:60]
            if probe and probe not in blob:
                missing.append(line)
    return missing


if __name__ == "__main__":
    out, docs = main()
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for lang in ("ru", "en"):
        print(lang, "about:", len(out["about"][lang]),
              "prologue:", len(out["prologue"][lang]),
              "appendix:", len(out["appendix"][lang]),
              "notes:", len(out["notes"][lang]),
              "closing:", len(out["closing"][lang]))
    for p in out["poses"]:
        print(p["number"], p["key"], "|", p["verses"]["ru"], "|",
              [s["type"] + ":" + (s.get("key") or s.get("label", "")) for s in p["text"]["ru"]])
    for lang in ("ru", "en"):
        miss = coverage(docs[lang], out)
        print(lang, "PDF lines not found in output:", len(miss))
        for line in miss[:25]:
            print("   !", line[:110])
