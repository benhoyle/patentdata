# -*- coding: utf-8 -*-
# Library to access EPO OPS
import epo_ops

import random
import warnings

from bs4 import BeautifulSoup

PARTIES = ["agent", "applicant", "inventor"]


class EPORegister:
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

        self.registered_client = epo_ops.Client(
            key=EPOOPS_C_KEY,
            secret=EPOOPS_SECRET_KEY,
            accept_type='xml',
            middlewares=middlewares)

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

    def get_party_details(self, number, party, numbertype='publication'):
        """ Return party details for an EP application."""
        if party not in PARTIES:
            raise ValueError("""Please enter a party as one of
                    {0}""".format(PARTIES))

        if numbertype == 'application':
            number = self.get_publication_no(number, "EP")

        response = self.registered_client.register(
            reference_type='publication',
            input=epo_ops.models.Epodoc(number),
            constituents=['biblio']
            )
        soup = BeautifulSoup(response.text, "xml")

        return [
            {
                child.name: child.text
                for child in entry.findChildren()
            }
            for entry in soup.find("{0}s".format(party)).find_all(party)
        ]
