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
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

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


# --- якоря знаков для кириллицы --------------------------------------------
#
# В Spectral и Cormorant Garamond у кириллических букв нет якорей GPOS
# mark-to-base: знак (точка, акут, макрон) не прикрепляется к букве, а рисуется
# справа от неё — то есть поверх следующей буквы. В тексте сайта это лечит CSS
# (.mk в assets/style.css), но там, где разметку поставить нельзя — в <option>
# выпадающего списка, в title, в буфере обмена, — знак остаётся поверх соседней
# буквы. Поэтому якоря добавляются в сам шрифт: после этого знак встаёт на
# место в любом контексте, а .mk продолжает работать как раньше.
#
# Геометрия та же, что у .mk: точка снизу — на 0.26em ниже базовой линии,
# знаки сверху — над верхом буквы (высота строчной у Spectral 0.45em,
# у Cormorant 0.386em, поэтому отступ считается от чернил самой буквы).

# (комбинируемый знак, класс, зазор над верхом буквы в долях em; None — знак снизу)
MARK_CLASSES = [
    (0x0323, 0, None),      # точка снизу
    (0x0307, 1, 0.159),     # точка сверху
    (0x0304, 2, 0.186),     # макрон
    (0x0301, 3, 0.127),     # акут
    (0x0303, 4, 0.150),     # тильда
]

DOT_BELOW_TOP = -130       # верх точки снизу, единиц на 1000 em
DOT_BELOW_TOP_TAIL = -352  # у «р» хвост идёт под точкой — опускаем её под хвост


def _ink_bounds(font, glyph):
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph].draw(pen)
    return pen.bounds


def _anchor(x, y):
    a = ot.Anchor()
    a.Format = 1
    a.XCoordinate = int(round(x))
    a.YCoordinate = int(round(y))
    a.AnchorPoint = None
    return a


