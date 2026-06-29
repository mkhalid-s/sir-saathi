#!/usr/bin/env python3
"""
VirgoD3 → English transliteration pipeline.

Chain: VirgoD3 encoded text → Devanagari Unicode → Roman/English

Approach: Character-by-character tokenizer that reads VirgoD3 encoding
and produces Devanagari Unicode directly, using É as the syllable boundary
marker (NOT as a matra). Then standard Devanagari→Roman transliteration.

Mapping source: DV-TTSurekhEN (log-os/font-mapper) + visual verification
against rendered PDF pages.
"""

import re

# =============================================================================
# Stage 1: VirgoD3 → Devanagari (tokenizer approach)
# =============================================================================

# VirgoD3 consonant chars → Devanagari consonant (base form, no halant).
#
# VirgoD3 has TWO types of consonants:
# - TWO-BYTE: consonant + specific second byte (e.g. Eò=क, ®ú=र, nù=द)
# - SINGLE-BYTE: consonant alone (e.g. ¶=श, ¨=म, º=स)
#
# Two-byte consonants are checked FIRST (longest match).
# The second byte is font-specific and NOT a modifier — it's part of the glyph ID.

_V_CONSONANTS_2BYTE = {
    "Eò": "क",     # ka
    "Gò": "क्र",   # kra (conjunct, 2-byte variant)
    "Hò": "क्त",   # kta (conjunct, 2-byte variant)
    "Uô": "छ",     # chha
    "`ö": "ठ",     # Tha
    "b÷": "ड",     # Da
    "fø": "ढ",     # Dha
    "nù": "द",     # da
    "pù": "द्र",   # dra (conjunct)
    "qù": "द्द",   # dda (conjunct)
    "¡ò": "फ",     # pha
    "®ú": "र",     # ra
    "¯û": "रु",    # ru (special)
    "°ü": "रू",    # ruu (special)
    "³ý": "ळ",     # La
    "½þ": "ह",     # ha
    "]õ": "ट",     # Ta (two-byte variant)
    "®ô": "र",     # ra (variant second byte)
    "Âö": "्ठ",    # Tha-halant (conjunct element)
    "Âõ": "्ट",    # Ta-halant (conjunct element)
    "Âù": "्द",    # da-halant (conjunct element)
    "Â÷": "्ड",    # Da-halant (conjunct element)
}

