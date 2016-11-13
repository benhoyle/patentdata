# -*- coding: utf-8 -*-

# == IMPORTS =============================================================#
import os
import logging
import re
import math
import random
# Use pickle for saving
import pickle

# Import abstract class functions
from abc import ABCMeta, abstractmethod

#Libraries for Zip file processing
# Can we use czipfile for faster processing?
import zipfile 
import tarfile
#from zip_open import zopen
from io import BytesIO #Python 3.5

# Import Beautiful Soup for XML parsing
from bs4 import BeautifulSoup

import utils

from datetime import datetime

# Import models for a patent document
from models import corpus_models as m

# EPOOPSCorpus imports
import configparser
import epo_ops
# == IMPORTS END =========================================================#

# Configure logging
logging.basicConfig(filename="processing_class.log", format='%(asctime)s %(message)s')

class BasePatentDataSource(metaclass=ABCMeta):
	""" Abstract class for patent data sources. """
	@abstractmethod
	def get_patentdoc(self, publication_number):
		""" Return a Patent Doc object corresponding to a publication number. """
		pass
		
	@abstractmethod
	def patentdoc_generator(self, publication_numbers=None, sample_size=None):
		""" Return a generator that provides Patent Doc objects. 
		publication_numbers is a list or iterator that provides a 
		limiting group of publication numbers.
		sample_size limits results to a random sample of size sample_size"""
		pass
	
	
