# -*- coding: utf-8 -*-
"""Раздел «Рукописи и издания» — справочный аппарат сайта, не текст PDF.

Этот раздел написан для сайта: в исходных PDF его нет. Всё, что в нём сказано,
взято из предисловия к изданию Петерсона 1888 года (в перепечатке 1987 года),
каталога Аурехта и описаний хранилищ; ссылки на них стоят в конце раздела.
Ничего не добавлено «по памяти»: где издание молчит или читается неуверенно,
это сказано прямо.

Правило набора: слово пишется либо целиком кириллицей, либо целиком латиницей
(IAST). Долгое «ā» внутри кириллического слова несёт латинская буква — так
устроена карта tools/translit.py; других латинских букв внутри кириллических
слов здесь нет (проверка: python3 tools/script_mix.py).
"""

from __future__ import annotations


def link(href: str, text: str) -> str:
    return ('<a href="' + href + '" target="_blank" rel="noopener">' + text + "</a>")


# --------------------------------------------------------------- по-русски

RU = [
    {"type": "note", "paragraphs": [
        "Раздел составлен для сайта: в PDF-источнике его нет, и в подсчёт строк "
        "издания он не входит. Перечень рукописей A–F взят из предисловия к "
        "изданию Петерсона 1888 года, остальные списки — из каталога Ауфрехта и "
        "описаний хранилищ; ссылки на них — в конце раздела. Текст самого "
        "трактата на сайте остаётся дословным, в остальных разделах.",
    ]},
    {"type": "h3", "text": "Печатные издания"},
    {"type": "p", "text":
        "Полного критического издания нет; полного перевода на какой-либо язык "
        "тоже нет. Оба тома PDF опираются на издание Петерсона 1888 года — "
        "единственное полное печатное издание санскритского текста."},
    {"type": "table", "rows": [
        ["Издание", "Год", "Что это"],
        ["The Paddhati of Śārṅgadhara: A Sanskrit Anthology, vol. I: The Text. "
         "Ed. Peter Peterson. Bombay Sanskrit Series 37. Bombay: Government "
         "Central Book Depôt", "1888",
         "Полный санскритский текст по шести рукописям. Критическим изданием не "
         "является; обещанный второй том (введение, разночтения, примечания) так "
         "и не вышел."],
        ["Перепечатки Nirṇaya Sāgara Press, Bombay",
         "1906 и 1915 — по разным библиографиям",
         "Перепечатка текста Петерсона."],
        ["Sarngadhara Paddhati, being an Anthology of Sanskrit Verses. Delhi: "
         "Chaukhamba Sanskrit Pratishthan (Vrajajivan Prachyabharati "
         "Granthamala 25)", "1987",
         "Воспроизведение издания Nirṇaya Sāgara Press — вместе с предисловием "
         "Петерсона и его перечнем рукописей."],
        ["The Paddhati of Sarngadhara, vol. I. Kessinger Publishing", "2010",
         "Фотоперепечатка тома I; ISBN 978-1-120-91138-4."],
        ["Th. Aufrecht. Ueber die Paddhati von Çârñgadhara. — ZDMG 27", "1873",
         "264 стиха по шести рукописям с немецким переводом и исследование; "
         "статья открывает том. Первая публикация текста."],
        ["O. Böhtlingk. Einige Bemerkungen zu den von Th. Aufrecht … "
         "veröffentlichten und übersetzten Sprüchen aus Çârñgadhara’s Paddhati. "
         "Halle", "1873", "Замечания к публикации Ауфрехта."],
    ]},
    {"type": "p", "text":
        "Не путать: Bṛhat-Śārṅgadharapaddhati (XVIII в., 588 разделов) — "
        "расширенный свод, а Śārṅgadhara-saṃhitā — медицинский трактат, "
        "возможно другого автора."},

    {"type": "h3", "text": "Рукописи, по которым набирал Петерсон"},
    {"type": "p", "text":
        "Шесть списков, описанных в предисловии к тому I (1888). Литеры A–F "
        "принадлежат изданию."},
    {"type": "list", "items": [
        {"html": "<strong>A</strong> — неполный, куплен для правительства Бомбея "
                 "в 1886–1887 гг., листы 1–253, обрывается на стихе 4153. Без "
                 "даты: по внешнему виду Петерсон относит его к XVI в. По его же "
                 "оценке — самый исправный.", "level": 1},
        {"html": "<strong>B</strong> — полный, куплен там же в 1886–1887 гг., "
                 "листы 1–295, до стиха 4620, то есть до настоящего конца. "
                 "Написан джайнским писцом, красиво, но моложе и менее исправен, "
                 "чем A.", "level": 1},
        {"html": "<strong>C</strong> — список пандита Дургāпрашāды, Saṃvat 1776, "
                 "полный; содержит главу Khaḍgaparīkṣā, которую Петерсон вынес "
                 "в приложение.", "level": 1},
        {"html": "<strong>D</strong> — неполный, от Джьештāрама Мукнджӣ, листы "
                 "1–144, обрывается на стихе 1588.", "level": 1},
        {"html": "<strong>E</strong> — список, полученный через того же "
                 "книготорговца от Сетха Данай-Махиувайи, Saṃvat 1819, полный "
                 "(имя владельца в перепечатке читается неуверенно).",
         "level": 1},
        {"html": "<strong>F</strong> — список из дворцовой библиотеки Джодхпура, "
                 "Saṃvat 1877; использован для последней части, где не хватало A.",
         "level": 1},
    ]},

    {"type": "h3", "text": "Другие списки"},
    {"type": "p", "text":
        "Каталог Ауфрехта (Catalogus Catalogorum) перечисляет рукописи по "
        "собраниям. Часть копий записана под другим названием — "
        "Śārṅgadharavrajyā, поэтому поиск по одному заглавию находит не всё."},
    {"type": "list", "items": [
        {"html": "Британская библиотека, собрание Индия-Офис: Io. 11 A (от "
                 "sūryānyokti до saṃkirṇānyokti), 125, 876, 1384 (до 44, 8), "
                 "2023, 2048 (до 63, 4).", "level": 1},
        {"html": "Бодлеянская библиотека, Оксфорд: Oxf. 122b.", "level": 1},
        {"html": "Королевское азиатское общество, Лондон: L. 950; Tod 32.",
         "level": 1},
        {"html": "Берлин: Bl. 6 и Bl. 112.", "level": 1},
        {"html": "Биканер: Bik. 259 и 534 (91–134, 20). Альвар: Ulwar 975.",
         "level": 1},
        {"html": "Прочие сигла каталога: Ak 599, Bd. 480 и 528, K. 250, B. 3, "
                 "56 и 58, Burnell 164b, Gu. 5 (извлечения), Peters. 2, 189 "
                 "(фрагмент) и 4, 30, Mackenzie 103, Pet. 727, Stein 64 и 74, "
                 "Hz. 343, Rgb. 421 (фрагмент) и 464 (неполный).", "level": 1},
    ]},

    {"type": "h3", "text": "Копии, описанные и оцифрованные"},
    {"type": "list", "items": [
        {"html": "Кембридж, University Library: "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-00884/1", "Add.884")
                 + " — 334 листа, Vikrama 1926 = 1869 г., полный; "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-01824/1", "Add.1824")
                 + " — 103 листа, 1857 г.; "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-02111/1", "Add.2111")
                 + " — 9 листов, XVII в., выборка.", "level": 1},
        {"html": "Лондон, Королевское азиатское общество — Tod 32: бумага, "
                 "девана̄гарӣ; подарена обществу Джеймсом Тодом 21 февраля "
                 "1824 г. В описании общества приведён лист 282r с пометой "
                 "«atha yogaḥ». " + link(
                     "https://royalasiaticsociety.org/intertextual-and-material-culture-researching-the-ras-collections/",
                     "Описание"), "level": 1},
        {"html": "Катманду, National Archives, NAK 3/132 — плёнка NGMCP "
                 + link("https://ngmcp.fdm.uni-hamburg.de/mediawiki/index.php/B_323-4_%C5%9A%C4%81r%E1%B9%85gadharapaddhati",
                        "B 323/4")
                 + ": 257 листов, 10 строк на странице, переписана saṃ 1847 в "
                 "Vaṃdīpura, писец Kriṣṇa Newar.", "level": 1},
        {"html": "Сурат, Chunilal Gandhi Vidyabhavan — "
                 + link("https://archive.org/details/sharngadharapaddhati-CGV-SDPB-0193",
                        "SDPB 0193")
                 + ": 79 листов, неполный список, обрывается.", "level": 1},
        {"html": "Дели, IGNCA, VMR 688: микрофильм рукописи из Пуны "
                 "(Vaidika Saṃśodhana Maṇḍala), 289 листов. " + link(
                     "https://ignca.bestbookbuddies.com/cgi-bin/koha/opac-detail.pl?biblionumber=743620",
                     "Запись каталога"), "level": 1},
    ]},

    {"type": "h3", "text": "Что остаётся неизвестным"},
    {"type": "list", "items": [
        "Сигла каталога Ауфрехта приведены так, как стоят в каталоге: до "
        "современных шифров они здесь не развёрнуты, а часть собраний с тех пор "
        "переехала (Индия-Офис → Британская библиотека).",
        "Литеры E и F в перепечатке 1987 года читаются плохо: описания списков "
        "надёжны, сами буквы — с оговоркой.",
        "Даты списков A и B — не из колофонов, а оценка Петерсона по бумаге; он "
        "сам оговаривает, что их «можно только предполагать».",
        "Tod 32 датируют по-разному: в английском томе PDF он назван поздним "
        "списком, описание Королевского азиатского общества предполагает XVII в.",
        "Полного критического издания и полного перевода по-прежнему нет — это "
        "общее место в литературе о тексте.",
    ]},

    {"type": "h3", "text": "Источники раздела"},
    {"type": "list", "items": [
        {"html": "Предисловие Петерсона с перечнем рукописей — перепечатка 1987 г.: "
                 + link("https://archive.org/details/in.ernet.dli.2015.407770",
                        "Sarngadhara Paddhati, Delhi 1987"), "level": 1},
        {"html": "Скан издания 1888 г.: "
                 + link("https://archive.org/details/sarngadharapaddhati-peterson",
                        "The Paddhati of Sarngadhara, Bombay 1888"), "level": 1},
        {"html": "Библиографическая запись тома I: "
                 + link("https://catalog.hathitrust.org/Record/100401324",
                        "HathiTrust"), "level": 1},
        {"html": "Каталог Ауфрехта, статья Śārṅgadharapaddhati: "
                 + link("https://www.wisdomlib.org/definition/sharngadharapaddhati",
                        "Catalogus Catalogorum"), "level": 1},
        {"html": "Описания кембриджских списков: "
                 + link("https://cudl.lib.cam.ac.uk/collections/sanskrit/1",
                        "Cambridge University Digital Library"), "level": 1},
        {"html": "Списки NGMCP (Непал): "
                 + link("https://www-archiv.fdm.uni-hamburg.de/ngmcp/index.html",
                        "указатель плёнок"), "level": 1},
    ]},
]


