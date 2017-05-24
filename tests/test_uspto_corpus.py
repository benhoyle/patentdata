from patentdata.corpus import USPublications
import pytest

import os


class TestGeneral(object):
    """ General set of tests."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        filepath = os.path.dirname(os.path.realpath(__file__))
        self.testfilepath = os.path.join(filepath, 'test_files')
        self.dbpath = os.path.join(filepath, 'test_files/fileindexes.db')


    def test_init(self):
        """ Test initialising object. """
        os.remove(self.dbpath)
        corpus = USPublications(self.testfilepath)
        # Check DB creates
        assert os.path.isfile(self.dbpath)
        assert '2006/I20060427.zip' in corpus.first_level_files

    def test_archive_list(self):
        """ Test getting archive names. """
        os.remove(self.dbpath)
        corpus = USPublications(self.testfilepath)
        corpus.index()
        records = corpus.c.execute("SELECT * FROM files").fetchall()
        assert records[0][0] == "US20060085912A1"

    def test_read_archive_file(self):
        """ Test reading an archive file. """
        corpus = USPublications(self.testfilepath)
        corpus.index()
        filename, name = corpus.search_files("US20060085912A1")
        filedata = corpus.read_archive_file(filename, name)
        assert len(filedata) == 50805

    def test_get_store_class(self):
        """ Test retrieving and storing a classification. """
        os.remove(self.dbpath)
        corpus = USPublications(self.testfilepath)
        corpus.process_classifications()
        records = corpus.c.execute(
            "SELECT section, subgroup FROM files").fetchall()
        assert records[0][0] == "A"
        assert records[0][1] == "08"

    def test_iter_xml(self):
        """ Test iter_xml method. """
        corpus = USPublications(self.testfilepath)
        xmldoc = next(corpus.iter_xml())
        assert "support" in xmldoc.title()

    def test_iter_filter(self):
        """ Test generating iterators based on classifications. """
        corpus = USPublications(self.testfilepath)
        corpus.process_classifications()
        filegenerator = corpus.iter_filter_xml(["A", None, "K"])
        xmldoc = next(filegenerator)
        assert "support" in xmldoc.title()


    #def test_class_match(self):
        #""" Test matching of classifications. """
        #class1 = corpus.m.Classification("G", "06", "F", "10", "22")
        #class2 = corpus.m.Classification("G", "06")
        #class3 = corpus.m.Classification("H", "06")
        #class4 = corpus.m.Classification("G", "07", "F", "10", "22")
        #assert class1.match(class2) == True
        #assert class1.match([class3,class4]) == False

    #def test_claim_text(self):
        #""" Test retrieving claim text. """
        #claim_text = self.xmldoc.claim_text()
        #assert len(claim_text) == 6474
        #assert "mounting apparatus" in claim_text

    #def test_description(self):
        #""" Test retrieving description. """
        #assert "mounting apparatus" in self.xmldoc.description_text()


    #def test_iter(self):
        #""" Test iter object. """
        #xml_files = self.corpus.iter_xml()
        #file1 = next(xml_files)
        #file2 = next(xml_files)
        #assert len(file1.title()) > 0
        #assert len(file2.title()) > 0
        #assert file1 != file2
