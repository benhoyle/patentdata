from patentdata.models.lib.utils import (
    remove_non_words,
    remove_stopwords,
    stem
)

class TestUtils(object):
    """ Set of tests to test utility functions."""

    def test_remove_non_words(self):
        """ Test removing digit and punctuation. """
        test_string = """The widget 535 is attached, via a (big) thing 554
        to 125 things! But is this right? No 1 knows."""
        processed = remove_non_words(test_string)
        assert not set(
            ["5", "(", ")", "2", "!", "?", ","]
            ).issubset(processed)

    def test_remove_stopwords(self):
        """ Test removing stopwords. """
        test_tokens = ["widget", "bone", "what", "who", "are"]
        processed = remove_stopwords(test_tokens)
        assert not set(
            ["what", "who", "are"]
            ).issubset(processed)

    def test_stem(self):
        """ Test stemming. """
        test_tokens = ["jumping", "passing", "coupled", "widget"]
        processed = stem(test_tokens)
        assert set(
            ["jump", "pass", "coupl"]
            ).issubset(processed)
