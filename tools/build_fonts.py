#!/usr/bin/env python3
"""Собирает шрифты сайта в assets/fonts/*.woff2.

Зачем свои файлы, а не <link> на Google Fonts: Google отдаёт каждый шрифт
нарезанным по unicode-range, и диакритика кириллической транслитерации
попадает в разные файлы — основа (U+0430 «а») лежит в кириллическом наборе, а
знак долготы (U+0304) только в latin-ext. Браузер берёт букву из одного файла,
знак из другого, прикрепить знак к букве (GPOS mark-to-base) уже невозможно —
и черта садится не над буквой, а поверх неё. Здесь каждый шрифт — один файл, в
котором есть и кириллица, и все комбинируемые знаки, поэтому знаки рисует сам
шрифт, а не CSS.

Исходники берутся из npm-пакетов с полными (ненарезанными) файлами Google
Fonts:

    npm i @expo-google-fonts/spectral @expo-google-fonts/cormorant-garamond
    npm i @fontsource/noto-serif-devanagari

Запуск:

    python3 tools/build_fonts.py --src node_modules
"""

import argparse
import os
import shutil
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fonts")

LATIN = "U+0000-00FF,U+0100-017F,U+0180-024F,U+1E00-1EFF,U+2000-206F,U+20A0-20BF,U+2116,U+2122,U+2032-2033,U+2190-2199,U+2212"
COMBINING = "U+0300-036F,U+02B0-02FF,U+1AB0-1AFF,U+1DC0-1DFF"
CYRILLIC = "U+0400-045F,U+0460-052F,U+0490-0491,U+04B0-04B1,U+2DE0-2DFF,U+A640-A69F,U+1C80-1C8A"
DEVANAGARI = "U+0900-097F,U+1CD0-1CFF,U+1CF2-1CF4,U+A830-A839,U+A8E0-A8FF"

TEXT_RANGES = ",".join([LATIN, COMBINING, CYRILLIC])
DEVA_RANGES = ",".join([LATIN, DEVANAGARI])

# (пакет, каталог веса, имя файла TTF, имя файла на сайте, unicode-range)
FONTS = [
    ("spectral/400Regular", "Spectral_400Regular.ttf", "spectral-400.woff2", TEXT_RANGES),
    ("spectral/400Regular_Italic", "Spectral_400Regular_Italic.ttf", "spectral-400i.woff2", TEXT_RANGES),
    ("spectral/500Medium", "Spectral_500Medium.ttf", "spectral-500.woff2", TEXT_RANGES),
    ("spectral/600SemiBold", "Spectral_600SemiBold.ttf", "spectral-600.woff2", TEXT_RANGES),
    ("spectral/600SemiBold_Italic", "Spectral_600SemiBold_Italic.ttf", "spectral-600i.woff2", TEXT_RANGES),
    ("cormorant-garamond/400Regular", "CormorantGaramond_400Regular.ttf", "cormorant-400.woff2", TEXT_RANGES),
    ("cormorant-garamond/400Regular_Italic", "CormorantGaramond_400Regular_Italic.ttf", "cormorant-400i.woff2", TEXT_RANGES),
    ("cormorant-garamond/500Medium", "CormorantGaramond_500Medium.ttf", "cormorant-500.woff2", TEXT_RANGES),
    ("cormorant-garamond/600SemiBold", "CormorantGaramond_600SemiBold.ttf", "cormorant-600.woff2", TEXT_RANGES),
    ("cormorant-garamond/600SemiBold_Italic", "CormorantGaramond_600SemiBold_Italic.ttf", "cormorant-600i.woff2", TEXT_RANGES),
]

DEVA_FONTS = [
    ("noto-serif-devanagari/files/noto-serif-devanagari-devanagari-400-normal.woff2", "deva-400.woff2"),
    ("noto-serif-devanagari/files/noto-serif-devanagari-devanagari-500-normal.woff2", "deva-500.woff2"),
]

LICENSES = [
    ("@expo-google-fonts/spectral/LICENSE_FONT", "OFL-Spectral.txt"),
    ("@expo-google-fonts/cormorant-garamond/LICENSE_FONT", "OFL-CormorantGaramond.txt"),
    ("@fontsource/noto-serif-devanagari/LICENSE", "OFL-NotoSerifDevanagari.txt"),
]


def subset_font(src, dst, unicodes):
    opts = subset.Options()
    opts.flavor = "woff2"
    # layout features must survive: mark-to-base is what puts the macron, the
    # dot and the acute on the letter instead of beside it
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.name_legacy = True
    opts.name_languages = ["*"]
    opts.notdef_outline = True
    opts.recommended_glyphs = True
    opts.glyph_names = False
    opts.legacy_cmap = True
    opts.symbol_cmap = True
    opts.hinting = True
    font = subset.load_font(src, opts)
    subsetter = subset.Subsetter(options=opts)
    subsetter.populate(unicodes=subset.parse_unicodes(unicodes))
    subsetter.subset(font)
    font.flavor = "woff2"
    subset.save_font(font, dst, opts)
    return os.path.getsize(dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="node_modules")
    args = ap.parse_args()
    src = args.src
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for leaf, name, out, ranges in FONTS:
        path = os.path.join(src, "@expo-google-fonts", leaf, name)
        if not os.path.exists(path):
            sys.exit("нет файла: " + path)
        size = subset_font(path, os.path.join(OUT, out), ranges)
        total += size
        print("%-26s %6.1f KB" % (out, size / 1024))
    for rel, out in DEVA_FONTS:
        path = os.path.join(src, "@fontsource", rel)
        if not os.path.exists(path):
            sys.exit("нет файла: " + path)
        size = subset_font(path, os.path.join(OUT, out), DEVA_RANGES)
        total += size
        print("%-26s %6.1f KB" % (out, size / 1024))
    for rel, out in LICENSES:
        path = os.path.join(src, rel)
        if os.path.exists(path):
            shutil.copyfile(path, os.path.join(OUT, out))
            print("%-26s лицензия" % out)
    print("итого %.1f KB" % (total / 1024))


if __name__ == "__main__":
    main()
