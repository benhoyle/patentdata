# -*- coding: utf-8 -*-

from patentdata.models.basemodels import BaseTextSet, BaseTextBlock
from patentdata.models.entity import Entity
from patentdata.models.lib.utils import (
    check_list, string2printint,
    highlight_multiple
)
from patentdata.models.lib.utils_entities import (
    extract_refs, filter_stopwords, expand_multiple
)
from collections import Counter
import nltk

extra_abbreviations = ['fig', 'figs', 'u.s.c', 'ser', 'no']
sent_tokenize = nltk.data.load('tokenizers/punkt/english.pickle')
sent_tokenize._params.abbrev_types.update(extra_abbreviations)


class Paragraph(BaseTextBlock):
    """ Object to model a paragraph of a patent description. """

    @property
    def sentences(self):
        """ If sentences have not been segmented, segment when accessed. """
        # Using NLTK is faster
        # return [s for s in self.doc.sents]
        try:
            return self._sentences
        except AttributeError:
            self._sentences = [
                Sentence(s) for s in sent_tokenize.tokenize(self.text)
                ]
            return self._sentences

    @property
    def sentence_count(self):
        return len(self.sentences)

    def print_character_list(self):
        """ Convert text into a list of integers representing the
        characters of the text mapped to printable characters (see
        models.lib.utils)."""
        return string2printint(self.text) + string2printint("\n\n")


class Sentence(BaseTextBlock):
    """ Object to model a sentence of a patent description. """
    pass


class Description(BaseTextSet):
    """ Object to model a patent description. """

    def __init__(self, initial_input):
        """ Initialise object.

        :param initial_input: Set of Paragraph objects, str or list
        of strings
        :type initial_input: list of Paragraph/str or str
        :return: None
        """
        input_list = check_list(initial_input)

        # Need split large string into paragraphs method here

        para_list = []
        for para in input_list:
            if not isinstance(para, Paragraph):
                para_object = Paragraph(para)
            else:
                para_object = para
            para_list.append(para_object)
        super(Description, self).__init__(para_list)

    def get_paragraph(self, number):
        """ Return paragraph having the passed number. """
        return super(Description, self).get_unit(number)

    @property
    def paragraph_count(self):
        """ Return count of paragraphs. """
        return len(self.units)

    @property
    def sentence_count(self):
        """ Return count of sentences. """
        return sum([p.sentence_count for p in self.units])

    @property
    def sentence_dist(self):
        """ Return distribution of sentences. """
        return Counter(
            [
                len(s.words)
                for p in self.units
                for s in p.sentences
            ]
        )

    @property
    def paragraphs(self):
        return self.units

    @property
    def sentences(self):
        """Return list of sentences."""
        return sum([p.sentences for p in self.units], list())

    @property
    def entities(self):
        """ List entities in description."""
        try:
            return self._entities
        except AttributeError:
            # Old routine below
            # self._entities = get_entity_ref_num_dict(self.doc)
            # New routine
            ref_numbers = [
                (rf_n, p.number, occ)
                for p in self.paragraphs
                for rf_n, occ in extract_refs(p.doc)
            ]
            # filter out "claim*" and "reference numeral*"
            ref_numbers = filter_stopwords(ref_numbers)
            ref_numbers = expand_multiple(ref_numbers)
            ref_num_set = set([ref_num.text for ref_num, _, _ in ref_numbers])
            entity_dict = dict()
            for ref_num in ref_num_set:
                entity_dict[ref_num] = Entity(ref_num, [])
            for ref_num_token, para_num, occ in ref_numbers:
                entity_dict[ref_num_token.text].add_occurrence(
                    ('paragraph', para_num, occ)
                    )
            self._entities = entity_dict
            return self._entities

    def entity_check(self):
        """ Returns any entities with multiple reference numerals. """
        highlight_multiple(self.entities)

    def pos(self):
        """ Return parts of speech for whole document."""
        return sum([p.pos for p in self.paragraphs], list())


class Figures:
    """ Object to model a set of patent figures. """
    pass