_V_CONSONANTS_1BYTE = {
    "C": "क्",    # k (always halant — conjunct form)
    "E": "क",     # ka (fallback if ò missing)
    "F": "क़",    # qa
    "G": "क्र",   # kra (conjunct)
    "H": "क्त",   # kta (conjunct)
    "I": "क्ष",   # ksha (conjunct)
    "J": "ख",     # kha
    "K": "ख़",    # kha (nukta)
    "L": "ख्र",   # khra (conjunct)
    "M": "ग",     # ga
    "N": "ग़",    # ga (nukta)
    "O": "ग्र",   # gra (conjunct)
    "P": "घ",     # gha
    "Q": "घ्र",   # ghra (conjunct)
    "R": "ङ",     # nga
    "S": "च",     # cha
    "T": "च्र",   # chra (conjunct)
    "U": "छ",     # chha (fallback)
    "V": "ज",     # ja
    "W": "ज़",    # za (nukta)
    "X": "ज्र",   # jra (conjunct)
    "Y": "ज्ञ",   # gnya (conjunct)
    "Z": "झ",     # jha
    "[": "झ्र",   # jhra (conjunct)
    "\\": "ञ",    # nya
    "]": "ट",     # Ta (fallback if õ missing)
    "^": "ट्ट",   # TTa (conjunct)
    "_": "ट्ठ",   # TTha (conjunct)
    "`": "ठ",     # Tha (fallback)
    "a": "ठ्ठ",   # TThTha (conjunct)
    "b": "ड",     # Da (fallback)
    "c": "ड़",    # Da (nukta)
    "d": "ड्ड",   # DDa (conjunct)
    "e": "ड्ढ",   # DDha (conjunct)
    "f": "ढ",     # Dha (fallback)
    "g": "ढ़",    # Dha (nukta)
    "h": "ण",     # Na
    "i": "त",     # ta
    "j": "त्र",   # tra (conjunct)
    "k": "त्त",   # tta (conjunct)
    "l": "थ",     # tha
    "m": "थ्र",   # thra (conjunct)
    "n": "द",     # da (fallback)
    "o": "दृ",    # dri (conjunct)
    "p": "द्र",   # dra (fallback)
    "q": "द्द",   # dda (conjunct, fallback)
    "r": "द्ध",   # ddha (conjunct)
    "s": "द्म",   # dma (conjunct)
    "t": "द्य",   # dya (conjunct)
    "u": "द्व",   # dva (conjunct)
    "v": "ध",     # dha
    "w": "ध्र",   # dhra (conjunct)
    "x": "न",     # na
    "y": "न्र",   # nra (conjunct)
    "z": "न्न",   # nna (conjunct)
    "{": "प",     # pa
    "|": "प्र",   # pra (conjunct)
    "}": "फ्",    # pha (halant — conjunct form)
    "~": "फ़्",   # fa (halant nukta)
    "¡": "फ",     # pha (fallback)
    "¢": "फ़",    # fa (nukta)
    "£": "फ्र",   # phra (conjunct)
    "¤": "ब",     # ba
    "¥": "ब्र",   # bra (conjunct)
    "¦": "भ",     # bha
    "§": "भ्र",   # bhra (conjunct)
    "¨": "म",     # ma
    "©": "म्र",   # mra (conjunct)
    "ª": "य",     # ya
    "«": "य्र",   # yra (conjunct)
    "®": "र",     # ra (fallback)
    "¯": "रु",    # ru (fallback)
    "°": "रू",    # ruu (fallback)
    "±": "ल",     # la
    "²": "ळ्",    # La (halant — conjunct form)
    "³": "ळ",     # La (fallback)
    "´": "व",     # va
    "µ": "व्र",   # vra (conjunct)
    "¶": "श",     # sha
    "•": "श्व",   # shva (conjunct)
    "·": "श्व",   # shva (conjunct, variant)
    "¸": "श्र",   # shra (conjunct)
    "¹": "ष",     # Sha
    "º": "स",     # sa
    "»": "स्र",   # sra (conjunct)
    "¼": "ह्",    # ha (halant — conjunct form)
    "½": "ह",     # ha (fallback)
    "À": "ह्म",   # hma (conjunct)
    "Á": "ह्य",   # hya (conjunct)
    "¾": "हृ",    # hri (conjunct)
    "¿": "ह्र",   # hra (conjunct)
}

# VirgoD3 matra chars → Devanagari matra
_V_MATRAS = {
    "Ò": "ी",    # ii
    "Ó": "ी",    # ii (variant glyph)
    # Note: Ô (0xD4) is handled specially — it means repha + ī on the PRECEDING consonant
    "Ö": "ु",    # u
    "×": "ु",    # u (variant)
    "Ù": "ु",    # u (variant)
    "Ú": "ू",    # uu
    "Ý": "ू",    # uu (variant)
    "Þ": "ृ",    # ri
    "ß": "ॄ",    # rii
    "ä": "े",    # e
    "æ": "े",    # e (variant glyph, same as ä)
    "è": "ै",    # ai
}

# VirgoD3 modifier chars → Devanagari
_V_MODIFIERS = {
    "Æ": "ं",    # anusvara
    "È": "ं",    # anusvara (variant glyph)
    "Ä": "ँ",    # chandrabindu
    # Note: Ç and Ì (repha) are handled specially in virgo_to_devanagari()
    # — they place र् BEFORE the following consonant, not after the current one.
    "Â": "्",    # halant (explicit)
    "Ã": "़",    # nukta
    "Å": "्र",   # ra-halant (subscript ra)
}

# VirgoD3 independent vowels
_V_VOWELS = {
    "+": "अ",    # a
    "<": "इ",    # i
    "=": "उ",    # u
    ">": "ऊ",    # uu
    "@": "ऋ",    # ri
    "A": "ॠ",    # rii
    "B": "ए",    # e
    "‹": "ए",    # e (variant)
}

# VirgoD3 special/multi-char sequences (checked before single-char)
_V_SPECIAL = {
    "¬": "्य",   # ya-halant (subscript ya)
    "Ï": "च्छि",  # conjunct: machchhi (च्छि)
}

# Composite matra chars
_V_COMPOSITE = {
    "å": "ें",   # e + anusvara
    "é": "ैं",   # ai + anusvara
    "ì": "ॅ",    # candra-e
}

