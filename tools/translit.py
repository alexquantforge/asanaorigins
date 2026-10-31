# -*- coding: utf-8 -*-
"""IAST -> Cyrillic transliteration, following the scheme of the source PDFs.

The Russian editions print the verses three times: Devanāgarī, IAST and a
Cyrillic transliteration. The Cyrillic lines are the model for this module:
every pair below is taken from those printed lines (see ``check.py``-style
comparison in ``python3 translit.py``, which reports how many of the 28 verse
lines of the Ahirbudhnya-saṃhitā edition are reproduced character by character).

Nothing is translated here: the output is the same sounds, written in the
Cyrillic alphabet with the same diacritics the printed edition uses.
"""

PAIRS = [
    # vowels
    ("ai", "аи"),
    ("au", "ау"),
    ("ā", "ā"),      # the edition keeps Latin ā: Cyrillic а has no macron form
    ("ī", "ӣ"),
    ("ū", "ӯ"),
    ("ṛ", "р̣"),
    ("ṝ", "р̇"),
    ("a", "а"),
    ("i", "и"),
    ("u", "у"),
    ("e", "е"),
    ("o", "о"),
    # consonants
    ("kh", "кх"),
    ("gh", "гх"),
    ("ch", "чх"),
    ("jh", "джх"),
    ("ṭh", "т̣х"),
    ("ḍh", "д̣х"),
    ("th", "тх"),
    ("dh", "дх"),
    ("ph", "пх"),
    ("bh", "бх"),
    ("k", "к"),
    ("g", "г"),
    ("ṅ", "н̇"),
    ("c", "ч"),
    ("j", "дж"),
    ("ñ", "н̃"),
    ("ṭ", "т̣"),
    ("ḍ", "д̣"),
    ("ṇ", "н̣"),
    ("t", "т"),
    ("d", "д"),
    ("n", "н"),
    ("p", "п"),
    ("b", "б"),
    ("m", "м"),
    ("y", "й"),
    ("r", "р"),
    ("l", "л"),
    ("v", "в"),
    ("ś", "ш́"),
    ("ṣ", "ш"),
    ("s", "с"),
    ("h", "х"),
    # capital letters (a term may start with one)
    ("Kh", "Кх"), ("Gh", "Гх"), ("Ch", "Чх"), ("Jh", "Джх"),
    ("Ṭh", "Т̣х"), ("Ḍh", "Д̣х"), ("Th", "Тх"), ("Dh", "Дх"),
    ("Ph", "Пх"), ("Bh", "Бх"),
    ("Ā", "Ā"), ("Ī", "Ӣ"), ("Ū", "Ӯ"), ("Ṛ", "Р̣"),
    ("A", "А"), ("I", "И"), ("U", "У"), ("E", "Е"), ("O", "О"),
    ("K", "К"), ("G", "Г"), ("Ṅ", "Н̇"), ("C", "Ч"), ("J", "Дж"),
    ("Ñ", "Н̃"), ("Ṭ", "Т̣"), ("Ḍ", "Д̣"), ("Ṇ", "Н̣"), ("T", "Т"),
    ("D", "Д"), ("N", "Н"), ("P", "П"), ("B", "Б"), ("M", "М"),
    ("Y", "Й"), ("R", "Р"), ("L", "Л"), ("V", "В"), ("Ś", "Ш́"),
    ("Ṣ", "Ш"), ("S", "С"), ("H", "Х"),
    # marks
    ("ṃ", "м̇"),
    ("ṁ", "м̇"),
    ("ḥ", "х̣"),
    ("Ṃ", "М̇"),
    ("Ḥ", "Х̣"),
    ("'", "’"),
]

# longest source strings win, so "kh" is read before "k"
_ORDER = sorted(PAIRS, key=lambda p: -len(p[0]))

_CYR = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяӣӯ")


def has_cyrillic(text: str) -> bool:
    return any(ch.lower() in _CYR for ch in text)


def iast_to_cyr(text: str) -> str:
    """Rewrite IAST in Cyrillic with diacritics; unknown characters pass through."""
    out = []
    i = 0
    while i < len(text):
        for src, dst in _ORDER:
            if text.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def term(term: str) -> str:
    """A word-by-word term: IAST becomes Cyrillic, anything else is kept as is.

    Slashes, hyphens, brackets, question marks and Latin sigla stay untouched;
    only Sanskrit syllables are rewritten.
    """
    if not term or has_cyrillic(term):
        return term
    return iast_to_cyr(term)


translit_term = term  # alias


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    data = json.loads((root / "data" / "ahirbudhnya-samhita.json").read_text())
    total = same = 0
    for pose in data["poses"]:
        sections = pose["text"]["ru"]
        iast = [s for s in sections if s["type"] == "verse" and s["key"] == "iast"]
        cyr = [s for s in sections if s["type"] == "verse" and s["key"] == "cyr"]
        for a, b in zip(iast, cyr):
            for left, right in zip(a["lines"], b["lines"]):
                total += 1
                same += iast_to_cyr(left).strip() == right.strip()
    print("verse lines reproduced from the printed transliteration: %d / %d" % (same, total))
