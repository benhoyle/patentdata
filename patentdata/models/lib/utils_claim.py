# -*- coding: utf-8 -*-
import re


def ends_with(s1, s2):
    """See if s1 ends with s2."""
    pattern = re.compile('(' + re.escape(s2) + ')$')
    located = pattern.search(s1)
    if located:
        return True
    else:
        return False


def get_number(text):
    """Extracts the claim number from the text."""
    p = re.compile(r'\d+\.')
    located = p.search(text)
    if located:
        # Set claim number as digit before fullstop
        number = int(located.group()[:-1])
        # text = text[located.end():].strip()
    else:
        number = 0
    return number, text


def detect_dependency(text):
    """
    Attempts to determine if the claim set out in text is dependent
    - if it is dependency is returned - if claim is deemed independent
    0 is returned as dependency

    :param text: claim text
    :type text: str
    :return: dependency as int
    """
    p = re.compile(
        r'(of|to|with|in)?\s(C|c)laims?\s\d+'
        r'((\sto\s\d+)|(\sor\s(C|c)laim\s\d+))?(,\swherein)?'
    )
    located = p.search(text)
    if located:
        num = re.compile('\d+')
        dependency = int(num.search(located.group()).group())
    else:
        # Also check for "preceding claims" or "previous claims" = claim 1
        pre = re.compile(
            r'\s(preceding|previous)\s(C|c)laims?(,\swherein)?'
        )
        located = pre.search(text)
        if located:
            dependency = 1
        else:
            dependency = 0
    # Or store as part of claim object property?
    return dependency


def detect_category(text):
    """
    Attempts to determine and return a string containing the
    claim category.

    :param text: claim text
    :type text: str
    :return: category as string
    """
    p = re.compile('(A|An|The)\s([\w-]+\s)*(method|process)\s(of|for)?')
    located = p.search(text)
    # Or store as part of claim object property?
    if located:
        return "method"
    else:
        return "system"

def entity_finder(pos_list):
    """ Find entities with reference numerals using POS data."""
    entity_list = list()
    record = False
    # Add indices
    enum_pos_list = list(enumerate(pos_list))
    for i, (word, pos) in enum_pos_list:
        if pos == "DT" and not record:
            # Start recording and record start index
            record = True
            start_index = i

        if pos == "DT" and record:
            # Step back until last noun is found
            for j, (word, pos) in reversed(enum_pos_list[:i]):
                if "NN" in pos:
                    # Add np_chunk to buffer
                    entity_list.append(pos_list[start_index:j+1])
                    break

            # Set new start index
            start_index = i

    return entity_list
