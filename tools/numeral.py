# -*- coding: utf-8 -*-
"""Chapter numbers are Arabic all over the site.

The sources number a chapter or an ullāsa now in Roman, now in Arabic figures:
«XXXI глава» in one treatise, «глава 1» in another, «улласа IX» in the third,
«chapter XXXI» in the English volume. This module puts every such number into
Arabic figures, so that the reader meets one convention everywhere.

What it does and does not do:

* it converts only a numeral that numbers a chapter or an ullāsa — one that
  stands next to a chapter word («глава XXXI», «XXXI глава», «chapter XXXI»,
  «ullāsa IX», «гл. I») or in a reference «chapter.verse» whose chapter is the
  chapter of the treatise itself («IX.24» → «9.24»);
* it never touches a Roman numeral of any other kind: centuries («в XII веке»),
  volumes («т. II»), shelf marks and catalogues («Oudh VIII, 24»), enumerations
  («I. Текст…», «II. Комментарий…»), citations of other works;
* the value of the number does not change: XXXI is 31 and stays 31 — no word
  is added, removed or reordered.
"""
import json
import re
import sys

_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

# A run of Roman letters standing on its own — not part of a Latin word; the
# run is checked against the grammar of Roman numerals before it is converted.
ROMAN = re.compile(r"(?<![A-Za-z])(?=[IVXLCDM])[IVXLCDM]+(?![A-Za-z])")
ROMAN_VALUE = re.compile(r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$")

# The words a chapter number may stand next to.
CHAPTER_WORDS = (
    r"глав[аыуе]|главой|главах|глав|гл\."
    r"|chapters?|chap\.|ch\."
    r"|ull[āa]s(?:a|as|e)?|уллас[аыуе]|улласы|уллас"
)
WORD = r"(?:%s)" % CHAPTER_WORDS

# «глава |XXXI» — a chapter word just before the numeral
BEFORE_CHAPTER = re.compile(r"(?:^|[^\w])%s[ \u00a0]*$" % WORD, re.I)
# «XXXI |глава» — a chapter word just after the numeral
AFTER_CHAPTER = re.compile(r"^[ \u00a0]*%s\b" % WORD, re.I)
# «IX.24» — chapter and verse; the chapter is checked against the treatise's own
REFERENCE = re.compile(r"(?<![IVXLCDM])([IVXLCDM]+)\.(\d{1,3})(?!\d)")


def roman_to_int(text):
    """Value of a Roman numeral, or None if the text is not one."""
    text = (text or "").strip().upper()
    if not text or not ROMAN_VALUE.fullmatch(text):
        return None
    total, prev = 0, 0
    for ch in reversed(text):
        val = _ROMAN[ch]
        total = total - val if val < prev else total + val
        prev = max(prev, val)
    return total


def arabic(value):
    """A chapter number in Arabic figures; anything else is returned as is."""
    if isinstance(value, int):
        return str(value)
    if not isinstance(value, str):
        return value
    n = roman_to_int(value)
    return str(n) if n else value


def fix_text(text, chapter=None):
    """Rewrite the chapter numbers of one string into Arabic figures.

    `chapter` is the number of the treatise's own chapter (a string or an int):
    that is what a reference such as «IX.24» is checked against.
    """
    if not isinstance(text, str) or not text:
        return text
    own = arabic(chapter) if chapter is not None else None

    def sub(match):
        value = roman_to_int(match.group(0))
        if value is None:
            return match.group(0)
        before, after = text[:match.start()], text[match.end():]
        if BEFORE_CHAPTER.search(before) or AFTER_CHAPTER.match(after):
            return str(value)
        return match.group(0)

    out = ROMAN.sub(sub, text)

    if own and own.isdigit():
        def sub_ref(m):
            if arabic(m.group(1)) == own:
                return "%s.%s" % (own, m.group(2))
            return m.group(0)
        out = REFERENCE.sub(sub_ref, out)
    return out


SKIP_KEYS = ("key", "file", "pdf", "url", "href")


def fix_tree(obj, chapter=None, skip_keys=SKIP_KEYS):
    """Apply `fix_text` to every string of a JSON tree."""
    if isinstance(obj, str):
        return fix_text(obj, chapter)
    if isinstance(obj, list):
        return [fix_tree(v, chapter, skip_keys) for v in obj]
    if isinstance(obj, dict):
        return {k: (v if k in skip_keys else fix_tree(v, chapter, skip_keys))
                for k, v in obj.items()}
    return obj


def fix_document(data):
    """Convert a treatise JSON: its own `chapter` field and every string."""
    chapter = arabic(data.get("chapter")) if data.get("chapter") else None
    out = fix_tree(data, chapter)
    if chapter:
        out["chapter"] = chapter
    return out


def diff(a, b, path="", acc=None):
    """The strings that `fix_document` changed, for a report."""
    if acc is None:
        acc = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            diff(a[k], b.get(k), path + "/" + k, acc)
    elif isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, path + "/%d" % i, acc)
    elif isinstance(a, str) and isinstance(b, str) and a != b:
        acc.append((path, a, b))
    return acc


def main(paths):
    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        fixed = fix_document(data)
        changed = diff(data, fixed)
        total += len(changed)
        if not changed:
            print("%s: unchanged" % path)
            continue
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(fixed, fh, ensure_ascii=False, indent=1)
            fh.write("\n")
        print("%s: %d strings" % (path, len(changed)))
        for where, old, new in changed:
            print("   %-24s %s" % (where, old[:100].replace("\n", " ")))
            print("   %-24s %s" % ("", new[:100].replace("\n", " ")))
    print("total:", total)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        for line in (
            "Описание āсан из XXXI главы Ахирбудхнйа-сам̣хиты",
            "в XXXI главе, начиная с 31.14 и до конца XXXII главы",
            "Так заканчивается XXXI глава",
            "A Description of the Āsanas in Chapter XXXI of the Ahirbudhnya-saṃhitā",
            "Thus ends chapter XXXI",
            "варттика на «Дакшин̣а̄мӯрти-стотру» · улласа IX · ст. 24–26",
            "a vārttika · ullāsa IX · vv. 24–26",
            "the reference IX.24 works for both",
            "исследователи относят текст к XII–XIII векам",
            "Adyar Library Series 4 · т. II, с. 293–296",
            "гл. I, с. 20–24",
            "Oudh VIII, 24",
            "<strong>I. Текст с</strong> комментарием",
        ):
            print("%-64s -> %s" % (line, fix_text(line, chapter="IX")))
