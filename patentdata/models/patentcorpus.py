# -*- coding: utf-8 -*-
from collections import Counter

from patentdata.models.patentdoc import PatentDoc
from patentdata.xmlparser import XMLDoc

from datetime import datetime

import logging
from zipfile import ZipFile
import Pickle
import importlib

logger = logging.getLogger(__name__)

from patentdata.corpus import (
    EPOOPS, USPublications, USGrants
)

DATASOURCE_OPTIONS = {
    'EPOOPS': EPOOPS,
    'USPublications': USPublications,
    'USGrants': USGrants
}

def string_to_class(datasource_str):
    """ Return a class indicated by a datasource_str."""
    if datasource_str not in list(DATASOURCE_OPTIONS.keys()):
        logger.error(
            "String value {0} not in group {1}"
            .format(datasource_str, list(DATASOURCE_OPTIONS.keys()))
        )
        raise ValueError
    else:
        return DATASOURCE_OPTIONS[datasource_str]


class PatentCorpus:
    """ Object to model a collection of patent documents. """
    def __init__(self, documents=[]):
        """ Initialise corpus.

        :param documents: list of patent documents
        :type documents: PatentDoc
        :return: PatentCorpus object

        """
        for doc in documents:
            if not isinstance(doc, PatentDoc):
                raise ValueError("Input must be a list of PatentDoc objects")
        self.documents = documents

    @classmethod
    def init_by_classification(
        cls, datasource, classification, sample_size=None
    ):
        """ Initialise with a classification of kind ["G", "06"] with
        one to five entries.

        Sample_size randomly samples to a particular
        number if supplied.

        If classification is None or an empty list, select a random
        sample across all classifications."""
        # Need to run a query to get list of filename, name entries

        # Then we can call init_by_filenames
        filegenerator = datasource.patentdoc_generator(
            classification, sample_size=sample_size
            )
        pcorp = cls()
        for doc in filegenerator:
            pcorp.add_document(doc)
        # Also add documents to cache here
        pcorp.classification = classification
        return pcorp

    def add_document(self, document):
        """ Add a document to the corpus.

        :param document: patent documents
        :type document: PatentDoc
        :return: PatentCorpus object

        """
        if not isinstance(document, PatentDoc):
            raise ValueError("Input must be a list of PatentDoc objects")
        logging.info("Adding Document: {0}".format(document.title))
        self.documents.append(document)

    def add_flat_document(self, flat_doc):
        """ Add a document from a flattened string form. """
        self.documents.append(PatentDoc.load_from_string(flat_doc))

    def char_stats(self):
        """ Provide statistics on characters in corpus."""
        sum_counter = Counter()
        for doc in self.documents:
            sum_counter += Counter(doc)
        print(
            "Documents contain {0} unique characters.".format(len(sum_counter))
            )
        return sum_counter

    def save(self, filename=None):
        """ Save patentdoc objects to disk to speed up loading of data. """
        # Create a zip archive
        # Have zip archive open as long as object is open
        # Serialise patentdoc using a method on that class
        # Also add load methods
        logging.info("Saving Patent Corpus")
        if not filename:
            filename = "{date}-{length}.patcorp.zip".format(
                date=datetime.now().strftime(format="%Y-%m-%d_%H-%M"),
                length=len(self.documents)
            )
        with ZipFile(filename, 'w') as myzip:
            for doc in self.documents:
                myzip.writestr(doc.number, doc.saveable)

    @classmethod
    def load(cls, filename):
        """ Load patentdoc objects from disk. """
        logging.info("Loading Patent Corpus")
        pcorp = cls()
        with ZipFile(filename) as myzip:
            for flat_doc in myzip.namelist():
                with myzip.open(flat_doc) as myfile:
                    pcorp.add_flat_document(myfile.read().decode('utf-8'))
        logging.info(
            "Loaded Patent Corpus with {0} documents"
            .format(len(pcorp.documents))
        )
        return pcorp


