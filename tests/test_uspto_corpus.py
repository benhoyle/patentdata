from patentdata.corpus.uspto_corpus import USPublications
import pytest


class TestGeneral(object):
    """ General set of tests."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        # Setup corpus to use a set of test files
        self.corpus = USPublications("/test_files")
        # Delete any existing DB

    def test_archive_list(self):
        """ Test generating an archive list. """
        pass

    def test_archive_names(self):
        """ Test getting first level archive names. """
        pass

    def test_read_archive_file(self):
        """ Test reading an archive file. """
        pass


