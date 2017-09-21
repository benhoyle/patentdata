# -*- coding: utf-8 -*-
# Library to access EPO OPS
import epo_ops

import os
import pickle
import feedparser

from bs4 import BeautifulSoup

from patentdata.xmlparser import (
    extract_pub_no, get_epodoc
)

PARTIES = ["agent", "applicant", "inventor"]

OA_SET = {
    "communication from the examining division",
    "european search opinion",
    "summons to attend oral proceedings"
}

RESPONSE_SET = {
    (
        "communication regarding possible amendment "
        "of the application/payment of claims fee"
    ),
    "reply to communication from the examining division",
    "amendments received before examination"
}

DOC_RSS_URL = (
    "https://register.epo.org/"
    "rssDocuments?application=EP{0}&proc=EP-PCT&lng=en"
)


class EPORegister:

    def __init__(self, key, secret):
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
            key=key,
            secret=secret,
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

    def get_status(self, appln_no):
        """ Get the status of a EP patent application. """

        if "." in appln_no:
            appln_no = appln_no.split(".")[0]

        response = self.registered_client.register(
            reference_type='application',
            input=epo_ops.models.Epodoc("EP{0}".format(appln_no)),
            constituents=['biblio']
            )
        soup = BeautifulSoup(response.text, "xml")
        return soup.find(
                "ep-patent-statuses"
            ).find_all('ep-patent-status')[0].text

    def count_prosecution(self, appln_no):
        """ Count prosecution events given an EP application."""
        # Strip checkdigit
        if "." in appln_no:
            appln_no = appln_no.split(".")[0]

        feed_url = DOC_RSS_URL.format(appln_no)
        d = feedparser.parse(feed_url)
        entries = [
            {
                'title': entry['title'],
                'date': entry['published'],
                'stage': entry['epr_procedure']
            } for entry in d['entries']
        ]
        count = dict()
        count['oa'] = 0
        count['response'] = 0
        for entry in entries:
            if entry['title'].split(": ")[1].lower() in OA_SET:
                count['oa'] += 1
            if entry['title'].split(": ")[1].lower() in RESPONSE_SET:
                count['response'] += 1
        return count

    def get_prosecution_data(self, appln_no, cache=True):
        """ Get statistics and status of EP prosecution.
        Plus save responses for later if cache = True. """

        if not cache:
            count = self.count_prosecution(appln_no)
            count['status'] = self.get_status(appln_no)
            return count

        if cache:
            # Strip checkdigit
            if "." in appln_no:
                appln_no = appln_no.split(".")[0]

            feed_file = "temp/{0}_feed.pkl".format(appln_no)
            if os.path.isfile(feed_file):
                with open(feed_file, 'rb') as f:
                    d = pickle.load(f)
            else:
                feed_url = DOC_RSS_URL.format(appln_no)
                d = feedparser.parse(feed_url)
                with open(feed_file, 'wb') as f:
                    pickle.dump(d, f)

            entries = [
                {
                    'title': entry['title'],
                    'date': entry['published'],
                    'stage': entry['epr_procedure']
                } for entry in d['entries']
            ]
            count = dict()
            count['oa'] = 0
            count['response'] = 0
            for entry in entries:
                if entry['title'].split(": ")[1].lower() in OA_SET:
                    count['oa'] += 1
                if entry['title'].split(": ")[1].lower() in RESPONSE_SET:
                    count['response'] += 1

            register_file = "temp/{0}_reg.pkl".format(appln_no)
            if os.path.isfile(register_file):
                with open(register_file, 'rb') as f:
                    response = pickle.load(f)
            else:
                response = self.registered_client.register(
                    reference_type='application',
                    input=epo_ops.models.Epodoc("EP{0}".format(appln_no)),
                    constituents=['biblio']
                ).text
                with open(register_file, 'wb') as f:
                    pickle.dump(response, f)
            soup = BeautifulSoup(response, "xml")
            count['status'] = soup.find(
                    "ep-patent-statuses"
                ).find_all('ep-patent-status')[0].text

            return count