def add_cyrillic_mark_anchors(font):
    """Добавляет mark-to-base для кириллицы. Возвращает число букв со якорями."""
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    marks = []
    for code, cls, gap in MARK_CLASSES:
        name = cmap.get(code)
        if not name:
            return 0                       # шрифт нарезан без этих знаков
        marks.append((name, cls, gap))

    bases = []
    for code in range(0x0400, 0x0460):
        name = cmap.get(code)
        if name:
            bases.append(name)
    bases = sorted(set(bases), key=lambda n: font.getGlyphID(n))
    if not bases:
        return 0

    # --- MarkArray: куда ставить сам знак -------------------------------
    marks = sorted(marks, key=lambda m: font.getGlyphID(m[0]))
    mark_glyphs = [m[0] for m in marks]
    mark_records = []
    for name, cls, gap in marks:
        bb = _ink_bounds(font, name)
        cx = (bb[0] + bb[2]) / 2
        # знак сверху цепляется низом, знак снизу — верхом
        y = bb[1] if gap is not None else bb[3]
        rec = ot.MarkRecord()
        rec.Class = cls
        rec.MarkAnchor = _anchor(cx, y)
        mark_records.append(rec)
    mark_array = ot.MarkArray()
    mark_array.MarkRecord = mark_records
    mark_array.MarkCount = len(mark_records)

    # --- BaseArray: за что цепляется знак у каждой буквы ----------------
    base_records = []
    for name in bases:
        bb = _ink_bounds(font, name)
        if not bb:
            base_records.append(_no_anchors(len(MARK_CLASSES)))
            continue
        cx = (bb[0] + bb[2]) / 2
        top = bb[3]
        by_class = {cls: gap for _name, cls, gap in marks}
        anchors = []
        for cls in range(len(MARK_CLASSES)):
            gap = by_class.get(cls)
            if gap is None:
                y = DOT_BELOW_TOP_TAIL if name in ("uni0440", "afii10080") else DOT_BELOW_TOP
                anchors.append(_anchor(cx, y * upm / 1000))
            else:
                anchors.append(_anchor(cx, top + gap * upm))
        rec = ot.BaseRecord()
        rec.BaseAnchor = anchors
        base_records.append(rec)
    base_array = ot.BaseArray()
    base_array.BaseRecord = base_records
    base_array.BaseCount = len(base_records)

    sub = ot.MarkBasePos()
    sub.Format = 1
    sub.MarkCoverage = ot.Coverage()
    sub.MarkCoverage.glyphs = mark_glyphs
    sub.BaseCoverage = ot.Coverage()
    sub.BaseCoverage.glyphs = bases
    sub.ClassCount = len(MARK_CLASSES)
    sub.MarkArray = mark_array
    sub.BaseArray = base_array

    lookup = ot.Lookup()
    lookup.LookupType = 4
    lookup.LookupFlag = 0
    lookup.SubTable = [sub]
    lookup.SubTableCount = 1

    gpos = font["GPOS"].table
    gpos.LookupList.Lookup.append(lookup)
    idx = len(gpos.LookupList.Lookup) - 1
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)

    # Новую запись в FeatureList добавлять нельзя: по спецификации она должна
    # быть отсортирована по тегу, а HarfBuzz ищет в ней двоичным поиском —
    # дописанная в конец запись просто не находится. Поэтому наш lookup
    # добавляется к уже существующей фиче «mark».
    fidx = None
    for i, rec in enumerate(gpos.FeatureList.FeatureRecord):
        if rec.FeatureTag == "mark":
            rec.Feature.LookupListIndex.append(idx)
            rec.Feature.LookupCount = len(rec.Feature.LookupListIndex)
            if fidx is None:
                fidx = i
    if fidx is None:
        return len(bases)          # в этом шрифте нет фичи mark — нечего дополнять

    # фича mark должна быть подключена к кириллице и к DFLT
    for script in gpos.ScriptList.ScriptRecord:
        if script.ScriptTag not in ("cyrl", "DFLT"):
            continue
        langsys = script.Script.DefaultLangSys
        if langsys is None:
            langsys = ot.LangSys()
            langsys.LookupOrder = None
            langsys.ReqFeatureIndex = 0xFFFF
            langsys.FeatureIndex = []
            langsys.FeatureCount = 0
            script.Script.DefaultLangSys = langsys
        if fidx not in langsys.FeatureIndex:
            langsys.FeatureIndex.append(fidx)
            langsys.FeatureIndex.sort()
            langsys.FeatureCount = len(langsys.FeatureIndex)

    # знаки должны быть помечены как mark в GDEF, иначе их пропустят
    if "GDEF" in font and font["GDEF"].table.GlyphClassDef:
        classes = font["GDEF"].table.GlyphClassDef.classDefs
        for name in mark_glyphs:
            classes[name] = 3
        for name in bases:
            classes.setdefault(name, 1)
    return len(bases)


def _no_anchors(count):
    rec = ot.BaseRecord()
    rec.BaseAnchor = [_anchor(0, 0) for _ in range(count)]
    return rec


def subset_font(src, dst, unicodes, cyrillic_marks=True):
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
    if cyrillic_marks:
        add_cyrillic_mark_anchors(font)
    font.flavor = "woff2"
    subset.save_font(font, dst, opts)
    return os.path.getsize(dst)


def patch_existing(cyrillic_marks=True):
    """Добавить якоря знаков в уже собранные файлы assets/fonts.

    Нужен, когда исходников под рукой нет: файлы полные, нарезать заново не
    требуется — достаточно дописать GPOS."""
    for leaf, name, out, ranges in FONTS:
        path = os.path.join(OUT, out)
        if not os.path.exists(path):
            print("%-26s нет файла" % out)
            continue
        font = TTFont(path)
        count = add_cyrillic_mark_anchors(font) if cyrillic_marks else 0
        font.flavor = "woff2"
        font.save(path)
        print("%-26s букв со якорями: %d" % (out, count))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="node_modules")
    ap.add_argument("--marks-only", action="store_true",
                    help="добавить якоря знаков в готовые assets/fonts, не пересобирая")
    args = ap.parse_args()
    src = args.src
    os.makedirs(OUT, exist_ok=True)
    if args.marks_only:
        patch_existing()
        return
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
        size = subset_font(path, os.path.join(OUT, out), DEVA_RANGES, cyrillic_marks=False)
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
