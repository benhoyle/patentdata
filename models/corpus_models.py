# -*- coding: utf-8 -*-

# Do we want one .py file per class and have nlpfunctions as class functions?

#import patentparser.nlpfunctions

import re
import nltk
import itertools

class PatentCorpus:
    """ Object to model a collection of patent documents. """
    def __init__(self):
        # Set documents as list of PatentDoc objects
        documents = []

class ApplnState:
    """ Object to model a state of a patent document. """
    pass

class PatentDoc:
    """ Object to model a patent document. """
    def __init__(self):
        self.description = Description()
        self.claimset = Claimset()
        self.figures = Figures()
        
    def text(self):
        """  Get text of patent document as string. """
        return "\n\n".join([self.description.text(), self.claimset.text()])
    
    def reading_time(self, reading_rate=100):
        """ Return estimate for time to read. """
        # Words per minute = between 100 and 200
        return len(nltk.word_tokenize(self.text())) / reading_rate

class Description:
    """ Object to model a patent description. """
    def __init__(self):
        # Set paragraphs as list of paragraph objects
        paragraphs = []
    
    def text(self):
        """ Return description as text string. """
        return "\n".join([p.text for p in self.paragraphs])
    
class Paragraph:
    """ Object to model a paragraph of a patent description. """
    def __init__(self, para_number, para_text):
        self.number = para_number
        self.text = para_text

class Claimset:
    """ Object to model a claim set. """ 
    def __init__(self): 
        # Set claims as list of Claim objects
        self.claims = []
    
    def text(self):
        """ Return claim set as text string. """
        return "\n".join([c.text for c in self.claims])
    
    def clean_data(claim_data):
        """ Cleans and checks claim data returned from EPO OPS. """
        
        # If claims_data is a single string attempt to split into a list
        if not isinstance(claim_data, list):
            claim_data = extract_claims(claim_data)
        
        claims = [get_number(claim) for claim in claims_list]
        
        for claim_no in range(1, len(claims)):
            if claims[claim_no-1][0] != claim_no:
                pass
                
        # Checks
        # - len(claims) = claims[-1] number
        # - 
    
    def extract_claims(text):
        """ Attempts to extract claims as a list from a large text string.
        param string text: string containing several claims
        """
        sent_list = nltk.tokenize.sent_tokenize(text)
        # On a test string this returned a list with the claim number and then the
        # claim text as separate items
        claims_list = [" ".join(sent_list[i:i+2]) for i in xrange(0, len(sent_list), 2)]
        return claims_list

class Figures:    
    """ Object to model a set of patent figures. """
    pass
    
# ========================== Claim Model =============================#