class USPublications(BasePatentDataSource):
    """Creates a new corpus object that simplifies processing of patent archive"""
    def __init__(self, path="/media/SAMSUNG/Patent_Downloads"):
        
        self.exten = (".zip",".tar")
        self.path = path
        if not os.path.isdir(path):
            print("Invalid path")
            # Raise custom exception here
            return
        # Set regular expression for valid patent publication files
        self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
        self.PUB_FORMAT = re.compile(r"(\w\w)(\d{4})(\d{7})([A,B]\d)")
        # Get upper level zip/tar files in path
        self.first_level_files = utils.get_files(self.path, self.exten)
        
        # Initialise arrays for lower level files - could this be a generator?
        self.archive_file_list = []

    def get_archive_list(self):
        """ Generate a list of lower level archive files. """
            
        try:
            # Look for pre-existing list in file directory - won't work for Patent_Downloads directory
            self.archive_file_list = pickle.load(open(os.path.join(self.path, "archive_list.p"), "rb"))
            #print("Loading pre-existing file list\n")
        except:
            # If not file exists generate list
            print("Getting archive file list - may take a few minutes\n")
            # Iterate through subdirs as so?
            #for subdirectory in utils.get_immediate_subdirectories(self.path):
            self.archive_file_list = [
                (filename, name) 
                for filename in self.first_level_files 
                for name in self.get_archive_names(filename) if self.correct_file(name) ]
            #Save archive list in path as pickle - this didn't work for the whole directory - gave memory error
            pickle.dump( self.archive_file_list, open( os.path.join(self.path, "archive_list.p"), "wb" ) )
                
    
    def get_archive_names(self, filename):
        """ Return names of files within archive having filename. """
        try:
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(os.path.join(self.path, filename), "r") as z:
                    names = z.namelist()
            elif filename.lower().endswith(".tar"):
                with tarfile.TarFile(os.path.join(self.path, filename), "r") as t:
                    names = t.getnames()           
        except Exception:
            logging.exception("Exception opening file:" + str(os.path.join(self.path, filename)))
            names = []
        return names
    
    def read_archive_file(self, filename, name):
        """ Read file data for XML_path nested within name archive within filename archive. """
        # Get xml file path from name
        file_name_section = name.rsplit('/',1)[1].split('.')[0]
        XML_path = file_name_section + '/' + file_name_section + ".XML"
       
        try:
            # For zip files
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(os.path.join(self.path, filename), 'r') as z:
                    with z.open(name, 'r') as z2:
                        z2_filedata = BytesIO(z2.read())
                        with zipfile.ZipFile(z2_filedata,'r') as nested_zip:
                            with nested_zip.open(XML_path, 'r') as xml_file:
                                filedata = xml_file.read()
            
            # For tar files
            elif filename.lower().endswith(".tar"):
                with tarfile.TarFile(os.path.join(self.path, filename), 'r') as z:
                    z2 = z.extractfile(name)
                    with zipfile.ZipFile(z2) as nested_zip:
                        with nested_zip.open(XML_path) as xml_file:
                            filedata = xml_file.read()
        except:
            logging.exception("Exception opening file:" + str(XML_path))
            filedata = None
        
        return filedata
    
    def correct_file(self, name):
        """ Checks whether nested file 'name' is of correct type."""
        if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name):
            return True
        else:
            return False
    # Function below takes about 1.5s to return each patent document 
    # > 5 days to parse one year's collection
    def iter_xml(self):
        """ Generator for xml file in corpus. """
        for filename in self.first_level_files:
            names = self.get_archive_names(filename)
            for name in names:
                if self.correct_file(name):
                    filedata = self.read_archive_file(filename, name)     
                    if filedata:
                        yield XMLDoc(filedata)
    
    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Generator to return Patent Doc objects. """
        # If no list of publication is passed iterate through whole datasource
        if not publication_numbers:
            gen_xml = self.iter_xml()
            for xmldoc in gen_xml:
                yield xmldoc.to_patentdoc()
        else:
            if sample_size and len(publication_numbers) > sample_size:
                # Randomly sample down to sample_size
                publication_numbers = random.sample(publication_numbers, sample_size)
            for publication_number in publication_numbers:
                yield self.get_patentdoc(publication_number)
    
    def iter_filter_xml(self, class_list):
        """ Generator to return xml that matches the classifications in 
        class_list. """
        for filename in self.first_level_files:
            names = self.get_archive_names(filename)
            for name in names:
                if self.correct_file(name):
                    filedata = self.read_archive_file(filename, name)     
                    if filedata:
                        soup_object = XMLDoc(filedata)
                        match = False
                        for c in soup_object.classifications():
                            if c.match(class_list):
                                match = True
                        if match:
                            yield soup_object
    
    # Use publication numbers rather than file indices in the methods below?
    
    def read_xml(self, a_file_index):
        """ Read XML from a particular zip file (second_level_zip_file)
        that is nested within a first zip file (first_level_zip_file) 
        param: int a_file_index - an index to a file within archive_file_list"""
        filename, name = self.archive_file_list[a_file_index]
        return self.read_archive_file(filename, name)

    def get_doc(self, a_file_index):
        """ Read XML and return an XMLDoc object. """
        if not self.archive_file_list:
            self.get_archive_list()
        return XMLDoc(self.read_xml(a_file_index))

    def search_archive_list(self, publication_number):
        """ Get filename and name for a given publication number."""
        if not self.archive_file_list:
            self.get_archive_list()
        filename, name = None, None
        for f, n in self.archive_file_list:
            if publication_number in n:
                filename, name = f, n
        return filename, name
    
    def search_files(self, publication_number):
        """ Return upper and lower level paths for publication. """
        for f in self.first_level_files:
            names = self.get_archive_names(f)
            # Look at last file 
            
            # Set is much quicker than list 
    
    
    def get_patentdoc(self, publication_number):
        """ Return a PatentDoc object for a given publication number."""
        # Parse publication number - get year
        
        # Use year to get suitable first_level_files
        
        filename, name = self.search_archive_list(publication_number)
        if filename and name:
            return XMLDoc(self.read_archive_file(filename, name)).to_patentdoc()
    
    def save(self):
        """ Save corpus object as pickle. """
        filename = self.path.replace("/","_") + ".p"
        pickle.dump( self, open( "savedata/" + filename, "wb" ) )
        
    @classmethod
    def load(cls, filename):
        """ Load a corpus by filename. """
        return pickle.load(open(filename, "rb"))
        
    def indexes_by_classification(self, class_list):
        """ Get a list of indexes of publications that match the supplied 
        class list.
        param: list of Classification objects - class_list"""
        #If there is a pre-existing search save file, start from last recorded index
        try:
            with open(os.path.join(self.path, "-".join([c.as_string() for c in class_list]) + ".data"), "r") as f:
                last_index = int(f.readlines()[-1].split(',')[0])+1
        except:
            last_index = 0
            
        if not self.archive_file_list:
            self.get_archive_list()
        # Iterate through publications
        matching_indexes = []
        
        for i in range(last_index, len(self.archive_file_list)):
            
            try:
                classifications = self.get_doc(i).classifications()
                # Look for matches with class_list entries bearing in mind None = ignore
                match = False
                for c in classifications:
                    if c.match(class_list):
                        match = True
                if match:
                    print("Match: ",str(i))
                    matching_indexes.append(i)
                    with open(os.path.join(self.path, "-".join([c.as_string() for c in class_list]) + ".data"), "a") as f:
                        print(i, end=",\n", file=f)
            except:
                print("Error with: ", self.archive_file_list[i][1])
        
        pickle.dump( matching_indexes, open( os.path.join(self.path, "-".join([c.as_string() for c in class_list]) + ".p"), "wb" ) )
        return matching_indexes

    def get_filtered_docs(self):
        """ Generator to return XMLDocs for matching indexes. """
        pass
    
    def get_indexes(self, filename):
        """ Load an index set from a passed filename in the corpus path. """
        with open(os.path.join(self.path,filename), 'r') as f:
            lines = f.readlines()
        return [int(line.split(',')[0]) for line in lines]

    def get_patentcorpus(self, indexes, number_of_docs):
        """ Get a random sample of documents having a total number_of_docs."""
        """ Indexes is a list of relevant patent indexes. """
        if len(indexes) > number_of_docs:
            indexes = random.sample(indexes, number_of_docs)
        return m.PatentCorpus([self.get_doc(i).to_patentdoc() for i in indexes])

# Have corpus to represent EPO OPS? and US API?
class EPOOPS(BasePatentDataSource):
    def __init__(self, path_to_config=None):
        # Load Key and Secret from config file called "config.ini" 
        # If path is none look in data dir of current directory
        if path_to_config == None:
            path_to_config = os.path.abspath(os.getcwd() + '/data/config.ini')
        parser = configparser.ConfigParser()
        parser.read(path_to_config)
        consumer_key = parser.get('Login Parameters', 'C_KEY')
        consumer_secret = parser.get('Login Parameters', 'C_SECRET')
        # Intialise EPO OPS client
        # Load Dogpile if it exists - if not just use Throttler
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
            key=consumer_key, 
            secret=consumer_secret, 
            accept_type='xml',
            middlewares=middlewares)
    
    def get_doc(self, publication_number):
        """ Get XML for publication number. """
        try:
            description = self.registered_client.published_data(
                reference_type='publication',
                input = epo_ops.models.Epodoc(publication_number),
                endpoint = 'description').text
            claims = self.registered_client.published_data(
                reference_type='publication',
                input = epo_ops.models.Epodoc(publication_number),
                endpoint = 'claims').text
        except:
            print("Full text document not available")
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
                publication_numbers = random.sample(publication_numbers, sample_size)
            
            for publication_number in publication_numbers:
                yield self.get_patentdoc(publication_number)

class XMLDoc():
    """ Object to wrap the XML for a US Patent Document. """
    
    def __init__(self, filedata, claimdata=None):
        """ Initialise object using either disk file data or HTML response data. """
        try:
            self.soup = BeautifulSoup(filedata, "xml")
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
            "text":p.text, 
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
            """ Sub function to get a dependency of a claim from xml if exists. """
            try:
                dependency = int(claim.find("dependent-claim-reference").attrs['depends_on'].split('-')[1])
            except AttributeError:
                try:
                    dependency = int(claim.find("claim-ref").attrs['idref'].split('-')[1])
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
                'text':claim.text, 
                'number': get_number(claim),
                'dependency': get_dependency(claim)
                } for claim in claims]
    
    def publication_details(self):
        """ Return US publication details. """
        try:
            pub_section = self.soup.find("document-id")
            pub_number = pub_section.find("doc-number").text
            pub_kind = pub_section.find("kind-code").text
            pub_date = datetime.strptime(
                pub_section.find("document-date").text,
                "%Y%m%d")
            return (pub_number, pub_kind, pub_date)
        except AttributeError:
            return None
    
    def title(self):
        """ Return title. """
        try:
            return self.soup.find(["invention-title", "title-of-invention"]).text
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
        #Post 2009
        class_list = [
            m.Classification(
                each_class.find("section").text, 
                each_class.find("class").text,
                each_class.find("subclass").text,
                each_class.find("main-group").text,
                each_class.find("subgroup").text)
        for each_class in self.soup.find_all("classifications-ipcr")]
        # Pre 2009
        if not class_list:
            # Use function from patentdata on text of ipc tag
            class_list = m.Classification.process_classification(self.soup.find("ipc").text)
        return class_list
        
    def to_patentdoc(self):
        """ Return a patent doc object. """
        paragraphs = [m.Paragraph(**p) for p in self.paragraph_list()]
        description = m.Description(paragraphs)
        claims = [m.Claim(**c) for c in self.claim_list()]
        claimset = m.Claimset(claims)
        return m.PatentDoc(description, claimset, title=self.title())
    




