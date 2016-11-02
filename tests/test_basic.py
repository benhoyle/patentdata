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

if __name__ == '__main__':
    unittest.main()