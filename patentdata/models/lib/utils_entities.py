from spacy.symbols import NUM, DET, NOUN, VERB, PUNCT
from collections import OrderedDict
from difflib import SequenceMatcher
import logging


# Could we change this to slice on a key? Probably
def sliceodict(d, i):
    """Slice an ordered dict based on a passed index.
    list[:i] for an ordered dict
    """
    temp_dict = {k: v for j, (k, v) in enumerate(d.items()) if j < i}
    return OrderedDict(sorted(temp_dict.items(), key=lambda t: t[1][0][0].i))


# We want to set these if they are not already set
def set_probability(token, p_all_e_word, entity, new_value):
    """ Set probability value if not set already"""
    if entity not in p_all_e_word[token].keys():
        if sum([v for k, v in p_all_e_word[token]] + new_value) <= 1:
            p_all_e_word[token][entity] = new_value
    return p_all_e_word


def check_start_phrase(token, doc):
    """ Check for start of phrases 'at least one' and 'one or more' as
    determinant.

    Return true if located."""
    i = token.i
    condition = (
        doc[i:i+3].text.lower() == "at least one" or
        doc[i:i+3].text.lower() == "one or more"
    )
    condition = condition and (doc[i-1].text.lower() != "the")
    return condition


def is_det(token, doc):
    """ Wrapper function for determinant check."""
    # Add 'said' as custom determination
    condition = (token.pos == DET or token.text == "said")
    # Alternatively we can have the start phrases as above
    condition = (condition or check_start_phrase(token, doc))
    # Add check for 'a)' and 'a.' - this is not a det
    condition = condition and (
        doc[token.i:token.i+2].text.lower() not in ['a)', 'a.']
        )
    return condition


def heuristics(token, doc, p_all_e_word):
    """ Apply heuristics to mark entity probabilities"""
    entity_stop_chars = ["\n", ":", ";", ".",  ","]
    # Set stop characters as non-entity
    if token.text in entity_stop_chars:
        p_all_e_word[token][0] = 1

    # Set noun as entity
    if token.pos == NOUN and p_all_e_word[token].get(0, None) != 1:
        p_all_e_word[token][0] = 0

    # 'for' is an entity boundary
    if token.lemma_ == "for":
        p_all_e_word[token][0] = 1

    # "comprise", "have", "be", "include" do not relate to an entity
    if token.lemma_ in ["comprise", "have", "be", "include"]:
        p_all_e_word[token][0] = 1

    # "where" and "wherein" do not relate to an entity
    if "where" in token.lemma_:
        p_all_e_word[token][0] = 1

    # Look ahead - check not at end
    if token.i < (len(doc)-1):

        # "configured/adapted to" do not relate to an entity
        if (
            doc[token.i+1].lemma_ == "to" and
            token.lemma_ in ["configure", "adapt"]
        ):
            p_all_e_word[token][0] = 1
            p_all_e_word[doc[token.i + 1]][0] = 1

    if token.i < (len(doc)-2):
        # Set DETs as entity
        if (
            token.pos == DET or token.text == "said"
        ) and (
            doc[token.i:token.i+2].text.lower() not in ['a)', 'a.']
        ):
            p_all_e_word[token][0] = 0
            p_all_e_word[doc[token.i+1]][0] = 0

        # DET X of .. relates to an entity
        if token.pos == DET and doc[token.i+2].lemma_ == "of":
            p_all_e_word[token][0] = 0
            p_all_e_word[doc[token.i + 1]][0] = 0
            # Set of
            p_all_e_word[doc[token.i + 2]][0] = 0
            # Set term after off
            p_all_e_word[doc[token.i + 3]][0] = 0

        # "in X with" does not relate to an entity
        if token.lemma_ == "in" and doc[token.i+2].lemma_ == "with":
            p_all_e_word[token][0] = 1
            p_all_e_word[doc[token.i + 1]][0] = 1
            p_all_e_word[doc[token.i + 2]][0] = 1

        # Associated with does not relate to an entity
        if doc[token.i:token.i+2].text.lower() == "associated with":
            p_all_e_word[token][0] = 1
            p_all_e_word[doc[token.i + 1]][0] = 1

    if token.i < (len(doc)-3):
        # "at least NUM" / "NUM or more" relates to an entity
        if (
            doc[token.i:token.i + 2].text.lower() == "at least" and
            doc[token.i + 2].pos == NUM
        ):
            p_all_e_word[token][0] = 0
            p_all_e_word[doc[token.i + 1]][0] = 0
            p_all_e_word[doc[token.i + 2]][0] = 0
        if (
            doc[token.i+1:token.i + 3].text.lower() == "or more" and
            token.pos == NUM
        ):
            p_all_e_word[token][0] = 0
            p_all_e_word[doc[token.i + 1]][0] = 0
            p_all_e_word[doc[token.i + 2]][0] = 0

    return p_all_e_word


