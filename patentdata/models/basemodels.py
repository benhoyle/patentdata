# -*- coding: utf-8 -*-

from nltk import word_tokenize, pos_tag
# Used for frequency counts
from collections import Counter
import string
import re

from patentdata.models.lib.utils import (
    check_list, remove_non_words, stem, remove_stopwords
    )


class BaseTextBlock:
    """ Abstract class for a block of text. """

    def __init__(self, text, number=None):
        self.text = text
        self.number = number

    def __repr__(self):
        if self.number:
            return "{0} {1}".format(self.number, self.text)
        else:
            return self.text

    @property
    def words(self):
        """ Tokenise text and store as variable. """
        try:
            return self._words
        except AttributeError:
            self._words = word_tokenize(self.text)
            return self._words

    @property
    def word_count(self):
        return len(self.words)

    @property
    def unfiltered_counter(self):
        """ Return a counter of unfiltered tokens in text block. """
        return Counter(self.words)

    @property
    def characters(self):
        """ Return characters in text block as list. """
        return [c for c in self.text]

    @property
    def character_counter(self):
        """ Return a counter of unfiltered characters in text block. """
        return Counter(self.characters)

    def get_word_freq(self, stopwords=True, normalize=True):
        """ Calculate term frequencies for words in claim. """
        # Take out punctuation
        if stopwords:
            # If stopwords = true then remove stopwords
            counter = Counter(
                [
                    w.lower() for w in self.words
                    if w.isalpha() and w.lower() not in ENG_STOPWORDS
                ]
            )
        else:
            counter = Counter([w.lower() for w in self.words if w.isalpha()])
        if normalize:
            sum_freqs = sum(counter.values())
            # Normalise word_freqs
            for key in counter:
                counter[key] /= sum_freqs
        return counter

    def set_pos(self):
        """ Get the parts of speech."""
        pos_list = pos_tag(self.words)
        # Hard set 'comprising' as VBG
        pos_list = [
            (word, pos) if word != 'comprising'
            else ('comprising', 'VBG') for (word, pos) in pos_list
            ]
        self.pos = pos_list
        return self.pos

    def appears_in(self, term):
        """ Determine if term appears in claim. """
        return term.lower() in [w.lower() for w in self.words]

    def set_word_order(self):
        """ Generate a list of tuples of word, order in claim. """
        self.word_order = list(enumerate(self.words))
        return self.word_order


class BaseTextSet:
    """ Abstract object to model a collection of text blocks. """
    def __init__(self, initial_input):
        """
        Initialise a base text set

        :param initial_input: Initial input as long string or list
        of strings
        :type initial_input: str or list
        :return: None
        """
        units = check_list(initial_input)
        self.units = units
        self.count = len(self.units)

    @property
    def text(self):
        """ Return unit set as text string. """
        return "\n".join([u.text for u in self.units])

    @property
    def unfiltered_counter(self):
        """ Return count of tokens in text set. """
        return sum([u.unfiltered_counter for u in self.units], Counter())

    @property
    def character_counter(self):
        """ Return count of characters in text set. """
        return sum([u.character_counter for u in self.units], Counter())

    def get_unit(self, number):
        """ Return unit having the passed number. """
        return self.units[number - 1]

    def term_counts(self, stopwords=True):
        """ Calculate word frequencies in units.
        Stopwords flag sets removal of stopwords."""
        return sum([u.get_word_freq(stopwords) for u in self.units], Counter())

    def appears_in(self, term):
        """ Returns unit string 'term' appears in. """
        return [u for u in self.units if u.appears_in(term)]

    def bag_of_words(
        self, clean_non_words=True, clean_stopwords=True, stem_words=True
        ):
        """ Get an array of all the words in the text set. """
        lowers = self.text.lower()

        tokens = word_tokenize(lowers)

        if clean_non_words:
            tokens = remove_non_words(tokens)

        if clean_stopwords:
            tokens = remove_stopwords(tokens)

        if stem_words:
            tokens = stem(tokens)

        return tokens
