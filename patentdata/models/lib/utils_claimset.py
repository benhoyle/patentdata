# -*- coding: utf-8 -*-
from nltk.tokenize import sent_tokenize
import re
import operator
import warnings
from patentdata.models.claim import check_claim_class, Claim
from patentdata.models.lib.utils_claim import (
    get_number, detect_dependency, detect_category
)


def nltk_extract_claims(text):
    """
    Attempts to extract claims as a list from a large text string.
    Uses nltk sent_tokenize function in tokenize library
    param string text: string containing several claims
    """
    sent_list = sent_tokenize(text)
    # On a test string this returned a list with the claim number
    # and then the claim text as separate items
    claims_list = []
    for i in range(0, len(sent_list), 2):
        try:
            number = int(sent_list[i].split(".")[0])
        except:
            number = 0

        claims_list.append(
            (number, sent_list[i+1])
        )

    return claims_list


def regex_extract_claims(text):
    """
    Uses regex to attempt to extract claims from a large string
    of text.

    :param text: Large string for claimset
    :type text: str
    :return: list of tuples (claim_number, claim_text)
    """
    claim_r = r'((\d+)\s*\.[ |\t])?([A-Z].*?[\.])\s*\n'
    matches = re.finditer(claim_r, text, re.DOTALL)
    claimset_list = []
    for match_num, match in enumerate(matches):
        match_num = match_num + 1
        claim_text = match.group(3)
        if match.group(2):
            number = match.group(2)
        else:
            number = match_num
        claimset_list.append((number, claim_text))
    return claimset_list


def clean_header(text):
    """ Strip header text from ocr text."""
    header_sub_re = r"\n{1,4}(\d{1,3}|W(O|0).+)\n{1,4}"
    return re.sub(header_sub_re, "\n\n", text)


def extract_claims_from_ocr(text):
    """ Extract claims from a long text string generated via tesseract.

    regex on claim start version."""
    lines = text.split("\n")

    start_claim_regex = r"(?P<number>\d{1,3})\s{0,4}(\.|,|‘)\s{0,4}[A-Z]"

    claim_start_lines = list()
    for i, line in enumerate(lines):
        m = re.match(start_claim_regex, line)
        if m:
            claim_start_lines.append((m.group("number"), i))

    claim_list = list()
    # Add on the length of the list to allow i+1 look-ahead
    claim_start_lines.append(("", len(lines)))

    for i, csl in enumerate(claim_start_lines[:-1]):
        claim_start = csl[1]
        claim_end = claim_start_lines[i+1][1]-1
        text = " ".join(lines[claim_start:claim_end])
        claim_list.append(Claim(text, number=csl[0]))
    return claim_list


def score_claimset(claimset_list):
    """
    Applies checks and generates a score indicating fitness.

    :param claimset_list: set of (number, text) tuples for claims.
    :type claimset_list: tuples (int, str)
    :return: score normalised between 0 and 1
    """
    score = 0
    # Score total = number of checks
    score_total = 4
    # Tests
    if check_first(claimset_list):
        score = score + 1
    if check_last(claimset_list):
        score = score + 1
    if check_consecutive(claimset_list):
        score = score + 1
    if check_dependencies(claimset_list):
        score = score + 1

    return round((score / score_total), 2)


def check_consecutive(claimset_list):
    """
    Checks claims are numbered consecutively.

    :param claimset_list: set of (number, text) tuples for claims.
    :type claimset_list: tuples (int, str)
    :return: true for consecutive; false if check fails
    """
    previous_number = 0
    try:
        for number, claim in claimset_list:
            if number == (previous_number + 1):
                previous_number = previous_number + 1
            else:
                return False
        return True
    except:
        return False


def check_first(claimset_list):
    """
    Checks claims begin at 1.

    :param claimset_list: set of (number, text) tuples for claims.
    :type claimset_list: tuples (int, str)
    :return: true if first claim = 1; false if check fails
    """
    try:
        if claimset_list[0][0] == 1:
            return True
        else:
            return False
    except:
        return False


def check_last(claimset_list):
    """
    Checks claims end with a claim number = length of list.

    :param claimset_list: set of (number, text) tuples for claims.
    :type claimset_list: tuples (int, str)
    :return: true if last claim = length of claims; false if not
    """
    try:
        if claimset_list[-1][0] == len(claimset_list):
            return True
        else:
            return False
    except:
        return False


def check_for_number(claimset_data):
    """
    Checks if claimset_data contains tuples with an integer entry.

    :param claimset_data: list of tuples or strings.
    :type claimset_data: list of tuples or strings
    :return: true if tuples with numbers; false if not
    """
    try:
        for entry in claimset_data:
            if len(entry) <= 1:
                return False
            else:
                if not isinstance(entry[0], int):
                    return False
        return True
    except:
        return False


def check_set_claims(potential_claimset):
    """ Checks if a passed object is a set of Claim objects. """
    claimset_flag = True
    if isinstance(potential_claimset, list):
        for potential_claim in potential_claimset:
            if not check_claim_class(potential_claim):
                claimset_flag = False
    else:
        claimset_flag = False
    return claimset_flag


def get_numbers(claimset_data):
    """
    Gets claim numbers using regex.

    :param claimset_data: list of strings.
    :type claimset_data: list of tuples or strings
    :return: claimset_list_out list of (number, text) tuples
    """
    claimset_list_out = []
    for entry in claimset_data:
        number, text = get_number(entry)
        claimset_list_out.append((number, text))
    return claimset_list_out


def check_dependencies(claimset_data):
    """
    Checks for dependency consistency.

    :param claimset_data: list of tuples or strings.
    :type claimset_data: list of tuples or strings
    :return: true if dependencies are consistent; false if not
    """
    category = {}
    try:
        for number, text in claimset_data:
            dependency = detect_dependency(text)
            category[number] = detect_category(text)
            # Check dependency is less than current claim number
            if dependency >= number:
                return False
            # Check categories of parent claims match
            if dependency != 0:
                if category[number] != category[dependency]:
                    return False
        return True
    except:
        return False


def clean_data(data_in):
    """
    Cleans and checks data_in.

    data_in may be a list of strings or a giant string
    """

    # Check & pass through if a set of claim objects already
    if check_set_claims(data_in):
        return data_in

    claimset_data = {}
    # Generate a string of all data in
    if isinstance(data_in, list):
        string_data_in = '\n'.join(data_in)

        # Check if claimset data has tuples with claim numbers
        if not check_for_number(data_in):
            claimset_data['passed'] = get_numbers(data_in)
    else:
        string_data_in = data_in
        claimset_data['passed'] = []

    # Use regex to split into claims with number
    claimset_data['regex'] = regex_extract_claims(string_data_in)

    # Use sentence tokenization to split into claims with number
    claimset_data['nltk'] = nltk_extract_claims(string_data_in)

    scores = {}

    scores['regex'] = score_claimset(claimset_data['regex'])
    scores['nltk'] = score_claimset(claimset_data['nltk'])
    scores['passed'] = score_claimset(claimset_data['passed'])

    sorted_scores = sorted(scores.items(), key=operator.itemgetter(1))

    # Top score
    top_score = sorted_scores[-1]
    if top_score[1] < 1:
        warnings.warn("Some claim checks failed for the claimset")
    data_out = claimset_data[top_score[0]]

    claimset_out = [
                Claim(claimtext, number)
                for number, claimtext in data_out
                ]

    return claimset_out
