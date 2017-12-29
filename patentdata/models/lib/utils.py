# -*- coding: utf-8 -*-
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
import re
import string
import unicodedata

import spacy
try:
    nlp = spacy.load('en', disable=['ner', 'textcat'])
except:
    nlp = spacy.load('en_core_web_sm')

# Extend these stopwords to include patent stopwords
ENG_STOPWORDS = stopwords.words('english')

REGEX_US_APPLICATION = r"\d{2}\/\d{3}(,|\s)\d{3}"
REGEX_US_GRANT = r"\d(,|\s)\d{3}(,|\s)\d{3}"
REGEX_PCT_APPLICATION = r"PCT\/[A-Z]{2}\d{2,4}\/\d{5,6}"

PRINTABLE_CHAR_MAP = {c: i for i, c in enumerate(string.printable[:-2])}
REVERSE_PRINT_CHAR_MAP = {i: c for i, c in enumerate(string.printable[:-2])}


class Sdict(dict):
    """ Class to extend a dict to add a value to a keyed list."""
    def add(self, key, value):
        if key not in self.keys():
            self[key] = list()
        self[key].append(value)
        return self


def check_list(listvar):
    """Turns single items into a list of 1."""
    if not isinstance(listvar, list):
        listvar = [listvar]
    return listvar


def safeget(dct, *keys):
    """ Recursive function to safely access nested dicts or return None.
    param dict dct: dictionary to process
    param string keys: one or more keys"""
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct


def remove_non_words(tokens):
    """ Remove digits and punctuation from text. """
    # Alternative for complete text is re.sub('\W+', '', text)
    return [w for w in tokens if w.isalpha()]


def remove_stopwords(tokens):
    """ Remove stopwords from tokens. """
    return [w for w in tokens if w not in ENG_STOPWORDS]


def stem(tokens):
    """ Stem passed text tokens. """
    stemmer = PorterStemmer()
    return [stemmer.stem(token) for token in tokens]


def lemmatise(tokens_with_pos):
    """ Lemmatise tokens using pos data. """
    pass


def stem_split(tokens):
    """ Takes a list of tokens and splits stemmed tokens into
    stem, ending - inserting ending as extra token.

    returns: revised (possibly longer) list of tokens. """
    stemmer = PorterStemmer()
    token_list = list()
    for token in tokens:
        if (token[0] is "_" and token[-1] is "_") or token in string.punctuation:
            # Control token so add and skip
            token_list.append(token)
        else:
            stem = stemmer.stem(token)
            split_list = token.split(stem)
            if token == stem:
                token_list.append("_" + token)
            elif len(split_list) > 1:
                token_list.append("_" + stem)
                token_list.append(split_list[1])
            else:
                token_list.append("_" + split_list[0])
    return token_list


def capitals_process(tokens):
    """ Process a list of tokens and lower case.

    Adds a new <CAPITAL> token before a capitalised word to
    retain capital information."""
    token_list = list()
    for token in tokens:
        if token:
            if token[0].isupper():
                capital_token = "_CAPITAL_"
                if len(token) > 1:
                    if token[1].isupper():
                        capital_token = "_ALL_CAPITAL_"
                token_list.append(capital_token)
            if token[0] is not "_" and token[-1] is not "_":
                token_list.append(token.lower())
            else:
                token_list.append(token)
    return token_list


def punctuation_split(tokens):
    """ Split hyphenated and slashed tokens into words. """
    # \W is an alternative but this is equal to [^a-zA-Z0-9_]
    return sum((re.split('([^a-zA-Z0-9])', token) for token in tokens), list())


def replace_patent_numbers(text):
    """ Replace patent number with _PATENT_NO_. """
    regex = r"({0}|{1}|{2})".format(
        REGEX_US_APPLICATION,
        REGEX_US_GRANT,
        REGEX_PCT_APPLICATION
        )
    m = re.sub(regex, "_PATENT_NO_", text)
    return m


def replace_non_alpha(tokens):
    """ Replace non alpha tokens with a special control symbol."""
    return [
        "_NOTALPHA_" if (
            t not in string.punctuation and not t.isalpha() and
            t[0] is not "_" and t[-1] is not "_"
        ) else t for t in tokens
    ]


def filter_tokens(spacy_doc):
    """ Takes a list of tokens and splits stemmed tokens into
    stem, ending - inserting ending as extra token.

    returns: revised (possibly longer) list of tokens. """

    # Generate token string list with capitals replaced

    stemmer = PorterStemmer()
    token_list = list()
    for token in spacy_doc:
        if not token.is_alpha and token.pos_ != "PUNCT":
            token_list.append("_NOTALPHA_")
        else:
            space = False
            if token.i >= 1:
                if spacy_doc[token.i-1].whitespace_:
                    space = True
            token_text = token.text
            if token_text[0] is not "_" and token_text[-1] is not "_":
                if token.is_upper:
                    token_list.append("_ALL_CAPITAL_")
                    token_text = token.lower_
                elif token.is_title:
                    token_list.append("_CAPITAL_")
                    token_text = token.lower_

            stem = stemmer.stem(token_text)
            split_list = token_text.split(stem)
            if token_text == stem or len(split_list) <= 1:
                if space:
                    token_list.append("_" + token_text)
                else:
                    token_list.append(token_text)
            elif len(split_list) > 1:
                if space:
                    token_list.append("_" + stem)
                else:
                    token_list.append(stem)
                token_list.append(split_list[1])
    return token_list


