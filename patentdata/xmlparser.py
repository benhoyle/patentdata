# Import Beautiful Soup for XML parsing
from bs4 import BeautifulSoup
from datetime import datetime
import logging

from patentdata.utils import process_classification

from patentdata.models import (
                                Paragraph, Description, Claim,
                                Claimset, PatentDoc
                            )

logging.basicConfig(
    filename="processing_class.log",
    format='%(asctime)s %(message)s'
)

class XMLDoc():
    """ Object to wrap the XML for a US Patent Document. """

    def __init__(self, filedata, claimdata=None):
        """ Initialise object using either disk file data or HTML
        response data. """
        try:
            self.soup = BeautifulSoup(filedata, "xml")
            if not self.soup:
                print("No soup object")
            if claimdata:
                claimsoup = BeautifulSoup(claimdata, "xml")
                # Try to convert <claim-text>....into <claim>
                # Maybe check if one large <claim> containing all claims
                # or several <claim> per claim
                claimsoup.claim.name = "claimset"
                for claimtag in claimsoup.find_all("claim-text"):
                    claimtag.name = "claim"
                self.soup.append(claimsoup.claimset)
        except:
            print("Error could not read file")
            raise

    def description_text(self):
        """ Return extracted description text."""
        paras = self.soup.find_all(["p", "paragraph"])
        return "\n".join([p.text for p in paras])

    def paragraph_list(self):
        """ Get list of paragraphs and numbers. """
        def safe_extract_number(p):
            try:
                return int(p.attrs.get('id', "").split('-')[1])
            except:
                return 0

        def safe_abstract_check(p):
            """ Returns true if not abstract or no "A" prefix ids."""
            try:
                return p.attrs.get('id', ' - ').split('-')[0] != "A"
            except:
                return True

        paras = self.soup.find_all(["p", "paragraph"])
        return [{
            "text": p.text,
            "number": safe_extract_number(p)
            }
            for p in paras if safe_abstract_check(p)]

    def claim_text(self):
        """ Return extracted claim text."""
        # EPO uses claim to cover the whole set of claims whereas US
        # uses it to cover just a single claim
        claims = self.soup.find_all(["claim"])
        return "\n".join([c.text for c in claims])

    def claim_list(self):
        """ Return list of claims. """

        def get_dependency(claim):
            """ Sub function to get a dependency of a claim from
            xml if exists. """
            try:
                dependency = int(
                    claim.find("dependent-claim-reference")
                    .attrs['depends_on'].split('-')[1]
                )
            except AttributeError:
                try:
                    dependency = int(
                        claim.find("claim-ref")
                        .attrs['idref'].split('-')[1]
                    )
                except AttributeError:
                    dependency = 0
            return dependency

        def get_number(claim):
            """ Sub function to get number of a claim from XML if exists. """
            try:
                return int(claim.attrs['id'].split('-')[1])
            except:
                return 0

        claims = self.soup.find_all(["claim"])
        # Can use claim-ref idref="CLM-00001" tag to check dependency
        # or dependent-claim-reference depends_on="CLM-00011"
        # Can use claim id="CLM-00001" to check number
        return [{
                'text': claim.text,
                'number': get_number(claim),
                'dependency': get_dependency(claim)
                } for claim in claims]

    def publication_details(self):
        """ Return US publication details. """
        try:
            # do we need to look for <publication-reference> first?
            pub_section = self.soup.find("document-id")
            pub_number = pub_section.find("doc-number").text
            # US grants in 2010 has "kind"
            pub_kind = pub_section.find(["kind", "kind-code"]).text
            pub_date = datetime.strptime(
                pub_section.find(["date", "document-date"]).text,
                "%Y%m%d")
            return {
                        'full_number': "US" + pub_number + pub_kind,
                        'date': pub_date,
                        'short_number': pub_number,
                        'kind': pub_kind
                    }
        except AttributeError:
            return None

    def title(self):
        """ Return title. """
        try:
            return self.soup.find(
                ["invention-title", "title-of-invention"]
            ).text
        except:
            return None

    def all_text(self):
        """ Return description and claim text. """
        desc = self.description_text()
        claims = self.claim_text()
        return "\n".join([desc, claims])

    def classifications(self):
        """ Return IPC classification(s). """
        # Need to adapt - up to 2001 uses string under tag 'ipc'
        # Post 2009
        class_list = list()
        class_tags = self.soup.find_all("classification-ipcr")
        if class_tags:
            class_list = [
                [
                    each_class.find("section").text,
                    each_class.find("class").text,
                    each_class.find("subclass").text,
                    each_class.find("main-group").text,
                    each_class.find("subgroup").text
                ]
                for each_class in class_tags
            ]

        if class_list:
            return class_list
        # Pre 2009
        else:
            # Use function from patentdata on text of ipc tag
            try:
                class_list = process_classification(
                    self.soup.find("ipc").text
                )
                return class_list
            except:
                # 2005 has 'classification-ipc' - 'main-classification'
                try:
                    class_list = process_classification(
                        self.soup.find("classification-ipc").find(
                            "main-classification"
                        ).text
                    )
                    return class_list
                except:
                    logging.exception(
                        "Exception opening file: {0}".format(
                        self.publication_details()
                        )
                    )
                    return []


    def to_patentdoc(self):
        """ Return a patent doc object. """

        paragraphs = [Paragraph(**p) for p in self.paragraph_list()]
        description = Description(paragraphs)
        claims = [Claim(**c) for c in self.claim_list()]
        claimset = Claimset(claims)
        number = self.publication_details()
        if number:
            number = number['full_number']
        return PatentDoc(
            claimset,
            description,
            title=self.title(),
            classifications=self.classifications(),
            number = number
            )


class XMLRegisterData():
    """ Wrapper for Register XML Data. """
    def __init__(self, data):
        """ Initialise object using either disk file data or HTML
        response data. """
        try:
            self.soup = BeautifulSoup(data, "xml")
        except:
            print("Error could not read file")
            raise

    def get_publication_no(self, countrycode="EP"):
        """
        Search for the publication number.

        :param countrycode: two-letter code identifying country.
        :type countrycode: str
        :return: publication number as string with countrycode
        """
        pub_no = None
        for tag in self.soup.find_all("publication-reference"):
            if tag.find("country").text == countrycode:
                pub_no = tag.find("doc-number").text
        if pub_no:
            return "".join([countrycode, pub_no])
        else:
            return None

    def get_citations(self):
        """
        Search for citations and return in a friendly format.
        """
        citations = []
        try:
            xml_citations = self.soup.find(
                "references-cited"
                ).find_all("citation")
            for xml_citation in xml_citations:
                try:
                    result = get_epodoc_from_soup(xml_citation)
                    result['category'] = xml_citation.find("category").text
                    citations.append(result)
                except:
                    pass
        except:
            pass
        return citations


def get_epodoc_from_soup(soup):
    """ Get epodoc details from passed soup object. """

    epodoc_entry = soup.find(
                    attrs={'document-id-type': "epodoc"}
                )
    epodoc_number = epodoc_entry.find("doc-number").text
    epodoc_date = epodoc_entry.find("date").text
    return {
        'number': epodoc_number,
        'date': epodoc_date
        }


def extract_pub_no(response):
    """ Extract publication numbers from a response."""
    soup = BeautifulSoup(response, "xml")
    try:
        return get_epodoc_from_soup(soup.find("publication-reference"))
    except:
        return None


def get_epodoc(response):
    """ Get the epodoc number from response data. """
    soup = BeautifulSoup(response, "xml")
    try:
        return get_epodoc_from_soup(soup)['number']
    except:
        return None
