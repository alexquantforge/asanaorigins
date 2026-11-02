# -*- coding: utf-8 -*-
"""Проверка статических страниц, которые пишет tools/prerender.js.

Скрипт ничего не меняет: он смотрит на готовые файлы и говорит, что в них не
так. Это дешёвая замена «открыть и посмотреть» — и способ заметить, что
страницы отстали от данных (тогда `node tools/prerender.js` надо повторить).

    cd tools && python3 prerender_check.py
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://alexquantforge.github.io/asanaorigins"
PAGES = sorted(p for p in ROOT.rglob("index.html") if "node_modules" not in p.parts)

# страница -> адрес, который должен стоять у неё в canonical
problems = []
warnings = []


def rel_dir(page):
    return page.parent.relative_to(ROOT).as_posix() + "/"


def text_of(html):
    body = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()


def check(page):
    html = page.read_text(encoding="utf-8")
    where = page.relative_to(ROOT).as_posix()
    url = SITE + "/" + ("" if page.parent == ROOT else rel_dir(page))

    def need(cond, message):
        if not cond:
            problems.append("%s: %s" % (where, message))

    need(html.count("<title>") == 1, "нет одного <title>")
    title = re.search(r"<title>(.*?)</title>", html)
    need(title and len(title.group(1)) > 4, "пустой <title>")

    need(html.count("<h1") == 1, "заголовков h1: %d" % html.count("<h1"))
    need('rel="canonical" href="%s"' % url in html, "canonical не совпадает с адресом")
    need('rel="alternate" hreflang="ru"' in html and 'rel="alternate" hreflang="en"' in html,
         "нет пары hreflang ru/en")
    need('name="description" content="' in html, "нет описания")

    ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    need(ld is not None, "нет микроразметки")
    if ld:
        try:
            json.loads(ld.group(1))
        except ValueError as err:
            problems.append("%s: микроразметка не разбирается: %s" % (where, err))
    else:
        pass

    need("data-static=\"1\"" in html, "нет data-static")
    need(not re.search(r'href="#/(pose|about|chapter|appendix|notes)', html),
         "остались ссылки на хеш-маршруты")

    length = len(text_of(html))
    need(length > 1200, "текста в HTML всего %d символов" % length)

    # ссылки внутри сайта должны вести на существующий файл
    base = page.parent
    for href in re.findall(r'href="([^"#][^"]*)"', html):
        if re.match(r"^(https?:|mailto:|data:|//)", href):
            continue
        clean = href.split("#")[0].split("?")[0]
        if not clean:
            continue
        target = (base / unquote(clean)).resolve()
        if clean.endswith("/"):
            target = target / "index.html"
        try:
            exists = target.exists()
        except OSError:          # имя файла источника длиннее, чем терпит система
            exists = True
        if not exists:
            problems.append("%s: битая ссылка %s" % (where, href))


def check_sitemap():
    path = ROOT / "sitemap.xml"
    if not path.exists():
        problems.append("нет sitemap.xml")
        return
    xml = path.read_text(encoding="utf-8")
    listed = set(re.findall(r"<loc>(.*?)</loc>", xml))
    have = set()
    for page in PAGES:
        url = SITE + "/" + ("" if page.parent == ROOT else rel_dir(page))
        have.add(url)
    for url in sorted(have - listed):
        problems.append("sitemap.xml: нет %s" % url)
    for url in sorted(listed - have):
        problems.append("sitemap.xml: лишний адрес %s" % url)


def check_robots():
    path = ROOT / "robots.txt"
    if not path.exists():
        problems.append("нет robots.txt")
        return
    text = path.read_text(encoding="utf-8")
    if "Sitemap: " + SITE + "/sitemap.xml" not in text:
        problems.append("robots.txt: не указан sitemap")


def check_freshness():
    newest = 0
    for pattern in ("data/*.json", "assets/app.js", "assets/style.css"):
        for path in ROOT.glob(pattern):
            newest = max(newest, path.stat().st_mtime)
    stale = [p for p in PAGES if p.stat().st_mtime < newest]
    if stale:
        warnings.append("страницы старше данных: %d — пересоберите: node tools/prerender.js"
                        % len(stale))


def main():
    for page in PAGES:
        check(page)
    check_sitemap()
    check_robots()
    check_freshness()

    for line in warnings:
        print("  ! " + line)
    for line in problems:
        print("  × " + line)
    print("\n  страниц: %d · проблем: %d · предупреждений: %d"
          % (len(PAGES), len(problems), len(warnings)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
