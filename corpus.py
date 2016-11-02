# -*- coding: utf-8 -*-

# == IMPORTS =============================================================#
import os
import logging
import re
import math
# Use pickle for saving
import pickle

#Libraries for Zip file processing
# Can we use czipfile for faster processing?
import zipfile 
import tarfile
#from zip_open import zopen
from io import BytesIO #Python 3.5

# Import Beautiful Soup for XML parsing
from bs4 import BeautifulSoup
# == IMPORTS END =========================================================#

#test_path= "/media/SAMSUNG/Patent_Downloads/2001"

class MyCorpus():
    """Creates a new corpus object that simplifies processing of patent archive"""
    def __init__(self, path="/media/SAMSUNG/Patent_Downloads"):
        logging.basicConfig(filename="processing_class.log", format='%(asctime)s %(message)s')
        self.exten = (".zip",".tar")
        self.path = path
        #Set regular expression for valid patent publication files
        self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
        #Set a list of upper level zip files in the path
        self.first_level_files = [os.path.join(subdir,f) for (subdir, dirs, files) in os.walk(self.path) for f in files if f.lower().endswith(self.exten)]
        #Initialise arrays for lower level files
        self.processed_fl_files = []
        self.archive_file_list = []
        
        #Set English stopwords - in other class?
        #self.stopwords = stopwords.words('english')

    def get_archive_list(self):
        """ Generate a list of lower level archive files. """
        print("Getting archive file list\n")
        for filename in self.first_level_files:
            print(".", end=" ")
            if filename.lower().endswith(".zip"):
                try:
                    #Look to see if we have already processed
                    if filename not in self.processed_fl_files:
                        afl = [(filename, name) for name in zipfile.ZipFile(filename, "r").namelist() if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name)]
                        self.archive_file_list += afl
                        self.processed_fl_files.append(filename)
                except Exception:
                    #Log error
                    logging.exception("Exception opening file:" + str(filename))
            elif filename.lower().endswith(".tar"):
                try:
                    #Look to see if we have already processed
                    if filename not in self.processed_fl_files:
                        #There is no namelist() function in TarFile
                        current_file = tarfile.TarFile(filename, "r")
                        names = current_file.getnames()
                        current_file.close()
                        afl = [(filename, name) for name in names if name.lower().endswith(self.exten) and self.FILE_FORMAT_RE.match(name)]
                        self.archive_file_list += afl
                        self.processed_fl_files.append(filename)
                except Exception:
                    #Log error
                    logging.exception("Exception opening file:" + str(filename))

    def read_xml(self, a_file_index):
        """ Read XML from a particular zip file (second_level_zip_file)
        that is nested within a first zip file (first_level_zip_file) 
        param: int a_file_index - an index to a file within archive_file_list"""
        first_level_a_file, second_level_a_file = self.archive_file_list[a_file_index]
        file_name_section = second_level_a_file.rsplit('/',1)[1].split('.')[0]
        XML_path = file_name_section + '/' + file_name_section + ".XML"
        if first_level_a_file.lower().endswith(".zip"):
            with zipfile.ZipFile(first_level_a_file, 'r') as z:
                with z.open(second_level_a_file, 'r') as z2:
                    z2_filedata = BytesIO(z2.read())
                    #if second_level_a_file.endswith(".zip"): - add here second check for second level tar files
                    with zipfile.ZipFile(z2_filedata,'r') as nested_zip:
                        with nested_zip.open(XML_path, 'r') as xml_file:
                            #xml_tree = parseString(xml_file.read()) 
                            # Return filedata so that we can use other XML libraries
                            filedata = xml_file.read()
                    #elif second_level_a_file.endswith(".tar"): -to add
        elif first_level_a_file.lower().endswith(".tar"):
            with tarfile.TarFile(first_level_a_file, 'r') as z:
                z2 = z.extractfile(second_level_a_file)
                #with z2 as z.extractfile(second_level_a_file):
                #z2_filedata = cStringIO.StringIO(z2.read())
                with zipfile.ZipFile(z2) as nested_zip:
                    with nested_zip.open(XML_path) as xml_file:
                        #xml_tree = parseString(xml_file.read())
                        filedata = xml_file.read()
        return filedata

    def save(self):
        """ Save corpus object as pickle. """
        filename = self.path.replace("/","_") + ".p"
        pickle.dump( self, open( filename, "wb" ) )
        
    @classmethod
    def load(cls, filename):
        """ Load a corpus by filename. """
        return pickle.load(open(filename, "rb"))

class XMLDoc():
    """ Object to wrap the XML for a US Patent Document. """
    
    def __init__(self, filedata):
        """ Initialise object using read file data from read_xml above. """
        try:
            self.soup = BeautifulSoup(filedata, "xml")
        except:
            print("Error could not read file")

    def description_text(self):
        """ Return extracted description text."""
        paras = self.soup.find_all(["p", "paragraph"])
        return "\n".join([p.text for p in paras])
        
    def claim_text(self):
        """ Return extracted claim text."""
        paras = self.soup.find_all(["claim"])
        return "\n".join([p.text for p in paras])
        
    def title(self):
        """ Return title. """
        return self.soup.find("invention-title").text
    
    def all_text(self):
        """ Return description and claim text. """
        desc = self.description_text()
        claims = self.claim_text()
        return "\n".join([desc, claims])



 



