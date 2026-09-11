import pytest
import unicodedata
from imaa_tracker.core.utils.text import normalize_title


class TestNormalizeTitle:

    def test_none_passes_through(self):
        assert normalize_title(None) is None

    @pytest.mark.parametrize("composed", [
        "ドラえもん",        # Japanese dakuten
        "한국어",              # Hangul jamo
        "Café Amèrica",     # Latin diacritics
        "Tiếng Việt",       # Vietnamese stacked marks
        "nǐ hǎo",           # pinyin tone marks
    ])
    def test_nfd_input_normalizes_to_nfc(self, composed):
        decomposed = unicodedata.normalize("NFD", composed)
        assert decomposed != composed
        assert normalize_title(decomposed) == composed

    def test_whitespace_collapse_and_strip(self):
        assert normalize_title("  Re:Zero    Season   2 ") == "Re:Zero Season 2"

    def test_fullwidth_space_collapse(self):
        assert normalize_title("君の\u3000名は") == "君の 名は"

    def test_halfwidth_kana_is_not_folded(self):
        """NFC/NFKC boundary"""
        assert normalize_title("ﾅﾅ") != "ナナ"

    def test_hangul_jamo_composed(self):
        assert normalize_title("\u1112\u1161\u11ab") == "한"

    def test_latin_diacritic_composed(self):
        assert normalize_title("Cafe\u0301") == "Café"
