
# tests for graph functions
from patentdata.models.graph import Graph
from patentdata.models.lib.utils import nlp

import pytest


class TestGraph(object):
    """ Tests for retrieving US grant information."""

    @pytest.fixture(autouse=True)
    def set_common_fixtures(self):
        self.text = nlp(
            "A further disadvantage of current "
            "portable scanning devices is hidden storage of a stylus for "
            "interacting with a user interface of the scanning device. "
            "Typically the stylus of the device is attached (e.g. via a cord) "
            "and fastened to an external surface of the "
            "device housing or handle, when not in use by the user of the "
            "device. Unfortunately, these external storage techniques of "
            "stylus can result in damage to the housing of the device, "
            "misplacement (e.g. loosing) of the stylus by the user, and/or "
            "positioning of the stylus in an awkward location on the "
            "device/handle that may interfere with the user when operating "
            "the scanning device without the current need for the stylus."
        )
        self.sent_one = list(self.text.sents)[0]

    def test_build(self):
        """ Test building a graph."""
        g = Graph(self.sent_one.root)
        node_labels = [n.label for n in g.nodes]
        assert "A_DT_det_0" in node_labels
        assert "._._punct_24" in node_labels
        assert g.edges[-1][1].label == 'scanning_NN_amod_22'

    def test_flatten(self):
        """ Test flattening a graph."""
        g = Graph(self.sent_one.root)
        g.flatten_graph()
        assert (
            'the_DT_det_21 scanning_NN_amod_22 device_NN_pobj_23'
            == g.nodes[-1].label
        )
