# -*- coding: utf-8 -*-
# Define this as a Flask Extension?
# See - http://flask.pocoo.org/docs/0.12/extensiondev/
# Library to access EPO OPS
import epo_ops

# EPOOPSCorpus imports
from patentdata.corpus.baseclasses import BasePatentDataSource

from patentdata.xmlparser import (
    XMLDoc, XMLRegisterData, get_epodoc, extract_pub_no
)

import random
import warnings


class EPOOPS(BasePatentDataSource):
    def __init__(self, EPOOPS_C_KEY, EPOOPS_SECRET_KEY):
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
        :type texttype: str
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

    def get_description(
        self, number, numbertype='publication', countrycode=None
    ):
        """ Get XML for description.

        :param number: publication or application number
        :type number: str
        :param numbertype: either "publication" or "application".
        :type texttype: str
        :param countrycode: two letter string with countrycode
        :type countrycode: str
        :return: response data as string
        """
        if numbertype == 'application':
            if not countrycode:
                raise ValueError("""Please enter a country code with
                    an application number""")
            epodoc_pub_no = self.get_publication_no(number, countrycode)
            if not epodoc_pub_no:
                warnings.warn("No publication number found.")
                return None
            else:
                number = epodoc_pub_no.number
        return self._get_text('description', number)

    def get_claims(
        self, number, numbertype='publication', countrycode=None
    ):
        """ Get XML for claims.

        :param number: publication or application number
        :type number: str
        :param numbertype: either "publication" or "application".
        :type texttype: str
        :param countrycode: two letter string with countrycode
        :type countrycode: str
        :return: response data as string
        """
        if numbertype == 'application':
            if not countrycode:
                raise ValueError("""Please enter a country code with
                    an application number""")
            epodoc_pub_no = self.get_publication_no(number, countrycode)
            if not epodoc_pub_no:
                warnings.warn("No publication number found.")
                return None
            else:
                number = epodoc_pub_no.number
        return self._get_text('claims', number)

    def get_citations(
        self, number, numbertype='publication', countrycode=None
    ):
        """ Get citations for a patent application from EPO.

        :param number: publication or application number
        :type number: str
        :param numbertype: either "publication" or "application".
        :type texttype: str
        :param countrycode: two letter string with countrycode
        :type countrycode: str
        :return: response data as string
        """
        if numbertype == 'application':
            if not countrycode:
                raise ValueError("""Please enter a country code with
                    an application number""")
            epodoc_pub_no = self.get_publication_no(number, countrycode)
            if not epodoc_pub_no:
                warnings.warn("No publication number found.")
                return None
            else:
                epodoc_number = epodoc_pub_no
        else:
            epodoc_number = epo_ops.models.Epodoc(number)

        biblio_data = self.registered_client.published_data(
                reference_type='publication',
                input=epodoc_number,
                endpoint='biblio'
                ).text
        return XMLRegisterData(biblio_data).get_citations()

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

    def convert_number(self, application_number, countrycode):
        """ Get a Epodoc number for the application. """
        # Use the convert number with original number
        # reference_type='application'
        appln_no = epo_ops.models.Original(
            application_number,
            countrycode
        )
        output_format = 'epodoc'
        doc_no = self.registered_client.number(
                'application',
                appln_no,
                output_format
            ).text
        parsed_doc_no = get_epodoc(doc_no)
        return parsed_doc_no

    def get_publication_no(self, application_number, countrycode):
        """ Get publication numbers for an application.

        :param application_no: appln. number in original or Epodoc format
        :type application_no: str
        :param countrycode: two letter string with countrycode
        :type countrycode: str
        :return: Epodoc object
        """
        # Convert number to a publication number
        try:
            # Assume number is passed as Epodoc
            biblio_data = self.registered_client.published_data(
                reference_type='application',
                input=epo_ops.models.Epodoc(application_number),
                endpoint='biblio'
                ).text

            pub_details = extract_pub_no(biblio_data)
            return epo_ops.models.Epodoc(
                pub_details['number'],
                date=pub_details['date']
                )
        except Exception as e:
            if "404" in e.args[0]:
                # Try to convert number to Epodoc first
                try:
                    epo_doc_no = self.convert_number(
                        application_number,
                        countrycode
                        )
                    biblio_data = self.registered_client.published_data(
                        reference_type='application',
                        input=epo_ops.models.Epodoc(epo_doc_no),
                        endpoint='biblio'
                        ).text

                    pub_details = extract_pub_no(biblio_data)
                    return epo_ops.models.Epodoc(
                        pub_details['number'],
                        date=pub_details['date']
                    )
                except Exception as e:
                    return None
            else:
                return None



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
