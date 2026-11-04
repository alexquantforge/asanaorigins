# -*- coding: utf-8 -*-
"""Ни одного слова из двух алфавитов сразу.

Слово в русском тексте сайта пишется либо целиком кириллицей (со знаками
диакритики), либо целиком латиницей (IAST). Смесь внутри слова — ошибка набора:
«Нирṇaya» вместо «Нирн̣айа» или «Nirṇaya».

Одно исключение — долгое «ā»: прекомпонованной кириллической «а с макроном»
в Unicode нет, и карта транслитерации проекта (tools/translit.py) несёт макрон
латинской буквой. Такая «ā» стоит внутри кириллического слова и считается
кириллицей; всё остальное латинское внутри слова — ошибка.

Строки кода и имена файлов (`скачанное_jp2.zip`) не проверяются: это не слова
текста, а пример скрипта из источника.

    python3 tools/script_mix.py            проверить и напечатать находки
    python3 tools/script_mix.py --fix      заменить латинские знаки на кириллицу
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CYRILLIC = re.compile(r"[\u0400-\u04ff]")
LATIN = re.compile(r"[A-Za-z\u00c0-\u024f\u1e00-\u1eff]")
TAG = re.compile(r"<[^>]+>")
TOKEN = re.compile(r"[^\s«»„“”\"'()\[\],;:—–/|]+")
FILENAME = re.compile(r"[._/\\]|[a-z]{2,}\d|\d+[a-z]{2,}")
# сокращение латиницей перед кириллическим словом — не смесь: OCR-чтение
ABBREVIATION = re.compile(r"^[A-Z]{2,5}-[а-яёА-ЯЁ]")

# латинская буква с диакритикой → кириллическая основа + тот же знак
TO_CYRILLIC = {
    "ā": "а\u0304", "Ā": "А\u0304",
    "ī": "ӣ", "Ī": "Ӣ",
    "ū": "ӯ", "Ū": "Ӯ",
    "ṛ": "р\u0323", "Ṛ": "Р\u0323",
    "ṝ": "р\u0323\u0304",
    "ḷ": "л\u0323", "Ḷ": "Л\u0323",
    "ṃ": "м\u0323", "Ṃ": "М\u0323",
    "ṁ": "м\u0323", "Ṁ": "М\u0323",
    "ḥ": "х\u0323", "Ḥ": "Х\u0323",
    "ṅ": "н\u0307", "Ṅ": "Н\u0307",
    "ñ": "н\u0303", "Ñ": "Н\u0303",
    "ṭ": "т\u0323", "Ṭ": "Т\u0323",
    "ḍ": "д\u0323", "Ḍ": "Д\u0323",
    "ṇ": "н\u0323", "Ṇ": "Н\u0323",
    "ś": "ш\u0301", "Ś": "Ш\u0301",
    "ṣ": "ш\u0323", "Ṣ": "Ш\u0323",
    "á": "а\u0301", "Á": "А\u0301",
    "é": "е\u0301", "É": "Е\u0301",
    "í": "и\u0301", "ó": "о\u0301", "ú": "у\u0301",
}

# «ā» — из карты транслитерации, а не ошибка набора
ALLOWED = {"ā", "Ā"}


def walk(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, path + "/" + str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, path + f"[{index}]")
    elif isinstance(node, str):
        yield path, node


def scan(text: str) -> list[tuple[str, str]]:
    """Слова, где кириллица и латиница стоят вместе."""
    found: list[tuple[str, str]] = []
    for token in TOKEN.findall(TAG.sub(" ", text)):
        if not (CYRILLIC.search(token) and LATIN.search(token)):
            continue
        if FILENAME.search(token) or ABBREVIATION.match(token):
            continue
        foreign = {ch for ch in token if LATIN.match(ch)} - ALLOWED
        if foreign:
            found.append((token, "".join(sorted(foreign))))
    return found


# просмотренные вручную замены: латиница внутри слова, которую не заменить
# одной буквой (корень в скобках написан латиницей, соседние — кириллицей)
MANUAL = {
    "ни-gad": "ни-гад",
}


def fix_token(token: str) -> str:
    if token in MANUAL:
        return MANUAL[token]
    out = []
    for ch in token:
        out.append(TO_CYRILLIC.get(ch, ch))
    return "".join(out)


def fix_text(text: str) -> str:
    pieces = TAG.split(text)
    if len(pieces) == 1:
        return TOKEN.sub(lambda m: fix_token(m.group(0))
                         if scan(m.group(0)) else m.group(0), text)
    out = []
    for index, piece in enumerate(pieces):
        if index:
            out.append(TAG.findall(text)[index - 1])
        out.append(TOKEN.sub(lambda m: fix_token(m.group(0))
                             if scan(m.group(0)) else m.group(0), piece))
    return "".join(out)


def fix_value(node, path=""):
    """Правка с сохранением порядка ключей и отступов файла."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "code" and isinstance(value, str):
                continue                       # пример скрипта, не текст
            node[key] = fix_value(value, path + "/" + str(key))
        return node
    if isinstance(node, list):
        for index, value in enumerate(node):
            node[index] = fix_value(value, path + f"[{index}]")
        return node
    if isinstance(node, str):
        return fix_text(node)
    return node


def main() -> None:
    do_fix = "--fix" in sys.argv[1:]
    problems = 0
    files = sorted(DATA.glob("*.json"))
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        hits = []
        for where, text in walk(data):
            if where.endswith("/code"):
                continue
            for token, foreign in scan(text):
                hits.append((where, token, foreign))
        if not hits:
            continue
        problems += len(hits)
        print(f"{path.relative_to(ROOT)}: {len(hits)}")
        for where, token, foreign in hits:
            print(f"    {where[:60]:60s} {token!r}  ← {foreign}")
        if do_fix:
            fixed = fix_value(data)
            path.write_text(json.dumps(fixed, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
            print("    исправлено")

    # подписи сайта: разметка страницы и скрипт
    for name in ("index.html", "assets/app.js"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        hits = scan(text)
        if hits:
            problems += len(hits)
            print(f"{name}: {len(hits)}")
            for token, foreign in hits:
                print(f"    {token!r}  ← {foreign}")
            if do_fix:
                path.write_text(fix_text(text), encoding="utf-8")
                print("    исправлено")

    if not problems:
        print("слов из двух алфавитов нет")
    elif not do_fix:
        print("\nзапустите с --fix, чтобы заменить латинские знаки кириллицей")


if __name__ == "__main__":
    main()
