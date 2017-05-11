# -*- coding: utf-8 -*-

# == IMPORTS ==========================================================#
import os
import logging
import re
import math
import random
# Use pickle for saving
import pickle

from patentdata.corpus.baseclasses import BasePatentDataSource

# Libraries for Zip file processing
# Can we use czipfile for faster processing?
import zipfile
import tarfile
# from zip_open import zopen
# Python 3.5
from io import BytesIO

import patentdata.utils as utils

import sqlite3

from datetime import datetime

from patentdata.xmlparser import XMLDoc

# == IMPORTS END ======================================================#

# Configure logging
logging.basicConfig(
    filename="processing_class.log",
    format='%(asctime)s %(message)s'
)


class USPublications(BasePatentDataSource):
    """
    Creates a new corpus object that simplifies processing of
    patent archive
    """
    def __init__(self, path="/media/SAMSUNG/Patent_Downloads"):

        self.exten = (".zip", ".tar")
        self.path = path
        if not os.path.isdir(path):
            print("Invalid path")
            # Raise custom exception here
            return
        # Set regular expression for valid patent publication files
        self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
        self.PUB_FORMAT = re.compile(r"(\w\w)(\d{4})(\d{7})")
        # Get upper level zip/tar files in path
        self.first_level_files = utils.get_files(self.path, self.exten)

        # Initialise arrays for lower level files - could this be a generator?
        self.archive_file_list = {}

        self.conn = sqlite3.connect(os.path.join(self.path, 'fileindexes.db'))
        self.c = self.conn.cursor()
        # Create indexes table if it doesn't exist
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS files
                (
                    pub_no TEXT,
                    year TEXT,
                    filename TEXT,
                    name TEXT,
                    UNIQUE (pub_no)
                )
                ''')
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def get_archive_list(self):
        """ Generate a list of lower level archive files. """

        print("Getting archive file list - may take a few minutes\n")
        # Iterate through subdirs as so? >
        for subdirectory in utils.get_immediate_subdirectories(self.path):
            print("Generating list for :", subdirectory)
            filtered_files = [f for f in self.first_level_files if subdirectory in os.path.split(f) and "SUPP" not in f]
            for filename in filtered_files:
                names = self.get_archive_names(filename)
                for name in names:
                    match = self.PUB_FORMAT.search(name)
                    if match and name.lower().endswith(self.exten):
                        data = (match.group(0), subdirectory, filename, name)
                        self.c.execute('INSERT OR IGNORE INTO files VALUES (?,?,?,?)', data)
                self.conn.commit()

    def get_archive_names(self, filename):
        """ Return names of files within archive having filename. """
        try:
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(
                    os.path.join(self.path, filename), "r"
                ) as z:
                    names = z.namelist()
            elif filename.lower().endswith(".tar"):
                with tarfile.TarFile(
                    os.path.join(self.path, filename), "r"
                ) as t:
                    names = t.getnames()
        except Exception:
            logging.exception(
                "Exception opening file:" +
                str(os.path.join(self.path, filename))
            )
            names = []
        return names

    def process_archive_names(self, names):
        """ Return a dictionary of 'pub_no':'filename' entries. """
        return {
            self.PUB_FORMAT.search(name).group(0):
                name for name in names if self.PUB_FORMAT.search(name)
        }

    def read_archive_file(self, filename, name):
        """ Read file data for XML_path nested
        within name archive within filename archive. """
        # Get xml file path from name
        file_name_section = name.rsplit('/', 1)[1].split('.')[0]
        XML_path = file_name_section + '/' + file_name_section + ".XML"

        try:
            # For zip files
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
                    with z.open(name, 'r') as z2:
                        z2_filedata = BytesIO(z2.read())
                        with zipfile.ZipFile(z2_filedata, 'r') as nested_zip:
                            with nested_zip.open(XML_path, 'r') as xml_file:
                                filedata = xml_file.read()

            # For tar files
            elif filename.lower().endswith(".tar"):
                with tarfile.TarFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
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
        if (
            name.lower().endswith(self.exten) and
            self.FILE_FORMAT_RE.match(name)
        ):
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
            # Add sample size restrictions here
            for xmldoc in gen_xml:
                yield xmldoc.to_patentdoc()
        else:
            if sample_size and len(publication_numbers) > sample_size:
                # Randomly sample down to sample_size
                publication_numbers = random.sample(
                    publication_numbers, sample_size
                )
            for publication_number in publication_numbers:
                result = self.get_patentdoc(publication_number)
                if result:
                    yield result

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
        param: int a_file_index, index to a file within archive_file_list"""
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
        """ Return upper and lower level paths for publication.
            Returns None if no match."""
        self.c.execute('SELECT filename, name FROM files WHERE pub_no=?', publication_number)
        return self.c.fetchone()

    def get_patentdoc(self, publication_number):
        """ Return a PatentDoc object for a given publication number."""
        # Parse publication number - get year

        # Use year to get suitable first_level_files

        # Below uses archive_list
        # filename, name = self.search_archive_list(publication_number)
        # Below does not use archive list
        try:
            filename, name = self.search_files(publication_number)
            if filename and name:
                return XMLDoc(
                    self.read_archive_file(filename, name)
                    ).to_patentdoc()
        except:
            return None

    def save(self):
        """ Save corpus object as pickle. """
        filename = self.path.replace("/", "_") + ".p"
        pickle.dump(self, open("savedata/{0}".format(filename), "wb"))

    @classmethod
    def load(cls, filename):
        """ Load a corpus by filename. """
        return pickle.load(open(filename, "rb"))

    def indexes_by_classification(self, class_list):
        """ Get a list of indexes of publications that match the supplied
        class list.
        param: list of Classification objects - class_list"""
        # If there is a pre-existing search save file,
        # start from last recorded index
        class_list = utils.check_list(class_list)

        try:
            with open(
                os.path.join(self.path, "-".join(
                    [c.as_string() for c in class_list]
                    ) + ".data"), "r"
            ) as f:
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
                # Look for matches with class_list entries, note None = ignore
                match = False
                for c in classifications:
                    if c.match(class_list):
                        match = True
                if match:
                    print("Match: ", str(i))
                    matching_indexes.append(i)
                    with open(
                        os.path.join(
                            self.path,
                            "-".join(
                                [c.as_string() for c in class_list]
                            ) + ".data"
                        ), "a"
                    ) as f:
                        print(i, end=",\n", file=f)
            except:
                print("Error with: ", self.archive_file_list[i][1])

        pickle.dump(
            matching_indexes,
            open(
                os.path.join(
                    self.path,
                    "-".join(
                        [c.as_string() for c in class_list]
                    ) + ".p"
                ), "wb")
        )
        return matching_indexes

    def store_matching_number(self, class_list, filename):
        """ Function that stores the publication numbers of documents
        that have a classification matching the classifications in
        class_list """
        # Get generator for file scan
        gen_xml = self.iter_filter_xml()
        for doc in gen_xml:
            with open(os.path.join(self.path, filename + ".data"), "a") as f:
                print(doc.publication_details(), end=",\n", file=f)

    def get_filtered_docs(self):
        """ Generator to return XMLDocs for matching indexes. """
        pass

    def get_indexes(self, filename):
        """ Load an index set from a passed filename in the corpus path. """
        with open(os.path.join(self.path, filename), 'r') as f:
            lines = f.readlines()
        return [int(line.split(',')[0]) for line in lines]

    def get_patentcorpus(self, indexes, number_of_docs):
        """ Get a random sample of documents having a total number_of_docs."""
        """ Indexes is a list of relevant patent indexes. """
        pass
        """if len(indexes) > number_of_docs:
            indexes = random.sample(indexes, number_of_docs)
        return m.PatentCorpus(
            [self.get_doc(i).to_patentdoc() for i in indexes]
            )"""