# Rendering hints / formatting chars that can appear after matras.
# When following a matra or at end of syllable, these are just rendering
# artifacts from VirgoD3 and should be ignored. They only have meaning
# as the second byte of a 2-byte consonant (handled in consonant parsing).
_V_RENDER_HINTS = set("òóôõö÷øùúûüýþ")
# Truly unused formatting chars + house number / formatting artifacts
_V_IGNORE = set("ðñŸã†")

# Set of all VirgoD3 consonant first-chars (for lookahead)
_V_CONS_SET = set(_V_CONSONANTS_1BYTE.keys()) | {k[0] for k in _V_CONSONANTS_2BYTE.keys()}

# É = 0xC9 — the carrier/filler character
_CARRIER = "É"


def virgo_to_devanagari(text):
    """Convert VirgoD3 encoded text to Unicode Devanagari.

    Tokenizer approach: reads char-by-char, using É as syllable boundary.

    Syllable patterns in VirgoD3:
      CONSONANT + É = consonant with inherent 'a' (no matra needed)
      CONSONANT + É + MATRA = consonant + that matra
      CONSONANT + ÉÉ = consonant + ा (aa matra)
      CONSONANT + ÉÉ + MATRA = consonant + composed matra (ो, ौ)
      CONSONANT (no É) = consonant in conjunct (halant + next consonant)
      Ê + CONSONANT... = ि (i-matra) applied to that consonant
      Ë + CONSONANT... = ी (ii-matra, rare prefix form)

    Independent vowels:
      + É = आ (aa)
      + É ä = ओ (o)
      + É è = औ (au)
    """
    result = []
    i = 0

    while i < len(text):
        ch = text[i]

        # --- Space and ASCII pass-through ---
        if ch == " " or (ch.isascii() and (ch.isdigit() or ch in "/-.,():")):
            result.append(ch)
            i += 1
            continue

        # --- Ignore formatting chars and stray render hints ---
        if ch in _V_IGNORE or ch in _V_RENDER_HINTS:
            i += 1
            continue

        # --- Repha (Ç, Ì): places र् BEFORE the following consonant ---
        if ch in ("Ç", "Ì"):
            i += 1
            # Skip any render hints after repha marker
            while i < len(text) and text[i] in _V_RENDER_HINTS:
                i += 1
            # Parse the next consonant syllable and prepend र्
            consonant_dev, i = _parse_consonant_syllable(text, i)
            if consonant_dev:
                result.append("र्" + consonant_dev)
            else:
                result.append("र्")  # standalone repha (shouldn't happen)
            continue

        # --- i-matra prefix (Ê) ---
        if ch == "Ê":
            # The ि matra applies to the NEXT consonant.
            # In Unicode, ि comes after the consonant in encoding.
            # We need to output: consonant + ि
            i += 1
            # Parse the next consonant syllable, then append ि
            consonant_dev, i = _parse_consonant_syllable(text, i)
            if consonant_dev:
                result.append(consonant_dev + "ि")
            else:
                result.append("ि")  # standalone (shouldn't happen)
            continue

        # --- ii-matra prefix (Ë) ---
        if ch == "Ë":
            i += 1
            consonant_dev, i = _parse_consonant_syllable(text, i)
            if consonant_dev:
                result.append(consonant_dev + "ी")
            else:
                result.append("ी")
            continue

        # --- Î (special ligature: स्थि) ---
        if ch == "Î":
            i += 1
            result.append("स्थि")
            continue

        # --- Independent vowels starting with + ---
        if ch == "+":
            i += 1
            if i < len(text) and text[i] == _CARRIER:
                i += 1  # consume É
                if i < len(text) and text[i] == _CARRIER:
                    # +ÉÉ = आ + check for composed matra
                    i += 1
                    if i < len(text) and text[i] in _V_MATRAS:
                        matra = _V_MATRAS[text[i]]
                        i += 1
                        if matra == "े":
                            result.append("ओ")  # आ + े = ओ
                        elif matra == "ै":
                            result.append("औ")  # आ + ै = औ
                        else:
                            result.append("आ" + matra)
                    else:
                        result.append("आ")
                elif i < len(text) and text[i] in _V_MATRAS:
                    matra = _V_MATRAS[text[i]]
                    i += 1
                    if matra == "े":
                        result.append("ओ")  # अ + É + े → ओ
                    elif matra == "ै":
                        result.append("औ")  # अ + É + ै → औ
                    else:
                        result.append("आ" + matra)
                else:
                    result.append("आ")  # +É = आ
            else:
                result.append("अ")  # + alone = अ
            # Check for modifier after vowel
            while i < len(text) and text[i] in _V_MODIFIERS:
                result.append(_V_MODIFIERS[text[i]])
                i += 1
            continue

        # --- Other independent vowels ---
        if ch in _V_VOWELS:
            result.append(_V_VOWELS[ch])
            i += 1
            # Check for Ç (ई variant: <Ç = ई)
            if ch == "<" and i < len(text) and text[i] == "Ç":
                result[-1] = "ई"
                i += 1
            elif ch == "<" and i < len(text) and text[i] == "È":
                result[-1] = "ईं"
                i += 1
            # Consume carrier if present
            if i < len(text) and text[i] == _CARRIER:
                i += 1
            # Check for matra after vowel (Bä = ऐ)
            if ch == "B" and i < len(text) and text[i] == "ä":
                result[-1] = "ऐ"
                i += 1
            continue

        # --- Consonant ---
        if ch in _V_CONS_SET:
            consonant_dev, i = _parse_consonant_syllable(text, i)
            result.append(consonant_dev)
            continue

        # --- Special sequences ---
        if ch in _V_SPECIAL:
            result.append(_V_SPECIAL[ch])
            i += 1
            continue

        # --- Standalone modifiers ---
        if ch in _V_MODIFIERS:
            result.append(_V_MODIFIERS[ch])
            i += 1
            continue

        # --- Composite matras ---
        if ch in _V_COMPOSITE:
            result.append(_V_COMPOSITE[ch])
            i += 1
            continue

        # --- Standalone carrier É (shouldn't be common) ---
        if ch == _CARRIER:
            i += 1
            continue

        # --- Punctuation ---
        if ch == "$":
            result.append("ॐ")
            i += 1
            continue
        if ch == "&":
            result.append("ः")
            i += 1
            continue
        if ch == "*":
            result.append("।")
            i += 1
            continue

        # --- Unmapped: keep as-is ---
        result.append(ch)
        i += 1

    return "".join(result)


