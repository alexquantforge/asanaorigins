# -*- coding: utf-8 -*-
"""Surnames of the scholars who date the texts, written in Russian.

The short dating rows under a pose name are the site's own digest: who proposes
which date and on what grounds. In the Ahirbudhnya-saṃhitā volume that digest
came from Russian prose («Ф. Отто Шрадер», «Д. Вьюстик», «Марион Растелли»),
but the table in the Vasiṣṭha Saṃhitā volume names the same kind of people by
their Latin bibliography keys («Birch 2011», «Wujastyk 2017»). Two treatises
were therefore reading differently in the same column.

This module gives the Russian spelling of those names, and only of the names:
years, titles of works, quoted phrases («as shown below») and section names
(«Chronology») stay exactly as the editions print them, because they are
quotations. The full dating article is never touched — it is verbatim.

Every form below is the one the Russian editions themselves use; the place is
given next to it. Where an edition has a stress mark («Колá»), it is kept as a
combining acute on the Cyrillic letter, the same mark the site draws for «ш́».

Run `python3 authors.py` to see every rewrite it would make in the data.
"""

import re

# Latin spelling as the editions print it → Russian spelling they use.
NAMES = [
    # «Формулировка Гупты и Бёрча «date to the twelfth century»»,
    # «Бёрч (2011: прим. 8, 10)», «В прим. 81 Бёрч ссылается…» — Vasishtha, RU
    ("Birch", "Бёрч"),
    ("Gupta", "Гупта"),
    # «Раздел текста о позах переведён у Маллинсона и Синглтона (2017: 104…)»
    ("Mallinson", "Маллинсон"),
    ("Singleton", "Синглтон"),
    # «Буи (1994: 84) обнаружил цитату…», «выводы Буи» — Vasishtha, RU
    ("Bouy", "Буи"),
    # «Жерар Колá считает…» — Vasishtha, RU; the acute is the edition's stress
    ("Colas", "Кола\u0301"),
    # «Д. Вьюстик в статье 2017 года предполагает…» — Ahirbudhnya, RU
    ("Wujastyk", "Вьюстик"),
    # Neither Russian edition spells this name in Russian (only «Ruth Westoby»
    # in the bibliography), so this is the ordinary Russian rendering.
    ("Westoby", "Уэстоби"),
]

_ORDER = sorted(NAMES, key=lambda p: -len(p[0]))
_WORD = re.compile(r"\b(%s)\b" % "|".join(re.escape(k) for k, _ in _ORDER))
_MAP = dict(NAMES)


def ru(text):
    """One digest string: Russian surnames, the site's «и» instead of «&»."""
    if not isinstance(text, str) or not text:
        return text
    text = _WORD.sub(lambda m: _MAP[m.group(0)], text)
    text = re.sub(r"\s*&\s*", " и ", text)
    return text


def ru_summary(summary):
    """The short dating block: only the columns that name people.

    The block exists in two shapes: the site's own `datingSummary` keeps both
    languages ({who: {ru, en}}), the copy inside the dating section is a flat
    Russian row ({who: "…"}). Both are handled.
    """
    for item in summary.get("items", []):
        for key in ("who", "work", "basis"):
            value = item.get(key)
            if isinstance(value, dict) and "ru" in value:
                value["ru"] = ru(value["ru"])
            elif isinstance(value, str):
                item[key] = ru(value)
    return summary


if __name__ == "__main__":
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    changed = 0
    for name in ("vasishtha-samhita.json", "treatises.json"):
        path = root / "data" / name
        data = json.loads(path.read_text())
        blocks = []
        if "datingSummary" in data:
            blocks.append(data["datingSummary"])
        for treat in data.get("treatises", []):
            if "datingSummary" in treat:
                blocks.append(treat["datingSummary"])
        for block in blocks:
            for item in block.get("items", []):
                for key in ("who", "work"):
                    if key not in item:
                        continue
                    old, new = item[key]["ru"], ru(item[key]["ru"])
                    if old != new:
                        changed += 1
                        print(" %s" % name)
                        print("   was:", old)
                        print("   now:", new)
    print("strings that would change:", changed)
