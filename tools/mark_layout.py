#!/usr/bin/env python3
"""Сторож для знаков кириллической транслитерации (м̣, н̣, н̇, ш́, ā).

Знаки рисует CSS: буква лежит в `<span class="mk">` — inline-block шириной
ровно в одну букву, а точка, черта или акут — в `::before`/`::after` этого
бокса, по центру. Всё построение держится на одном условии: **внутри `.mk`
буква стоит там, где стоит бокс**. Стоило один раз это нарушить, и буквы
наехали друг на друга: стих набран с висячим отступом (`.verse-lines > span`
даёт `padding-left` + отрицательный `text-indent`), а `text-indent` —
свойство наследуемое, поэтому внутри inline-block он применялся второй раз
и сдвигал букву влево, на предыдущую.

Скрипт проверяет ровно эти условия:

* `.mk` гасит наследуемые `text-indent` и `letter-spacing`;
* настоящий комбинируемый знак внутри `.mk > .cmb` не занимает места;
* если где-то в CSS остался отрицательный `text-indent`, он не попадает
  в `.mk` (то есть гашение на месте).

Запуск: `python3 tools/mark_layout.py`. Код выхода 1 — есть находки.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "assets" / "style.css"


def rules(css: str) -> list[tuple[str, str]]:
    """Плоский список (селектор, тело правила) без вложенности @media."""
    out: list[tuple[str, str]] = []
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selector = " ".join(m.group(1).split())
        body = m.group(2)
        if selector.startswith("@") or not selector:
            continue
        out.append((selector, body))
    return out


def declaration(body: str, prop: str) -> str | None:
    for part in body.split(";"):
        if ":" not in part:
            continue
        name, _, value = part.partition(":")
        if name.strip() == prop:
            return value.strip()
    return None


def main() -> int:
    css = CSS.read_text(encoding="utf-8")
    problems: list[str] = []
    parsed = rules(css)

    mk = [(sel, body) for sel, body in parsed if sel == ".mk"]
    if not mk:
        problems.append("в style.css нет правила `.mk` — знаки нечем рисовать")
    else:
        body = mk[0][1]
        for prop in ("text-indent", "letter-spacing"):
            value = declaration(body, prop)
            if value is None:
                problems.append(
                    f"`.mk` не гасит `{prop}`: наследуемое значение сдвинет букву "
                    "внутри бокса, и она ляжет на соседнюю"
                )
            elif value.rstrip(";") not in ("0", "0em", "0px"):
                problems.append(f"`.mk` задаёт `{prop}: {value}` — ожидался ноль")

    cmb = [(sel, body) for sel, body in parsed if sel.startswith(".mk > .cmb")]
    if not cmb:
        problems.append("нет правила `.mk > .cmb`: настоящий знак займёт место в строке")
    else:
        value = declaration(cmb[0][1], "font-size")
        if value not in ("0", "0px", "0em"):
            problems.append(
                f"`.mk > .cmb` задаёт `font-size: {value}` — настоящий знак "
                "начнёт занимать место рядом с нарисованным"
            )

    # информационно: где вообще есть висячий отступ, из-за которого всё началось
    hanging = [
        sel
        for sel, body in parsed
        if (declaration(body, "text-indent") or "").lstrip().startswith("-")
    ]
    if hanging and not any(sel == ".mk" for sel, _ in mk):
        problems.append(
            "висячий отступ есть (" + ", ".join(hanging) + "), а гашения в `.mk` нет"
        )

    if problems:
        print("знаки транслитерации:")
        for p in problems:
            print("  •", p)
        return 1

    print("знаки транслитерации: бокс и знак на месте")
    if hanging:
        print("  висячий отступ: " + ", ".join(hanging) + " — внутри `.mk` погашен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