def extract_entities(doc):
    """Extract entities from a spaCy doc object."""
    # Start with all words relate to no entities
    p_all_e_word = dict()

    for token in doc:
        # Initialise probabilities
        p_all_e_word[token] = dict()

    # This can be combined with first pass easily - similar checks
    logging.info("First pass - entity label heuristics")
    for token in doc:
        p_all_e_word = heuristics(token, doc, p_all_e_word)
        logging.info("{0} - [{1}]".format(
            token.text,
            p_all_e_word[token]
        )
        )

    logging.info("Second pass - look for DET ... NOUN groupings")
    # Second parse - take any DET ... NOUN <boundary> portions
    last_break = 0
    for token in doc:
        # Look for hard end points or DET
        if (p_all_e_word[token].get(0, None) == 1) or (token.pos == DET):
            logging.info("{0} is e_0=1 or DET - looking back".format(token))
            # Step back marking as e_0=1 until first NOUN
            for j in range(token.i-1, last_break, -1):
                logging.info(
                    "Step back token - {0} with pos - {1}"
                    .format(doc[j], doc[j].pos)
                    )
                if doc[j].pos != NOUN:
                    logging.info("Setting non-Noun")
                    p_all_e_word[doc[j]][0] = 1
                else:
                    last_break = j
                    break

        # Look at grouping from DET
        if is_det(token, doc):
            # Tweak for "at least X" and "X or more"
            if (
                doc[token.i:token.i + 2].text.lower() == "at least"
                and doc[token.i + 2].pos == NUM
            ) or (
                doc[token.i+1:token.i + 3].text.lower() == "or more"
                and token.pos == NUM
            ):
                # logging.info("Head index set to {0}".format())
                head_index = doc[token.i+2].head.i
            else:
                head_index = token.head.i
            possible_entity = True
            # Step through intermediate tokens between current and head
            for j in range(token.i, head_index):
                # If head is outside of DET ... end_NOUN sequence
                if doc[j].head.i < token.i and doc[j].head.i > head_index:
                    # Check for nested portions
                    possible_entity = False
            if possible_entity:
                for k in range(token.i, head_index + 1):
                    p_all_e_word[doc[k]][0] = 0
        # Need to adapt the above for at least one ... X and one or
        # more ... Xs - "at" > head > "least" > "one" > X

        # Look at plural nouns
        if token.tag_ == "NNS":
            logging.info("Located plural noun: {0}".format(token))
            # Step back and mark as e_0=0 preceding words w/ token as a head
            for j in range(token.i-1, 0, -1):
                logging.info(doc[j], doc[j].head.i, p_all_e_word[doc[j]])
                if p_all_e_word[doc[j]]:
                    break
                elif (
                    doc[j].head.i == token.i
                ):
                    logging.info("Setting {0} as e_0=0".format(doc[j]))
                    p_all_e_word[doc[j]][0] = 0

    for token in doc:
        logging.info(
            "Probs: {0} - [{1}]".format(
                token.text,
                p_all_e_word[token]
            )
        )

    for token in doc:
        if not p_all_e_word[token]:
            logging.info(
                "Non p-set words: {0} - [{1}]".format(
                    token.text,
                    p_all_e_word[token]
                )
            )

    logging.info("Extracted possible occurrences:\n")
    poss_occ = list()
    for token in doc[1:]:
        # If transition
        if (
            p_all_e_word[token].get(0, 0) == 0 and
            p_all_e_word[doc[token.i-1]].get(0, 1) == 1
        ):
            # Add consecutive e_0=0
            for j in range(token.i, len(doc)+1):
                if p_all_e_word[doc[j]].get(0, 1) != 0:
                    poss_occ.append(doc[token.i:j])
                    break

    logging.info(poss_occ)

    # Matching occurrences
    entity_dict = dict()
    # Now group by unique
    for entity in poss_occ:
        np_start = entity.start
        # Ignore the determinant
        if doc[np_start].pos == DET:
            np_start += 1
        # Generate a string representation excluding the determinant
        np_string = doc[np_start:entity.end].text.lower()
        if np_string:
            if np_string not in entity_dict.keys():
                entity_dict[np_string] = list()
            entity_dict[np_string].append(entity)

    logging.info(doc)
    # logging.info(entity_dict)

    # Quick function to sort entities by occurrence
    # Need to sort the keys by the index of the first word in the first entry
    ordered_entities = OrderedDict(
        sorted(entity_dict.items(), key=lambda t: t[1][0][0].i)
        )

    logging.info(ordered_entities)

    # Look for duplict entities and merge
    new_o_e = ordered_entities.copy()
    for i, (entity_string, occurrences) in enumerate(ordered_entities.items()):
        # Check if first entry in occurrences begins with the
        current_occurrence = occurrences[0]
        if current_occurrence[0].lemma_ in ["the", "each"]:
            logging.info(
                "Found entity '{0}' with incorrect antecedence"
                .format(current_occurrence)
                )
            possible_matches = list()
            for pes, previous_o in sliceodict(ordered_entities, i).items():
                first_entry = previous_o[0]
                # Check to see if head of occurrence with "the" agrees
                # with head of previous occurrence

                if (
                    first_entry[-1].text.lower() ==
                    current_occurrence[-1].text.lower()
                ) and (
                    first_entry[-1].tag == current_occurrence[-1].tag
                ):
                    logging.info(
                        "Found possible match with {0}"
                        .format(pes)
                    )

                    # Need to check here for multiple term matches
                    possible_matches.append(pes)

            logging.info(possible_matches)
            if len(possible_matches) > 0:
                if len(possible_matches) > 1:
                    best_match = 0.0
                    best_match_string = ""
                    for match in possible_matches:
                        s = SequenceMatcher(
                                a=entity_string,
                                b=match
                            ).quick_ratio()
                        logging.info(s)
                        if s > best_match:
                            best_match = s
                            logging.info("Best match = {0}".format(best_match))
                            best_match_string = match
                    previous_entity_string = best_match_string
                else:
                    previous_entity_string = possible_matches[0]
                # Merge entries in copy of dict
                logging.info(
                    "Selected previous entity = {0}"
                    .format(previous_entity_string)
                )
                new_o_e[previous_entity_string] += occurrences
                new_o_e.pop(entity_string)

    logging.info(new_o_e)
    return new_o_e


