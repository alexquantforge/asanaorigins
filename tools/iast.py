# -*- coding: utf-8 -*-
"""Bring the English volume to IAST.

The English reference prints Sanskrit in the simplified Latin transliteration
usual in English books — «Shankara», «Sureshvara», «Mandana Mishra»,
«Manasollasa», «Dakshinamurti-stotra». The site shows every Sanskrit word with
its diacritics (that is the rule for the whole project), so this module
rewrites those words to IAST.

What it does and does not do:

* it only rewrites letters that the Sanskrit spelling requires — ś for sh,
  ṣ for sh, ṇ/ṭ/ḍ for n/t/d, ā/ī/ū for a/i/u, ṃ for m before a consonant,
  c for ch; no word is added, none is removed, nothing is reordered;
* it never touches a web address, a file name or an identifier
  (``archive.org/details/…Sureshwaracharya…`` stays exactly as printed);
* Sanskrit place names of the tradition are transliterated like any other
  Sanskrit word (Vārāṇasī, Śṛṅgeri, Kāñcī, Dvārakā); the English forms of
  modern places, of institutions and of modern scholars' names are left as
  printed (Mysore, Madras, Ramtek, Jammu, Chennai, Kashi Hindu University,
  Aufrecht, Thrasher, Dasgupta, Swami Harshananda, Anantakrishna Shastri,
  «Bibliotheca Sanskrita»): those are names, not Sanskrit words of the text;
* a word that the source already printed with diacritics keeps them, and an
  older transliteration of the same word is brought to the one spelling used
  in the volume (``Sureśvarāchārya`` → ``Sureśvarācārya``, ``Dakshinámúrti``
  → ``Dakṣiṇāmūrti``, ``Vārtika`` → ``Vārttika``).
"""
import re

