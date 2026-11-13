# -*- coding: utf-8 -*-
"""Диакритика в санскритских словах — по единой карте проекта.

Сайт сам объявляет правило (§1 «Соглашения»): «Диакритика в именах и терминах —
строго по единой карте… Исключение — имена богов и давно освоенные русским
языком слова: Брахма, Вишну, Рудра, Шива, Шакти, Брахман, йога, санскрит».
В набранных текстах это правило соблюдено не везде: в глоссарии стоит
«варттика» вместо «вāрттика», «авидья» вместо «авидйā», «деванагари» вместо
«деванāгарӣ», латинское «Devanagari» рядом с «Devanāgarī», «Йогая̄джн̃авалкья»
с «я» там, где карта даёт «йā».

Что делает модуль:

* переписывает знаки в каноническую запись карты (`а̄` → `ā`, `ш̣` → `ш`,
  `мӯла` → `мӯла`, `я̄` → `йā`, `khecarı̄` → `khecarī`): буквы те же, меняется
  только кодовая точка, поэтому это делается во всех строках, включая стихи;
* дописывает недостающие знаки в терминах, именах и названиях поз — ровно те,
  что даёт `translit.MAP` для соответствующего IAST; ни одно слово не
  придумано: целевая форма всегда получается из IAST-написания, которое уже
  есть в данных (поза — из своего поля `iast`, термин — из списка ниже);
* не трогает цитаты: строки стихов (`lines`), поля `iast`, `gu`, `deva`,
  библиографические `edition`/`pdf`, адреса и идентификаторы, имена
  учреждений («Bharata Itihasa Samshodhaka Mandala», «Kaivalyadhama» и др.);
* имена богов и освоенные русским языком слова из списка исключений самого
  сайта (Брахма, Вишну, Рудра, Шива, Шакти, Брахман, йога, санскрит) остаются
  без диакритики.

Запуск:

    python3 tools/diacritics.py --fix data/*.json     # исправить на месте
    python3 tools/diacritics.py --check data/*.json   # только проверить (код 1, если есть что править)
    python3 tools/diacritics.py --report data/*.json  # показать, что и чем правится

Шаг выполняется после извлечения и после `tools/numeral.py` — так же, как он.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from translit import translit  # noqa: E402

# --------------------------------------------------------------------------
# 1. Кодовая точка, а не слово: каноническая запись знаков карты.
# --------------------------------------------------------------------------
MARKS = [
    ("а\u0304", "ā"),     # а + макрон -> латинское ā, как в карте
    ("А\u0304", "Ā"),
    ("a\u0304", "ā"),
    ("у\u0304", "ӯ"),
    ("я\u0304", "йā"),
    ("ı\u0304", "ī"),
    ("ш\u0323", "ш"),     # ṣ по карте идёт без точки
    ("Ш\u0323", "Ш"),
    ("r\u0325", "ṛ"),
]

# --------------------------------------------------------------------------
# 2. Термины: русская основа -> основа в IAST, окончания русские.
#    Целевая форма считается через translit(), поэтому диакритика берётся
#    из карты, а не набирается руками.
# --------------------------------------------------------------------------
STEMS = [
    ("варттик", "vārttik", ["", "а", "и", "е", "у", "ом", "ой", "ам", "ах"]),
    ("варттикакар", "vārttikakār", ["а"]),
    ("уллас", "ullās", ["", "а", "ы", "е", "у", "ом", "ам", "ах"]),
    ("адвайт", "advait", ["а", "ы", "е", "у"]),
    ("ведант", "vedānt", ["а", "ы", "е", "у"]),
    ("веданти", "vedānti", ["ческий", "ческого", "ческому", "ческим",
                            "ческая", "ческой", "ческую", "ческие", "ческих",
                            "ческими"]),
    ("шабд", "śabd", ["а", "ы", "е", "у", "ам", "ах"]),
    ("шабдадвайт", "śabdadvait", ["а", "у", "е"]),
    ("спхот", "sphoṭ", ["а", "е", "ы", "у", "ам"]),
    ("виваран", "vivaraṇ", ["а", "ы", "е", "у", "ам", "ой"]),
    ("шайв", "śaiv", ["а", "ы", "е", "у"]),
    ("вайшнав", "vaiṣṇav", ["а", "ы", "е", "у", "ам", "ами", "ах",
                             "ский", "скому", "ского", "ской", "ские", "ских"]),
    ("хатх", "haṭh", ["а", "и", "е", "у", "ой"]),
    ("кундалини", "kuṇḍalinī", [""]),
    ("самват", "saṃvat", ["", "а", "е"]),
    ("варанаси", "vārāṇasī", [""]),
    ("шанкар", "śaṅkar", ["а", "ы", "е", "у", "ой"]),
    ("патал", "paṭal", ["а", "ы", "е", "у", "ам"]),
    ("агам", "āgam", ["а", "ы", "е", "ам"]),
    ("пран", "prāṇ", ["а", "ы", "е", "у", "ой", "ам"]),
    ("карани", "karaṇī", [""]),
    ("кхечари", "khecarī", [""]),
    ("унмани", "uṇmanī", [""]),
    ("данд", "daṇḍ", ["а", "ы", "е", "у", "ой", "ам"]),
    ("пашчим", "paścim", ["а", "ы", "е", "у", "ой"]),
    ("дхаран", "dhāraṇ", ["а", "ы", "е", "у", "ой"]),
    ("самадх", "samādh", ["и", "ям"]),
    ("дхйан", "dhyān", ["а", "ы", "е", "у", "ом"]),
    ("майур", "mayūr", ["а", "ы", "е", "у", "ой"]),
    ("нрисимх", "nṛsiṃh", ["а", "и", "е", "у", "ой"]),
    ("пашчиматан", "paścimatān", ["а", "ы", "е", "у", "ой", "ака", "аки", "аке", "аку"]),
    ("манасоллас", "mānasollās", ["а", "ы", "е", "у", "ой"]),
    ("сурешвар", "sureśvar", ["а", "ы", "е", "у", "ой"]),
    ("ганг", "gaṅg", ["а", "и", "е", "у", "ой"]),
    ("бхагиратх", "bhāgīrath", ["и"]),
    ("атман", "ātman", ["", "а", "е", "ом", "у"]),
    ("атманепад", "ātmanepad", ["а"]),
    ("асан", "āsan", ["", "а", "ы", "у", "е", "ом", "ам", "ами", "ах", "ой"]),
]

# Слова с мягким знаком и «я», которые карта переписывает иначе.
PAIRS = [
    ("авидья", "avidyā"), ("авидьи", "avidyi"), ("авидье", "avidye"),
    ("авидью", "avidyu"), ("авидьей", "avidyey"),
    ("махавакья", "mahāvākya"), ("махавакьи", "mahāvākyi"),
    ("махавакье", "mahāvākye"),
    ("бхашья", "bhāṣya"), ("бхашьи", "bhāṣyi"), ("бхашье", "bhāṣye"),
    ("бхашьей", "bhāṣyey"),
    ("бхамати", "bhāmatī"),
    ("шш́рӣ", "śrī"),
    ("дакшинāмнāйа", "dakṣiṇāmnāya"),
    ("шарма", "śarmā"),
    ("маюра", "mayūra"), ("маюры", "mayūry"), ("маюре", "mayūre"),
    ("маюрой", "mayūroy"), ("Маюра", "mayūra"),
    ("деванагари", "devanāgarī"),
    ("гранатх", "granth"),
    ("аāтман", "ātman"), ("аāтмана", "ātmana"),
    ("аāтмане", "ātmane"), ("аāтманом", "ātmanom"),
    ("яджн̃авалкья", "yājñavalkya"), ("яджн̃авалкье", "yājñavalkye"),
    ("яджн̃авалкьи", "yājñavalkyi"), ("яджн̃авалкью", "yājñavalkyu"),
    ("яджн̃авалкьей", "yājñavalkyey"),
]

# Имена, в которых «ь» и «я» стоят там, где карта даёт «й» (y → й).
# Форма получается так: translit(IAST-основа) + русское окончание; буквы
# берутся из карты, от руки набрано только окончание, которое и так русское.
# У «Йога-Йāджн̃авалкйи» и «Ахирбудхнйа-сам̣хитā» дефис стоит в самой основе:
# это тот же знак, каким они набраны в остальных томах, а не новый.
DECL = [
    ("матсья", "matsya", ""), ("матсьи", "matsya", "и"),
    ("матсьендра", "matsyendra", ""), ("матсьендры", "matsyendra", "ы"),
    ("матсьендре", "matsyendra", "е"), ("матсьендру", "matsyendra", "у"),
    ("матсьендром", "matsyendra", "ом"), ("матсьендрой", "matsyendra", "ой"),
    ("матсьендрам", "matsyendra", "ам"),
    ("матсьендрāсана", "matsyendrāsana", ""),
    ("матсьендрāсаны", "matsyendrāsana", "ы"),
    ("матсьендрāсане", "matsyendrāsana", "е"),
    ("матсьендрāсану", "matsyendrāsana", "у"),
    ("матсьендрāсаной", "matsyendrāsana", "ой"),
    ("матсьянāтха", "matsyanātha", ""),
    ("матсьянāтхой", "matsyanātha", "ой"),
    ("матсьянāтхе", "matsyanātha", "е"),
    ("матсьянāтхи", "matsyanātha", "и"),
    ("яджнавалкья", "yājñavalkya", ""), ("яджнавалкье", "yājñavalkye", ""),
    ("яджнавалкьи", "yājñavalkyi", ""),
    ("йогайāджн̃авалкья", "yoga-yājñavalkya", "", True),
    ("йогайāджн̃авалкье", "yoga-yājñavalkye", "", True),
    ("йогайāджн̃авалкьи", "yoga-yājñavalkyi", "", True),
    ("йогайāджн̃авалкью", "yoga-yājñavalkyu", "", True),
    ("ахирбудхньясам̣хитā", "ahirbudhnya-saṃhitā", ""),
    ("ахирбудхньясам̣хите", "ahirbudhnya-saṃhite", ""),
    ("кайвальядхāма", "kaivalyadhāma", ""),
    ("кайвальядхāмы", "kaivalyadhāma", "ы"),
    ("кайвальядхāме", "kaivalyadhāma", "е"),
    ("кайвальядхāму", "kaivalyadhāma", "у"),
    ("кайвальядхāмой", "kaivalyadhāma", "ой"),
    ("кайвальядхама", "kaivalyadhāma", ""),
    ("кайвальядхамы", "kaivalyadhāma", "ы"),
    ("ш́ан̇карачарья", "śaṅkarācārya", ""),
    ("ш́ан̇карачарьи", "śaṅkarācārya", "и"),
    ("ш́ан̇карачарье", "śaṅkarācārya", "е"),
    ("ш́ан̇карачāрьи", "śaṅkarācārya", "и"),
    ("ш́ан̇карачāрьей", "śaṅkarācārya", "ей"),
    ("рахасья", "rahasya", ""), ("рахасье", "rahasya", "е"),
    ("джьештāрама", "jyeṣṭārāma", ""),
    ("адинатха", "ādinātha", ""), ("адинатхой", "ādinātha", "ой"),
    ("адинатхе", "ādinātha", "е"), ("адинатху", "ādinātha", "у"),
    ("матсйендранатх", "matsyendranātha", ""),
    ("матсйендранатха", "matsyendranātha", "а"),
    ("матсйендранатхой", "matsyendranātha", "ой"),
    ("матсьендранатх", "matsyendranātha", ""),
    ("матсьендранатха", "matsyendranātha", "а"),
    ("джьештха", "jyeṣṭha", ""),
    ("махакавья", "mahākāvya", ""), ("махакавье", "mahākāvya", "е"),
    ("махакавьи", "mahākāvya", "и"), ("махакавьях", "mahākāvy", "ах"),
    ("махакавьями", "mahākāvy", "ами"),
    ("āюрведист", "āyurved", "ист"), ("āюрведы", "āyurveda", "ы"),
    ("вāю", "vāyu", ""),
]

# Английская сторона: те же термины в IAST.
EN_PAIRS = [
    ("Devanagari", "Devanāgarī"),
    ("devanagari", "devanāgarī"),
    ("Varanasi", "Vārāṇasī"),
]

# Имена учреждений и выходные данные — в том виде, в каком они напечатаны.
PROTECTED = (
    "Bharata Itihasa Samshodhaka Mandala",
    "Maharaja Man Singh Pustak Prakash",
    "Maharaja Sayajirao",
    "Kaivalyadhama",
    "Sarasvati Bhavan",
    "Sarasvati Mahal",
    "Сарасвати Бхаван",
    "Сарасвати Махал",
    "Sampurnanand Sanskrit University",
)

# Поля, которые не переписываются: цитаты в оригинале, адреса, ключи.
SKIP_KEYS = {"lines", "iast", "gu", "deva", "key", "id", "code", "type",
             "edition", "pdf", "href", "src"}

# Окончания, с которыми название позы может стоять в русской фразе.
ENDINGS = ["", "а", "ы", "у", "е", "ом", "ой", "ам", "ами", "ах"]

_URL = re.compile(r"(?:https?://|www\.)[^\s\"'<>)]+"
                  r"|(?:href|src)=\"[^\"]*\"")
_TOKEN = re.compile(r"[A-Za-zА-Яа-яЁёӢӣӮӯĀāĪīŪūṚṛṜṝḶḷḸḹṄṅÑñṬṭḌḍ"
                    r"ṆṇṂṃṀṁḤḥŚśṢṣ\u0300-\u036f\u0323\u0307"
                    r"\u0301\u0303\u0325]+")


def _cap(source, target):
    """Сохранить заглавную букву исходного слова (и частей через дефис)."""
    joint = target.startswith("\0")
    if joint:
        target = target[1:]
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source[0].isupper():
        if joint:
            head, sep, tail = target.partition("-")
            target = head + sep + tail[:1].upper() + tail[1:]
        return target[0].upper() + target[1:]
    return target


def _plain(text):
    """Слово без диакритики — так, как оно могло быть набрано."""
    text = text.replace("ā", "а").replace("Ā", "А")
    for ch in "\u0300\u0301\u0303\u0304\u0307\u0323\u0325\u0328":
        text = text.replace(ch, "")
    return text.replace("ӣ", "и").replace("ӯ", "у")


def _terms():
    """Все пары «как набрано» -> «как надо» из списка основ и пар."""
    out = {}
    for plain, iast, endings in STEMS:
        stem = translit(iast)
        for end in endings:
            out[plain + end] = stem + end
    for plain, iast in PAIRS:
        out[plain] = translit(iast)
    for plain, base, ending, *rest in DECL:
        target = translit(base)
        if ending:
            # русское окончание встаёт на место конечной гласной основы
            if target[-1] in "аиуеоӣӯā":
                target = target[:-1]
            target += ending
        out[plain] = target
        if rest and rest[0]:
            # «Йога-Йāджн̃авалкйа»: вторая часть сложного имени — с заглавной
            out[plain] = ("\0" + out[plain])   # метка для _cap
    return out


def _pose_terms_from(docs):
    """Названия поз: как на странице позы, так и в тексте.

    Для каждой позы всех трактатов берётся её поле `iast` и переводится
    картой — получается та форма, которой подписана сама поза. Затем
    добавляются русские падежные окончания, чтобы «Курма», «Курмы»,
    «Курмой» писались так же, как «Кӯрма» на своей странице.
    """
    forms = {}
    for data in docs:
        for pose in data.get("poses") or []:
            iast = (pose.get("iast") or "").strip()
            if not iast or " " in iast:
                continue
            target = translit(iast)
            if target == iast:
                continue
            # основа без конечного гласного: «Падмāсана» -> «Падмāсан»
            stem = target[:-1] if target[-1] in "аиӣуӯ" else target
            stem = stem[0].lower() + stem[1:]
            plain = _plain(stem).lower()
            if len(plain) < 3 or not plain.isalpha():
                continue
            for end in ENDINGS:
                forms.setdefault(plain + end, stem + end)
    return forms


def _protect(text):
    """Спрятать адреса и имена учреждений под метки, чтобы их не задеть."""
    saved = []

    def keep(match):
        saved.append(match.group(0))
        return "%d" % (len(saved) - 1)

    text = _URL.sub(keep, text)
    for phrase in PROTECTED:
        while phrase in text:
            text = text.replace(phrase, keep(re.search(re.escape(phrase), text)), 1)
    return text, saved


def _restore(text, saved):
    return re.sub("(\\d+)", lambda m: saved[int(m.group(1))], text)


DOUBLE = re.compile(r"(.)\1([\u0300-\u036f])")

# Слова с диакритикой, но с русским окончанием: «ваишн̣авская», «бо́льшая».
# Их «я» — русское окончание, а не санскритское ya.
RUSSIAN_TAIL = re.compile(r"(ская|цкая|шая|щая|жая|чая|ая|ее)$")
DIA = re.compile("[āӣӯĀĪŪ\u0301\u0323\u0307\u0303\u0325]")
YOD = [
    ("ья", "йа"), ("ье", "йе"), ("ьи", "йи"), ("ью", "йу"), ("ьё", "йо"),
]


def yod(word):
    """y → й там, где набрано «ь» или «я»: «Матсьендра» → «Матсйендра».

    Карта не даёт мягкого знака вовсе, а «я» и «ю» после гласной — это тоже
    «йа» и «йу» («Даттāтрея» → «Даттāтрейа»). Применяется только к словам,
    в которых уже есть диакритика, то есть к транслитерации: русские слова
    («статье», «семье», «черепашья») остаются как есть.
    """
    for src, dst in YOD:
        word = word.replace(src, dst)
    word = re.sub(r"(?<=[аеёиоуыэяюӣӯā])я", "йа", word)
    word = re.sub(r"(?<=[аеёиоуыэяюӣӯā])ю", "йу", word)
    return word


def fix_text(text, terms, en_terms):
    """Одна строка: сначала знаки, потом слова."""
    for src, dst in MARKS:
        text = text.replace(src, dst)
    # «шш́лока» — удвоение буквы перед знаком от прежних правок
    text = DOUBLE.sub(r"\1\2", text)
    if not terms and not en_terms:
        return text
    text, saved = _protect(text)

    def sub(match):
        original = match.group(0)
        word = original
        if DIA.search(word) and not RUSSIAN_TAIL.search(word.lower()):
            word = yod(word)
        table = terms if re.search("[А-Яа-яЁё]", word) else en_terms
        # ключи таблицы записаны так, как слово набрано сейчас, — то есть до
        # перевода «ь»/«я» в «й», поэтому смотрим оба написания
        target = table.get(word.lower()) or table.get(original.lower())
        return word if target is None else _cap(word, target)

    text = _TOKEN.sub(sub, text)
    return _restore(text, saved)


def _docs_on_disk():
    """Все собранные тома: название позы берётся и из соседних трактатов."""
    out = []
    for path in sorted((Path(__file__).resolve().parent.parent / "data").glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def fix_document(data):
    """Готовый том: карта терминов + названия поз (свои и из соседних томов)."""
    terms = _terms()
    for key, value in _pose_terms_from(_docs_on_disk() + [data]).items():
        terms.setdefault(key, value)
    return fix_tree(data, terms, {k.lower(): v for k, v in EN_PAIRS})


def fix_tree(obj, terms, en_terms, key=None):
    if key in SKIP_KEYS:
        return obj          # цитата, адрес или выходные данные целиком
    if isinstance(obj, str):
        return fix_text(obj, terms, en_terms)
    if isinstance(obj, list):
        return [fix_tree(v, terms, en_terms, key) for v in obj]
    if isinstance(obj, dict):
        return {k: fix_tree(v, terms, en_terms, k) for k, v in obj.items()}
    return obj


def diff(a, b, path="", acc=None):
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


def _changed_words(old, terms, en_terms):
    """Пары «было -> стало» для отчёта: слово за словом, без сдвигов."""
    text, _ = _protect(old)
    out = []
    for word in _TOKEN.findall(text):
        base = word
        if DIA.search(base) and not RUSSIAN_TAIL.search(base.lower()):
            base = yod(base)
        table = terms if re.search("[А-Яа-яЁё]", base) else en_terms
        target = table.get(base.lower()) or table.get(word.lower())
        fixed = base if target is None else _cap(base, target)
        if fixed != word:
            out.append((word, fixed))
    return out


def main(argv):
    mode = "check"
    if "--fix" in argv:
        mode = "fix"
    elif "--report" in argv:
        mode = "report"
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        paths = sorted(str(p) for p in
                       (Path(__file__).resolve().parent.parent / "data").glob("*.json"))
    docs = []
    for path in paths:
        try:
            docs.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            docs.append({})
    terms = _terms()
    for key, value in _pose_terms_from(docs).items():
        terms.setdefault(key, value)
    en_terms = {k.lower(): v for k, v in EN_PAIRS}

    total = 0
    words = {}
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        fixed = fix_tree(data, terms, en_terms)
        changed = diff(data, fixed)
        if not changed:
            continue
        total += len(changed)
        for _, old, _new in changed:
            for x, y in _changed_words(old, terms, en_terms):
                words[(x, y)] = words.get((x, y), 0) + 1
        if mode == "fix":
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(fixed, fh, ensure_ascii=False, indent=1)
                fh.write("\n")
        if mode != "report":
            print("%s: строк %d" % (path, len(changed)))

    if mode == "report" or total:
        print("\nзамены (сколько раз):")
        for (x, y), n in sorted(words.items(), key=lambda kv: -kv[1]):
            print("  %5d  %s → %s" % (n, x, y))
    if mode == "check" and total:
        print("\nвсего строк с расхождениями:", total)
        return 1
    if not total:
        print("\nдиакритика на месте: править нечего")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
