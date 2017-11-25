from patentdata.corpus import USGrants
import pytest

import os


class TestUSGrants(object):
    """ Tests for retrieving US grant information."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        filepath = os.path.dirname(os.path.realpath(__file__))
        self.testfilepath = os.path.join(filepath, 'test_files/Grant')
        self.dbpath = os.path.join(
            filepath,
            'test_files/Grant/fileindexes.db'
            )

    def test_init(self):
        """ Test initialising object. """
        try:
            os.remove(self.dbpath)
        except:
            pass
        corpus = USGrants(self.testfilepath)
        # Check DB creates
        assert os.path.isfile(self.dbpath)
        assert '2011/ipg110726_reduced.zip' in corpus.first_level_files

    def test_archive_list(self):
        """ Test getting archive names. """
        try:
            os.remove(self.dbpath)
        except:
            pass
        corpus = USGrants(self.testfilepath)
        corpus.index()
        records = corpus.c.execute("SELECT * FROM files").fetchall()
        assert records[0][0] == 'US07984558B2'

    def test_read_archive_file(self):
        """ Test reading an archive file. """
        corpus = USGrants(self.testfilepath)
        corpus.index()
        filename, offset = corpus.search_files('US07984558B2')
        filedata = corpus.read_by_offset(filename, offset)
        assert len(filedata) == 82118

    def test_get_store_class(self):
        """ Test retrieving and storing a classification. """
        try:
            os.remove(self.dbpath)
        except:
            pass
        corpus = USGrants(self.testfilepath)
        corpus.process_classifications()
        records = corpus.c.execute(
            "SELECT section, subgroup FROM files").fetchall()
        assert records[0][0] == "G"
        assert records[0][1] == "008"

    def test_iter_xml(self):
        """ Test iter_xml method. """
        corpus = USGrants(self.testfilepath)
        xmldoc = next(corpus.iter_xml())
        assert "measuring machine" in xmldoc.title()

    def test_iter_filter(self):
        """ Test generating iterators based on classifications. """
        corpus = USGrants(self.testfilepath)
        corpus.process_classifications()
        filegenerator = corpus.iter_filter_xml(["G"])
        xmldoc = next(filegenerator)
        assert "measuring machine" in xmldoc.title()

    def test_patent_corpus(self):
        """ Test generating a patent doc corpus. """
        corpus = USGrants(self.testfilepath)
        corpus.process_classifications()
        doc_generator = corpus.patentdoc_generator()
        doc = next(doc_generator)
        assert "measuring machine" in doc.title