# ---------------------------------------------------------------- the map
# Key: the form printed in the English volume. Value: the IAST form.
MAP = {
    # -- the treatise and its neighbours
    "manasollasa": "mānasollāsa",
    "manasollasa-vardhini": "mānasollāsa-vardhinī",
    "vardhini": "vardhinī",
    "madhuri": "mādhurī",
    "tattvasudha": "tattvasudhā",
    "brahmasiddhi": "brahmasiddhi",
    "naishkarmya": "naiṣkarmya",
    "pranava": "praṇava",
    "bhamati": "bhāmatī",
    "brihadaranyaka": "bṛhadāraṇyaka",
    "taittiriya": "taittirīya",
    "uktanukta-duruktartha-vyaktikari": "uktānukta-duruktārtha-vyaktikāri",
    "dakshinamnaya": "dakṣiṇāmnāya",
    "shri": "śrī",
    "sri": "śrī",
    "vivarana": "vivaraṇa",
    "samkshepa": "saṃkṣepa",
    "shariraka": "śārīraka",
    "jayamadhava": "jayamādhava",
    "varttika": "vārttika",
    "varttikas": "vārttikas",
    "vartika": "vārttika",
    "vartikas": "vārttikas",
    "vārtika": "vārttika",
    "vārtikas": "vārttikas",
    "varttikakara": "vārttikakāra",
    "varttikam": "vārttikam",
    "ullasa": "ullāsa",
    "ullasas": "ullāsas",
    "stotra": "stotra",
    "stotras": "stotras",
    "asana": "āsana",
    "asanas": "āsanas",
    "vajrasana": "vajrāsana",
    "pashchimottanasana": "paścimottānāsana",
    "dakshinamurti": "dakṣiṇāmūrti",
    "dakshinamurti-stotra": "dakṣiṇāmūrti-stotra",
    "dakshinamurti-upanishad": "dakṣiṇāmūrti-upaniṣad",
    "dakshinamurtistotravarttika": "dakṣiṇāmūrtistotravārttika",
    # a word the PDF table hyphenated at the end of a cell line
    "dharma-rtha": "dharmārtha",
    # the same words in the acute-accent transliteration of older English books
    "dakshinámúrti-stotra": "dakṣiṇāmūrti-stotra",
    "dakshinámúrti": "dakṣiṇāmūrti",
    "mánasollása": "mānasollāsa",
    "shankara": "śaṅkara",
    "sankara": "śaṅkara",
    "shankaracharya": "śaṅkarācārya",
    "sankaracharya": "śaṅkarācārya",
    "shaṅkarāchārya": "śaṅkarācārya",
    "śaṅkarāchārya": "śaṅkarācārya",
    "sureshvara": "sureśvara",
    "sureshvaracharya": "sureśvarācārya",
    "sureshwaracharya": "sureśvarācārya",
    "sureshwara": "sureśvara",
    "suresvaracharya": "sureśvarācārya",
    "suresvara": "sureśvara",
    "sureśvarāchārya": "sureśvarācārya",
    "mandana": "maṇḍana",
    "mishra": "miśra",
    "vachaspati": "vācaspati",
    "svayamprakasha": "svayamprakāśa",
    "svayamprakasa": "svayamprakāśa",
    "ramatirtha": "rāmatīrtha",
    "someshvara": "someśvara",
    "appayya": "appayya",
    "dikshita": "dīkṣita",
    "sarvajnatman": "sarvajñātman",
    "mimamsaka": "mīmāṃsaka",
    "yudhishthira": "yudhiṣṭhira",
    "parameshvara": "parameśvara",

    # -- the hymn and the terms around it
    "shloka": "śloka",
    "shlokas": "ślokas",
    "dandas": "daṇḍas",
    "grantha": "grantha",
    "granthas": "granthas",
    "matha": "maṭha",
    "mathas": "maṭhas",
    "pandit": "paṇḍit",
    "upanishad": "upaniṣad",
    "upanishads": "upaniṣads",
    "bhagavadgita": "bhagavadgītā",
    "sutra": "sūtra",
    "sutras": "sūtras",
    "bhashya": "bhāṣya",
    "nyaya": "nyāya",
    "chandrika": "candrikā",
    "nibandha": "nibandha",
    "suchi": "sūcī",
    "padachcheda": "padaccheda",
    "lakshanas": "lakṣaṇas",
    "mimāmsaka": "mīmāṃsaka",
    "sandhi": "sandhi",
    "siddhi": "siddhi",
    "acharya": "ācārya",
    "yati": "yati",
    "kavi": "kavi",
    "guru": "guru",
    "muni": "muni",

    # -- schools, deities, the body of the text
    "advaita": "advaita",
    "vedanta": "vedānta",
    "vaishnava": "vaiṣṇava",
    "vaishnava-asana": "vaiṣṇava-āsana",
    "shaiva": "śaiva",
    "saiva": "śaiva",
    "shakta": "śākta",
    "sakta": "śākta",
    "raudra": "raudra",
    "brahma-asana": "brāhma-āsana",
    "brahma, vaishnava, raudra, shakta, shaiva": "brāhma, vaiṣṇava, raudra, śākta, śaiva",
    "vaishnava, raudra, shakta, brahma": "vaiṣṇava, raudra, śākta, brāhma",
    "the brahma one": "the brāhma one",
    "brahma-sutras": "brahma-sūtras",
    "brahma-sūtras": "brahma-sūtras",
    "brahma-sutra": "brahma-sūtra",
    "brahma-sūtra": "brahma-sūtra",
    "brahma-siddhi": "brahma-siddhi",
    "brahma": "brahmā",
    "vishnu": "viṣṇu",
    "shiva": "śiva",
    "shakti": "śakti",
    "rudra": "rudra",
    "brahman": "brahman",
    "atman": "ātman",
    "paramatman": "paramātman",
    "sadasiva": "sadāśiva",
    "sadashiva": "sadāśiva",
    "ishvara": "īśvara",
    "jiva": "jīva",
    "avidya": "avidyā",
    "vidya": "vidyā",
    "maya": "māyā",
    "karma": "karma",
    "dharma": "dharma",
    "yoga": "yoga",
    "yogic": "yogic",
    "yogin": "yogin",
    "yogins": "yogins",
    "hatha": "haṭha",
    "bandha": "bandha",
    "bandhas": "bandhas",
    "mudra": "mudrā",
    "mudras": "mudrās",
    "kundalini": "kuṇḍalinī",
    "akasha": "ākāśa",
    "vayu": "vāyu",
    "vayus": "vāyus",
    "prana": "prāṇa",
    "apana": "apāna",
    "pranayama": "prāṇāyāma",
    "pratyahara": "pratyāhāra",
    "dharana": "dhāraṇā",
    "dhyana": "dhyāna",
    "samadhi": "samādhi",
    "yama": "yama",
    "niyama": "niyama",
    "rechaka": "recaka",
    "puraka": "pūraka",
    "kumbhaka": "kumbhaka",
    "krikara": "kṛkara",
    "devadatta": "devadatta",
    "purusha": "puruṣa",
    "shabda": "śabda",
    "shabdadvaita": "śabdādvaita",
    "sphota": "sphoṭa",
    "aparoksha": "aparokṣa",
    "mahavakya": "mahāvākya",
    "parampara": "paramparā",
    "paramparas": "paramparās",
    "samvat": "saṃvat",
    "shaka": "śaka",
    "yuga": "yuga",
    "agamas": "āgamas",
    "pratyabhijna": "pratyabhijñā",
    "darshana": "darśana",
    "bhumika": "bhūmikā",
    "adhyatma": "adhyātma",
    "prakasha": "prakāśa",
    "shabda-aparoksha": "śabda-aparokṣa",
    "shastra": "śāstra",
    "shastras": "śāstras",
    "nagari": "nāgarī",
    "devanagari": "devanāgarī",
    "devanāgarī": "devanāgarī",

    # -- the āsanas of IX.24–26
    "svastika": "svastika",
    "gomukha": "gomukha",
    "padma": "padma",
    "hamsa": "haṃsa",
    "nrisimha": "nṛsiṃha",
    "garuda": "garuḍa",
    "kurma": "kūrma",
    "naga": "nāga",
    "vira": "vīra",
    "mayura": "mayūra",
    "vajra": "vajra",
    "siddha": "siddha",
    "yoni": "yoni",
    "pashchima": "paścima",
    "paschima": "paścima",
    "niralambana": "nirālambana",
    "nirālambana-asana": "nirālambana-āsana",

    # -- the seats of the tradition
    "shringeri": "śṛṅgeri",
    "sringeri": "śṛṅgeri",
    "sharada": "śāradā",
    "kalika": "kālikā",
    "kanchi": "kāñcī",
    "dvaraka": "dvārakā",
    "varanasi": "vārāṇasī",
    "raghunath": "raghunātha",
    "gangotri": "gaṅgotrī",
    "maharaja": "mahārāja",
    "mahamandaleshvara": "mahāmaṇḍaleśvara",
    "peetham": "pīṭham",
}

