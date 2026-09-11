"""Text normalization"""
import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_title(text):
    """
    Canonical form for title text string.
    NFC composed, strips leading/trailing whitespace, collapses whitespace runs to a single space.

    Does NOT apply NFKC: characters such as half-width kana and full-width Latin are distinct.
    """
    if text is None:
        return None
    text = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", text).strip()

