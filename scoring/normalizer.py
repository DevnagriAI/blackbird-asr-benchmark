"""Text normalisation applied to both reference and hypothesis before scoring.

This follows the AI4Bharat Vistaar evaluation protocol exactly
(github.com/AI4Bharat/vistaar, evaluation.py), so Blackbird numbers sit
directly beside the published Vistaar results for Google STT, Azure STT,
NVIDIA and IndicWhisper on the same test files:

  1. remove ASCII punctuation plus the danda (।), double danda (॥), Urdu full
     stop (۔), apostrophe and hyphen
  2. apply the indic-nlp-library IndicNormalizer for the language (skipped for
     Urdu, as in Vistaar)
  3. collapse runs of spaces

One addition, which changes nothing for Indic-script text:
  4. lowercase Latin letters, so "Booking" and "booking" match in English and
     code-mixed speech

Deliberately NOT done:
  - numbers are never rewritten (no "10" <-> "दस"), so a wrong number is
    always an error
  - filler words are not removed
  - no transliteration between scripts
"""
from __future__ import annotations

import re
import string
import unicodedata
from functools import lru_cache

from indicnlp.normalize.indic_normalize import IndicNormalizerFactory

_STRIP = str.maketrans("", "", string.punctuation + "।۔'-॥")
_FACTORY = IndicNormalizerFactory()

# Which indic-nlp normaliser each language uses. Languages indic-nlp has no
# entry for borrow the normaliser of the script they are written in.
# Arabic-script (ur, ks, sd), Ol Chiki (sat) and Latin (en) text get none,
# matching Vistaar's treatment of Urdu.
_NORMALIZER_CODE = {
    "as": "as", "bn": "bn", "gu": "gu", "hi": "hi", "kn": "kn", "ml": "ml",
    "mr": "mr", "ne": "ne", "or": "or", "pa": "pa", "sa": "sa", "ta": "ta",
    "te": "te",
    "bho": "hi", "brx": "hi", "doi": "hi", "hne": "hi", "kok": "hi",
    "mai": "hi", "bhb": "hi", "bgc": "hi",
    "mni": "bn",
}


@lru_cache(maxsize=None)
def _normalizer(lang: str):
    code = _NORMALIZER_CODE.get(lang)
    return _FACTORY.get_normalizer(code) if code else None


def normalize(text: str, lang: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = text.translate(_STRIP)
    norm = _normalizer(lang)
    if norm is not None:
        text = norm.normalize(text)
    text = text.lower()          # affects Latin script only
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------------------------------------------------------------------------
# Spelling-tolerant variant (SECONDARY metric, always reported next to the
# strict number above, never instead of it).
#
# A single reference spelling penalises recognisers for writing a word in a
# different but valid way (the problem the Voice of India benchmark addresses
# with multi-reference lattices). These rules fold ONLY spelling variants that
# do not change the word. Applied identically to reference and hypothesis:
#
#   T1  nukta removed            ज़ -> ज, फ़ -> फ (all Indic scripts)
#   T2  chandrabindu -> anusvara ँ -> ं (Devanagari)
#   T3  nasal consonant + virama before a consonant of the same class is
#       written as anusvara      नम्बर -> नंबर, कम्पनी -> कंपनी (Devanagari)
#   T4  three Hindi word pairs where the reference uses the formal spelling of
#       what is pronounced colloquially, or both spellings are standard:
#       वह = वो, यह = ये, छः = छह
#   T5  Malayalam chillu letters canonicalised: the atomic chillu (ൻ, ർ, ൽ,
#       ൾ, ൺ, ൿ) and consonant + virama are two encodings of the same visible
#       letter (എൻ്റെ = എന്റെ); zero-width joiners are dropped
#
# Grammar is NOT forgiven: की/कि, है/हैं, के/की etc. remain errors.
# ---------------------------------------------------------------------------
_NUKTAS = "़়਼઼଼಼഼"
_NUKTA_STRIP = str.maketrans("", "", _NUKTAS)
_DEV_VIRAMA = "्"
# nasal consonant -> the consonant classes (vargas) it can precede
_NASAL_CLASS = {
    "ङ": "कखगघ", "ञ": "चछजझ", "ण": "टठडढ", "न": "तथदध", "म": "पफबभ",
}
_NASAL_RE = re.compile(
    "|".join(f"{n}{_DEV_VIRAMA}(?=[{cls}])" for n, cls in _NASAL_CLASS.items())
)
_HI_WORD_EQUIV = {"वो": "वह", "ये": "यह", "छः": "छह"}
_ML_CHILLU = str.maketrans({"ൺ": "ണ്", "ൻ": "ന്", "ർ": "ര്", "ൽ": "ല്", "ൾ": "ള്",
                            "ൿ": "ക്", "‍": None, "‌": None})


def normalize_tolerant(text: str, lang: str) -> str:
    text = normalize(text, lang)
    text = text.translate(_NUKTA_STRIP)                     # T1
    text = text.replace("ँ", "ं")                 # T2
    text = _NASAL_RE.sub("ं", text)                    # T3
    if lang == "hi":                                        # T4
        text = " ".join(_HI_WORD_EQUIV.get(w, w) for w in text.split())
    if lang == "ml":                                        # T5
        text = text.translate(_ML_CHILLU).replace("്്", "്")
    return text
