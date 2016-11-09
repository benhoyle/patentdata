# -*- coding: utf-8 -*-

# Do we want one .py file per class and have nlpfunctions as class functions?

#import patentparser.nlpfunctions

import re
import nltk
import itertools
import math
# Used for frequency counts
from collections import Counter

import utils

# Import nltk stopwords - (we may want to create our own list with patent stopwords)
eng_stopwords = nltk.corpus.stopwords.words('english')

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
    def __init__(self, description, claimset, figures=None, title=None):
        """ description, claimset and figures are objects as below. """
        self.description = description
        self.claimset = claimset
        self.figures = figures
        self.title = title
    
    def text(self):
        """  Get text of patent document as string. """
        return "\n\n".join([self.description.text(), self.claimset.text()])
    
    def reading_time(self, reading_rate=100):
        """ Return estimate for time to read. """
        # Words per minute = between 100 and 200
        return len(nltk.word_tokenize(self.text())) / reading_rate

class Description:
    """ Object to model a patent description. """
    def __init__(self, paragraphs):
        """ paragraphs is a list of Paragraph objects. """
        self.paragraphs = paragraphs
    
    def text(self):
        """ Return description as text string. """
        return "\n".join([p.text for p in self.paragraphs])
        
    def get_paragraph(self, number):
        """ Return paragraph having the passed number. """
        return self.paragraphs[number - 1]
    
class Paragraph:
    """ Object to model a paragraph of a patent description. """
    def __init__(self, number, text):
        self.number = number
        self.text = text