# May not need this - functionality handled by USPublications object
class LazyPatentCorpus:
    """ Object to model a collection of patent documents that loads
    each document from file lazily. """

    def __init__(
        self, datasource, classification=[], sample_size=None
    ):
        """ Initialise with a classification of kind ["G", "06"] with
        one to five entries.

        Sample_size randomly samples to a particular
        number if supplied.

        If classification is None or an empty list, select a random
        sample across all classifications."""
        # Need to run a query to get list of filename, name entries

        # Then we can call init_by_filenames
        self.datasource = datasource
        self.filelist = self.datasource.get_records(
            classification, sample_size=sample_size
            )
        return self

    def init_by_filenames(self, datasource, filelist):
        """ Initialise with a list of file references of the format
        (id, filename, name)."""
        self.datasource = datasource
        self.filelist = filelist
        return self

    @property
    def documents(self):
        for doc in self:
            yield doc

    def __iter__(self):
        """ Iterator to return patent documents. """
        for _, filedata in self.datasource.iter_read(self.filelist):
            yield XMLDoc(filedata).to_patentdoc()

    def build_token_dict(self):
        """ Iterate through documents to build a dictionary of tokens. """
        # Unfiltered
        total_token_counter = Counter()
        for doc in self.documents:
            total_token_counter += doc.unfiltered_counter
        self.token_dict = {
            t: i for i, t in enumerate(total_token_counter.keys())
            }
        return self.token_dict, total_token_counter
        # Do we want to filter here and UNK rare tokens

    def docs_to_index(self):
        """ Go through documents replacing tokens with the index in
        the token dictionary."""
        pass

    def save_claims(self, filter_cancelled=True, clean_chars=True):
        """ Save all claim text as a Pickle file."""
        # But be careful because we want indicies to sync
        # May want to delete cancelled claims entirely
        pass

    # This is currently a generator but needs to be an iterator
    def sentences(self, add_claims=False):
        """ Iterate through sentences in the corpus - useable as input
         to gensim's word2vec model.

        if add_claims is set to true, the claims are added as sentences.
        """
        for doc in self.documents:
            try:
                for paragraph in doc.description.paragraphs:
                    for sentence in paragraph.sentences:
                        # yield sentence.filtered_tokens
                        yield sentence.words
                if add_claims:
                    for claim in doc.claimset.claims:
                        yield claim.words
            except:
                logger.error("Error processing doc - {0}".format(doc.title))

    def get_description_text(self):
        """ Return text of all descriptions as one long string. """
        return "\n\n".join([doc.description.text for doc in self.documents])

    def get_claim_text(self):
        """ Return text of all claims as one long string. """
        return "\n\n".join([doc.claimset.text for doc in self.documents])

    def get_statistics(self):
        """ Iterate through documents,compute and statistics."""
        unfiltered_counter = Counter()
        filtered_counter = Counter()
        character_counter = Counter()
        paragraph_count = Counter()
        sentence_count = Counter()
        sentence_dist = Counter()
        for i, doc in enumerate(self.documents):
            try:
                # Sum unfiltered_counter
                unfiltered_counter += doc.unfiltered_counter
                # Sum filtered_counter
                filtered_counter += doc.filtered_counter
                # Sum character_counter
                character_counter += doc.character_counter
                # Count description - paragraph_count (Sum counter for totals)
                paragraph_count[doc.description.paragraph_count] += 1
                # Count description - sentence_count (Sum counter for totals)
                sentence_count[doc.description.sentence_count] += 1
                # Sum sentence_dist
                sentence_dist += doc.description.sentence_dist
                if (i % 500) == 0:
                    status_string = "Processing {0}th document - {1}".format(
                            i,
                            doc.title
                        )
                    logger.info(status_string)
                    print(status_string)
            except:
                logger.error("Error processing doc - {0}".format(i))

        unfiltered_vocabulary = len(unfiltered_counter)
        filtered_vocabulary = len(filtered_counter)
        character_vocabulary = len(character_counter)
        total_paragraphs = sum([k*i for k, i in paragraph_count.items()])
        total_sentences = sum([k*i for k, i in sentence_count.items()])
        print_string = """
            Unfiltered vocabulary = {0}
            Filtered vocabulary = {1}
            Character vocabulary = {2}
            Total Number of Paragraphs = {3}
            Total Number of Sentences = {4}
        """.format(
            unfiltered_vocabulary, filtered_vocabulary, character_vocabulary,
            total_paragraphs, total_sentences
        )
        print(print_string)
        return (
            unfiltered_counter,
            filtered_counter,
            character_counter,
            paragraph_count,
            sentence_count,
            sentence_dist
        )

    # Many introductory tutorials work with a list of words as strings
    def word_list(self, add_claims=True):
        """ Provide a list of all the words in the corpus
        in lowercase and without punctuation.
        If add_claims is true, the claim text is provided as well.
        """
        words = list()
        for _, filedata in self.datasource.iter_read(self.filelist):
            try:
                doc = XMLDoc(filedata).to_patentdoc()
                words += doc.description.bag_of_words(
                                                clean_non_words=True,
                                                clean_stopwords=False,
                                                stem_words=False
                                                )
                if add_claims:
                    words += doc.claimset.bag_of_words(
                                                clean_non_words=True,
                                                clean_stopwords=False,
                                                stem_words=False
                                                )
            except:
                logger.error("Error processing doc - {0}".format(filedata))

        return words

    def save(self, filename=None):
        """ Save details of the patent corpus."""
        logging.info("Saving Lazy Patent Corpus")
        if not filename:
            filename = "{date}-{length}.lzypatcorp".format(
                date=datetime.now().strftime(format="%Y-%m-%d_%H-%M"),
                length=len(self.documents)
            )
        # Save the class name and path of the datasource to allow
        # it to be re-generated?
        ds_params = (ds.__class__.__name__, ds.path)
        params_to_save = (ds_params, self.filelist)
        with open(filename, 'wb') as f:
            pickle.dump(params_to_save, f)

    @classmethod
    def load(cls, filename):
        """ Load a lazy corpus of documents. """
        logging.info("Loading Lazy Patent Corpus")
        with open(filename, 'rb') as f:
            (ds_classname, ds_path), filelist = pickle.load(f)
        # What do we do about the datasource?
        datasource = string_to_class(ds_classname)(ds_path)
        lzy = cls()
        return lzy.init_by_filenames(datasource, filelist)

class CorpusSentenceIterator:
    """ Iterator to return sentences from files in filelist f
    rom datasource. """

    def __init__(self, datasource, filelist, add_claims=False):
        """ Initialise with a datasource and filelist. """
        self.datasource = datasource
        self.filelist = filelist
        self.add_claims = add_claims

    def __iter__(self):
        """ Iterate through files"""
        for _, filedata in self.datasource.iter_read(self.filelist):
            try:
                doc = XMLDoc(filedata).to_patentdoc()
                for paragraph in doc.description.paragraphs:
                    for sentence in paragraph.sentences:
                        # yield sentence.filtered_tokens
                        yield sentence.bag_of_words(
                            clean_non_words=True,
                            clean_stopwords=False,
                            stem_words=False
                        )
                if self.add_claims:
                    for claim in doc.claimset.claims:
                        yield claim.bag_of_words(
                            clean_non_words=True,
                            clean_stopwords=False,
                            stem_words=False
                        )
            except:
                logger.error("Error processing doc - {0}".format(filedata))