def string2int(text, filter_printable=True):
    """ Convert text of document into a list of integers representing
    its characters.

    If filter_printable is true limit to 98 printable characters."""
    if filter_printable:
        ints = [
            ord(c) if c in string.printable[:-2] else ord(" ")
            for c in text
            ]
    else:
        ints = [ord(c) for c in text]
    return ints


def string2printint(text):
    """ Convert a string into a list of integers representing
    its printable characters."""
    return [
        PRINTABLE_CHAR_MAP[c]
        if c in PRINTABLE_CHAR_MAP.keys()
        else PRINTABLE_CHAR_MAP[" "]
        for c in text
    ]


def printint2string(doc_as_ints):
    """ Reconstruct document string from list of integers."""
    return "".join([REVERSE_PRINT_CHAR_MAP[i] for i in doc_as_ints])


# Create character cleaning dictionary
char_cleaner = dict()


char_cleaner['”'] = '"'
char_cleaner['“'] = '"'
char_cleaner['\u2003'] = ' '
char_cleaner['\ue89e'] = ' '
char_cleaner['\u2062'] = ' '
char_cleaner['\ue8a0'] = ' '
char_cleaner['−'] = '-'
char_cleaner['—'] = '-'
char_cleaner['′'] = "'"
char_cleaner['‘'] = "'"
char_cleaner['’'] = "'"
char_cleaner['×'] = '*'
char_cleaner['⁄'] = '/'


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


def clean_characters(text):
    """ Clean / normalise non-printable characters in the text.

    E.g. accented characters are replaced with non-accented versions.
    Character fractions are replaced with numbers and slashes."""
    replacement_text = list()
    for character in text:
        # Perform mapping for commonly occuring characters
        if character in char_cleaner.keys():
            character = char_cleaner[character]

        if character in string.printable:
            replacement_text.append(character)
        else:
            # If not printable determine if character can be decomposed
            replacement_chars = decompose_character(character)
            if replacement_chars:
                # Recursively call function on text of replacement chars
                replacement_text.append(
                    clean_characters("".join(replacement_chars))
                    )
            else:
                replacement_text.append("_")
    return "".join(replacement_text)


def entity_finder(pos_list):
    """ Find entities with reference numerals using POS data."""
    entity_list = list()
    entity = []
    record = False
    for i, (word, pos) in enumerate(pos_list):
        if pos == "DT":
            record = True
            entity = []

        if record:
            entity.append((word, pos))

        if "FIG" in word:
            # reset entity to ignore phrases that refer to Figures
            record = False
            entity = []

        if pos == "CD" and entity and record and ('NN' in pos_list[i-1][1]):
            record = False
            entity_list.append(entity)

    return entity_list


def filter_entity_list(entity_list):
    """Filter output to remove reference to priority claims."""
    filter_list = list()
    for entity in entity_list:
        if not (
            {"claims", "priority", "under"} <= set([w for w, _ in entity])
        ):
            filter_list.append(entity)
    return filter_list


def print_entity_list(entity_list):
    """Little function to print entity list."""
    words = [[word for word, _ in e] for e in entity_list]
    print([" ".join(word_list) for word_list in words])


def get_entity_set(entity_list):
    """ Get a set of unique entity n-grams from a list of entities."""
    ngram_list = list()
    for entity in entity_list:
        ngram_list.append(
            " ".join(
                    [
                        word
                        for word, pos in entity
                        if (pos != 'DT' and pos != 'CD')
                    ]
                )
            )
    return set(ngram_list)


def get_entity_dict(entity_list):
    """ Get a dictionary of entities indexed by reference numeral."""
    entity_dict = {}
    for entity in entity_list:
        ref_num = entity[-1][0]
        if ref_num not in entity_dict.keys():
            entity_dict[ref_num] = list()
        # Check if a variation already exists
        exists = False
        n_gram = " ".join([w for w, _ in entity[1:-1]])
        for existing in entity_dict[ref_num]:
            if n_gram == existing:
                exists = True
        if not exists:
            entity_dict[ref_num].append(n_gram)
    return entity_dict


def highlight_multiple(entity_dict):
    """ Highlight reference numerals used for multiple entities. """
    for key, value in entity_dict.items():
        if len(value) > 1:
            print(key, value)