def _parse_consonant_syllable(text, i):
    """Parse a consonant + optional carrier + optional matra from position i.

    Returns (devanagari_string, new_position).

    Patterns:
      CONS + É + É + MATRA → consonant + composed matra (ो, ौ)
      CONS + É + É         → consonant + ा
      CONS + É + MATRA     → consonant + matra
      CONS + É             → consonant (inherent 'a', no matra)
      CONS (no É)          → consonant + ् (halant — conjunct with next)
    """
    if i >= len(text) or text[i] not in _V_CONS_SET:
        return ("", i)

    # Try 2-byte consonant first
    is_2byte = False
    if i + 1 < len(text):
        two = text[i:i+2]
        if two in _V_CONSONANTS_2BYTE:
            cons = _V_CONSONANTS_2BYTE[two]
            i += 2
            is_2byte = True
        elif text[i] in _V_CONSONANTS_1BYTE:
            cons = _V_CONSONANTS_1BYTE[text[i]]
            i += 1
        else:
            return ("", i)
    elif text[i] in _V_CONSONANTS_1BYTE:
        cons = _V_CONSONANTS_1BYTE[text[i]]
        i += 1
    else:
        return ("", i)

    # Check for É carrier
    if i < len(text) and text[i] == _CARRIER:
        i += 1  # consume first É

        # Check for Ô (repha + ī combined: places र् before consonant + ी after)
        if i < len(text) and text[i] == "Ô":
            i += 1
            return ("र्" + cons + "ी", i)

        # Check for Ç/Ì repha after carrier — handled in main loop, but
        # could appear here too. If so, this consonant is complete (inherent 'a')
        # and repha applies to the NEXT consonant.
        if i < len(text) and text[i] in ("Ç", "Ì"):
            # Don't consume — let the main loop handle it as prefix for next syllable
            return (cons, i)

        if is_2byte:
            # For 2-BYTE consonants: single É = ा (aa matra).
            # No double-É needed (2nd byte already provides inherent 'a').
            if i < len(text) and text[i] in _V_MATRAS:
                matra = _V_MATRAS[text[i]]
                i += 1
                if matra == "े":
                    return (cons + "ो", i)   # ा + े = ो
                elif matra == "ै":
                    return (cons + "ौ", i)   # ा + ै = ौ
                else:
                    return (cons + "ा" + matra, i)
            if i < len(text) and text[i] in _V_COMPOSITE:
                result = _V_COMPOSITE[text[i]]
                i += 1
                return (cons + "ा" + result, i)
            # É with no following matra = ा
            mods = ""
            while i < len(text) and text[i] in _V_MODIFIERS:
                mods += _V_MODIFIERS[text[i]]
                i += 1
            return (cons + "ा" + mods, i)

        else:
            # For 1-BYTE consonants: single É = inherent 'a' (carrier).
            # Double ÉÉ = ा (aa matra).
            if i < len(text) and text[i] == _CARRIER:
                i += 1  # consume second É → aa matra

                # Check for matra after ÉÉ (composed: ो, ौ)
                if i < len(text) and text[i] in _V_MATRAS:
                    matra = _V_MATRAS[text[i]]
                    i += 1
                    if matra == "े":
                        return (cons + "ो", i)   # ा + े = ो
                    elif matra == "ै":
                        return (cons + "ौ", i)   # ा + ै = ौ
                    else:
                        return (cons + "ा" + matra, i)
                else:
                    return (cons + "ा", i)  # ÉÉ = ा

            # Check for matra after single É
            if i < len(text) and text[i] in _V_MATRAS:
                matra = _V_MATRAS[text[i]]
                i += 1
                return (cons + matra, i)

            # Check for composite matra
            if i < len(text) and text[i] in _V_COMPOSITE:
                result = _V_COMPOSITE[text[i]]
                i += 1
                return (cons + result, i)

            # Single É, no matra = inherent 'a' (no matra needed in Devanagari)
            mods = ""
            while i < len(text) and text[i] in _V_MODIFIERS:
                mods += _V_MODIFIERS[text[i]]
                i += 1
            return (cons + mods, i)

    else:
        # No É after consonant.
        # For 2-BYTE consonants: the second byte already provides inherent 'a'.
        # A matra can follow directly without É.
        if is_2byte:
            # Check Ô (repha + ī)
            if i < len(text) and text[i] == "Ô":
                i += 1
                return ("र्" + cons + "ी", i)
            if i < len(text) and text[i] in _V_MATRAS:
                matra = _V_MATRAS[text[i]]
                i += 1
                # Skip trailing render hints
                while i < len(text) and text[i] in _V_RENDER_HINTS:
                    i += 1
                return (cons + matra, i)
            if i < len(text) and text[i] in _V_COMPOSITE:
                result = _V_COMPOSITE[text[i]]
                i += 1
                while i < len(text) and text[i] in _V_RENDER_HINTS:
                    i += 1
                return (cons + result, i)
            # Check for modifier
            mods = ""
            while i < len(text) and text[i] in _V_MODIFIERS:
                mods += _V_MODIFIERS[text[i]]
                i += 1
            return (cons + mods, i)  # inherent vowel, no halant

        # For 1-BYTE consonants without É:
        # Check Ô (repha + ī)
        if i < len(text) and text[i] == "Ô":
            i += 1
            return ("र्" + cons + "ी", i)
        # Check if a matra follows directly (some VirgoD3 sequences skip É before matras)
        if i < len(text) and text[i] in _V_MATRAS:
            matra = _V_MATRAS[text[i]]
            i += 1
            # Skip trailing render hints after matra
            while i < len(text) and text[i] in _V_RENDER_HINTS:
                i += 1
            return (cons + matra, i)
        if i < len(text) and text[i] in _V_COMPOSITE:
            result = _V_COMPOSITE[text[i]]
            i += 1
            while i < len(text) and text[i] in _V_RENDER_HINTS:
                i += 1
            return (cons + result, i)
        # Check for Ç/Ì repha: consonant + Ç = repha above this consonant
        if i < len(text) and text[i] in ("Ç", "Ì"):
            i += 1
            # Skip render hints after repha marker
            while i < len(text) and text[i] in _V_RENDER_HINTS:
                i += 1
            return ("र्" + cons, i)
        # No É, no matra, no repha = conjunct (add halant)
        # UNLESS the consonant mapping already includes halant (like C=क्, }=फ्)
        if cons.endswith("्"):
            return (cons, i)  # Already has halant
        else:
            return (cons + "्", i)  # Add halant for conjunct


