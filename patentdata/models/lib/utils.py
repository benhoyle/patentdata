# -*- coding: utf-8 -*-
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

# Extend these stopwords to include patent stopwords
ENG_STOPWORDS = stopwords.words('english')


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
        stem = stemmer.stem(token)
        split_list = token.split(stem)
        if token == stem:
            token_list.append(token)
        elif len(split_list) > 1:
            token_list.append(stem)
            token_list.append(split_list[1])
        else:
            token_list.append(split_list[0])
    return token_list


def capitals_process(tokens):
    """ Process a list of tokens and lower case.

    Adds a new <CAPITAL> token before a capitalised word to
    retain capital information."""
    token_list = list()
    for token in tokens:
        if token[0].isupper():
            if len(token) > 1:
                if token[1].isupper():
                    token_list.append("<ALL_CAPITAL>")
                else:
                    token_list.append("<CAPITAL>")
        token_list.append(token.lower())
    return token_list
