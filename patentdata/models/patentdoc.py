# -*- coding: utf-8 -*-
from nltk import word_tokenize
import string
import json

class PatentDoc:
    """ Object to model a patent document. """
    def __init__(
            self,
            claimset,
            description=None,
            figures=None,
            title=None,
            classifications=None,
            number=None
    ):
        """ description, claimset and figures are objects as below. """
        self.description = description
        self.claimset = claimset
        self.figures = figures
        self.title = title
        self.classifications = classifications
        self.number = number

    def __repr__(self):
        return (
            "<Patent Document object for {0}, "
            "title: {1} - containing: "
            "description with {2} paragraphs and "
            "claimset with {3} claims; "
            "classifications: {4}"
            ).format(
                self.number,
                self.title,
                self.description.paragraph_count,
                self.claimset.claim_count,
                self.classifications
            )

    @property
    def text(self):
        """  Get text of patent document as string. """
        if self.description:
            desc_text = self.description.text
        else:
            desc_text = ""
        return "\n\n".join([desc_text, self.claimset.text])

    @property
    def unfiltered_counter(self):
        """ Return token counts across claims and description. """
        return (
            self.description.unfiltered_counter +
            self.claimset.unfiltered_counter
        )

    @property
    def filtered_counter(self):
        """ Return filtered token counts across claims and description. """
        return (
            self.description.filtered_counter +
            self.claimset.filtered_counter
        )

    @property
    def character_counter(self):
        """ Return token counts across claims and description. """
        return (
            self.description.character_counter +
            self.claimset.character_counter
        )

    @property
    def vocabulary(self):
        """ Return number of unique tokens. """
        return len(self.unfiltered_counter)

    @property
    def unique_characters(self):
        """ Return number of unique characters."""
        return len(self.character_counter)

    def reading_time(self, reading_rate=100):
        """ Return estimate for time to read. """
        # Words per minute = between 100 and 200
        return len(word_tokenize(self.text)) / reading_rate

    def bag_of_words(
        self, clean_non_words=True, clean_stopwords=True, stem_words=True
    ):
        """ Return tokens from description and claims. """
        joined_bow = self.description.bag_of_words(
            clean_non_words, clean_stopwords, stem_words
            ) + self.claimset.bag_of_words(
            clean_non_words, clean_stopwords, stem_words
            )
        remove_duplicates = list(set(joined_bow))
        return remove_duplicates

    @property
    def saveable(self):
        """ Generate a saveable representation of patentdoc to disk."""
        # First we can generate a dictionary version of the pdoc
        # Then we can use json to convert dict to a json string
        pdoc_dict = dict()
        pdoc_dict['title'] = self.title
        pdoc_dict['number'] = self.number
        pdoc_dict['classifications'] = [
            c.as_dict() for c in self.classifications
            ]
        pdoc_dict['description'] = self.description.paragraphs
        pdoc_dict['claims'] = [
            c.as_dict() for c in self.claimset.claims
        ]
        return json.dumps(pdoc_dict)

    @classmethod
    def load_from_string(cls, pdoc_string):
        """ Load patent doc from a JSON string. """
        pdoc_dict = json.loads(pdoc_string)
        return cls(*pdoc_dict)