# The letters a Sanskrit word in IAST may continue with. A replacement is made
# only when the key stands alone between these (or punctuation).
_LETTER = "A-Za-zĀāĪīŪūṚṛṜṝḶḷṂṃṀṁḤḥṄṅÑñṬṭḌḍṆṇŚśṢṣ"

_KEYS = sorted(MAP, key=len, reverse=True)
PATTERN = re.compile(
    r"(?<![%s])(%s)(?![%s])" % (_LETTER, "|".join(re.escape(k) for k in _KEYS),
                                _LETTER),
    re.I)

# A web address, a file name or a shelf mark is reproduced as printed.
SKIP_TOKEN = re.compile(
    r"[/\\_@]|://|\.(?:org|com|net|edu|htm|html|png|jp2|zip|xml|json|pdf)\b",
    re.I)
TAG = re.compile(r"<[^>]+>")


def _match_case(source, target):
    if source.isupper() and len(source) > 1:
        return target
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


def fix_text(text):
    """Rewrite the Sanskrit words of one English string; nothing else moves."""
    out = []
    pos = 0
    for m in TAG.finditer(text):
        out.append(_fix_plain(text[pos:m.start()]))
        out.append(m.group(0))          # markup as printed
        pos = m.end()
    out.append(_fix_plain(text[pos:]))
    return "".join(out)


def _fix_plain(text):
    """Rewrite the words of one run of plain text (markup excluded).

    A token that is a web address, a file name or a shelf mark is listed as
    blocked, and no replacement is made inside it.
    """
    if not text:
        return text
    blocked = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)
               if SKIP_TOKEN.search(m.group(0))]

    def repl(match):
        start = match.start()
        for b0, b1 in blocked:
            if b0 <= start < b1:
                return match.group(0)
        return _match_case(match.group(0), MAP[match.group(0).lower()])

    return PATTERN.sub(repl, text)


SKIP_KEYS = {"key", "number", "verses", "pdf", "file", "id"}


def fix_tree(obj, skip_types=("code", "deva")):
    """Apply `fix_text` to every string of a block tree.

    Route keys, numbers and file names are left exactly as they are: they are
    identifiers, not words of the text.
    """
    if isinstance(obj, str):
        return fix_text(obj)
    if isinstance(obj, list):
        return [fix_tree(v, skip_types) for v in obj]
    if isinstance(obj, dict):
        if obj.get("type") in skip_types:
            return obj
        return {k: (v if k in SKIP_KEYS else fix_tree(v, skip_types))
                for k, v in obj.items()}
    return obj


if __name__ == "__main__":
    for line in (
        "The \"Manasollasa\" of Sureshvaracharya — a commentary on the "
        "\"Dakshinamurti-stotra\"",
        "Mandana Mishra and Shankara are different persons (Shringeri Matha)",
        "the brahma-asana and the vaishnava-asana; yoni is the shakta one",
        "archive.org/details/NeGr_m-1192-manasollas-of-sureshvaracharya-ramtek",
        "Svastika, gomukha, padma, hamsa — the brahma-asana.",
        "Sureshvara (A. D. 800) — Hindupedia",
    ):
        print(fix_text(line))
