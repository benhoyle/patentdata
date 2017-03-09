from patentdata.corpus.epo_corpus import EPOOPS

class TestGeneral(object):
    """ General set of tests."""

    def test_get_claims(self):
        """ Test retrieving claims. """
        epo_client = EPOOPS()
        claims = epo_client.get_claims("EP2979166")

        assert "child nodes" in claims

    def test_get_description(self):
        """ Test retrieving description. """
        epo_client = EPOOPS()
        description = epo_client.get_description("EP2979166")

        assert "request module 226" in description
