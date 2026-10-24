"""Title normalization used to build duplicate-detection keys.

Rules, applied in order:
  1. Unicode NFKD, drop combining marks (accents), casefold.
  2. Replace '&' with 'and'.
  3. Remove punctuation (anything that is not a letter, digit or space); collapse whitespace.
  4. Drop a leading article ('the', 'a', 'an') when more words follow it.
Parenthesised qualifiers such as '(US)' or '(2019)' are NOT removed here: they carry identity.
Their punctuation is stripped by rule 3, so '(US)' becomes 'us'.
"""
import re
import unicodedata

_ARTICLES = ("the", "a", "an")


def normalize_title(title):
    text = unicodedata.normalize("NFKD", title)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    text = text.replace("&", " and ")
    text = re.sub(r"[^\w\s]|_", " ", text)
    words = text.split()
    if len(words) > 1 and words[0] in _ARTICLES:
        words = words[1:]
    return " ".join(words)