class Claimset:
    """ Object to model a claim set. """ 
    def __init__(self, claims): 
        """ claims is a list of Claim objects. """
        self.claims = claims
        self.number_of_claims = len(self.claims)
    
    def text(self):
        """ Return claim set as text string. """
        return "\n".join([c.text for c in self.claims])
    
    def get_claim(self, number):
        """ Return claim having the passed number. """
        return self.claims[number - 1]
        
    def term_counts(self, stopwords=True):
        """ Calculate word frequencies in claims. 
        Stopwords flag sets removal of stopwords."""
        return sum([c.get_word_freq(stopwords) for c in self.claims], Counter())
    
    def claim_tf_idf(self, number):
        """ Calculate term frequency - inverse document frequency statistic
        for claim 'number' when compared to whole claimset. """
        claim = self.get_claim(number)
        
        # Need to remove punctuation, numbers and normal english stopwords?
        
        # Calculate term frequencies and normalise
        word_freqs = claim.get_word_freq()
        sum_freqs = sum(word_freqs.values())
        # Normalise word_freqs
        for key in word_freqs:
            word_freqs[key] /= sum_freqs
        
        # Calculate IDF > log(total no. of claims / no. of claims term appears in)
        tf_idf = [{
            'term': key, 
            'tf': word_freqs[key],
            'tf_idf': word_freqs[key]*len(self.appears_in(key))
            }
            for key in word_freqs]
        # Sort list by tf_idf
        tf_idf = sorted(tf_idf, key=lambda k: k['tf_idf'], reverse=True)
        
        return tf_idf
    
    def appears_in(self, term):
        """ Returns claims string 'term' appears in. """
        return [c for c in self.claims if c.appears_in(term)]
    
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

    def __init__(self, text, number=None, dependency=None):
        """ Initiate claim object with string containing claim text."""
        # Load text
        self.text = text
        
        # Check for and extract claim number
        parsed_number, self.text = self.get_number()
        if number:
            self.number = number
            if number != parsed_number:
                print("Warning: detected claim number does not equal passed claim number.")
        else:
            self.number = parsed_number
        
        # Get category
        self.category = self.detect_category()
        
        # Get dependency
        parsed_dependency = self.detect_dependency()
        if dependency:
            self.dependency = dependency
            if dependency != parsed_dependency:
                print("Warning: detected dependency does not equal passed dependency.")
                # Quick check - parsed dependency likely to be correct if passed dependency >= claim number
                if dependency >= self.number:
                    self.dependency = parsed_dependency
        else:
            self.dependency = parsed_dependency
        
        # Tokenise text into words
        self.words = nltk.word_tokenize(self.text)
        # Label parts of speech - uses averaged_perceptron_tagger as downloaded above
        self.pos = self.get_pos()
        # Apply chunking into noun phrases
        (self.word_data, self.mapping_dict) = self.label_nounphrases()
        
        #Split claim into features
        self.features = self.split_into_features()
        
    def get_word_freq(self, stopwords=True):
        """ Calculate term frequencies for words in claim. """
        # Take out punctuation
        if stopwords:
            # If stopwords = true then remove stopwords
            return Counter([w.lower() for w in self.words if w.isalpha() and w.lower() not in eng_stopwords])
        else:
            return Counter([w.lower() for w in self.words if w.isalpha()])
    
    def get_pos(self):
        """ Get the parts of speech."""
        pos_list = nltk.pos_tag(self.words)
        # Hard set 'comprising' as VBG
        pos_list = [(word, pos) if word != 'comprising' else ('comprising', 'VBG') for (word, pos) in pos_list]
        return pos_list
    
    def appears_in(self, term):
        """ Determine if term appears in claim. """
        return term.lower() in [w.lower() for w in self.words]
            

    def get_number(self):
        """Extracts the claim number from the text."""
        p = re.compile('\d+\.')
        located = p.search(self.text)
        if located:
            # Set claim number as digit before fullstop
            number = int(located.group()[:-1])
            text = self.text[located.end():].strip()
        else:
            number = None
            text = self.text
        return number, text
    
    def detect_category(self):
        """Attempts to determine and return a string containing the claim category."""
        p = re.compile('(A|An|The)\s([\w-]+\s)*(method|process)\s(of|for)?')
        located = p.search(self.text)
        # Or store as part of claim object property?
        if located:
            return "method"
        else:
            return "system"

    def determine_entities(self):
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
        
    def print_nps(self):
        ent_tree = self.determine_entities(self.pos)
        traverse(ent_tree)
    
    def detect_dependency(self):
        """Attempts to determine if the claim set out in text is dependent - if it is dependency is returned - if claim is deemed independent 0 is returned as dependency """
        p = re.compile('(of|to|with|in)?\s(C|c)laims?\s\d+((\sto\s\d+)|(\sor\s(C|c)laim\s\d+))?(,\swherein)?')
        located = p.search(self.text)
        if located:
            num = re.compile('\d+')
            dependency = int(num.search(located.group()).group())
        else:
            # Also check for "preceding claims" or "previous claims" = claim 1
            pre = re.compile('\s(preceding|previous)\s(C|c)laims?(,\swherein)?')
            located = pre.search(self.text)
            if located:
                dependency = 1
            else:
                dependency = 0
        # Or store as part of claim object property?
        return dependency
    
    def split_into_features(self):
        """ Attempts to split a claim into features.
        param string text: the claim text as a string
        """
        featurelist = []
        startindex = 0
        #split_re = r'(.+;\s*(and)?)|(.+,.?(and)?\n)|(.+:\s*)|(.+\.\s*$)'
        split_expression = r'(;\s*(and)?)|(,.?(and)?\n)|(:\s*)|(\.\s*$)'
        p = re.compile(split_expression)
        for match in p.finditer(self.text):
            feature = {}
            feature['startindex'] = startindex
            endindex = match.end()
            feature['endindex'] = endindex
            feature['text'] = self.text[startindex:endindex]
            featurelist.append(feature)
            startindex = endindex
        # Try spliting on ';' or ',' followed by '\n' or ':'
        #splitlist = filter(None, re.split(r";|(,.?\n)|:", text))
        # This also removes the characters - we want to keep them - back to search method?
        # Or store as part of claim object property?
        return featurelist
        
    def label_nounphrases(self):
        """ Label noun phrases in the output from pos chunking. """
        grammar = '''
            NP: {<DT|PRP\$> <VBG> <NN.*>+} 
                {<DT|PRP\$> <NN.*> <POS> <JJ>* <NN.*>+}
                {<DT|PRP\$>? <JJ>* <NN.*>+ }
            '''
    
        cp = nltk.RegexpParser(grammar)
        result = cp.parse(self.pos)
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
                ends_with_list = [np for np in nps if utils.ends_with(np_string, np)]
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

