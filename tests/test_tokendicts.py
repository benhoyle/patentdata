from patentdata.models.chardict import BaseDict, CharDict, WordDict


class TestGeneral(object):
    """ General set of tests."""

    def test_base(self):
        """ Test base class object."""
        b = BaseDict()
        assert b.int2token(0) == '_PAD_'
        assert b.token2int(b.int2token(0)) == 0
        assert b.int2token(b.startwordint) == "_SOW_"
        assert b.int2token(b.startwordint) == "_EOW_"

    def test_char(self):
        """ Test chardict object."""
        c = CharDict()
        assert len(c.vocab) == 84
        assert c.clean_char('×') == '*'
        assert c.clean_char('*') == '*'
        test_list = [9, 31, 16, 30, 31, 80, 43, 57, 60]
        assert c.text2int('Test 5×—') == test_list
        assert c.intlist2text(test_list) == 'Test 5*-'

    def test_word(self):
        """ Test worddict object."""
        w = WordDict()