# =============================================================================
# Stage 2: Devanagari Unicode → Roman/English
# =============================================================================

_DEV_TO_ROMAN = {
    # Vowels
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ऋ": "ri", "ॠ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ऑ": "o",
    # Matras
    "ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
    "ृ": "ri", "ॄ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ॉ": "o", "ॅ": "e",
    # Anusvara, visarga, chandrabindu
    "ं": "n", "ँ": "n", "ः": "h",
    # Consonants
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "ळ": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "d",
    "ढ़": "dh", "फ़": "f",
    "्": "", "़": "",
    "।": ".", "ॐ": "om",
}

_CONJUNCT_MAP = {
    "क्र": "kr", "क्त": "kt", "क्ष": "ksh",
    "ज्ञ": "gny", "ज्र": "jr",
    "त्र": "tr", "त्त": "tt",
    "थ्र": "thr",
    "द्र": "dr", "द्द": "dd", "द्ध": "ddh", "द्म": "dm",
    "द्य": "dy", "द्व": "dv",
    "ध्र": "dhr",
    "न्र": "nr", "न्न": "nn",
    "प्र": "pr", "फ्र": "phr",
    "ब्र": "br", "भ्र": "bhr",
    "म्र": "mr", "य्र": "yr", "व्र": "vr",
    "श्र": "shr", "श्व": "shv",
    "स्र": "sr", "स्थ": "sth",
    "ह्म": "hm", "ह्य": "hy", "ह्र": "hr",
}

