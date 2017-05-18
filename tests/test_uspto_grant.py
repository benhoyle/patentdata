from patentdata.corpus import USGrants
import pytest

import os


class TestUSGrants(object):
    """ Tests for retrieving US grant information."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        filepath = os.path.dirname(os.path.realpath(__file__))
        self.testfilepath = os.path.join(filepath, 'test_files')
        # self.dbpath = os.path.join(filepath, 'test_files/fileindexes.db')