class Claim:
    """ Object to model a patent claim."""

    def __init__(self, claimstring, number=None, dependency=None):
        """ Initiate claim object with string containing claim text."""
        # Load text
        self.text = claimstring
        
        # Check for and extract claim number
        parsed_number, self.text = patentparser.nlpfunctions.get_number(claimstring)
        if number:
            self.number = number
            if number != parsed_number:
                print("Warning: detected claim number does not equal passed claim number.")
        else:
            self.number = parsed_number
        
        # Get category
        self.category = patentparser.nlpfunctions.detect_category(self.text)
        
        # Get dependency
        parsed_dependency = patentparser.nlpfunctions.detect_dependency(self.text)
        if dependency:
            self.dependency = dependency
            if dependency != parsed_dependency:
                print("Warning: detected dependency does not equal passed dependency.")
        else:
            self.dependency = parsed_dependency
        
        # Tokenise text into words
        self.words = patentparser.nlpfunctions.get_words(self.text)
        # Label parts of speech - uses averaged_perceptron_tagger as downloaded above
        self.pos = patentparser.nlpfunctions.get_pos(self.words)
        # Apply chunking into noun phrases
        (self.word_data, self.mapping_dict) = patentparser.nlpfunctions.label_nounphrases(self.pos)
        
        #Split claim into features
        self.features = patentparser.nlpfunctions.split_into_features(self.text)

    def get_number(text):
        """Extracts the claim number from the text."""
        p = re.compile('\d+\.')
        located = p.search(text)
        if located:
            # Set claim number as digit before fullstop
            number = int(located.group()[:-1])
            text = text[located.end():].strip()
        else:
            number = None
            text = text
        return number, text
    
    def detect_category(text):
        """Attempts to determine and return a string containing the claim category."""
        p = re.compile('(A|An|The)\s([\w-]+\s)*(method|process)\s(of|for)?')
        located = p.search(text)
        # Or store as part of claim object property?
        if located:
            return "method"
        else:
            return "system"

    def determine_entities(pos):
        """ Determines noun entities within a patent claim.
        param: pos - list of tuples from nltk pos tagger"""
        # Define grammar for chunking
        grammar = '''
            NP: {<DT|PRP\$> <VBG> <NN.*>+} 
                {<DT|PRP\$> <NN.*> <POS> <JJ>* <NN.*>+}
                {<DT|PRP\$>? <JJ>* <NN.*>+ }
            '''
        cp = nltk.RegexpParser(grammar)
        # Or store as part of claim object property?
        
        # Option: split into features / clauses, run over clauses and then re-correlate
        return cp.parse(pos)
        
    def print_nps(pos):
        ent_tree = determine_entities(pos)
        traverse(ent_tree)
    
    def detect_dependency(text):
        """Attempts to determine if the claim set out in text is dependent - if it is dependency is returned - if claim is deemed independent 0 is returned as dependency """
        p = re.compile('(of|to|with|in)?\s(C|c)laims?\s\d+((\sto\s\d+)|(\sor\s(C|c)laim\s\d+))?(,\swherein)?')
        located = p.search(text)
        if located:
            num = re.compile('\d+')
            dependency = int(num.search(located.group()).group())
        else:
            # Also check for "preceding claims" or "previous claims" = claim 1
            pre = re.compile('\s(preceding|previous)\s(C|c)laims?(,\swherein)?')
            located = pre.search(text)
            if located:
                dependency = 1
            else:
                dependency = 0
        # Or store as part of claim object property?
        return dependency
    
    def split_into_features(text):
        """ Attempts to split a claim into features.
        param string text: the claim text as a string
        """
        featurelist = []
        startindex = 0
        #split_re = r'(.+;\s*(and)?)|(.+,.?(and)?\n)|(.+:\s*)|(.+\.\s*$)'
        split_expression = r'(;\s*(and)?)|(,.?(and)?\n)|(:\s*)|(\.\s*$)'
        p = re.compile(split_expression)
        for match in p.finditer(text):
            feature = {}
            feature['startindex'] = startindex
            endindex = match.end()
            feature['endindex'] = endindex
            feature['text'] = text[startindex:endindex]
            featurelist.append(feature)
            startindex = endindex
        # Try spliting on ';' or ',' followed by '\n' or ':'
        #splitlist = filter(None, re.split(r";|(,.?\n)|:", text))
        # This also removes the characters - we want to keep them - back to search method?
        # Or store as part of claim object property?
        return featurelist
        
    def label_nounphrases(pos):
        """ Label noun phrases in the output from pos chunking. """
        grammar = '''
            NP: {<DT|PRP\$> <VBG> <NN.*>+} 
                {<DT|PRP\$> <NN.*> <POS> <JJ>* <NN.*>+}
                {<DT|PRP\$>? <JJ>* <NN.*>+ }
            '''
    
        cp = nltk.RegexpParser(grammar)
        result = cp.parse(pos)
        ptree = nltk.tree.ParentedTree.convert(result)
        subtrees = ptree.subtrees(filter=lambda x: x.label()=='NP')
        
        # build up mapping dict - if not in dict add new entry id+1; if in dict label using key
        mapping_dict = {}
        pos_to_np = {}
        for st in subtrees:
            np_string = " ".join([leaf[0] for leaf in st.leaves() if leaf[1] != ("DT" or "PRP$")])
            np_id = mapping_dict.get(np_string, None)
            if not np_id:
                # put ends_with here
                nps = [i[0] for i in mapping_dict.items()]
                ends_with_list = [np for np in nps if ends_with(np_string, np)]
                if ends_with_list:
                    np_id = mapping_dict[ends_with_list[0]]
                else:
                    np_id = len(mapping_dict)+1
                    mapping_dict[np_string] = np_id
            pos_to_np[st.parent_index()] = np_id
        
        # Label Tree with entities
        flat_list = []
        for i in range(0, len(ptree)):
            #print(i)
            # Label 
            if isinstance(ptree[i], nltk.tree.Tree):
                for leaf in ptree[i].leaves():
                    # Unpack leaf and add label as triple
                    flat_list.append((leaf[0], leaf[1], pos_to_np.get(i, "")))
            else:
                flat_list.append((ptree[i][0], ptree[i][1], pos_to_np.get(i, "")))
        return (flat_list, mapping_dict)
    
    def json(self):
        """ Provide words as JSON. """
        # Add consecutive numbered ids for Reactgit@github.com:benhoyle/python-epo-ops-client.git
        #words = [{"id": i, "word":word, "pos":part} for i, (word, part) in list(enumerate(self.pos))]
        words = [{"id": i, "word":word, "pos":part, "np":np} for i, (word, part, np) in list(enumerate(self.word_data))]
        return {"claim":{ "words":words }}