# ------------------------------------------------------------------ in English

EN = [
    {"type": "note", "paragraphs": [
        "This section was written for the site: it is not in the source PDFs and "
        "is not counted by the coverage check. The list of manuscripts A–F comes "
        "from Peterson’s preface of 1888, the other shelfmarks from Aufrecht’s "
        "catalogue and from library descriptions; the links are given at the end. "
        "The text of the treatise itself stays verbatim, in the other sections.",
    ]},
    {"type": "h3", "text": "Printed editions"},
    {"type": "p", "text":
        "There is no complete critical edition, and no complete translation into "
        "any language. Both PDF volumes rest on Peterson’s edition of 1888 — the "
        "only complete printed edition of the Sanskrit text."},
    {"type": "table", "rows": [
        ["Edition", "Year", "What it is"],
        ["The Paddhati of Śārṅgadhara: A Sanskrit Anthology, vol. I: The Text. "
         "Ed. Peter Peterson. Bombay Sanskrit Series 37. Bombay: Government "
         "Central Book Depôt", "1888",
         "The complete Sanskrit text, based on six manuscripts. Not a critical "
         "edition; the promised second volume (introduction, variant readings, "
         "notes) never appeared."],
        ["Reprints, Nirṇaya Sāgara Press, Bombay",
         "1906 and 1915, according to different bibliographies",
         "A reprint of Peterson’s text."],
        ["Sarngadhara Paddhati, being an Anthology of Sanskrit Verses. Delhi: "
         "Chaukhamba Sanskrit Pratishthan (Vrajajivan Prachyabharati "
         "Granthamala 25)", "1987",
         "A reproduction of the Nirṇaya Sāgara Press edition, with Peterson’s "
         "preface and his list of manuscripts."],
        ["The Paddhati of Sarngadhara, vol. I. Kessinger Publishing", "2010",
         "A photographic reprint of volume I; ISBN 978-1-120-91138-4."],
        ["Th. Aufrecht. Ueber die Paddhati von Çârñgadhara. — ZDMG 27", "1873",
         "264 verses from six manuscripts with a German translation, plus a "
         "study; the article opens the volume. The first publication of the text."],
        ["O. Böhtlingk. Einige Bemerkungen zu den von Th. Aufrecht … "
         "veröffentlichten und übersetzten Sprüchen aus Çârñgadhara’s Paddhati. "
         "Halle", "1873", "Remarks on Aufrecht’s publication."],
    ]},
    {"type": "p", "text":
        "Not to be confused: the Bṛhat-Śārṅgadharapaddhati (18th c., 588 "
        "sections) is an expanded compendium, and the Śārṅgadhara-saṃhitā is a "
        "medical treatise, possibly by another author."},

    {"type": "h3", "text": "The manuscripts Peterson used"},
    {"type": "p", "text":
        "Six copies described in the preface to volume I (1888); the letters A–F "
        "belong to the edition."},
    {"type": "list", "items": [
        {"html": "<strong>A</strong> — incomplete, bought for the Government of "
                 "Bombay in 1886–7, leaves 1–253, breaking off in the middle of "
                 "verse 4153. Undated: from its appearance Peterson places it in "
                 "the 16th century. In his judgement, the most correct copy.",
         "level": 1},
        {"html": "<strong>B</strong> — complete, also bought in 1886–7, leaves "
                 "1–295, down to verse 4620, the proper end. Very beautifully "
                 "written by a Jain scribe, but neither so old nor so correct "
                 "as A.", "level": 1},
        {"html": "<strong>C</strong> — the copy of Paṇḍit Durgāprasāda, Saṃvat "
                 "1776, complete; it contains the Khaḍgaparīkṣā chapter, which "
                 "Peterson placed at the end of the book as an appendix.",
         "level": 1},
        {"html": "<strong>D</strong> — incomplete, lent by Jyeṣṭārāma Mukundjī, "
                 "leaves 1–144, breaking off in the middle of verse 1588.",
         "level": 1},
        {"html": "<strong>E</strong> — lent through the same bookseller by Seth "
                 "Dhanay-Mahīuvāyī, Saṃvat 1819, complete (the owner’s name is "
                 "hard to read in the reprint).", "level": 1},
        {"html": "<strong>F</strong> — a copy from the Palace Library at "
                 "Jodhpur, Saṃvat 1877; used for the last part of the book, "
                 "where A was wanting.", "level": 1},
    ]},

    {"type": "h3", "text": "Other copies"},
    {"type": "p", "text":
        "Aufrecht’s Catalogus Catalogorum lists manuscripts by collection. Some "
        "copies are recorded under another title — Śārṅgadharavrajyā — so a "
        "search under one title alone does not find everything."},
    {"type": "list", "items": [
        {"html": "British Library, India Office collection: Io. 11 A (from "
                 "sūryānyokti to saṃkirṇānyokti), 125, 876, 1384 (to 44, 8), "
                 "2023, 2048 (to 63, 4).", "level": 1},
        {"html": "Bodleian Library, Oxford: Oxf. 122b.", "level": 1},
        {"html": "Royal Asiatic Society, London: L. 950; Tod 32.", "level": 1},
        {"html": "Berlin: Bl. 6 and Bl. 112.", "level": 1},
        {"html": "Bikaner: Bik. 259 and 534 (91–134, 20). Alwar: Ulwar 975.",
         "level": 1},
        {"html": "Other sigla of the catalogue: Ak 599, Bd. 480 and 528, "
                 "K. 250, B. 3, 56 and 58, Burnell 164b, Gu. 5 (extracts), "
                 "Peters. 2, 189 (fragment) and 4, 30, Mackenzie 103, Pet. 727, "
                 "Stein 64 and 74, Hz. 343, Rgb. 421 (fragment) and 464 "
                 "(incomplete).", "level": 1},
    ]},

    {"type": "h3", "text": "Copies described and digitised"},
    {"type": "list", "items": [
        {"html": "Cambridge, University Library: "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-00884/1", "Add.884")
                 + " — 334 ff., Vikrama 1926 = 1869 CE, complete; "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-01824/1", "Add.1824")
                 + " — 103 ff., 1857; "
                 + link("https://cudl.lib.cam.ac.uk/view/MS-ADD-02111/1", "Add.2111")
                 + " — 9 ff., 17th c., a selection.", "level": 1},
        {"html": "London, Royal Asiatic Society — Tod 32: paper, Devanāgarī; "
                 "given to the Society by James Tod on 21 February 1824. The "
                 "Society’s description shows fol. 282r with the words "
                 "«atha yogaḥ». " + link(
                     "https://royalasiaticsociety.org/intertextual-and-material-culture-researching-the-ras-collections/",
                     "Description"), "level": 1},
        {"html": "Kathmandu, National Archives, NAK 3/132 — NGMCP reel "
                 + link("https://ngmcp.fdm.uni-hamburg.de/mediawiki/index.php/B_323-4_%C5%9A%C4%81r%E1%B9%85gadharapaddhati",
                        "B 323/4")
                 + ": 257 ff., 10 lines to a page, copied in saṃ 1847 at "
                 "Vaṃdīpura by the scribe Kriṣṇa Newar.", "level": 1},
        {"html": "Surat, Chunilal Gandhi Vidyabhavan — "
                 + link("https://archive.org/details/sharngadharapaddhati-CGV-SDPB-0193",
                        "SDPB 0193")
                 + ": 79 ff., an incomplete copy that ends abruptly.",
         "level": 1},
        {"html": "Delhi, IGNCA, VMR 688: a microfilm of a manuscript from Pune "
                 "(Vaidika Saṃśodhana Maṇḍala), 289 ff. " + link(
                     "https://ignca.bestbookbuddies.com/cgi-bin/koha/opac-detail.pl?biblionumber=743620",
                     "Catalogue record"), "level": 1},
    ]},

    {"type": "h3", "text": "What remains unknown"},
    {"type": "list", "items": [
        "The sigla of Aufrecht’s catalogue are given as they stand in the "
        "catalogue: they are not expanded into modern shelfmarks here, and some "
        "collections have moved since (India Office → British Library).",
        "The letters E and F are hard to read in the 1987 reprint: the "
        "descriptions of the copies are reliable, the letters themselves are "
        "given with that caveat.",
        "The dates of A and B are not from colophons but Peterson’s estimate "
        "from the paper; he says himself that they «can only be conjectured».",
        "Tod 32 is dated differently in different places: the English PDF calls "
        "it a late copy, the Royal Asiatic Society’s description suggests the "
        "17th century.",
        "There is still no complete critical edition and no complete "
        "translation — a commonplace in the literature on the text.",
    ]},

    {"type": "h3", "text": "Sources of this section"},
    {"type": "list", "items": [
        {"html": "Peterson’s preface with the list of manuscripts — the 1987 "
                 "reprint: "
                 + link("https://archive.org/details/in.ernet.dli.2015.407770",
                        "Sarngadhara Paddhati, Delhi 1987"), "level": 1},
        {"html": "A scan of the 1888 edition: "
                 + link("https://archive.org/details/sarngadharapaddhati-peterson",
                        "The Paddhati of Sarngadhara, Bombay 1888"), "level": 1},
        {"html": "Bibliographic record of volume I: "
                 + link("https://catalog.hathitrust.org/Record/100401324",
                        "HathiTrust"), "level": 1},
        {"html": "Aufrecht’s catalogue, article Śārṅgadharapaddhati: "
                 + link("https://www.wisdomlib.org/definition/sharngadharapaddhati",
                        "Catalogus Catalogorum"), "level": 1},
        {"html": "Descriptions of the Cambridge copies: "
                 + link("https://cudl.lib.cam.ac.uk/collections/sanskrit/1",
                        "Cambridge University Digital Library"), "level": 1},
        {"html": "The NGMCP records (Nepal): "
                 + link("https://www-archiv.fdm.uni-hamburg.de/ngmcp/index.html",
                        "index of reels"), "level": 1},
    ]},
]

TITLE = {"ru": "Рукописи и издания", "en": "Manuscripts and Editions"}
