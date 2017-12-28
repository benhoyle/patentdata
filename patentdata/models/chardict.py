# -*- coding: utf-8 -*-
import string
import unicodedata


def decompose_character(char):
    """ Attempt to return decomposed version of a character
    as list of normalised."""
    try:
        return [
            chr(int(u, 16))
            for u in unicodedata.decomposition(char).split(" ")
            if u and '<' not in u
            ]
    except:
        return None


CONTROL_CHARACTERS = [
    "_PAD_",  # Make sure <PADDING> control symbol is set = 0
    "_SODOC_", "_EODOC_",  # Document start / end
    "_SOP_", "_EOP_",  # Paragraph start / end
    "_SOS_", "_SOS_",  # Sentence start / end
    "_SOW_", "_EOW_",  # Word start / end
    "_CAPITAL_", "_ALL_CAPITAL_",  # Capital / Uppercase markers
    "_OOD_"  # Out of dict
]

CHARACTER_VOCAB = list(
            string.ascii_lowercase +
            string.digits +
            string.punctuation +
            string.whitespace[:-2]
            )


class BaseDict:
    """Abstract class for character and word dictionaries."""

    def __init__(self):
        """ Initialise and add control tokens. """
        self.token_set = [] + CONTROL_CHARACTERS

    def build_dicts(self):
        """ Build mapping dictionaries."""
        # Populate rest of dictionary from character set
        self.reverse_dict = {
            i: c for i, c in enumerate(self.token_set)
            }

        self.vocab_size = len(self.reverse_dict)

        self.forward_dict = {
            v: k for k, v in self.reverse_dict.items()
            }

    def int2token(self, integer):
        """ Convert an integer into a token using the object. """
        try:
            return self.reverse_dict[integer]
        except AttributeError:
            self.build_dicts()
            return self.reverse_dict[integer]

    def token2int(self, token):
        """ Convert a token into an integer using the object. """
        try:
            if token in self.forward_dict.keys():
                return self.forward_dict[token]
            else:
                # Return OOD token
                return self.forward_dict["_OOD_"]
        except AttributeError:
            self.build_dicts()
            return self.token2int(token)

    @property
    def startwordint(self):
        """ Return integer for start of word character. """
        return self.forward_dict["_SOW_"]

    @property
    def endwordint(self):
        """ Return integer for start of word character. """
        return self.forward_dict["_EOW_"]


class CharDict(BaseDict):
    """ Class to model mapping between characters and integers. """

    def __init__(self):
        """ Initialise and reverse control characters. """
        # Set character set we will use
        super(CharDict, self).__init__()
        self.token_set += CHARACTER_VOCAB
        self.build_dicts()

        # Create character cleaning dictionary
        self.char_cleaner = dict()
        self.char_cleaner['”'] = '"'
        self.char_cleaner['“'] = '"'
        self.char_cleaner['\u2003'] = ' '
        self.char_cleaner['\ue89e'] = ' '
        self.char_cleaner['\u2062'] = ' '
        self.char_cleaner['\ue8a0'] = ' '
        self.char_cleaner['−'] = '-'
        self.char_cleaner['—'] = '-'
        self.char_cleaner['′'] = "'"
        self.char_cleaner['‘'] = "'"
        self.char_cleaner['’'] = "'"
        self.char_cleaner['×'] = '*'
        self.char_cleaner['⁄'] = '/'

    def clean_char(self, character):
        if character in self.char_cleaner.keys():
            return self.char_cleaner[character]
        else:
            return character

    def text2int(self, text):
        """ Convert a block of text into an integer. """

        integer_list = list()
        for character in text:
            # Perform mapping for commonly occuring characters
            if character in self.char_cleaner.keys():
                character = self.char_cleaner[character]

            # If character is in mapping dictionary add int to list
            if character in self.forward_dict.keys():
                integer_list.append(self.forward_dict[character])
            elif character in string.ascii_uppercase:
                # If uppercase
                integer_list.append(self.forward_dict["_CAPITAL_"])
                integer_list.append(self.forward_dict[character.lower()])
            else:
                replacement_chars = decompose_character(character)
                if replacement_chars:
                    integer_list += self.text2int("".join(replacement_chars))
                else:
                    integer_list.append(self.forward_dict["_OOD_"])
        return integer_list

    def intlist2text(self, int_list):
        """ Convert a list of integers back into text. """
        text = str()
        capitalise = False
        for i in int_list:
            char = self.reverse_dict[i]
            if char == "_CAPITAL_":
                capitalise = True
            else:
                if capitalise:
                    char = char.upper()
                text += char
                capitalise = False
        return text


class WordDict(BaseDict):
    """ Class to model mapping between words and integers. """
    pass
