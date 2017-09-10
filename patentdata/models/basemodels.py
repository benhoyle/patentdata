# -*- coding: utf-8 -*-

#from nltk import word_tokenize, pos_tag
from patentdata.models.lib.utils import nlp
# Used for frequency counts
from collections import Counter

from patentdata.models.lib.utils import (
    check_list, remove_non_words, stem, remove_stopwords,
    replace_patent_numbers, punctuation_split, capitals_process,
    stem_split, ENG_STOPWORDS, string2printint
    )

from patentdata.models.lib.utils_entities import (
    extract_entities
)

from patentdata.models.chardict import CharDict
from patentdata.models.entity import Entity

# Initialise character dictionary for mappings
chardict = CharDict()


class Word:
    """ Abstract class to model a word. """
    def __init__(self, text):
        self.text = text

    def as_char_list(self):
        """ Return word as a list of character indexes.

            Word start and end characters are added to start and end.

            returns a list of integer indexes."""
        # Convert main word characters to list of integers
        text2intlist = chardict.text2int(self.text)
        # Add control characters to start and end
        text2intlist.insert(0, chardict.startwordint)
        text2intlist.append(chardict.endwordint)
        return text2intlist


class BaseTextBlock:
    """ Abstract class for a block of text. """

    def __init__(self, text, number=None):
        self.text = text
        self.number = number
        self.doc = nlp(text)

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
            self._words = [w for word in self.doc]
            return self._words

    @property
    def filtered_tokens(self):
        """ Clean and tokenise text and store as variable. """
        try:
            return self._filtered_tokens
        except AttributeError:
            filtered_text = replace_patent_numbers(self.text)
            words = word_tokenize(filtered_text)
            filtered_words = punctuation_split(words)
            caps_processed = capitals_process(filtered_words)
            self._filtered_tokens = stem_split(caps_processed)
            return self._filtered_tokens

    @property
    def word_count(self):
        return len(self.words)

    @property
    def unfiltered_counter(self):
        """ Return a counter of unfiltered tokens in text block. """
        return Counter(self.words)

    @property
    def filtered_counter(self):
        """ Return a counter of filtered tokens in text block. """
        return Counter(self.filtered_tokens)

    @property
    def characters(self):
        """ Return characters in text block as list. """
        return [c for c in self.text]

    @property
    def character_counter(self):
        """ Return a counter of unfiltered characters in text block. """
        return Counter(self.characters)

    @property
    def pos(self):
        """ Return parts of speech. """
        try:
            return self._pos
        except AttributeError:

            self._pos = [(word.text, word.pos_) for word in self.doc]
            return self._pos

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

    def appears_in(self, term):
        """ Determine if term appears in text. """
        return term.lower() in self.text.lower()

    def set_word_order(self):
        """ Generate a list of tuples of word, order in claim. """
        self.word_order = list(enumerate(self.words))
        return self.word_order

    def print_character_list(self):
        """ Convert text into a list of integers representing the
        characters of the text mapped to printable characters (see
        models.lib.utils)."""
        return string2printint(self.text)

    def filtered_token2int(self, vocab_dict):
        """ Map filtered tokens to integers based on mapping in
        vocab_dict. Return a list of integers."""
        tokens = self.filtered_tokens
        return [
            vocab_dict[token] if token in vocab_dict.keys()
            else vocab_dict["_UNK_"]
            for token in tokens
            ]

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

    @property
    def entities(self):
        """ Return entities."""
        try:
            return self._entities
        except AttributeError:
            ed = extract_entities(self.doc)
            self._entities = [
                Entity(
                    string_name=k,
                    occurrences=v
                )
                for k, v in ed.items()
            ]
            return self._entities

    def as_dict(self):
        """ Return object as dictionary. """
        return {'text': self.text, 'number': self.number}


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
        self.doc = nlp(self.text)
        self.index = 0

    def __iter__(self):
        """ Initialise iterator that returns units."""
        self.index = 0
        return self

    def __next__(self):
        """ Return units one by one. """
        try:
            result = self.units[self.index]
        except IndexError:
            raise StopIteration
        self.index += 1
        return result

    @property
    def text(self):
        """ Return unit set as text string. """
        return "\n".join([u.text for u in self.units])

    @property
    def unfiltered_counter(self):
        """ Return count of tokens in text set. """
        return sum([u.unfiltered_counter for u in self.units], Counter())

    @property
    def filtered_counter(self):
        """ Return count of filtered tokens in text set. """
        return sum([u.filtered_counter for u in self.units], Counter())

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

    def print_character_list(self):
        """ Return list of all printable characters converted to
        integers. """
        return sum([u.print_character_list() for u in self.units], list())
