# -*- coding: utf-8 -*-
from collections import Counter

from patentdata.models.specification import PatentDoc
from patentdata.xmlparser import XMLDoc


class PatentCorpus:
    """ Object to model a collection of patent documents. """
    def __init__(self, documents):
        """ Initialise corpus.

        :param documents: list of patent documents
        :type documents: PatentDoc
        :return: PatentCorpus object

        """
        for doc in documents:
            if not isinstance(doc, PatentDoc):
                raise ValueError("Input must be a list of PatentDoc objects")
        self.documents = documents
        return self

    def add_document(self, document):
        """ Add a document to the corpus.

        :param document: patent documents
        :type document: PatentDoc
        :return: PatentCorpus object

        """
        if not isinstance(document, PatentDoc):
            raise ValueError("Input must be a list of PatentDoc objects")
        self.documents.append(document)
        return self

    def char_stats(self):
        """ Provide statistics on characters in corpus."""
        sum_counter = Counter()
        for doc in self.documents:
            sum_counter += Counter(doc)
        print(
            "Documents contain {0} unique characters.".format(len(sum_counter))
            )
        return sum_counter


# May not need this - functionality handled by USPublications object
class LazyPatentCorpus:
    """ Object to model a collection of patent documents that loads
    each document from file lazily. """

    def init_by_id(self, list_of_ids, id_type):
        """ Initialise with a list of ids, where id_type is rowid or
        publication (number)."""
        # Need to run a query to get list of filename, name entries

        # Then we can call init_by_filenames
        pass

    def init_by_classification(self, classification, sample_size=None):
        """ Initialise with a classification of kind ["G", "06"] with
        one to five entries.

        Sample_size randomly samples to a particular
        number if supplied.

        If classification is None or an empty list, select a random
        sample across all classifications."""
        # Need to run a query to get list of filename, name entries

        # Then we can call init_by_filenames
        pass

    def init_by_filenames(self, datasource, filelist):
        """ Initialise with a list of file references of the format
        (id, filename, name)."""
        self.datasource = datasource
        self.filelist = filelist

    @property
    def documents(self):
        for _, filedata in self.datasource.iter_read(self.filelist):
            yield XMLDoc(filedata).to_patentdoc()

    def __iter__(self):
        """ Iterator to return patent documents. """
        # This needs to basically run iter_read(filelist) then
        # wrap the output filedata through XMLDoc(filedata).to_patent
        pass

    def build_token_dict(self):
        """ Iterate through documents to build a dictionary of tokens. """
        # Unfiltered
        total_token_counter = Counter()
        for doc in self.documents:
            total_token_counter += doc.unfiltered_counter
        self.token_dict = {
            t: i for i, t in enumerate(total_token_counter.keys())
            }
        # Do we want to filter here and UNK rare tokens

    def docs_to_index(self):
        """ Go through documents replacing tokens with the index in
        the token dictionary."""
        pass
