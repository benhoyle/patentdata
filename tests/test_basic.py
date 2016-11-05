# -*- coding: utf-8 -*-

from .context import corpus
# Import other stuff here

import unittest

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def setUp(self):
        """Pre-test activities."""
        self.load_corpus = corpus.MyCorpus.load("tests/test2010.p")
        self.xmldoc = self.load_corpus.get_doc(2377)
    
    def test_classifications(self):
        """ Test retrieving classifications. """
        classifications = self.xmldoc.classifications()
        assert classifications[0].section == "G"
        assert classifications[0].subgroup == "16"
        
    def test_class_match(self):
        """ Test matching of classifications. """
        class1 = corpus.Classification("G", "06", "F", "10", "22")
        class2 = corpus.Classification("G", "06")
        class3 = corpus.Classification("H", "06")
        class4 = corpus.Classification("G", "07", "F", "10", "22")
        assert class1.match(class2) == True
        assert class1.match([class3,class4]) == False
        
    def test_claim_text(self):
        """ Test retrieving claim text. """
        claim_text = self.xmldoc.claim_text()
        assert len(claim_text) == 6474
        assert "mounting apparatus" in claim_text
        
    def test_title(self):
        """ Test retrieving title. """
        assert "MOUNTING APPARATUS" in self.xmldoc.title()
        
    def test_description(self):
        """ Test retrieving description. """
        assert "mounting apparatus" in self.xmldoc.description_text()
        
    # Test Corpus Loading Functions
    def test_get_archive_names(self):
        """ Test getting archive filenames. """
        assert len(self.load_corpus.get_archive_names(self.load_corpus.first_level_files[0])) > 0
        
    def test_read_archive_file(self):
        """ Test reading data from archive file. """
        filename = self.load_corpus.first_level_files[1]
        name = self.load_corpus.get_archive_names(filename)[6]
        
        data = self.load_corpus.read_archive_file(filename, name)
        assert len(data) > 0 

    def test_iter(self):
        """ Test iter object. """
        xml_files = self.load_corpus.iter_xml()
        file1 = next(xml_files)
        file2 = next(xml_files)
        assert len(file1.title()) > 0
        assert len(file2.title()) > 0
        assert file1 != file2

if __name__ == '__main__':
    unittest.main()