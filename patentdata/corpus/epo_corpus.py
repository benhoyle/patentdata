# -*- coding: utf-8 -*-
# Library to access EPO OPS
import epo_ops

# EPOOPSCorpus imports
from patentdata.corpus.baseclasses import BasePatentDataSource
from patentdata.corpus.epo_settings import (
    EPOOPS_C_KEY, EPOOPS_SECRET_KEY
)
from patentdata.xmlparser import XMLDoc, XMLRegisterData

import random
import warnings


class EPOOPS(BasePatentDataSource):
    def __init__(self):
        """
        Intialise EPO OPS client
        Load Dogpile if it exists - if not just use Throttler
        """
        try:
            middlewares = [
                epo_ops.middlewares.Dogpile(),
                epo_ops.middlewares.Throttler(),
            ]
        except:
            middlewares = [
                epo_ops.middlewares.Throttler()
            ]

        self.registered_client = epo_ops.RegisteredClient(
            key=EPOOPS_C_KEY,
            secret=EPOOPS_SECRET_KEY,
            accept_type='xml',
            middlewares=middlewares)

    def _get_text(self, texttype, publication_number):
        """
        Abstract method to get text for both description and claims.

        :param texttype: either "description" or "claims".
        :type txttype: str
        :param publication_number: publication number including countrycode
        :type publication_number: str
        :return: response data as string
        """
        if texttype not in ['description', 'claims']:
            raise TypeError("testtype needs to be 'description' or 'claims'")
        try:
            text = self.registered_client.published_data(
                reference_type='publication',
                input=epo_ops.models.Epodoc(publication_number),
                endpoint=texttype).text
        except:
            # Try to retrieve claims for corresponding PCT application
            try:
                # Get publication number of any corresponding PCT appln.
                register_data = self.registered_client.register(
                    reference_type='publication',
                    input=epo_ops.models.Epodoc(publication_number),
                    constituents=['biblio']).text
                parsed_data = XMLRegisterData(register_data)
                wo_publication_no = parsed_data.get_publication_no("WO")
                if wo_publication_no:
                    text = self.registered_client.published_data(
                        reference_type='publication',
                        input=epo_ops.models.Epodoc(wo_publication_no),
                        endpoint=texttype).text
                else:
                    text = None
            except:
                text = None
        if not text:
            warnings.warn("Error: Not able to retrieve data")
        return text

    def get_description(self, publication_number):
        """ Get XML for description. """
        return self._get_text('description', publication_number)

    def get_claims(self, publication_number):
        """ Get XML for description. """
        return self._get_text('claims', publication_number)

    def get_doc(self, publication_number):
        """ Get XML for publication number. """
        try:
            description = self.registered_client.published_data(
                reference_type='publication',
                input=epo_ops.models.Epodoc(publication_number),
                endpoint='description').text
            claims = self.registered_client.published_data(
                reference_type='publication',
                input=epo_ops.models.Epodoc(publication_number),
                endpoint='claims').text
        except:
            warnings.warn("Full text document not available")
            description = claims = None
        if description and claims:
            return XMLDoc(description, claims)

    def get_patentdoc(self, publication_number):
        """ Get PatentDoc object for publication number. """
        return self.get_doc(publication_number).to_patentdoc()

    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Get generator for PatentDoc objects. """
        if not publication_numbers:
            pass
            # Need to determine set of valid publication numbers and to iterate
        else:
            if sample_size and len(publication_numbers) > sample_size:
                # Randomly sample down to sample_size
                publication_numbers = random.sample(
                    publication_numbers,
                    sample_size
                )

            for publication_number in publication_numbers:
                yield self.get_patentdoc(publication_number)
