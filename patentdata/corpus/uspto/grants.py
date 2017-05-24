# -*- coding: utf-8 -*-

from patentdata.corpus.baseclasses import LocalDataSource
import patentdata.utils as utils
from patentdata.xmlparser import XMLDoc

import zipfile
import os
import sqlite3


def separated_xml(zip_file):
    """ Generator to separate a large XML file with concatenated
    <us-patent-grant></us-patent-grant> root nodes. """
    # Extract first file name from zip file, which = xml file
    xml_file = zip_file.namelist()[0]
    with zip_file.open(xml_file, 'r') as open_xml_file:
        # open_xml_file is a binary file object - hence lines are bytes
        data_buffer = [open_xml_file.readline()]
        for line in open_xml_file:
            if line.startswith(b'<?xml '):
                yield b''.join(data_buffer)
                data_buffer = []
            data_buffer.append(line)
        yield b''.join(data_buffer)


def separated_xml_with_lines(zip_file):
    """ Generator to separate a large XML file with concatenated
    <us-patent-grant></us-patent-grant> root nodes. """
    # Extract first file name from zip file, which = xml file
    xml_file = zip_file.namelist()[0]
    with zip_file.open(xml_file, 'r') as open_xml_file:
        # open_xml_file is a binary file object - hence lines are bytes
        data_buffer = [open_xml_file.readline()]
        # Initialise a buffer to store the current start line offset
        start_offset = 0

        for line_no, line in enumerate(open_xml_file, start=1):
            # If line is a new XML declaration
            if line.startswith(b'<?xml '):

                # return start offset, end offeset, data
                yield start_offset, line_no, b''.join(data_buffer)
                # Reset data buffer
                data_buffer = []
                # Increment start to previous end
                start_offset = line_no + 1
            # If line is not a new XML declaration
            data_buffer.append(line)

        yield start_offset, line_no, b''.join(data_buffer)


def get_xml_by_line_offset(zip_file, start_offset):
    """ Retrieve XML data from zip_file based on a starting byte offset. """
    xml_file = zip_file.namelist()[0]
    with zip_file.open(xml_file, 'r') as open_xml_file:
        for line_no, line in enumerate(open_xml_file):
            if line_no < start_offset:
                continue
            elif line_no == start_offset:
                data_buffer = [line]
            elif line_no >= start_offset:
                if line.startswith(b'<?xml '):
                    return b''.join(data_buffer)
                else:
                    data_buffer.append(line)
        return b''.join(data_buffer)


class USGrants(LocalDataSource):
    """ Model for US granted patent data. """

    def __init__(self, path):
        """ Object initialisation. """

        self.exten = (".zip", ".tar")
        self.path = path
        if not os.path.isdir(path):
            print("Invalid path")
            # Raise custom exception here
            return
        self.first_level_files = utils.get_files(self.path, self.exten)

        # Connect to DB to store file data
        self.conn = sqlite3.connect(os.path.join(self.path, 'fileindexes.db'))
        self.c = self.conn.cursor()
        # Create indexes table if it doesn't exist
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS files
                (
                    pub_no TEXT,
                    countrycode TEXT,
                    year NUMBER,
                    number NUMBER,
                    kindcode TEXT,
                    filename TEXT,
                    start_offset NUMBER,
                    section TEXT,
                    class TEXT,
                    subclass TEXT,
                    maingroup TEXT,
                    subgroup TEXT,
                    UNIQUE (pub_no)
                )
                ''')
        self.conn.commit()

    def __del__(self):
        self.conn.close()

    def read_archive_file(self, filename):
        """ Read large XML file from Zip.

            Returns individual documents from file
        """
        with zipfile.ZipFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
            for sl, el, filedata in separated_xml_with_lines(z):
                yield sl, el, XMLDoc(filedata)

    def read_by_offset(self, filename, offset):
        """ Get XML from zip file with filename starting at line offset. """
        with zipfile.ZipFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
            return XMLDoc(get_xml_by_line_offset(z, offset))

    def index(self):
        """ Generate metadata for individual publications. """

        print("Getting archive file list - may take a while!\n")
        # set query string for later
        query_string = (
                            'INSERT OR IGNORE INTO files'
                            ' (pub_no, countrycode, year, number, '
                            'kindcode, filename, start_offset, '
                            'section, class, subclass, maingroup,'
                            'subgroup) '
                            'VALUES ({0})').format(",".join("?"*12))

        # Iterate through subdirs as so?
        for subdirectory in utils.get_immediate_subdirectories(self.path):
            print("Generating list for: {0}".format(subdirectory))
            filtered_files = [
                f for f in self.first_level_files
                if subdirectory in os.path.split(f) and "SUPP" not in f
            ]
            for filename in filtered_files:
                print("Processing file: {0}".format(filename))
                params = []
                i = 0
                for sl, el, xml_doc in self.read_archive_file(filename):
                    # Use XMLDoc publication_details() to get
                    # publication number and other details
                    # May as well get classifications here as well
                    # May need to skip D, P and RE publications
                    pub_details = xml_doc.publication_details()
                    classifications = xml_doc.classifications()
                    if pub_details:
                        data = [
                                    pub_details['full_number'],
                                    'US',
                                    pub_details['date'].year,
                                    pub_details['short_number'],
                                    pub_details['kind'],
                                    filename,
                                    sl
                                ]
                        if classifications:
                            data += classifications[0]
                        else:
                            data += [None, None, None, None, None]
                        params.append(data)

                    if (len(params) % 1000) == 0:
                        i += 1000
                        self.c.executemany(query_string, params)
                        self.conn.commit()

    def get_patentdoc(self, publication_number):
        """ Return a Patent Doc object corresponding
        to a publication number. """
        pass

    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Return a generator that provides Patent Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size"""
        pass
