from patentdata.corpus import EPOOPS
import pytest


class TestGeneral(object):
    """ General set of tests."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        self.epo_client = EPOOPS()

    def test_get_claims(self):
        """ Test retrieving claims. """
        claims = self.epo_client.get_claims("EP2979166")
        assert "child nodes" in claims

        claims = self.epo_client.get_claims("rubbishhere")
        assert claims is None

        claims = self.epo_client.get_claims(
            "13880507.2",
            numbertype='application',
            countrycode='EP'
        )
        assert "child nodes" in claims

    def test_get_description(self):
        """ Test retrieving description. """
        description = self.epo_client.get_description("EP2979166")
        assert "request module 226" in description

        description = self.epo_client.get_description("rubbishhere")
        assert description is None

        description = self.epo_client.get_description(
            "13880507.2",
            numbertype='application',
            countrycode='EP'
        )
        assert "request module 226" in description

    def test_convert_number(self):
        """ Test converting an application number."""
        epo_no = self.epo_client.convert_number("13880507.2", "EP")
        assert epo_no == "EP20130880507"

    def test_get_publication_no(self):
        """ Test getting publication numbers. """
        pub_no = self.epo_client.get_publication_no("13880507.2", "EP")
        assert "EP2979166" in pub_no.number

    def test_get_citations(self):
        """ Test getting citations. """
        citations = self.epo_client.get_citations("EP1000000")
        assert len(citations) == 3
        assert citations[1]['number'] == 'NL9400663'

        citations = self.epo_client.get_citations("rubbishhere")
        assert len(citations) == 0

        citations = self.epo_client.get_citations(
            "13880507.2",
            numbertype='application',
            countrycode='EP'
        )
        assert len(citations) == 1
        assert citations[0]['category'] == 'I'


