# -*- coding: utf-8 -*-
"""Devanāgarī -> IAST, letter by letter.

The «Ма̄насолла̄са» prints its verses only in Devanāgarī, while the site shows
every Sanskrit word in IAST (and, in the Russian version, in the Cyrillic
transliteration of `translit.py`). This module does nothing but rewrite the
letters the edition printed with the standard IAST values: no word is added,
none is joined, and an unknown code point is passed through untouched so that a
defect in the source never silently disappears.
"""

CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ṅ",
    "च": "c", "छ": "ch", "ज": "j", "झ": "jh", "ञ": "ñ",
    "ट": "ṭ", "ठ": "ṭh", "ड": "ḍ", "ढ": "ḍh", "ण": "ṇ",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "ś", "ष": "ṣ", "स": "s", "ह": "h",
    "ळ": "ḷ", "क़": "q", "ख़": "k͟h", "ग़": "ġ", "ज़": "z",
    "ड़": "ṛ", "ढ़": "ṛh", "फ़": "f", "य़": "ẏ",
}

# independent vowels
VOWELS = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū",
    "ऋ": "ṛ", "ॠ": "ṝ", "ऌ": "ḷ", "ॡ": "ḹ",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ऍ": "e", "ऑ": "o",
}

# dependent vowel signs
MATRAS = {
    "ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū",
    "ृ": "ṛ", "ॄ": "ṝ", "ॢ": "ḷ", "ॣ": "ḹ",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ॅ": "e", "ॉ": "o",
}

SIGNS = {
    "ं": "ṃ", "ँ": "m̐", "ः": "ḥ", "्": "", "ऽ": "'",
    "ॐ": "oṃ", "।": "|", "॥": "||",
}

DIGITS = {chr(0x0966 + i): str(i) for i in range(10)}


def to_iast(text):
    """Rewrite a Devanāgarī string in IAST; other characters are kept as they are."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in CONSONANTS:
            out.append(CONSONANTS[ch])
            # a consonant carries "a" unless a matra or the virama follows
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt in MATRAS:
                out.append(MATRAS[nxt])
                i += 2
                continue
            if nxt == "्":
                i += 1
                continue
            out.append("a")
            i += 1
            continue
        if ch in VOWELS:
            out.append(VOWELS[ch])
        elif ch in MATRAS:
            out.append(MATRAS[ch])
        elif ch in SIGNS:
            out.append(SIGNS[ch])
        elif ch in DIGITS:
            out.append(DIGITS[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


if __name__ == "__main__":
    for line in (
        "स्वस्तिकं गोमुखं पद्मं हंसाख्यं ब्राह्ममासनम्",
        "नृसिंहं गरुडं कूर्मं नागाख्यं वैष्णवासनम्",
        "वीरं मयूरं वज्राख्यं सिद्धाख्यं रौद्रमासनम्",
        "योन्यासनं विदुश्शाक्तं शैवं पश्चिमतानकम्",
        "निरालम्बनयोगस्य निरालम्बनमासनम्",
        "मानसोल्लासवार्तिकम्",
        "पश्चिमोत्तान",
    ):
        print(to_iast(line))
