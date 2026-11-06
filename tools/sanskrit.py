# -*- coding: utf-8 -*-
"""Diacritics for Sanskrit words written in Cyrillic.

The Russian editions in `sources/` print Sanskrit terms inconsistently: in one
place «āсана», in another «асана»; the pose names in the margins of the
Ahirbudhnya-saṃhitā PDF carry no marks at all. The site shows one convention:
every Sanskrit word is written with the marks it needs — the same letters and
the same marks the editions use elsewhere in the same PDFs.

Only the marks are added. No letter is inserted, removed or reordered, and no
word is translated; every form below is checked against the IAST of the same
edition (see `python3 sanskrit.py`, which prints every rewrite it makes).

The words that do not need a mark (yoga, tantra, mudrā, grantha, kanda,
niyama, yama, cakra, bhadra…) are deliberately absent from the table.
"""

import re

# Sanskrit words in Cyrillic that need a mark, longest form first.
# The left side is what the editions print, the right side is the same word
# with the marks of the project's transliteration map (tools/translit.py).
FORMS = [
    # the treatise name, as it is spelled in the Russian PDFs
    ("Ахирбудхнья", "Ахирбудхнйа"),
    ("Ахирбудхньи", "Ахирбудхнйи"),
    ("Ахирбудхнье", "Ахирбудхнйе"),
    # pose names and their stems (the case endings stay untouched)
    ("Чакрасан", "Чакрāсан"),
    ("Падмасан", "Падмāсан"),
    ("Курмасан", "Кӯрмāсан"),
    ("Майурасан", "Мāйӯрāсан"),
    ("Куккутасан", "Куккут̣āсан"),
    ("Вирасана", "Вӣрāсана"),
    ("Свастикасан", "Свастикāсан"),
    ("Бхадрасан", "Бхадрāсан"),
    ("Симхасан", "Сим̣хāсан"),
    ("Муктасан", "Муктāсан"),
    ("Гомукхасан", "Гомукхāсан"),
    # the same stems as they are listed in the enumeration of the chapter
    ("Мукта", "Муктā"),
    ("Курма", "Кӯрма"),
    ("Майура", "Мāйӯра"),
    ("Куккута", "Куккут̣а"),
    ("Вира", "Вӣра"),
    ("Симха", "Сим̣ха"),
    # saṃhitā
    ("самхита", "сам̣хитā"),
    ("самхиты", "сам̣хиты"),
    ("самхите", "сам̣хите"),
    ("самхитой", "сам̣хитой"),
    ("самхит", "сам̣хит"),
    # āsana
    ("асанного", "āсанного"),
    ("асанами", "āсанами"),
    ("асанах", "āсанах"),
    ("асанам", "āсанам"),
    ("асаной", "āсаной"),
    ("асана", "āсана"),
    ("асаны", "āсаны"),
    ("асану", "āсану"),
    ("асан", "āсан"),
    # prāṇāyāma
    ("пранаямой", "прāн̣āйāмой"),
    ("пранаяме", "прāн̣āйāме"),
    ("пранаяму", "прāн̣āйāму"),
    ("пранаяма", "прāн̣āйāма"),
    # names and terms
    ("Панчаратры", "Пāн̃чарāтры"),
    ("Панчаратре", "Пāн̃чарāтре"),
    ("Панчаратра", "Пāн̃чарāтра"),
    ("пāн̃чарāтр", "пāн̃чарāтр"),
    ("Кришнамачарьей", "Кр̣шн̣амāчāрйей"),
    ("Кришнамачарьи", "Кр̣шн̣амачāрйи"),
    ("Кришнамачарья", "Кр̣шн̣амāчāрйа"),
    ("Муктапиде", "Муктāпӣд̣е"),
    ("Муктапида", "Муктāпӣд̣а"),
    ("йоганг", "йогāн̇г"),
]

# longest left side first, so «асанами» is not cut to «āсана» + «ми»
_ORDER = sorted(FORMS, key=lambda p: -len(p[0]))
_WORD = re.compile(r"[А-Яа-яЁё\u0300-\u036fӣӯ]+")


def fix_word(word):
    for src, dst in _ORDER:
        if word.startswith(src):
            return dst + word[len(src):]
        cap = src[:1].upper() + src[1:]
        if word.startswith(cap):
            return dst[:1].upper() + dst[1:] + word[len(cap):]
    return word


def fix(text):
    """Rewrite one Russian string: only the marks of the table are added."""
    if not isinstance(text, str) or not text:
        return text
    return _WORD.sub(lambda m: fix_word(m.group(0)), text)


def fix_tree(obj, skip_keys=("lines",)):
    """Walk a piece of data and fix every Russian string in it.

    `lines` (verse text in Devanāgarī / IAST / Cyrillic transliteration) is
    never touched: those lines are quotations of the editions.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip_keys:
                continue
            if isinstance(v, str):
                obj[k] = fix(v)
            else:
                fix_tree(v, skip_keys)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, str):
                obj[i] = fix(v)
            else:
                fix_tree(v, skip_keys)
    return obj


def fix_blocks(blocks):
    """About / dating blocks: p, h2..h4 (`html`), list items, quotes, tables."""
    for b in blocks:
        if "html" in b:
            b["html"] = fix(b["html"])
        if "items" in b:
            for item in b["items"]:
                if isinstance(item, dict):
                    item["html"] = fix(item["html"])
                else:
                    b["items"][b["items"].index(item)] = fix(item)
        if "paragraphs" in b:
            b["paragraphs"] = [fix(p) for p in b["paragraphs"]]
        if "rows" in b:
            b["rows"] = [[fix(c) for c in row] for row in b["rows"]]
    return blocks


def fix_sections(sections):
    """Pose sections: prose, notes and labels; verse lines are never touched."""
    for sec in sections:
        if sec.get("type") == "verse":
            continue
        if "label" in sec:
            sec["label"] = fix(sec["label"])
        for key in ("paragraphs",):
            if key in sec:
                sec[key] = [fix(p) for p in sec[key]]
        if "items" in sec:
            for item in sec["items"]:
                if isinstance(item, dict):
                    item["html"] = fix(item["html"])
                else:
                    sec["items"][sec["items"].index(item)] = fix(item)
        if "groups" in sec:
            sec["groups"] = [[[fix(t), g] for t, g in group] for group in sec["groups"]]
        if "pairs" in sec:
            sec["pairs"] = [[fix(t), g] for t, g in sec["pairs"]]
    return sections


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    changed = []

    for name in ("treatises.json", "ahirbudhnya-samhita.json",
                 "vasishtha-samhita.json"):
        path = root / "data" / name
        data = json.loads(path.read_text())

        def walk(obj, path_=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "en":
                        continue
                    walk(v, path_ + "/" + k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, path_ + "[%d]" % i)
            elif isinstance(obj, str):
                new = fix(obj)
                if new != obj:
                    changed.append((name + path_, obj, new))

        walk(data)
    print("strings that would change:", len(changed))
    for where, old, new in changed[:60]:
        print(" ", where)
        for a, b in zip(old.split(" "), new.split(" ")):
            if a != b:
                print("     ", a, "->", b)