def extract_steps(doc):
    """ Extract steps of a method claim from a spaCy doc object."""
    step_boundaries = list()

    # Alternative to below is to look at head of "method" token in claim
    for t1 in doc:
        if t1.lemma_ in ["comprise"]:
            # Scan ahead for colon
            for t2 in doc[t1.i+1:]:
                if t2.lemma_ == ":":
                    print("Colon found at {0} (text='{1}')".format(t2.i, t2))
                    step_boundaries.append(t2)
                    # Scan ahead to find semi-colons associated with colon
                    for t3 in doc[t2.i+1:]:
                        if t3.pos == PUNCT and t3.tag_ in [":", "."]:
                            step_boundaries.append(t3)
                    break
            break

    print("Step boundaries are {0}".format(step_boundaries))

    # Find first verb after each in set [colon, semi-colon]
    step_verbs = list()
    for sb in step_boundaries[:-1]:
        for t1 in doc[sb.i+1:]:
            if t1.pos == VERB and t1.tag_ == "VBG":
                # sb is previous step boundary - we want next step boundary
                step_verbs.append(t1)
                break

    print("Step verbs are {0}".format(step_verbs))

    steps = list()
    # Tada set of method steps
    for sv, sb in zip(step_verbs, step_boundaries[1:]):
        print("Step verb is {0} with lemma {1}".format(sv, sv.lemma_))
        print("Step text is {0}".format(doc[sv.i:sb.i].text))
        steps.append((sv, sb))

    return steps


def ref_num_entity_finder(doc):
    """ Find entities with reference numerals a sentence
    in the form of a spaCy span."""
    entity_list = list()
    start_index = 0
    record = False
    for token in doc:
        if token.pos == DET:
            record = True
            start_index = token.i

        if "FIG" in token.text:
            record = False

        if token.pos == NUM and doc[token.i-1].pos == NOUN:
            # Hack for plural nouns that may lack a determinant
            if not record and doc[token.i-1].tag_ == "NNS":
                # Follow tree for plural noun phrase
                children = [c for c in doc[token.i-1].children]
                if children:
                    start_index = children[0].i
                entity_list.append(doc[start_index:token.i+1])
            # Add
            if record:
                record = False
                entity_list.append(doc[start_index:token.i+1])

    return entity_list


def get_entity_ref_num_dict(doc):
    """ Get a dictionary of entities indexed by reference numeral.

    param spaCy_doc doc: document to process as a spaCy 'doc' object
    """
    entity_list = ref_num_entity_finder(doc)
    entity_dict = {}
    for entity in entity_list:
        ref_num = entity[-1].text
        # Clean fullstops
        if ref_num[-1] == ".":
            ref_num = ref_num[:-1]
        if ref_num not in entity_dict.keys():
            entity_dict[ref_num] = list()
        # Check if a variation already exists
        exists = False
        n_gram = entity[1:-1]
        for existing in entity_dict[ref_num]:
            if n_gram == existing:
                exists = True
        if not exists:
            entity_dict[ref_num].append(n_gram)
    return entity_dict
