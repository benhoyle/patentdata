import pytest
from patentdata.models import (
    Description, Figures, Claimset, Claim, Classification
)
from patentdata.models.patentdoc import PatentDoc
from patentdata.corpus import USPublications
import os

class TestPatentCorpus(object):
    """ Testing PatentCorpus functions. """

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        filepath = os.path.dirname(os.path.realpath(__file__))
        self.pubstestfilepath = os.path.join(
            filepath, 'test_files/Publication'
            )
        self.pubsdbpath = os.path.join(
            filepath,
            'test_files/Publication/fileindexes.db'
            )
        self.granttestfilepath = os.path.join(filepath, 'test_files/Grant')
        self.grantdbpath = os.path.join(
            filepath,
            'test_files/Grant/fileindexes.db'
            )