_DEV_CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलळवशषसह"
                      "क़ख़ग़ज़ड़ढ़फ़")
_DEV_MATRAS = set("ािीुूृॄेैोौॉॅ")
_DEV_MODIFIERS = set("ंँः़")


def devanagari_to_roman(text):
    """Convert Devanagari Unicode text to Roman/English.

    Adds inherent 'a' after consonants not followed by matra or halant.
    """
    result = []
    i = 0

    while i < len(text):
        ch = text[i]

        if ch == " ":
            result.append(" ")
            i += 1
            continue
        if ch.isascii():
            result.append(ch)
            i += 1
            continue

        # Try 3-char conjunct
        tri = text[i:i+3]
        if tri in _CONJUNCT_MAP:
            result.append(_CONJUNCT_MAP[tri])
            i += 3
            if i < len(text) and text[i] in _DEV_MATRAS:
                result.append(_DEV_TO_ROMAN.get(text[i], ""))
                i += 1
            elif i >= len(text) or text[i] in (" ",) or text[i] in _DEV_CONSONANTS or text[i] in _DEV_MODIFIERS:
                result.append("a")
            continue

        # Try 2-char conjunct
        bi = text[i:i+2]
        if bi in _CONJUNCT_MAP:
            result.append(_CONJUNCT_MAP[bi])
            i += 2
            if i < len(text) and text[i] in _DEV_MATRAS:
                result.append(_DEV_TO_ROMAN.get(text[i], ""))
                i += 1
            elif i >= len(text) or text[i] in (" ",) or text[i] in _DEV_CONSONANTS or text[i] in _DEV_MODIFIERS:
                result.append("a")
            continue

        # Consonant
        if ch in _DEV_CONSONANTS:
            result.append(_DEV_TO_ROMAN.get(ch, ch))
            i += 1
            if i < len(text) and text[i] == "्":
                i += 1  # halant — no vowel
            elif i < len(text) and text[i] in _DEV_MATRAS:
                result.append(_DEV_TO_ROMAN.get(text[i], ""))
                i += 1
            elif i >= len(text) or text[i] in (" ",) or text[i] in _DEV_CONSONANTS or text[i] in _DEV_MODIFIERS:
                result.append("a")
            continue

        if ch in _DEV_TO_ROMAN:
            result.append(_DEV_TO_ROMAN[ch])
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


# =============================================================================
# Combined pipeline
# =============================================================================

def virgo_to_english(text):
    """Convert VirgoD3 encoded text to English/Roman script."""
    dev = virgo_to_devanagari(text)
    roman = devanagari_to_roman(dev)
    roman = re.sub(r'\s+', ' ', roman).strip()
    return roman


