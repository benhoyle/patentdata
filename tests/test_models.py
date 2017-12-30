import pytest
from patentdata.models import (
    Description, Figures, Claimset, Claim, Classification
)
from patentdata.models.patentdoc import PatentDoc
from patentdata.corpus import USPublications
import os


class TestGeneral(object):
    """ General set of tests."""

    def test_claims(self):
        """ Test Claim objects. """
        claim = Claim("Claim 1 has an x.", 1)
        assert claim.number == 1
        assert "has an x" in claim.text

    def test_description(self):
        """ Test Description objects. """
        desc = Description(["one", "two", "three"])
        assert "two" in desc.get_paragraph(2).text

    def test_claimset(self):
        """ Test Claimset objects. """
        claims = [
            "{0}. Claim {0} has an x.".format(num)
            for num in range(1, 11)
            ]
        claimset = Claimset(claims)

        assert claimset.claim_count == 10
        assert "Claim 5 has an x" in claimset.get_claim(5).text
        assert isinstance(claimset.claims[2], Claim)

    def test_init(self):
        """ Test all objects initialise. """
        claims = [
            Claim("Claim {0} has an x.".format(num), num)
            for num in range(1, 10)
            ]
        claimset = Claimset(claims)
        desc = Description(["one", "two", "three"])
        fig = Figures()
        classification = Classification("A")

        pd1 = PatentDoc(claimset)
        pd2 = PatentDoc(
            claimset,
            desc,
            fig,
            "Title",
            classification,
            "20010101010"
            )

        assert "has an x" in pd1.text
        assert "has an x" in pd2.text
        assert "three" in pd2.text
        assert pd1.reading_time() > 0 and \
            pd1.reading_time() < pd2.reading_time()


class TestDescription(object):
    """ Test description functions. """

    @pytest.fixture()
    def description(self):
        return [
            ("Lorem ipsum dolor sit amet, consectetur "
            "adipiscing elit. Integer nec odio. \n"),
            ("Praesent libero 100. Sed cursus 102 ante dapibus diam. "
            "Sed nisi. \n"),
            ("Sed, dignissim lacinia, <nunc>. Curabitur tortor 2."
            "Pellentesque nibh. \n"),
            "Quisque volutpat 554 condimentum velit."
        ]

    def test_init(self, description):
        """ Test object initialisation. """
        desc = Description(description)
        assert "<nunc>" in desc.get_paragraph(3).text

    def test_paragraphs(self):
        pass

    def test_bag_of_words(self, description):
        """ Test returning a bag of words. """
        desc = Description(description)
        bow = desc.bag_of_words()
        assert "<nunc>" not in bow
        assert "nunc" in bow
        assert "554" not in bow
        assert "." not in bow
        assert "sed" in bow


class TestOnData(object):
    """ Testing functions on Patent Example."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        filepath = os.path.dirname(os.path.realpath(__file__))
        testfilepath = os.path.join(filepath, 'test_files')
        corpus = USPublications(testfilepath)
        self.patent_doc = next(corpus.iter_xml()).to_patentdoc()

    def test_features(self):
        pd = self.patent_doc
        assert "39 claims" in pd.__repr__()
        assert pd.description.get_paragraph(26).sentence_count == 5
        assert pd.description.sentence_count == 137
        assert (
            "shaft" in
            pd.description.get_paragraph(26).sentences[2].words
            )

    def test_counters(self):
        """ Test token and character counting functions. """
        pd = self.patent_doc
        assert pd.vocabulary == 730
        assert pd.unique_characters == 65

