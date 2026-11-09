#!/usr/bin/env python3
"""Сборка data/rudrayamala.json из двух томов статьи о реестре āсан.

Источник — русский и английский тома одной работы о разделе об āсанах
«Рудрайāмалоттаратантры» (пат̣алы 23–24) по изданию Судхāкара Мāлавӣйи
(Дели, 1999, с. 333–351). Тома — не перевод стихов, а исследование реестра:
состав перечня, датировка и сверка перевода с печатным изданием. Поэтому
стиховых карточек в этом файле нет и быть не может: строк стиха в томах
не приводится.

Что скрипт берёт из томов, а не набирает руками:

    «Приложение. Реестр āсан»      → пятьдесят семь строк реестра
                                     (№, IAST, кириллица по карте, русское
                                     название, пат̣ала) и страницы āсан
    таблица ключевых чтений        → раздел «Примечания к чтениям»
    колофон 23-й пат̣алы           → деванагарӣ, IAST, кириллица, перевод

Всё остальное — проза томов, разложенная по полям сайта. Каждая цитата
проверяется на присутствие в томе дословно; если фрагмент не найден, сборка
останавливается.

Диакритика названий поз сверяется с картой сайта: `translit.translit(IAST)`
должно совпасть со столбцом «Кириллица по карте» самого тома. Совпадает
во всех пятидесяти пяти полных строках; в двух строках том сокращает
столбец («и др.»), и это напечатано на странице приложения.

Запуск:  python3 tools/extract_rudrayamala.py [--check]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diacritics  # noqa: E402  (диакритика терминов и названий поз)
import script_mix  # noqa: E402  (одно слово — один алфавит)
import translit  # noqa: E402  (карта IAST → кириллица)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rudrayamala.json"

PDF = {
    "ru": ROOT / "sources" / "Рудрайāмалоттаратантра. Āсаны (пат̣алы 23–24).pdf",
    "en": ROOT / "sources" / "Rudrayāmalottaratantra. Āsanas (paṭalas 23–24).pdf",
}

# Границы столбцов приложения: x0 строки попадает в один из промежутков.
# У русского тома столбцов пять (есть «Кириллица по карте»), у английского
# четыре: №, название, английское название, пат̣ала.
REGISTER_COLUMNS = {
    "ru": [(0, 110), (150, 266), (266, 360), (360, 440), (440, 600)],
    "en": [(0, 110), (150, 306), (306, 424), (424, 600)],
}

NO_FOOTER = 720  # ниже этой линии — колонцифра, в таблицу она не входит

# ---------------------------------------------------------------- чтение PDF


def normalize(text: str) -> str:
    """Строка без переносов: для сверки цитат с томом."""
    text = text.replace("\u00ad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    return re.sub(r"\s+", " ", text).strip()


def page_lines(path: Path):
    doc = pymupdf.open(path)
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                x0, y0 = line["bbox"][0], line["bbox"][1]
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text and y0 <= NO_FOOTER:
                    yield x0, text


def read_register(path: Path, columns):
    """Строки приложения: номер начинает строку, продолжения дописываются."""
    rows = []
    current = None
    for x0, text in page_lines(path):
        index = next((i for i, (lo, hi) in enumerate(columns) if lo <= x0 < hi), None)
        if index is None:
            continue
        if index == 0:
            if re.fullmatch(r"\d+", text):
                current = {"no": int(text), "cells": {0: [text]}}
                rows.append(current)
            continue
        if current is None:
            continue
        current["cells"].setdefault(index, []).append(text)

    out = []
    for row in rows:
        get = lambda i: " ".join(row["cells"].get(i, [])).strip()  # noqa: E731
        out.append({"no": row["no"], "cells": [get(i) for i in range(len(columns))]})
    return out


# --------------------------------------------------------------- реестр āсан

# Ключ страницы позы: общий для всех трактатов, поэтому четырнадцать поз
# сохраняют прежние адреса, а сорок один получает адрес из своего имени.
KEYS = {
    1: "adhomundasana", 2: "padmasana", 3: "baddhapadmasana",
    4: "svastikasana", 5: "karmukasana", 6: "kukkutasana",
    7: "khagasana", 8: "lolasana", 9: "kukkutakriti",
    10: "uttamangasana", 11: "parvatasana", 12: "yonyasana",
    13: "baddhayonyasana", 14: "bhekasana", 15: "pranasana",
    16: "apanasana", 17: "virasana", 18: "granthibhedasana",
    20: "sarvangasana", 21: "mayurasana", 22: "jnanasana",
    23: "garudasana", 24: "kokilasana", 25: "anandamandirasana",
    26: "khanjanasana", 27: "pavanasana", 28: "sarpasana",
    29: "kakaskandhasana", 30: "kurmasana", 32: "kumbhirasana",
    33: "matsyasana", 34: "makarasana", 35: "simhasana",
    36: "kunjarasana", 37: "vyaghrasana", 38: "bhallukasana",
    39: "kamasana", 40: "vartulasana", 41: "mokshasana",
    42: "malasana", 43: "divyasana", 44: "ardhodayasana",
    45: "chandrasana", 46: "hamsasana", 47: "suryasana",
    48: "yogasana", 49: "gadasana", 50: "lakshmyasana",
    51: "kulyasana", 52: "brahmanasana", 53: "kshatriyasana",
    54: "vaishyasana", 55: "shudrasana", 56: "jatyasana",
    57: "pashavasana",
}

# Позы, описанные в реестре дважды: вторая строка не заводит вторую страницу,
# а дописывается к первой — на странице позы тогда стоят оба места реестра.
REPEATED = {19: 5, 31: 17}

# Имена, которые том печатает сокращённо в столбце кириллицы («и др.»):
# полные имена собраны из IAST по той же карте.
FULL_NAMES = {14: "Bhekāsana", 17: "Vīrāsana"}

# Что статья говорит именно об этой позе. Ключ — ключ страницы позы.
POSES_RU = {
    "padmasana": ["В статье Падмāсана отнесена к классическим медитативным "
                  "положениям — вместе со Свастикāсаной и Баддхападмāсаной."],
    "svastikasana": ["В статье Свастикāсана отнесена к классическим медитативным "
                     "положениям — вместе с Падмāсаной и Баддхападмāсаной."],
    "baddhapadmasana": ["В статье Баддхападмāсана отнесена к классическим "
                        "медитативным положениям — вместе с Падмāсаной и "
                        "Свастикāсаной."],
    "mayurasana": ["В статье Майӯрāсана названа среди акробатических поз, "
                   "требующих значительной силы, — вместе с Куккут̣āсаной."],
    "kukkutasana": ["В статье Куккут̣āсана названа среди акробатических поз, "
                    "требующих значительной силы, — вместе с Майӯрāсаной."],
    "kurmasana": ["В статье Кӯрмāсана отнесена к позам, названным по животным, — "
                  "вместе с Матсйāсаной и Вйāгхрāсаной.",
                  "Плод этой позы в томе назван так: Кӯрмāсана разрушает «всю "
                  "скверну и грехи века кали»."],
    "matsyasana": ["В статье Матсйāсана отнесена к позам, названным по животным, — "
                   "вместе с Кӯрмāсаной и Вйāгхрāсаной."],
    "vyaghrasana": ["В статье Вйāгхрāсана отнесена к позам, названным по животным, — "
                    "вместе с Кӯрмāсаной и Матсйāсаной."],
    "brahmanasana": ["В статье позы, названные по сословиям, выделены в особый слой: "
                     "плод в них сформулирован социально — брахманическое "
                     "достоинство, богатство, правдивость, служение. Слой "
                     "указывает на позднюю компилятивную руку, но датировать по "
                     "нему текст нельзя."],
    "kshatriyasana": ["В статье позы, названные по сословиям, выделены в особый слой: "
                      "плод в них сформулирован социально — брахманическое "
                      "достоинство, богатство, правдивость, служение. Слой "
                      "указывает на позднюю компилятивную руку, но датировать по "
                      "нему текст нельзя."],
    "vaishyasana": ["В статье позы, названные по сословиям, выделены в особый слой: "
                    "плод в них сформулирован социально — брахманическое "
                    "достоинство, богатство, правдивость, служение. Слой указывает "
                    "на позднюю компилятивную руку, но датировать по нему текст "
                    "нельзя."],
    "shudrasana": ["В статье позы, названные по сословиям, выделены в особый слой: "
                   "плод в них сформулирован социально — брахманическое "
                   "достоинство, богатство, правдивость, служение. Слой указывает "
                   "на позднюю компилятивную руку, но датировать по нему текст "
                   "нельзя."],
    "karmukasana": ["Плод этой позы в томе назван так: у практикующего "
                    "Кāрмукāсану «погибают все враги — болезни и прочее» (23.86)."],
    "granthibhedasana": ["Плод этой позы в томе назван так: Грантхибхедāсана "
                         "«показывает кхечарӣ и прочее» (23.82). В критическом "
                         "издании на этом месте стоит другое чтение — "
                         "khecarādi-phalapradam, «дающая плод кхечарӣ и прочего»; "
                         "принято чтение Мāлавӣйи, khecarādi-pradarśanam."],
    "khanjanasana": ["В томе сказано, что в Кхан̃джанāсане, как и в Сарпāсане, "
                     "совершается «питьё воздуха» (вāйу-пāна)."],
    "sarpasana": ["В томе сказано, что в Сарпāсане, как и в Кхан̃джанāсане, "
                  "совершается «питьё воздуха» (вāйу-пāна)."],
    "malasana": ["В томе отмечено, что в Мāлāсане стоит слово вāйавӣ-прийах̣ — "
                 "одно из мест, по которым «Уттаратантру» относят к поздним "
                 "сочинениям."],
}

POSES_EN = {
    "padmasana": ["The article counts Padmāsana among the classical meditative "
                  "postures, together with Svastikāsana and Baddhapadmāsana."],
    "svastikasana": ["The article counts Svastikāsana among the classical meditative "
                     "postures, together with Padmāsana and Baddhapadmāsana."],
    "baddhapadmasana": ["The article counts Baddhapadmāsana among the classical "
                        "meditative postures, together with Padmāsana and "
                        "Svastikāsana."],
    "mayurasana": ["The article lists Mayūrāsana among the acrobatic postures that "
                   "demand considerable strength, together with Kukkuṭāsana."],
    "kukkutasana": ["The article lists Kukkuṭāsana among the acrobatic postures that "
                    "demand considerable strength, together with Mayūrāsana."],
    "kurmasana": ["The article counts Kūrmāsana among the postures named after "
                  "animals, together with Matsyāsana and Vyāghrāsana.",
                  "The fruit of this posture is given as follows: Kūrmāsana destroys "
                  "“all impurity and the sins of the kali age”."],
    "matsyasana": ["The article counts Matsyāsana among the postures named after "
                   "animals, together with Kūrmāsana and Vyāghrāsana."],
    "vyaghrasana": ["The article counts Vyāghrāsana among the postures named after "
                    "animals, together with Kūrmāsana and Matsyāsana."],
    "brahmanasana": ["The article sets the postures named after the social classes "
                     "apart as a distinct layer: their fruit is formulated socially — "
                     "brahminical dignity, wealth, truthfulness, service. The layer "
                     "points to a late compilatory hand, but it cannot serve to date "
                     "the text."],
    "kshatriyasana": ["The article sets the postures named after the social classes "
                      "apart as a distinct layer: their fruit is formulated socially — "
                      "brahminical dignity, wealth, truthfulness, service. The layer "
                      "points to a late compilatory hand, but it cannot serve to date "
                      "the text."],
    "vaishyasana": ["The article sets the postures named after the social classes "
                    "apart as a distinct layer: their fruit is formulated socially — "
                    "brahminical dignity, wealth, truthfulness, service. The layer "
                    "points to a late compilatory hand, but it cannot serve to date "
                    "the text."],
    "shudrasana": ["The article sets the postures named after the social classes "
                   "apart as a distinct layer: their fruit is formulated socially — "
                   "brahminical dignity, wealth, truthfulness, service. The layer "
                   "points to a late compilatory hand, but it cannot serve to date "
                   "the text."],
    "karmukasana": ["The fruit of this posture is given as follows: for the "
                    "practitioner of Kārmukāsana “all enemies perish — disease and "
                    "the rest” (23.86)."],
    "granthibhedasana": ["The fruit of this posture is given as follows: "
                         "Granthibhedāsana “shows forth khecarī and the rest” "
                         "(23.82). The critical edition reads khecarādi-phalapradam "
                         "here, “granting the fruit of khecarī and the rest”; the "
                         "reading of Mālavīya, khecarādi-pradarśanam, has been "
                         "adopted."],
    "khanjanasana": ["The article states that Khañjanāsana, like Sarpāsana, is the "
                     "posture of the “drinking of air” (vāyu-pāna)."],
    "sarpasana": ["The article states that Sarpāsana, like Khañjanāsana, is the "
                  "posture of the “drinking of air” (vāyu-pāna)."],
    "malasana": ["The article notes that Mālāsana contains the word vāyavī-priyaḥ, "
                 "one of the features by which the Uttaratantra is assigned to a "
                 "late period."],
}


def build_poses(register_ru, register_en):
    """Страницы āсан: одна строка позы, а повторные строки — к первой."""
    by_no_ru = {row["no"]: row for row in register_ru}
    by_no_en = {row["no"]: row for row in register_en}

    groups = {}
    for no in sorted(by_no_ru):
        head = REPEATED.get(no, no)
        groups.setdefault(head, []).append(no)

    poses = []
    for index, head in enumerate(sorted(groups), start=1):
        numbers = groups[head]
        rows_ru = [by_no_ru[n] for n in numbers]
        rows_en = [by_no_en[n] for n in numbers]
        key = KEYS[head]

        first_ru, first_en = rows_ru[0], rows_en[0]
        iast = FULL_NAMES.get(head, re.sub(r"\s*\((?:I|II)\)\s*$", "",
                                           first_ru["cells"][1]).strip())
        name_ru = translit.translit(iast)
        gloss_ru = first_ru["cells"][3]
        if key == "virasana":
            gloss_ru = "поза героя; в реестре названа также Самāнāсаной"
        gloss_en = first_en["cells"][2]

        # ссылка в шапке позы. Отдельного поля chapter у позы нет: пат̣ала и
        # номер строки реестра уже стоят здесь, и второй раз их не печатаем.
        def refs(lang):
            order = []
            for row in rows_ru:
                if row["cells"][4] not in order:
                    order.append(row["cells"][4])
            parts = []
            for number in order:
                inside = [r["no"] for r in rows_ru if r["cells"][4] == number]
                word = f"пат̣ала {number}" if lang == "ru" else f"paṭala {number}"
                if lang == "ru":
                    nos = ("строки " if len(inside) > 1 else "строка ") + \
                        " и ".join(str(n) for n in inside)
                else:
                    nos = ("lines " if len(inside) > 1 else "line ") + \
                        " and ".join(str(n) for n in inside)
                parts.append(word + ", " + nos)
            return " · ".join(parts)

        def row_text(row, lang):
            # пометки «(I)» и «(II)» различают два описания одной позы, но в
            # русском столбце тома это уже сказано словами («второе описание»)
            parts = [re.sub(r"\s*\((?:I|II)\)\s*$", "", part).strip()
                     for part in row["cells"][1].split("/")]
            if lang == "ru":
                parts = [translit.translit(part) for part in parts]
                return (f"№ {row['no']} — " + " / ".join(parts)
                        + f", „{row['cells'][3]}“")
            raw = " / ".join(parts)
            return f"no. {row['no']} — {raw}, “{row['cells'][2]}”"

        def by_patala(rows, lang):
            order = []
            for row in rows:
                if row["cells"][-1] not in order:
                    order.append(row["cells"][-1])
            parts = []
            for number in order:
                inside = [row_text(r, lang) for r in rows if r["cells"][-1] == number]
                head = f"пат̣ала {number}" if lang == "ru" else f"paṭala {number}"
                parts.append(head + ": " + "; ".join(inside))
            return "; ".join(parts)

        lead_ru = ("Реестр «Рудрайāмалоттаратантры» (по изданию Мāлавӣйи 1999, "
                   "с. 333–351), "
                   + by_patala(rows_ru, "ru") + ".")
        lead_en = ("Register of the Rudrayāmalottaratantra (ed. Mālavīya 1999: "
                   "pp. 333–351), " + by_patala(rows_en, "en") + ".")
        if key == "virasana":
            lead_ru += (" В реестре эта поза названа двумя именами — Самāнāсана и "
                        "Вӣрāсана — и описана дважды.")
            lead_en += (" The register gives this posture two names, Samānāsana and "
                        "Vīrāsana, and describes it twice.")

        note_ru = ("Стихов и техники этой позы в двух томах статьи нет: тома "
                   "описывают реестр и датировку, а стихи не переводят. Поэтому у "
                   "позы здесь нет ни строк стиха, ни пословного разбора — их в "
                   "источнике нет, и дописывать их нельзя.")
        note_en = ("The two volumes of the article contain neither the verses nor "
                   "the technique of this posture: they describe the register and "
                   "its dating, and do not translate the verses. So this page has "
                   "neither verse lines nor a word-by-word analysis — the source "
                   "has none, and they are not to be supplied.")

        def blocks(extra, note, key_):
            out = [{"type": "p", "html": key_}]
            out += [{"type": "p", "html": t} for t in extra]
            out.append({"type": "note", "paragraphs": [note]})
            return out

        poses.append({
            "key": key,
            "iast": iast,
            "number": head,
            "name": {"ru": name_ru, "en": iast},
            "gloss": {"ru": gloss_ru, "en": gloss_en},
            "verses": {"ru": refs("ru"), "en": refs("en")},
            "text": {
                "ru": blocks(POSES_RU.get(key, []), note_ru, lead_ru),
                "en": blocks(POSES_EN.get(key, []), note_en, lead_en),
            },
            "register": numbers,
        })
    return poses


# ------------------------------------------------------------------ приложение


def register_table(register_ru, register_en):
    header_ru = ["№", "Название (IAST)", "Кириллица по карте",
                 "Русское название", "Пат̣ала"]
    header_en = ["No.", "Name (IAST)", "English rendering", "Paṭala"]

    by_no_ru = {row["no"]: row for row in register_ru}
    by_no_en = {row["no"]: row for row in register_en}

    def key_of(no):
        return KEYS.get(REPEATED.get(no, no))

    rows_ru = [header_ru]
    rows_en = [header_en]
    for no in sorted(by_no_ru):
        ru, en = by_no_ru[no], by_no_en[no]
        printed = ru["cells"][1]  # название так, как напечатано, с пометкой (I)/(II)
        cyr = ru["cells"][2]
        if "и др." in cyr:
            # том сократил столбец: полное имя собирается из IAST по карте
            parts = [re.sub(r"\s*\((?:I|II)\)\s*$", "", part).strip()
                     for part in printed.split("/")]
            cyr = " / ".join(translit.translit(part) for part in parts)
        rows_ru.append([
            str(no),
            {"html": '<a href="pose:' + key_of(no) + '">' + printed + "</a>"},
            cyr,
            ru["cells"][3],
            ru["cells"][4],
        ])
        rows_en.append([
            str(no),
            {"html": '<a href="pose:' + key_of(no) + '">' + printed + "</a>"},
            en["cells"][2],
            en["cells"][3],
        ])
    return rows_ru, rows_en


def collation_rows():
    """Таблица ключевых чтений: как напечатано в обоих томах."""
    return [
        ("23.34–35", "dvātriṃśad indum edāya…", "vāyu-siddhaye",
         "dvātriṃśad bindu-bhedāya…", "vāyu-vṛddhaye"),
        ("23.48", "kṣemavāyuṃ vikumbhayet", "", "sūkṣmavāyuṃ vikumbhayet", ""),
        ("23.49", "humbhakaṃ… dvandva-vāyu-layaṃ", "", "kumbhakam… sūkṣma-vāyu-layaṃ", ""),
        ("23.50", "sumbhāsanaṃ… dvicīrandhre", "yathāhutraṃ",
         "śubhāsanaṃ… sūcīrandhre", "yathāsūtraṃ"),
        ("23.58", "mūlam ākucya", "", "mūlam ākuñcya", ""),
        ("23.62", "kuryād dattvā nirāśrayaḥ", "", "kuryād dattvā nirāvile", ""),
        ("23.73", "bhrāmayen… ātmendvāmṛtaiḥ siktāṃ", "",
         "bhrāvayen… ātmacandrāmṛta-rasair", "āplutāṃ"),
        ("23.82", "khecarādi-phalapradam", "", "khecarādi-pradarśanam", ""),
        ("23.110–111", "maṇḍale… baddhe… bhayāt tvaktvā", "",
         "maṇḍule… baddhye… bhayān tyaktvā", ""),
        ("23.112ab", "sarvān vighnān vinirjitya nidrādoṣān", "",
         "sarvān vighnān vaśīkṛtya nidrādīn", ""),
    ]


def collation_table(lang):
    head = (["Стихи", "Критическое издание", "Мāлавӣйа (принято в переводе)"]
            if lang == "ru" else
            ["Verses", "Critical edition", "Mālavīya (adopted)"])
    rows = [head]
    for verses, crit_a, crit_b, mal_a, mal_b in collation_rows():
        crit = crit_a + ("… " if crit_b else "") + crit_b if crit_b else crit_a
        mal = mal_a + ("… " if mal_b else "") + mal_b if mal_b else mal_a
        rows.append([verses, crit, mal])
    return rows


# ------------------------------------------------------------------- цитаты

QUOTES = {
    "ru": [
        "самое загадочное из «йāмал»",
        "более пятидесяти текстов надписываются её именем",
        "Композиционная рамка — диалог",
        "бхāвāсананирн̣айа",
        "Объём памятника в разных изданиях различается",
        "Переведённый раздел содержит 57 описаний",
        "двāтрим̣ш́ад бинду-бхедāйа калпайед вāйу-вр̣ддхайе",
        "тридцать два — для прободения точек",
        "савйāпасавйайогена",
        "сто тысяч лакхов āсан",
        "Формула описания устойчива",
        "чирāн̃джӣвӣ",
        "Особый слой образуют позы, названные по сословиям",
        "Построчное сличение показало",
        "В рассмотренных ниже чтениях критическое издание",
        "гипотеза о систематическом сдвиге на единицу",
        "Перевод выполнен прямо с санскрита",
        "лин̇га-агра",
        "Точной даты у памятника нет",
        "Аргументы поздности",
        "вāйавӣ калā в стихе 25",
        "единственное в ш́айва-тантрах употребление термина хат̣хайога",
        "Оценка «не ранее XI–XII в.»",
        "Одна и та же поза может быть описана дважды",
        "Позы бхекāсана, кхечарāсана и махāбхекāсана описаны в одном разделе",
    ],
    "en": [
        "the most mysterious of all the yāmalas",
        "more than fifty texts are ascribed to it",
        "Its frame is a dialogue",
        "bhāvāsananirṇaya",
        "The extent of the work differs between editions",
        "The translated section contains 57 descriptions",
        "dvātriṃśad bindu-bhedāya",
        "thirty-two for the piercing of the points",
        "savyāpasavyayogena",
        "a hundred thousand lakhs of āsanas",
        "The formula of a description is stable",
        "cirāñjīvī",
        "A distinct layer is formed by the postures named after the social classes",
        "A line-by-line comparison showed",
        "In the six places examined",
        "the earlier hypothesis of a systematic shift by one",
        "The translation was made directly from Sanskrit",
        "liṅga-agra",
        "There is no precise date",
        "The arguments for lateness",
        "vāyavī kalā in verse 25",
        "the only occurrence of the term haṭhayoga in Śaiva tantras",
        "not earlier than the 11th–12th century",
        "The same posture may be described twice",
        "Bhekāsana, Khecarāsana and Mahābhekāsana are described in a single section",
    ],
}

# ------------------------------------------------------------------- датировка


def dating_summary(lang):
    if lang == "ru":
        return {
            "note": {"ru": "Точной даты у памятника нет, и в самом тексте "
                           "хронологических указаний не содержится.",
                     "en": "No precise date is established, and the text itself "
                           "contains no chronological indications."},
            "groups": [
                {
                    "title": {"ru": "Что говорят исследователи",
                              "en": "What the scholars say"},
                    "label": {"ru": "Цитата", "en": "Quotation"},
                    "items": [
                        {
                            "who": {"ru": "Т. Гудриян и С. Гупта, о йāмалах как жанре, "
                                          "с. 40",
                                    "en": "T. Goudriaan and S. Gupta on the yāmalas "
                                          "as a genre, p. 40"},
                            "when": {"ru": "период формирования жанра — до 900 года нашей эры",
                                     "en": "the formative period of the genre — "
                                           "before 900 CE"},
                            "work": {"ru": "“The time of their origin is difficult to "
                                           "assess. Their formative period in any case "
                                           "lies before A. D. 900.”",
                                     "en": "“The time of their origin is difficult to "
                                           "assess. Their formative period in any case "
                                           "lies before A. D. 900.”"},
                        },
                        {
                            "who": {"ru": "Т. Гудриян и С. Гупта, о нашей тантре, с. 47",
                                    "en": "T. Goudriaan and S. Gupta on our tantra, p. 47"},
                            "when": {"ru": "«безусловно, много позднее» эпохи старой "
                                           "йāмала-литературы",
                                     "en": "“certainly much later” than the old Yāmala "
                                           "literature"},
                            "whenNote": {"ru": "точного века здесь не названо",
                                         "en": "no century is named here"},
                            "work": {"ru": "“The text which is most often credited with "
                                           "being the Rudrayāmala proper, the "
                                           "Uttaratantra, is certainly much later than "
                                           "the period in which the old Yāmala "
                                           "literature flourished.”",
                                     "en": "“The text which is most often credited with "
                                           "being the Rudrayāmala proper, the "
                                           "Uttaratantra, is certainly much later than "
                                           "the period in which the old Yāmala "
                                           "literature flourished.”"},
                        },
                        {
                            "who": {"ru": "Дж. Берч, примечание 90",
                                    "en": "J. Birch, note 90"},
                            "when": {"ru": "не ранее XI века",
                                     "en": "not before the 11th century"},
                            "whenNote": {"ru": "единственное в ш́айва-тантрах "
                                               "употребление термина хат̣хайога — в 55-й "
                                               "главе; Берч сам оговаривает, что место "
                                               "может быть вставкой, но для датировки "
                                               "довод сохраняется: техническое "
                                               "употребление термина фиксируется не "
                                               "ранее XI века",
                                         "en": "the only occurrence of the term "
                                               "haṭhayoga in Śaiva tantras, in chapter "
                                               "55; Birch concedes that the passage may "
                                               "be an interpolation, yet the argument "
                                               "for dating stands: the technical use of "
                                               "the term is not attested before the "
                                               "11th century"},
                            "work": {"ru": "Birch, Jason. 2011. “The Meaning of haṭha "
                                           "in Early Haṭhayoga”. Journal of the American "
                                           "Oriental Society 131.4: 527–554.",
                                     "en": "Birch, Jason. 2011. “The Meaning of haṭha "
                                           "in Early Haṭhayoga”. Journal of the American "
                                           "Oriental Society 131.4: 527–554."},
                        },
                    ],
                },
                {
                    "title": {"ru": "Оценка автора статьи (не цитата)",
                              "en": "The article’s own assessment (not a quotation)"},
                    "label": {"ru": "На чём основано", "en": "Basis"},
                    "items": [
                        {
                            "who": {"ru": "Автор статьи",
                                    "en": "The author of the article"},
                            "when": {"ru": "не ранее XI–XII века",
                                     "en": "not earlier than the 11th–12th century"},
                            "whenNote": {"ru": "это вывод из совокупности признаков, а не "
                                               "цитата: ни один из процитированных "
                                               "авторов такого века не называет",
                                         "en": "an inference from the features listed, "
                                               "not a quotation: none of the authors "
                                               "cited names such a century"},
                            "work": {"ru": "развитая система чакр; зависимость от "
                                           "«Кулāрн̣аваы»; слово вāйавӣ для кун̣д̣алинӣ; "
                                           "перечень видов хат̣хайоги; слой поз, "
                                           "названных по сословиям",
                                     "en": "the developed system of cakras; dependence "
                                           "on the Kulārṇava; the term vāyavī for the "
                                           "kuṇḍalinī; the enumeration of types of "
                                           "haṭhayoga; the layer of postures named "
                                           "after the social classes"},
                        },
                    ],
                },
            ],
            "note2": {"ru": "Слой поз, названных по сословиям, датировать текст не "
                           "помогает: он выделяется надёжно, но даты не даёт.",
                      "en": "The layer of postures named after the social classes "
                            "cannot date the text: it stands out reliably, but it "
                            "offers no date."},
        }
    return {
        "note": {"en": "No precise date is established, and the text itself contains "
                       "no chronological indications.",
                 "ru": "Точной даты у памятника нет, и в самом тексте хронологических "
                       "указаний не содержится."},
        "groups": [
            {
                "title": {"en": "What the scholars say", "ru": "Что говорят исследователи"},
                "label": {"en": "Quotation", "ru": "Цитата"},
                "items": [
                    {
                        "who": {"en": "T. Goudriaan and S. Gupta on the yāmalas as a "
                                      "genre, p. 40",
                                "ru": "Т. Гудриян и С. Гупта, о йāмалах как жанре, с. 40"},
                        "when": {"en": "the formative period of the genre — before "
                                       "900 CE",
                                 "ru": "период формирования жанра — до 900 года нашей эры"},
                        "work": {"en": "“The time of their origin is difficult to assess. "
                                       "Their formative period in any case lies before "
                                       "A. D. 900.”",
                                 "ru": "“The time of their origin is difficult to assess. "
                                       "Their formative period in any case lies before "
                                       "A. D. 900.”"},
                    },
                    {
                        "who": {"en": "T. Goudriaan and S. Gupta on our tantra, p. 47",
                                "ru": "Т. Гудриян и С. Гупта, о нашей тантре, с. 47"},
                        "when": {"en": "“certainly much later” than the old Yāmala "
                                       "literature",
                                 "ru": "«безусловно, много позднее» эпохи старой "
                                       "йāмала-литературы"},
                        "whenNote": {"en": "no century is named here",
                                     "ru": "точного века здесь не названо"},
                        "work": {"en": "“The text which is most often credited with "
                                       "being the Rudrayāmala proper, the Uttaratantra, "
                                       "is certainly much later than the period in which "
                                       "the old Yāmala literature flourished.”",
                                 "ru": "“The text which is most often credited with being "
                                       "the Rudrayāmala proper, the Uttaratantra, is "
                                       "certainly much later than the period in which "
                                       "the old Yāmala literature flourished.”"},
                    },
                    {
                        "who": {"en": "J. Birch, note 90", "ru": "Дж. Берч, примечание 90"},
                        "when": {"en": "not before the 11th century",
                                 "ru": "не ранее XI века"},
                        "whenNote": {"en": "the only occurrence of the term haṭhayoga in "
                                           "Śaiva tantras, in chapter 55; Birch concedes "
                                           "that the passage may be an interpolation, yet "
                                           "the argument for dating stands: the technical "
                                           "use of the term is not attested before the "
                                           "11th century",
                                     "ru": "единственное в ш́айва-тантрах употребление "
                                           "термина хат̣хайога — в 55-й главе; Берч сам "
                                           "оговаривает, что место может быть вставкой, "
                                           "но для датировки довод сохраняется: "
                                           "техническое употребление термина "
                                           "фиксируется не ранее XI века."},
                        "work": {"en": "Birch, Jason. 2011. “The Meaning of haṭha in Early "
                                       "Haṭhayoga”. Journal of the American Oriental "
                                       "Society 131.4: 527–554.",
                                 "ru": "Birch, Jason. 2011. “The Meaning of haṭha in Early "
                                       "Haṭhayoga”. Journal of the American Oriental "
                                       "Society 131.4: 527–554."},
                    },
                ],
            },
            {
                "title": {"en": "The article’s own assessment (not a quotation)",
                          "ru": "Оценка автора статьи (не цитата)"},
                "label": {"en": "Basis", "ru": "На чём основано"},
                "items": [
                    {
                        "who": {"en": "The author of the article",
                                "ru": "Автор статьи"},
                        "when": {"en": "not earlier than the 11th–12th century",
                                 "ru": "не ранее XI–XII века"},
                        "whenNote": {"en": "an inference from the features listed, not a "
                                           "quotation: none of the authors cited names "
                                           "such a century",
                                     "ru": "это вывод из совокупности признаков, а не "
                                           "цитата: ни один из процитированных авторов "
                                           "такого века не называет"},
                        "work": {"en": "the developed system of cakras; dependence on the "
                                       "Kulārṇava; the term vāyavī for the kuṇḍalinī; the "
                                       "enumeration of types of haṭhayoga; the layer of "
                                       "postures named after the social classes",
                                 "ru": "развитая система чакр; зависимость от «Кулāрн̣аваы»; "
                                       "слово вāйавӣ для кун̣д̣алинӣ; перечень видов "
                                       "хат̣хайоги; слой поз, названных по сословиям"},
                    },
                ],
            },
        ],
        "note2": {"en": "The layer of postures named after the social classes cannot "
                        "date the text: it stands out reliably, but it offers no date.",
                  "ru": "Слой поз, названных по сословиям, датировать текст не "
                        "помогает: он выделяется надёжно, но даты не даёт."},
    }


# ---------------------------------------------------------------------- текст


def about_blocks(lang):
    if lang == "en":
        return EN_ABOUT
    return RU_ABOUT


def dating_blocks(lang):
    return EN_DATING if lang == "en" else RU_DATING


def notes_blocks(lang, tables):
    if lang == "ru":
        return [
            {"type": "subhead", "label": "Ключевые чтения: критическое издание и Мāлавӣйа"},
            {"type": "p", "html": "В десяти местах, разобранных в томе, критическое "
                                  "издание Университета Сам̣пӯрн̣āнанды читается "
                                  "иначе, чем издание Мāлавӣйи. Приняты чтения "
                                  "Мāлавӣйи: документ-источник воспроизводит его "
                                  "дословно."},
            {"type": "table", "rows": tables["ru"]},
            {"type": "p", "html": "Благодаря чтению Мāлавӣйи прояснились места, "
                                  "нечитаемые в критическом издании: «хумбхака» и "
                                  "«сумбхāсана» оказались кумбхака и «ш́убхāсана», "
                                  "«двичӣрандхра» — игольным отверстием, сквозь которое "
                                  "проходит нить, а „нирāш́райах̣“ — нирāвиле, «в чистом, "
                                  "незамутнённом [месте]»."},
            {"type": "note", "paragraphs": [
                "Нумерация стихов совпадает с изданием Мāлавӣйи (23–114 в пат̣але 23; "
                "9–37 в пат̣але 24), а не с критическим изданием; гипотеза о "
                "систематическом сдвиге на единицу, выдвинутая ранее по тексту "
                "распознавания, снята.",
                "В 24-й пат̣але найден иной дефект: объявления поз сдвинуты на "
                "полстиха, так что имя позы попадает в конец предыдущего описания. "
                "Содержание при этом не утрачено — утрачены только границы стихов.",
            ]},
        ]
    return [
        {"type": "subhead", "label": "Key readings: the critical edition and Mālavīya"},
        {"type": "p", "html": "In the ten places examined in the volume the critical "
                              "edition of Sampurnanand Sanskrit University reads "
                              "differently from the edition of Mālavīya. The readings "
                              "of Mālavīya have been adopted: the source document "
                              "reproduces him verbatim."},
        {"type": "table", "rows": tables["en"]},
        {"type": "p", "html": "Thanks to Mālavīya’s text, passages unreadable in the "
                              "critical edition become clear: “humbhaka” and "
                              "“sumbhāsana” turn out to be kumbhaka and śubhāsana, "
                              "“dvicīrandhra” — the eye of a needle through which the "
                              "thread is passed, and “nirāśrayaḥ” — nirāvile, “in a "
                              "clear, unmuddied [place]”."},
        {"type": "note", "paragraphs": [
            "The verse numbering coincides with that of Mālavīya (23–114 in paṭala 23; "
            "9–37 in paṭala 24), not with the critical edition; the earlier hypothesis "
            "of a systematic shift by one, based on OCR text, is withdrawn.",
            "In paṭala 24 a different defect was found: the announcements of the "
            "postures are displaced by half a verse, so that the name of a posture "
            "falls at the end of the preceding description. Nothing is lost in "
            "substance — only the verse boundaries.",
        ]},
    ]


RU_ABOUT = [
    {"type": "title", "html": "Āсаны «Рудрайāмалоттаратантры» (пат̣алы 23–24)"},
    {"type": "byline", "html": "состав перечня, датировка и сверка перевода с "
                               "изданием Судхāкара Мāлавӣйи"},

    {"type": "h2", "html": "Что это за текст"},
    {"type": "p", "html": "<strong>Рудрайāмала.</strong> «Рудрайāмала» — самое "
                          "загадочное из «йāмал»: более пятидесяти текстов "
                          "надписываются её именем, но текста «Рудрайāмала» без "
                          "добавлений не найти (Goudriaan &amp; Gupta 1981: 47). Тот "
                          "текст, который обычно принимают за собственно "
                          "Рудрайāмалу, — «Уттаратантра», последующая тантра."},
    {"type": "p", "html": "<strong>Рамка.</strong> Композиционная рамка — диалог: "
                          "богиня Āнандабхаиравӣ излагает учение супругу, Ш́иве, "
                          "обращаясь к нему как Махāбхайрава, Нāтха, Нӣлакан̣тха, "
                          "Вӣранāтха."},
    {"type": "p", "html": "<strong>Колофон 23-й пат̣алы</strong> (издание Мāлавӣйи "
                          "1999, с. 345) назван здесь целиком: деванāгарӣ, латинская "
                          "транслитерация, кириллическая — по карте проекта — и "
                          "перевод."},
    {"type": "deva", "lines": ["इति श्रीरुद्रयामले उत्तरतन्त्रे महातन्त्रोद्दीपने "
                               "भावासननिर्णये पाशवकल्पे षट्चक्रसारसङ्केते "
                               "सिद्धमन्त्रप्रकरणे भैरवीभैरवसंवादे त्रयोविंशः पटलः ॥ २३ ॥"]},
    {"type": "p", "html": "<em>Кириллическая транслитерация:</em> ити ш́рӣрудрайāмале "
                          "уттаратантре махāтантрод дӣпане бхāвāсананирн̣айе "
                          "пāш́авакалпе шат̣чакрасāрасан̇кете сиддхамантрапракаран̣е "
                          "бхаиравӣбхаиравасам̣вāде трайовим̣ш́ах̣ пат̣алах̣ || 23 ||"},
    {"type": "p", "html": "<em>Перевод:</em> «Так [завершается] в Ш́рӣ-Рудрайāмале, в "
                          "Уттаратантре, в „Махāтантроддӣпане“, в [разделе] "
                          "„определение бхāва и āсан“, в Пāш́ава-калпе, в „своде сути "
                          "шести чакр“, в разделе о мантрах сиддхов, в беседе Бхайравӣ "
                          "и Бхайравы — двадцать третья пат̣ала»."},
    {"type": "note", "paragraphs": [
        "Каждый том печатает колофон по-своему: русский — деванāгарӣ и кириллицей, "
        "латинской транслитерации в нём нет; английский — только латинской "
        "транслитерацией, без деванāгарӣ и без кириллицы. Сайт показывает каждый том "
        "так, как он напечатан, и не дописывает тому недостающие строки.",
    ]},
    {"type": "p", "html": "Сам колофон указывает на содержательные рубрики: "
                          "«бхāвāсананирн̣айа» — определение бхāва и āсана; "
                          "«шат̣чакра-сāрасан̇кета» — свод сути шести чакр; "
                          "«сиддхамантра-пракаран̣а» — раздел о мантрах сиддхов. Āсана, "
                          "таким образом, встроены в программу, где поза, дыхание, "
                          "чакры и мантра составляют одно целое, — и это объясняет, "
                          "почему плодом позы всюду оказывается не телесное удобство, "
                          "а изменение состояния дыхания и сознания."},
    {"type": "p", "html": "<strong>Объём.</strong> Объём памятника в разных изданиях "
                          "различается: у Дж. Вӣдйāсāгары — 66 глав, у С. Мāлавӣйи "
                          "первый том охватывает пат̣алы 1–45. Нумерация пат̣ал в "
                          "изданиях расходится, но асанный материал в них устойчиво "
                          "занимает 23-ю и 24-ю пат̣алы."},
    {"type": "p", "html": "<strong>Что здесь есть и чего нет.</strong> Раздел собран по "
                          "двум томам одной статьи — русскому и английскому. Тома "
                          "описывают состав реестра и датировку; стихи в них не "
                          "переводятся. Поэтому у āсан этого памятника здесь нет ни "
                          "строк стиха, ни пословного разбора: их в источнике нет. Что "
                          "сказано о позе в статье — сказано на странице этой позы."},

    {"type": "h2", "html": "Состав и логика перечня"},
    {"type": "p", "html": "Переведённый раздел содержит 57 описаний: 29 в 23-й пат̣але "
                          "(стихи 23–114) и 28 в 24-й (стихи 9–37). Стихи 23.34–35 "
                          "объявляют двойной перечень:"},
    {"type": "p", "html": "<em>двāтрим̣ш́ад бинду-бхедāйа калпайед вāйу-вр̣ддхайе…</em> — "
                          "«тридцать два — для прободения точек, [и ещё] тридцать два — "
                          "для возрастания ветра», то есть 32 позы, повторяемые в "
                          "прямом и обратном порядке (савйāпасавйайогена), дают 64."},
    {"type": "p", "html": "Отсюда ясно, что объём реестра — не 57 и не 64 «разных» "
                          "позы, а 32 положения, удваиваемые зеркальным повтором. "
                          "Пат̣ала 24 открывается гиперболой иного порядка: на земле "
                          "«сто тысяч лакхов āсан», созданных великими р̣ши на небе и в "
                          "пат̣āле (24.3). Обе цифры сосуществуют: первая — "
                          "техническая, вторая — риторическая."},
    {"type": "p", "html": "Формула описания устойчива: название позы → её плод → "
                          "техника (положение ног, рук, головы) → дыхание. Порядок "
                          "компонентов иногда меняется, но набор остаётся: техника без "
                          "плода в этом разделе почти не встречается. В 24-й пат̣але к "
                          "этому добавляется итог: стихи 38–39 обещают долголетие "
                          "(чирāн̃джӣвӣ), а через год практики — освобождение при жизни "
                          "(джӣванмукти)."},
    {"type": "p", "html": "Особый слой образуют позы, названные по сословиям: в них "
                          "плод сформулирован социально — брахманическое достоинство, "
                          "богатство, правдивость, служение. Это отчётливо отличается "
                          "от стихов 23–47, где плод всегда йогический, и указывает на "
                          "позднюю компилятивную руку. Датировать по этому слою текст "
                          "нельзя, но он выделяется надёжно."},
    {"type": "p", "html": "<strong>Две позы описаны дважды.</strong> Кāрмукāсана стоит в "
                          "реестре под номерами 5 и 19, Самāнāсана — под номерами 17 и "
                          "31. На сайте у каждой позы одна страница: оба места реестра "
                          "названы на ней, а в реестре остаются обе строки. Бхекāсана, "
                          "Кхечарāсана и Махāбхекāсана, наоборот, описаны в одном "
                          "разделе и потому занимают в реестре одну строку."},

    {"type": "h2", "html": "Плоды практик: четыре уровня"},
    {"type": "p", "html": "Плоды (пхала) в разделе распределяются по четырём уровням, и "
                          "это распределение само по себе характеризует текст:"},
    {"type": "table", "rows": [
        ["Уровень", "Содержание", "Примеры"],
        ["Дыхательный", "овладение вāйу, признаки кумбхаки",
         "шесть месяцев практики дают признаки совершенства в задержке дыхания и "
         "«великое счастье» (23.51); «питьё воздуха» (вāйу-пāна) в Кхан̃джанāсане и "
         "Сарпāсане"],
        ["Соматический", "устранение болезней и пороков тела",
         "у практикующего Кāрмукāсану «погибают все враги — болезни и прочее» (23.86); "
         "Кӯрмāсана разрушает «всю скверну и грехи века кали»"],
        ["Сиддхи", "сверхспособности",
         "вāйавӣ калā дарует «великую сиддхи» (23.25); Грантхибхедāсана «показывает "
         "кхечарӣ и прочее» (23.82); способность принимать любой облик (кāмарӯпа)"],
        ["Финальный", "бессмертие и освобождение",
         "долгожительство (чирāн̃джӣвӣ) и через год практики — джӣванмукти (24.38–39); "
         "бессмертие и статус сиддха (24.5)"],
    ]},
    {"type": "p", "html": "Такая последовательность нетипична для позднейших "
                          "хат̣ха-текстов, где акцент смещён к здоровью и долголетию: "
                          "здесь долголетие — лишь предпоследняя ступень, а последняя — "
                          "освобождение при жизни."},

    {"type": "h2", "html": "Издания и сверка"},
    {"type": "p", "html": "Работа велась по четырём текстам: комментированное издание "
                          "С. Мāлавӣйи (1999, санскрит и подстрочный "
                          "хинди-комментарий «Саралā» с вариантами), критическое "
                          "издание Университета Сам̣пӯрн̣āнанды, издание "
                          "Дж. Вӣдйāсāгары (третье издание, Калькутта, 1937, 66 глав) и, для "
                          "сверки объёма, сведения об издании Вāрендра-анусандхāна-самити "
                          "(1895)."},
    {"type": "p", "html": "Построчное сличение показало: документ-источник "
                          "воспроизводит текст Мāлавӣйи дословно — и стихи, и "
                          "хинди-комментарий. Все расхождения, зафиксированные ранее "
                          "при сверке с критическим изданием, оказались расхождениями "
                          "не документа с традицией, а Мāлавӣйи с критическим изданием; "
                          "в ряде мест повреждено именно последнее. Таблица ключевых "
                          "чтений — в разделе «Примечания к чтениям»."},
    {"type": "p", "html": "Нумерация стихов совпадает с изданием Мāлавӣйи (23–114 в "
                          "пат̣але 23; 9–37 в пат̣але 24), а не с критическим изданием: "
                          "гипотеза о систематическом сдвиге на единицу, выдвинутая "
                          "ранее по тексту распознавания, снята. В 24-й пат̣але найден "
                          "иной дефект — объявления поз сдвинуты на полстиха, так что "
                          "имя позы попадает в конец предыдущего описания; содержание "
                          "не утрачено, утрачены только границы стихов."},
    {"type": "note", "paragraphs": [
        "Расхождение двух томов. В выводах английский том говорит о «шести "
        "рассмотренных местах», русский — о «рассмотренных ниже чтениях», а таблица "
        "ключевых чтений содержит десять строк. Оба текста оставлены как напечатаны: "
        "сайт не правит том за томом и не выбирает между ними.",
    ]},

    {"type": "h2", "html": "Как сделан перевод"},
    {"type": "p", "html": "Перевод выполнен прямо с санскрита, без английского "
                          "посредника. Каждый стих представлен шестью слоями: "
                          "деванāгарӣ, IAST, кириллическая транслитерация с "
                          "диакритикой, пословный разбор, буквальный перевод и "
                          "литературный перевод; где есть хинди-комментарий Мāлавӣйи, "
                          "он переведён отдельным блоком, а расхождения с критическим "
                          "изданием отмечены в примечании."},
    {"type": "p", "html": "Отказ от английского посредника принципиален, и сверка это "
                          "подтвердила. Английский перевод документа-источника местами "
                          "добавляет толкования, которых в санскрите нет: лин̇га-агра "
                          "передан как «tip/base of the lingam» с пояснением "
                          "«perineum», хотя текст говорит только «кончик лин̇ги». При "
                          "переводе через английский такое пояснение неотличимо от "
                          "текста; при прямом переводе оно остаётся тем, что есть, — "
                          "интерполяцией переводчика."},
    {"type": "p", "html": "Кириллическая транслитерация выполнена по карте проекта: "
                          "санскритское -ya передаётся как -йа (Мāлавӣйа), а -ai- как "
                          "-аи- (Āнандабхаиравӣ), хотя в русской традиции приняты "
                          "написания «Мāлавӣя» и «Анандабхайрави». В цитатах из "
                          "англоязычных исследований санскритские слова сохранены в "
                          "оригинальном написании."},

    {"type": "h2", "html": "Выводы тома"},
    {"type": "list", "ordered": True, "items": [
        "Раздел об āсанах «Рудрайāмалоттаратантры» — один из наиболее полных "
        "до-хат̣хайогических реестров: 57 описаний (29 в пат̣але 23 и 28 в пат̣але 24), "
        "которые по стихам 23.34–35 мыслятся как 32 положения, удвоенные зеркальным "
        "повтором, то есть 64.",
        "Нумерация стихов документа совпадает с изданием Мāлавӣйи; документ "
        "воспроизводит его дословно, включая хинди-комментарий.",
        "В рассмотренных чтениях критическое издание Университета Сам̣пӯрн̣āнанды в "
        "большинстве случаев испорчено, и Мāлавӣйа даёт связный текст; именно его "
        "чтения приняты в переводе.",
        "Датировка: точная дата не установлена. Жанр йāмал сложился до 900 года, но "
        "«Уттаратантра» — «безусловно, много позднее» (Goudriaan &amp; Gupta 1981: 40, "
        "47); по совокупности признаков — не ранее XI–XII в. (оценка).",
        "Āсаны в этом памятнике — не гимнастика, а ступень прāн̣āйāмы: поза служит "
        "опорой дыханию, дыхание — прободению узлов и движению кун̣д̣алинӣ, а "
        "результат описывается в терминах сиддхи и освобождения.",
    ]},

    {"type": "h2", "html": "Литература"},
    {"type": "list", "items": [
        "Goudriaan, Teun &amp; Sanjukta Gupta. 1981. Hindu Tantric and Śākta "
        "Literature (A History of Indian Literature, ed. J. Gonda, vol. II, fasc. 2). "
        "Wiesbaden: Otto Harrassowitz. — С. 40 (прим. 39), 47 (прим. 62, 63).",
        "Birch, Jason. 2011. “The Meaning of haṭha in Early Haṭhayoga”. Journal of the "
        "American Oriental Society 131.4: 527–554 (примечание 90 — о 55-й главе "
        "уттаратантры).",
        "Mālavīya, Sudhākara, издание и комментарий. 1999. Rudrayāmalam (Uttaratantram), prathamo "
        "bhāgaḥ (1–45 paṭalātmakaḥ), «Saralā»-hindīvyākhyopetam. Delhi: Chaukhamba "
        "Sanskrit Pratishthan. — С. 333–351 (пат̣алы 23–24).",
        "Rudra Yamala. Varanasi: Yoga Tantra Department, Sampurnanand Sanskrit "
        "University. — Пат̣алы 23–24 (контрольный текст).",
        "Rudrayāmalottaratantra, издание Дж. Вӣдйāсāгары. Калькутта, третье "
        "издание, 1937 (66 глав).",
        "Miśra, Rāmāśaṅkara. 2015. Rudrayāmala Uttaratantra (Dharma aur Darśana). "
        "Delhi: Parimal Publications.",
        "Bagchi, P. C. — Cultural Heritage of India, vol. IV, p. 216–217. Цит. по "
        "Goudriaan &amp; Gupta 1981.",
        "Gonda, J. 1977. Medieval Religious Literature in Sanskrit. Wiesbaden. — P. 208.",
        "Pandey, K. C. 1963. Abhinavagupta: A Study in Indian Culture. Varanasi. — "
        "P. 554.",
    ]},
]

EN_ABOUT = [
    {"type": "title", "html": "The āsanas of the Rudrayāmalottaratantra (paṭalas 23–24)"},
    {"type": "byline", "html": "register, dating, and a collation of the translation "
                               "with the edition of Sudhākara Mālavīya"},

    {"type": "h2", "html": "What this text is"},
    {"type": "p", "html": "<strong>The Rudrayāmala.</strong> The Rudrayāmala is the most "
                          "mysterious of all the yāmalas: more than fifty texts are "
                          "ascribed to it, yet a “Rudrayāmala” without further "
                          "qualification is nowhere to be found (Goudriaan &amp; Gupta "
                          "1981: 47). The text usually taken to be the Rudrayāmala "
                          "proper is the Uttaratantra, the “later tantra”."},
    {"type": "p", "html": "<strong>Frame.</strong> Its frame is a dialogue: the goddess "
                          "Ānandabhairavī teaches her husband Śiva, addressing him as "
                          "Mahābhairava, Nātha, Nīlakaṇṭha and Vīranātha."},
    {"type": "p", "html": "<strong>The colophon of paṭala 23</strong> (ed. Mālavīya "
                          "1999: 345) is given here in full: Devanāgarī, IAST and a "
                          "translation."},
    {"type": "p", "html": "<em>IAST:</em> iti śrīrudrayāmale uttaratantre "
                          "mahātantrod dīpane bhāvāsananirṇaye pāśavakalpe "
                          "ṣaṭcakrasārasaṅkete siddhamantraprakaraṇe "
                          "bhairavībhairavasaṃvāde trayoviṃśaḥ paṭalaḥ || 23 ||"},
    {"type": "p", "html": "<em>Translation:</em> “Thus [ends] in the blessed "
                          "Rudrayāmala, in the Uttaratantra, in the "
                          "Mahātantrodīpana, in the determination of bhāva and āsana, "
                          "in the Pāśavakalpa, in the summary of the six cakras, in the "
                          "section on the mantras of the siddhas, in the dialogue of "
                          "Bhairavī and Bhairava — the twenty-third paṭala.”"},
    {"type": "note", "paragraphs": [
        "Each volume prints the colophon in its own scripts: the Russian one in "
        "Devanāgarī and Cyrillic, without a Latin transliteration; the English one in "
        "IAST alone, without Devanāgarī and without Cyrillic. The site shows each "
        "volume as it is printed and does not supply the lines a volume lacks.",
    ]},
    {"type": "p", "html": "The colophon itself names the substantive headings: "
                          "bhāvāsananirṇaya, “the determination of bhāva and āsana”; "
                          "ṣaṭcakra-sārasaṅketa, “the summary of the six cakras”; "
                          "siddhamantraprakaraṇa, “the section on the mantras of the "
                          "siddhas”. The āsanas are thus embedded in a programme in "
                          "which posture, breath, cakras and mantra form a single whole "
                          "— which explains why the fruit of a posture is never bodily "
                          "comfort but a change in the state of breath and "
                          "consciousness."},
    {"type": "p", "html": "<strong>Extent.</strong> The extent of the work differs between "
                          "editions: 66 chapters in J. Vidyāsāgara’s edition, while the "
                          "first volume of S. Mālavīya covers paṭalas 1–45. The "
                          "numbering of paṭalas differs too, but the āsana material "
                          "consistently falls in paṭalas 23–24."},
    {"type": "p", "html": "<strong>What is here and what is not.</strong> This section is "
                          "built from the two volumes of a single article, Russian and "
                          "English. The volumes describe the composition of the register "
                          "and its dating; they do not translate the verses. So the "
                          "āsanas of this work have here neither verse lines nor a "
                          "word-by-word analysis: the source has none. Whatever the "
                          "article says about a posture is said on that posture’s page."},

    {"type": "h2", "html": "Composition and logic of the register"},
    {"type": "p", "html": "The translated section contains 57 descriptions: 29 in paṭala "
                          "23 (verses 23–114) and 28 in paṭala 24 (verses 9–37). Verses "
                          "23.34–35 announce a double register:"},
    {"type": "p", "html": "<em>dvātriṃśad bindu-bhedāya kalpayed vāyu-vṛddhaye…</em> — "
                          "“thirty-two for the piercing of the points, [and another] "
                          "thirty-two for the increase of the wind”, that is, 32 "
                          "postures performed in direct and reverse order "
                          "(savyāpasavyayogena), giving 64."},
    {"type": "p", "html": "It follows that the size of the register is neither 57 nor 64 "
                          "“different” postures, but 32 positions doubled by mirror "
                          "repetition. Paṭala 24 opens with a hyperbole of another "
                          "order: “a hundred thousand lakhs of āsanas” on earth, created "
                          "by the great ṛṣis in heaven and in the nether world (24.3). "
                          "Both figures coexist: the first is technical, the second "
                          "rhetorical."},
    {"type": "p", "html": "The formula of a description is stable: name of the posture → "
                          "its fruit → technique (position of legs, arms, head) → "
                          "breath. The order of the components varies, but the set does "
                          "not: a technique without a fruit is almost never found here. "
                          "In paṭala 24 a conclusion is added: verses 38–39 promise "
                          "longevity (cirāñjīvī) and, after one year of practice, "
                          "liberation while alive (jīvanmukti)."},
    {"type": "p", "html": "A distinct layer is formed by the postures named after the "
                          "social classes, in which the fruit is formulated socially — "
                          "brahminical dignity, wealth, truthfulness, service. This "
                          "differs markedly from verses 23–47, where the fruit is always "
                          "yogic, and points to a late compilatory hand. The layer "
                          "cannot serve to date the text, but it stands out reliably."},
    {"type": "p", "html": "<strong>Two postures are described twice.</strong> "
                          "Kārmukāsana stands in the register as no. 5 and as no. 19, "
                          "Samānāsana as no. 17 and as no. 31. On this site each "
                          "posture has one page: both places in the register are named "
                          "on it, while the register keeps both lines. Bhekāsana, "
                          "Khecarāsana and Mahābhekāsana, by contrast, are described in "
                          "a single section and therefore occupy one line."},

    {"type": "h2", "html": "The fruits of practice: four levels"},
    {"type": "p", "html": "The fruits (phala) in this section fall into four levels, and "
                          "this distribution is itself characteristic of the text:"},
    {"type": "table", "rows": [
        ["Level", "Content", "Examples"],
        ["Respiratory", "mastery of vāyu, signs of kumbhaka",
         "six months of practice yield the marks of perfection in breath retention and "
         "“great bliss” (23.51); the “drinking of air” (vāyu-pāna) in Khañjanāsana and "
         "Sarpāsana"],
        ["Somatic", "removal of disease and bodily fault",
         "for the practitioner of Kārmukāsana “all enemies perish — disease and the "
         "rest” (23.86); Kūrmāsana destroys “all impurity and the sins of the kali age”"],
        ["Siddhis", "supernormal powers",
         "vāyavī kalā grants “great siddhi” (23.25); Granthibhedāsana “shows forth "
         "khecarī and the rest” (23.82); the power to assume any form (kāmarūpa)"],
        ["Final", "immortality and liberation",
         "longevity (cirāñjīvī) and, after a year of practice, jīvanmukti (24.38–39); "
         "immortality and the status of a siddha (24.5)"],
    ]},
    {"type": "p", "html": "Such a sequence is untypical of later haṭha texts, where the "
                          "emphasis shifts to health and longevity: here longevity is "
                          "only the penultimate stage, and the last is liberation while "
                          "alive."},

    {"type": "h2", "html": "Editions and the collation"},
    {"type": "p", "html": "Four witnesses were used: the annotated edition of "
                          "S. Mālavīya (1999: Sanskrit, interlinear Hindi commentary "
                          "“Saralā”, and variant readings), the critical edition of "
                          "Sampurnanand Sanskrit University, the edition of "
                          "J. Vidyāsāgara (third edition, 1937, 66 chapters) and, for the "
                          "extent of the work, the data on the Varendra Anusandhāna "
                          "Samiti edition (1895)."},
    {"type": "p", "html": "A line-by-line comparison showed that the translated document "
                          "reproduces Mālavīya verbatim — both the verses and the Hindi "
                          "commentary. All the divergences noted earlier in the "
                          "collation with the critical edition proved to be divergences "
                          "not between the document and the tradition, but between "
                          "Mālavīya and the critical edition; in a number of places it "
                          "is the latter that is corrupt. The table of key readings is "
                          "in the section “Notes on the readings”."},
    {"type": "p", "html": "The verse numbering of the translation coincides with that of "
                          "Mālavīya (23–114 in paṭala 23; 9–37 in paṭala 24), not with "
                          "the critical edition; the earlier hypothesis of a systematic "
                          "shift by one, based on OCR text, is withdrawn. In paṭala 24 a "
                          "different defect was found: the announcements of the postures "
                          "are displaced by half a verse, so that the name of a posture "
                          "falls at the end of the preceding description. Nothing is "
                          "lost in substance — only the verse boundaries."},
    {"type": "note", "paragraphs": [
        "A divergence between the two volumes. In its conclusions the English volume "
        "speaks of “the six places examined”, the Russian one of “the readings examined "
        "below”, while the table of key readings contains ten lines. Both texts are "
        "left as printed: the site does not correct one volume by the other, nor choose "
        "between them.",
    ]},

    {"type": "h2", "html": "Method of translation"},
    {"type": "p", "html": "The translation was made directly from Sanskrit, without an "
                          "English intermediary. Each verse is presented in six layers: "
                          "Devanāgarī, IAST, Cyrillic transliteration with diacritics, "
                          "word-by-word analysis, literal translation and literary "
                          "translation; where Mālavīya’s Hindi commentary exists, it is "
                          "translated in a separate block, and divergences from the "
                          "critical edition are noted in a remark."},
    {"type": "p", "html": "The refusal of an English intermediary is a matter of "
                          "principle, and the collation confirmed it. The English "
                          "translation of the source document occasionally adds "
                          "interpretations absent from the Sanskrit: liṅga-agra is "
                          "rendered “tip/base of the lingam” with the gloss “perineum”, "
                          "although the text says only “the tip of the liṅga”. When "
                          "translating through English, such a gloss is "
                          "indistinguishable from the text; in a direct translation it "
                          "remains what it is — an interpolation of the translator."},
    {"type": "p", "html": "The Cyrillic transliteration follows the map of the project: "
                          "Sanskrit -ya is rendered -йа (Мāлавӣйа), and -ai- is rendered "
                          "-аи- (Āнандабхаиравӣ), although the Russian tradition writes "
                          "«Мāлавӣя» and «Анандабхайрави». In quotations from "
                          "English-language scholarship Sanskrit words retain their "
                          "original spelling."},

    {"type": "h2", "html": "The volume’s conclusions"},
    {"type": "list", "ordered": True, "items": [
        "The āsana section of the Rudrayāmalottaratantra is one of the fullest "
        "pre-haṭhayogic registers: 57 descriptions (29 in paṭala 23 and 28 in "
        "paṭala 24), conceived in verses 23.34–35 as 32 positions doubled by mirror "
        "repetition, that is, 64.",
        "The verse numbering of the document coincides with Mālavīya’s edition; the "
        "document reproduces it verbatim, including the Hindi commentary.",
        "In the places examined, the critical edition of Sampurnanand Sanskrit "
        "University is corrupt, and Mālavīya offers coherent text; it is his readings "
        "that have been adopted.",
        "Dating: no precise date is established. The yāmala genre took shape before "
        "900 CE, but the Uttaratantra is “certainly much later” (Goudriaan &amp; Gupta "
        "1981: 40, 47); on the cumulative evidence, not earlier than the 11th–12th "
        "century (an assessment).",
        "In this work āsana is not gymnastics but a stage of prāṇāyāma: the posture "
        "supports the breath, the breath pierces the knots and moves the kuṇḍalinī, and "
        "the result is described in terms of siddhi and liberation.",
    ]},

    {"type": "h2", "html": "References"},
    {"type": "list", "items": [
        "Bagchi, P. C. “Tantras.” In: The Cultural Heritage of India, vol. IV, "
        "pp. 216–217. Cited via Goudriaan &amp; Gupta 1981.",
        "Birch, Jason. 2011. “The Meaning of haṭha in Early Haṭhayoga.” Journal of the "
        "American Oriental Society 131.4: 527–554.",
        "Gonda, J. 1977. Medieval Religious Literature in Sanskrit. Wiesbaden, p. 208.",
        "Goudriaan, Teun &amp; Sanjukta Gupta. 1981. Hindu Tantric and Śākta Literature "
        "(A History of Indian Literature, ed. J. Gonda, vol. II, fasc. 2). Wiesbaden: "
        "Otto Harrassowitz, pp. 40 (n. 39), 47 (nn. 62–63).",
        "Mālavīya, Sudhākara, издание и комментарий. 1999. Rudrayāmalam (Uttaratantram), prathamo "
        "bhāgaḥ (1–45 paṭalātmakaḥ), “Saralā”-hindīvyākhyopetam. Delhi: Chaukhamba "
        "Sanskrit Pratishthan, pp. 333–351.",
        "Miśra, Rāmāśaṅkara. 2015. Rudrayāmala Uttaratantra (Dharma aur Darśana). Delhi: "
        "Parimal Publications.",
        "Pandey, K. C. 1963. Abhinavagupta: A Study in Indian Culture. Varanasi, p. 554.",
        "Rudra Yamala. Varanasi: Yoga Tantra Department, Sampurnanand Sanskrit "
        "University (control text, paṭalas 23–24).",
        "Rudrayāmalottaratantra, ed. Jīvānanda Vidyāsāgara Bhaṭṭācārya. Calcutta, 3rd "
        "edition, 1937 (66 chapters).",
    ]},
]

RU_DATING = [
    {"type": "p", "html": "Точной даты у памятника нет, и в самом тексте хронологических "
                          "указаний не содержится. Наиболее определённые суждения "
                          "принадлежат Т. Гудрияну и С. Гупте."},
    {"type": "h3", "html": "О йāмалах как жанре (Goudriaan &amp; Gupta 1981: 40)"},
    {"type": "quote", "paragraphs": [
        "“The time of their origin is difficult to assess. Their formative period in "
        "any case lies before A. D. 900.”",
        "«Время их возникновения оценить трудно. Во всяком случае, период их "
        "формирования лежит до 900 года нашей эры»",
    ]},
    {"type": "h3", "html": "О нашей тантре (Goudriaan &amp; Gupta 1981: 47)"},
    {"type": "quote", "paragraphs": [
        "“The text which is most often credited with being the Rudrayāmala proper, the "
        "Uttaratantra, is certainly much later than the period in which the old Yāmala "
        "literature flourished.”",
        "«Текст, который чаще всего считают собственно Рудрайāмалой, — Уттаратантра, — "
        "безусловно, много позднее того периода, когда процветала старая "
        "йāмала-литература».",
    ]},
    {"type": "p", "html": "Аргументы поздности, перечисленные там же (с. 47), частью "
                          "приложимы прямо к нашему разделу: развитая система чакр; "
                          "зависимость от «Кулāрн̣аваы»; употребление слова вāйавӣ для "
                          "кун̣д̣алинӣ (в нашем тексте — вāйавӣ калā в стихе 25 и "
                          "вāйавӣ-прийах̣ в Мāлāсане); перечень видов хат̣хайоги. Там же "
                          "указано, что Пандей, Багчи и Гонда также считают "
                          "«Уттаратантра» относительно поздней (прим. 63; цит. по "
                          "Гудрияну)."},
    {"type": "p", "html": "Наконец, Дж. Берч отмечает единственное в ш́айва-тантрах "
                          "употребление термина хат̣хайога — в 55-й главе "
                          "«Рудрайāмалоттаратантраы», оговаривая сомнительность этого "
                          "места (Birch 2011, примечание 90). Для датировки довод "
                          "сохраняется: техническое употребление термина фиксируется не "
                          "ранее XI века."},
    {"type": "p", "html": "<strong>Итог.</strong> Точная дата не установлена, "
                          "общепринятого века у «Уттаратантра» нет. Жанр йāмал сложился "
                          "до 900 года, но наш текст — «безусловно, много позднее». Оценка "
                          "«не ранее XI–XII века», которой держится статья, — вывод из "
                          "совокупности перечисленных признаков, а не цитата: ни один из "
                          "процитированных авторов такого века не называет."},
    {"type": "note", "paragraphs": [
        "Слой поз, названных по сословиям, датировать текст не помогает: в них плод "
        "сформулирован социально, и это отчётливо отличается от стихов 23–47, где плод "
        "всегда йогический. Слой выделяется надёжно, но даты не даёт.",
    ]},
]

EN_DATING = [
    {"type": "p", "html": "There is no precise date, and the text itself contains no "
                          "chronological indications. The most definite statements "
                          "belong to T. Goudriaan and S. Gupta."},
    {"type": "h3", "html": "On the yāmalas as a genre (Goudriaan &amp; Gupta 1981: 40)"},
    {"type": "quote", "paragraphs": [
        "“The time of their origin is difficult to assess. Their formative period in "
        "any case lies before A. D. 900.”",
    ]},
    {"type": "h3", "html": "On our tantra (Goudriaan &amp; Gupta 1981: 47)"},
    {"type": "quote", "paragraphs": [
        "“The text which is most often credited with being the Rudrayāmala proper, the "
        "Uttaratantra, is certainly much later than the period in which the old Yāmala "
        "literature flourished.”",
    ]},
    {"type": "p", "html": "The arguments for lateness listed there (p. 47) apply in part "
                          "directly to our section: the developed system of cakras; "
                          "dependence on the Kulārṇava; the use of the term vāyavī for "
                          "the kuṇḍalinī (in our text — vāyavī kalā in verse 25 and "
                          "vāyavī-priyaḥ in Mālāsana); the enumeration of types of "
                          "haṭhayoga. The same page notes that Pandey, Bagchi and Gonda "
                          "likewise regard the Uttaratantra as a relatively late text "
                          "(note 63; cited via Goudriaan)."},
    {"type": "p", "html": "Finally, J. Birch notes the only occurrence of the term "
                          "haṭhayoga in Śaiva tantras — in the fifty-fifth chapter of "
                          "the Rudrayāmalottaratantra — while conceding that the passage "
                          "may be an interpolation (Birch 2011, note 90). The argument for "
                          "dating stands either way: the technical use of the term is "
                          "not attested before the eleventh century."},
    {"type": "p", "html": "<strong>In sum.</strong> No precise date has been established, "
                          "and there is no received century for the Uttaratantra. The "
                          "yāmala genre took shape before 900 CE, but our text is "
                          "“certainly much later”. The estimate “not earlier than the "
                          "11th–12th century”, which the article adopts, is an inference "
                          "from the features listed above, not a quotation: none of the "
                          "authors cited names such a century."},
    {"type": "note", "paragraphs": [
        "The layer of postures named after the social classes cannot date the text: "
        "their fruit is formulated socially, which differs markedly from verses 23–47, "
        "where the fruit is always yogic. The layer stands out reliably, but it offers "
        "no date.",
    ]},
]


# ------------------------------------------------------------------ проверки


def verify(lang: str, text: str, where: str, quotes=QUOTES):
    flat = normalize(text)
    for quote in quotes[lang]:
        if normalize(quote) not in flat:
            raise SystemExit(f"[{lang}] цитата не найдена в томе ({where}): {quote!r}")
    return len(quotes[lang])


def verify_prose(data, texts):
    """Каждый абзац, взятый из тома дословно, должен в томе найтись.

    Проверяются только те абзацы, что помечены как цитата тома: список
    PROSE_QUOTES. Остальное — наш пересказ, и он проверяется глазами.
    """
    flat = {lang: normalize(texts[lang]) for lang in texts}
    missing = []
    for lang, strings in PROSE_QUOTES.items():
        for string in strings:
            if normalize(string) not in flat[lang]:
                missing.append((lang, string))
    if missing:
        for lang, string in missing:
            print(f"  нет в томе ({lang}): {string[:90]}")
        raise SystemExit(f"проза расходится с томом: {len(missing)} фрагм.")
    return sum(len(v) for v in PROSE_QUOTES.values())


PROSE_QUOTES = {
    "ru": [
        "Каждый стих представлен шестью слоями",
        "Перевод выполнен прямо с санскрита, без английского посредника",
        "лин̇га-агра",
        "шесть месяцев практики дают признаки совершенства в задержке дыхания",
        "вāйу-пāна",
        "способность принимать любой облик (кāмарӯпа)",
        "долгожительство (чирāн̃джӣвӣ)",
        "у практикующего Кāрмукāсану «погибают все враги — болезни и прочее» (23.86)",
        "Кӯрмāсана разрушает «всю скверну и грехи века кали»",
        "Грантхибхедāсана «показывает кхечарӣ и прочее» (23.82)",
        "вāйавӣ калā дарует «великую сиддхи» (23.25)",
        "вāйавӣ-прийах̣ в Мāлāсане",
        "Работа велась по четырём текстам",
        "игольным отверстием, сквозь которое проходит нить",
        "Нумерация стихов перевода совпадает с нумерацией Мāлавӣйи",
    ],
    "en": [
        "Each verse is presented in six layers",
        "The translation was made directly from Sanskrit, without an English intermediary",
        "liṅga-agra",
        "khecarādi-phalapradam",
        "six months of practice yield the marks of perfection in breath retention",
        "“drinking of air”",
        "the power to assume any form (kāmarūpa)",
        "longevity (cirāñjīvī) and, after a year of practice, jīvanmukti",
        "for the practitioner of Kārmukāsana “all enemies perish — disease and the rest” (23.86)",
        "Kūrmāsana destroys “all impurity and the sins of the kali age”",
        "Granthibhedāsana “shows forth khecarī and the rest” (23.82)",
        "vāyavī kalā grants “great siddhi” (23.25)",
        "vāyavī-priyaḥ in Mālāsana",
        "Four witnesses were used",
        "the eye of a needle through which the thread is passed",
        "The verse numbering of the translation coincides with that of Mālavīya",
    ],
}

# Кириллическая транслитерация колофона и его IAST: том печатает их сам.
COLOPHON = {
    "deva": "इति श्रीरुद्रयामले उत्तरतन्त्रे महातन्त्रोद्दीपने भावासननिर्णये "
            "पाशवकल्पे षट्चक्रसारसङ्केते सिद्धमन्त्रप्रकरणे भैरवीभैरवसंवादे "
            "त्रयोविंशः पटलः ॥ २३ ॥",
    "iast": "iti śrīrudrayāmale uttaratantre mahātantrod dīpane bhāvāsananirṇaye "
            "pāśavakalpe ṣaṭcakrasārasaṅkete siddhamantraprakaraṇe "
            "bhairavībhairavasaṃvāde trayoviṃśaḥ paṭalaḥ || 23 ||",
    "cyr": "ити ш́рӣрудрайāмале уттаратантре махāтантрод дӣпане бхāвāсананирн̣айе "
           "пāш́авакалпе шат̣чакрасāрасан̇кете сиддхамантрапракаран̣е "
           "бхаиравӣбхаиравасам̣вāде трайовим̣ш́ах̣ пат̣алах̣ || 23 ||",
}


# -------------------------------------------------------------------- сборка


def build():
    register_ru = read_register(PDF["ru"], REGISTER_COLUMNS["ru"])
    register_en = read_register(PDF["en"], REGISTER_COLUMNS["en"])
    if len(register_ru) != 57 or len(register_en) != 57:
        raise SystemExit(f"реестр: {len(register_ru)} и {len(register_en)} строк вместо 57")
    for a, b in zip(register_ru, register_en):
        if a["no"] != b["no"] or a["cells"][1] != b["cells"][1]:
            raise SystemExit(f"реестр: строки расходятся — {a} / {b}")
        if a["cells"][4] != b["cells"][3]:
            raise SystemExit(f"реестр: пат̣ала расходится в строке {a['no']}")

    # кириллица тома сверяется с картой сайта в каждой полной строке
    checked = 0
    for row in register_ru:
        if row["no"] in FULL_NAMES:
            continue
        names = [re.sub(r"\s*\((?:I|II)\)\s*$", "", n).strip()
                 for n in row["cells"][1].split("/")]
        columns = [c.strip() for c in row["cells"][2].split("/")]
        if len(names) != len(columns):
            continue
        for name, column in zip(names, columns):
            expected = translit.translit(name)
            if expected.lower() != column.lower():
                raise SystemExit(f"карта расходится с томом, строка {row['no']}: "
                                 f"{expected} ≠ {column}")
            checked += 1

    texts = {
        lang: "".join(page.get_text() for page in pymupdf.open(PDF[lang]))
        for lang in PDF
    }
    quotes = {lang: verify(lang, texts[lang], "цитаты статьи") for lang in PDF}
    prose = verify_prose(None, texts)
    for lang in PDF:
        if lang == "ru" and normalize(COLOPHON["deva"]) not in normalize(texts["ru"]):
            raise SystemExit("колофон в деванагарӣ не найден в русском томе")
        if lang == "en" and normalize(COLOPHON["iast"]) not in normalize(texts["en"]):
            raise SystemExit("колофон в IAST не найден в английском томе")
        if lang == "ru" and normalize(COLOPHON["cyr"]) not in normalize(texts["ru"]):
            raise SystemExit("колофон в кириллице не найден в русском томе")

    poses = build_poses(register_ru, register_en)
    tables_ru, tables_en = register_table(register_ru, register_en)
    tables = {"ru": tables_ru, "en": tables_en}

    data = {
        "id": "rudrayamala",
        "title": {"ru": "Āсаны «Рудрайāмалоттаратантры» (пат̣алы 23–24)",
                  "en": "The āsanas of the Rudrayāmalottaratantra (paṭalas 23–24)"},
        "chapterWord": {"ru": "пат̣ала", "en": "paṭala"},
        "poses": poses,
        "prologue": {"ru": [], "en": []},
        "about": {"ru": about_blocks("ru"), "en": about_blocks("en")},
        "appendix": {
            "ru": [
                {"type": "subhead", "label": "Приложение. Реестр āсан (по изданию Мāлавӣйи 1999)"},
                {"type": "p", "html": "Пятьдесят семь строк реестра — так, как они "
                                      "напечатаны в томе: номер, название в IAST, "
                                      "кириллица по карте проекта, русское название и "
                                      "пат̣ала. Название ведёт на страницу позы."},
                {"type": "table", "rows": tables["ru"]},
                {"type": "p", "html": "Раздел 5 перевода (вводный стих о группах āсан, "
                                      "23.34–35) в реестр не входит: это не описание "
                                      "позы. Позы бхекāсана, кхечарāсана и махāбхекāсана "
                                      "описаны в одном разделе и потому занимают одну "
                                      "строку. Одна и та же поза может быть описана "
                                      "дважды (кāрмукāсана, самāнāсана)."},
                {"type": "note", "paragraphs": [
                    "В строках 14 и 17 русский том даёт столбец кириллицы "
                    "сокращённо; в таблице стоят полные имена, собранные из IAST по "
                    "той же карте. Полные имена — и на страницах этих поз.",
                ]},
            ],
            "en": [
                {"type": "subhead", "label": "Appendix. Register of āsanas (after Mālavīya 1999)"},
                {"type": "p", "html": "Fifty-seven lines of the register as they are "
                                      "printed in the volume: number, name in IAST, "
                                      "English rendering and paṭala. The name leads to "
                                      "the posture’s page."},
                {"type": "table", "rows": tables["en"]},
                {"type": "p", "html": "Section 5 of the translation (the introductory "
                                      "verse on groups of āsanas, 23.34–35) is not "
                                      "included in the register, as it does not describe "
                                      "a posture. Bhekāsana, Khecarāsana and "
                                      "Mahābhekāsana are described in a single section "
                                      "and therefore occupy one line. The same posture "
                                      "may be described twice (Kārmukāsana, "
                                      "Samānāsana)."},
                {"type": "note", "paragraphs": [
                    "In lines 14 and 17 the Russian volume gives its Cyrillic column "
                    "in abbreviated form; the table carries the full names, built from "
                    "the IAST by the same map. The full names are also on the pages of "
                    "those postures.",
                ]},
            ],
        },
        "notes": {"ru": notes_blocks("ru", tables), "en": notes_blocks("en", tables)},
        "datingSummary": dating_summary("ru"),
        "dating": {
            "ru": {"title": "Датировка «Рудрайāмалоттаратантры»", "blocks": RU_DATING},
            "en": {"title": "Dating the Rudrayāmalottaratantra", "blocks": EN_DATING},
        },
    }

    data = script_mix.fix_value(data)
    data = diacritics.fix_document(data)

    report = {
        "строк реестра": len(register_ru),
        "страниц āсан": len(poses),
        "новых ключей": sum(1 for p in poses if p["key"] not in KNOWN_KEYS),
        "цитат сверено": sum(quotes.values()) + prose,
        "строк по карте сверено": checked,
    }
    return data, report


# ключи, которые уже были на сайте к моменту сборки этого тома
KNOWN_KEYS = {
    "padmasana", "baddhapadmasana", "svastikasana", "kukkutasana", "virasana",
    "mayurasana", "garudasana", "kurmasana", "matsyasana", "makarasana",
    "simhasana", "vyaghrasana", "hamsasana", "yogasana",
}


def main():
    data, report = build()
    text = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        have = OUT.read_text(encoding="utf8") if OUT.exists() else ""
        if have == text:
            print("data/rudrayamala.json совпадает с томами")
            return
        raise SystemExit("data/rudrayamala.json расходится с томами: "
                         "пересоберите без --check")
    OUT.write_text(text, encoding="utf8")
    for key, value in report.items():
        print(f"{key}: {value}")
    print(f"записано: data/rudrayamala.json · {len(text.encode()) // 1024} КБ")


if __name__ == "__main__":
    main()