# =============================================================================
# CLI / Testing
# =============================================================================

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        tests = [
            ("¶ÉäJÉ", "शेख", "shekh"),
            ("¨Éä½þiÉÉ", "मेहता", "mehta"),
            ("{ÉÉ]õÒ±É", "पाटील", "paatil"),
            ("ºÉÉ´ÉÆiÉ", "सावंत", "saavant"),
            ("JÉÉiÉÖxÉ", "खातुन", "khaatun"),
            ("½þ±ÉÒ¨ÉÉ", "हलीमा", "haleemaa"),
            ("¨ÉÆMÉä¶É", "मंगेश", "mangesh"),
            ("Ê´É±ÉÉºÉ", "विलास", "vilaas"),
            ("¨ÉÉä½þ¨¨Énù", "मोहम्मद", "mohammad"),
            ("ÊxÉVÉÉ¨ÉÖqùÒxÉ", "निजामुद्दीन", "nijaamuddin"),
            ("ºÉÉÊVÉnù+±ÉÒ", "साजिदअली", "saajidali"),
            ("EòÉ®úJÉÉxÉÒºÉ", "कारखानीस", "kaarkhaanees"),
            ("{ÉÖ¯û¹ÉÉäkÉ¨É", "पुरुषोत्तम", "purushottam"),
            ("Ê´ÉvÉÉxÉºÉ¦ÉÉ", "विधानसभा", "vidhaanasabhaa"),
            ("¨ÉiÉnùÉ®ô", "मतदार", "matadaar"),
            ("ÊSÉiÉ³äý", "चितळे", "chitale"),
            ("¶ÉÆEò®ú", "शंकर", "shankar"),
            ("{ÉÉ]õÒ±É +ÊxÉ±É ¶ÉÉ¨É®úÉ´É", "पाटील अनिल शामराव", "paatil anil shaamraav"),
            ("EòÉÆ¤É³äý", "कांबळे", "kaanbale"),
            # Edge case chars (newly mapped)
            ("VÉxÉÉnÇùxÉ", "जनार्दन", "janaardana"),        # Ç = repha
            ("ÊEòiÉÔ", "किर्ती", "kirtee"),                  # Ô = ्री
            ("MÉÉä{ÉÓxÉÉlÉ", "गोपीनाथ", "gopeenaath"),     # Ó = ी variant
            ("Eò´Éæ", "कवे", "kave"),                         # æ = े variant
            ("MÉÉÆMÉÖbæ÷", "गांगुडे", "gaangude"),           # æ = े + render hint
            ("xÉÉb÷EòhÉÔ", "नाडकर्णी", "naadakarnee"),     # Ô in surname
            ("{ÉÚÌhÉ¨ÉÉ", "पूर्णमा", "poornama"),           # Ì = repha variant
        ]
        dev_pass = 0
        en_pass = 0
        for item in tests:
            encoded, exp_dev, exp_en = item
            dev = virgo_to_devanagari(encoded)
            en = virgo_to_english(encoded)
            d_ok = "✓" if dev == exp_dev else "✗"
            e_ok = "✓" if exp_en in en.lower() else "~"
            if dev == exp_dev: dev_pass += 1
            if exp_en in en.lower(): en_pass += 1
            print(f"  {d_ok} {e_ok} {encoded:35s} → {dev:25s} | {en:25s}")
            if dev != exp_dev:
                print(f"       dev expected: {exp_dev}")
            if exp_en not in en.lower():
                print(f"       en  expected: ~{exp_en}")
        print(f"\nDevanagari: {dev_pass}/{len(tests)} exact")
        print(f"English:    {en_pass}/{len(tests)} match")

    elif len(sys.argv) > 1 and sys.argv[1] == "--convert":
        infile = sys.argv[2] if len(sys.argv) > 2 else "data/trombay_2002_all_voters.json"
        with open(infile) as f:
            voters = json.load(f)
        print(f"Converting {len(voters)} records...")
        for v in voters:
            v["voter_name_en"] = virgo_to_english(v["voter_name"])
            v["relative_name_en"] = virgo_to_english(v["relative_name"])
            v["voter_name_dev"] = virgo_to_devanagari(v["voter_name"])
            v["relative_name_dev"] = virgo_to_devanagari(v["relative_name"])
        outfile = infile.replace(".json", "_enriched.json")
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(voters, f, ensure_ascii=False, indent=2)
        print(f"Saved: {outfile}")
        for v in voters[:10]:
            print(f"  #{v['serial_number']:>4} {v['voter_name_en']:35s} | {v['voter_name_dev']}")

    else:
        text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("VirgoD3 text: ")
        print(f"Devanagari: {virgo_to_devanagari(text)}")
        print(f"English:    {virgo_to_english(text)}")
