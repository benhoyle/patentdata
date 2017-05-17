# -*- coding: utf-8 -*-
from patentdata.models.specification import PatentDoc

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

    def add_documnet(document):
        """ Add a document to the corpus.

        :param document: patent documents
        :type document: PatentDoc
        :return: PatentCorpus object

        """
        if not isinstance(document, PatentDoc):
                raise ValueError("Input must be a list of PatentDoc objects")
        self.documents.append(document)
        return self

