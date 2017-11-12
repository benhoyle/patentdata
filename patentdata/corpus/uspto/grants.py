# -*- coding: utf-8 -*-

from patentdata.corpus.baseclasses import DBIndexDataSource
import patentdata.utils as utils
from patentdata.xmlparser import XMLDoc

import zipfile
import os
import random


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


def get_multiple_xml_by_offset(zip_file, offset_list):
    """ A generator to return XML inside a zip_file
    given a list of offsets. """
    xml_file = zip_file.namelist()[0]
    offset_list.sort()
    # Reverse list so we can pop from end
    offset_list.reverse()
    start_offset = offset_list.pop()
    with zip_file.open(xml_file, 'r') as open_xml_file:

        for line_no, line in enumerate(open_xml_file):
            if line_no < start_offset:
                continue
            elif line_no == start_offset:
                data_buffer = [line]
            elif line_no >= start_offset:
                if line.startswith(b'<?xml '):
                    # Get next offset if offsets
                    if offset_list:
                        start_offset = offset_list.pop()
                        yield b''.join(data_buffer)
                    else:
                        break
                else:
                    data_buffer.append(line)
        yield b''.join(data_buffer)


class USGrants(DBIndexDataSource):
    """ Model for US granted patent data. """

    def __init__(self, path):
        super(USPublications, self).__init__(path)
        self.fieldname = "start_offset"

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
            return get_xml_by_line_offset(z, offset)

    def iter_xml(self):
        """ Generator for xml file in corpus. """
        for filename in self.first_level_files:
            for sl, el, xml_doc in self.read_archive_file(filename):
                yield xml_doc

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
                self.c.executemany(query_string, params)
                self.conn.commit()

    def process_classifications(self):
        self.index()

    def iter_filter_xml(self, classification, sample_size=None):
        """ Generator to return xml that matches has classification.

        :param classification: list in form
        ["G", "61", "K", "039", "00"]. If an entry has None or
        no entry, it and its remaining entries are not filtered.
        """
        records = self.get_records(classification, sample_size)
        filegenerator = self.iter_read(records)
        # Iterate through records and return XMLDocs
        for _, filedata in filegenerator:
            if filedata:
                yield XMLDoc(filedata)

    def filedata_generator(self, filename, entries):
        """ Generator to return file data for each name in entries
        for a given filename. Entries is a list of form (id, start_offset).

        Returns: id, filedata as tuple."""
        # For zip files
        if filename.lower().endswith(".zip"):
            offsets = [o for _, o in entries]
            with zipfile.ZipFile(
                os.path.join(self.path, filename), 'r'
            ) as z:
                for filedata in get_multiple_xml_by_offset(z, offsets):
                    yield None, filedata

    def xmldoc_generator(
        self, classification=None,
        publication_numbers=None, sample_size=None
    ):
        """ Return a generator that provides XML Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size.

        This may be faster than returning the whole patent docs."""
        if not classification and not publication_numbers:
            if sample_size:
                query_string = (
                    "SELECT ROWID, filename, start_offset FROM files"
                    " WHERE ROWID IN"
                    "(SELECT ROWID FROM files ORDER BY RANDOM() LIMIT ?)"
                    )
                records = self.c.execute(
                    query_string, (sample_size,)).fetchall()
            else:
                query_string = (
                    "SELECT ROWID, filename, start_offset FROM files"
                )
                records = self.c.execute(query_string).fetchall()

            for _, filename, offset in records:

                    yield XMLDoc(self.read_by_offset(filename, offset))

        # If a list of publication numbers are supplied
        if publication_numbers:
            if sample_size and len(publication_numbers) > sample_size:
                # Randomly sample down to sample_size
                publication_numbers = random.sample(
                    publication_numbers, sample_size
                )

            for publication_number in publication_numbers:
                result = self.get_patentdoc(publication_number)
                if result:
                    yield result
        # If a classification is supplied
        if classification:
            filegenerator = self.iter_filter_xml(classification, sample_size)
            for xmldoc in filegenerator:
                yield xmldoc

    def get_patentdoc(self, publication_number):
        """ Return a Patent Doc object corresponding
        to a publication number. """
        try:
            filename, start_offset = self.search_files(publication_number)
            if filename and start_offset:
                return XMLDoc(
                    self.read_by_offset(filename, start_offset)
                    ).to_patentdoc()
        except:
            print("Could not locate granted patent.")
            return None
