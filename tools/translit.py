# -*- coding: utf-8 -*-
"""IAST -> Cyrillic transliteration, with the single map used by the project.

The map is fixed: it is the one printed below, with the dot *below* the
Cyrillic «м» (ṃ/ṁ -> м̣). Nothing else is added or invented — every Sanskrit
letter is rewritten by this table, the rest of the string is left as it is.
"""

# Транслитерационная карта с точкой под м
MAP = {
    "a": "а", "ā": "ā", "i": "и", "ī": "ӣ",
    "u": "у", "ū": "ӯ", "ṛ": "р̣", "ṝ": "р̣̄",
    "ḷ": "л̣", "ḹ": "л̣̄", "e": "е", "ai": "аи",
    "o": "о", "au": "ау", "k": "к", "g": "г",
    "ṅ": "н̇", "c": "ч", "j": "дж", "ñ": "н̃",
    "ṭ": "т̣", "ḍ": "д̣", "ṇ": "н̣", "t": "т",
    "d": "д", "n": "н", "p": "п", "b": "б",
    "m": "м", "ṃ": "м̣", "ṁ": "м̣", "ḥ": "х̣",
    "y": "й", "r": "р", "l": "л", "v": "в",
    "ś": "ш́", "ṣ": "ш", "s": "с", "h": "х",
}

# longest key first, so "ai" is read before "a" and "jh" never splits
_ORDER = sorted(MAP.items(), key=lambda kv: -len(kv[0]))

# Cyrillic letters that mean the string is already transliterated
_CYR = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяӣӯ")


def has_cyrillic(text: str) -> bool:
    return any(ch.lower() in _CYR for ch in text)


def translit(text: str) -> str:
    """Rewrite IAST in Cyrillic by the map; unknown characters pass through."""
    out = []
    i = 0
    while i < len(text):
        for src, dst in _ORDER:
            if text.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
            cap = src[:1].upper() + src[1:]
            if text.startswith(cap, i):
                out.append(dst[:1].upper() + dst[1:])
                i += len(cap)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def normalize_marks(text: str) -> str:
    """Bring a printed Cyrillic line to the dot-below convention of the map.

    The oldest edition in the collection prints ṃ with a dot *above* «м»; the
    map used here puts the dot below (м̣), so a line that was transliterated
    before that decision is rewritten to the same convention. Letters, line
    breaks and everything else stay untouched.
    """
    DOT_ABOVE = "\u0307"
    DOT_BELOW = "\u0323"
    out = []
    for ch in text:
        if ch == DOT_ABOVE and out and out[-1] in ("м", "М", "р", "Р"):
            out.append(DOT_BELOW)   # ṝ becomes р̣̄: dot below, then the macron
            continue
        out.append(ch)
    return "".join(out)


def term(text: str) -> str:
    """A word-by-word term: IAST becomes Cyrillic, anything else is kept as is."""
    if not text or has_cyrillic(text):
        return text
    return translit(text)


if __name__ == "__main__":
    import json
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    data = json.loads((root / "data" / "ahirbudhnya-samhita.json").read_text())
    total = same = 0
    diff = []
    for pose in data["poses"]:
        sections = pose["text"]["ru"]
        iast = [s for s in sections if s["type"] == "verse" and s["key"] == "iast"]
        cyr = [s for s in sections if s["type"] == "verse" and s["key"] == "cyr"]
        for a, b in zip(iast, cyr):
            for left, right in zip(a["lines"], b["lines"]):
                total += 1
                if translit(left).strip() == right.strip():
                    same += 1
                else:
                    diff.append((translit(left).strip(), right.strip()))
    print("verse lines reproduced from the printed transliteration: %d / %d" % (same, total))
    for got, printed in diff:
        a = set(re.findall(r"\S+", got))
        b = set(re.findall(r"\S+", printed))
        print("  only in map:   ", " ".join(sorted(a - b))[:90] or "—")
        print("  only in printed:", " ".join(sorted(b - a))[:90] or "—")
