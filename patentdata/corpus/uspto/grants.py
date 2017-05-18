# -*- coding: utf-8 -*-

from patentdata.corpus.baseclasses import BasePatentDataSource
import patentdata.utils as utils
from patentdata.xmlparser import XMLDoc

import zipfile
import os


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


#def separated_xml_with_lines(zip_file):
    #""" Generator to separate a large XML file with concatenated
    #<us-patent-grant></us-patent-grant> root nodes. """
    ## Extract first file name from zip file, which = xml file
    #xml_file = zip_file.namelist()[0]
    #with zip_file.open(xml_file, 'r') as open_xml_file:
        ## open_xml_file is a binary file object - hence lines are bytes
        #data_buffer = [open_xml_file.readline()]
        ## Initialise a buffer to store the current start byte offset
        #start_offset = 0
        ## Initialise a buffer to store current end byte offset
        #end_offset = start_offset + len(data_buffer[0])
        #for line in open_xml_file:
            ## If line is a new XML declaration
            #if line.startswith(b'<?xml '):
                ## return start offset, end offeset, data
                #yield start_offset, end_offset, b''.join(data_buffer)
                ## Reset data buffer
                #data_buffer = []
                ## Increment start to previous end
                #start_offset = end_offset
            ## If line is not a new XML declaration
            #data_buffer.append(line)
            ## Increment the (byte) end offset by the length of the line
            #end_offset += len(line)

        #yield start_offset, end_offset, b''.join(data_buffer)


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


#def get_xml_by_offset(zip_file, start_offset):
    #""" Retrieve XML data based on a starting byte offset. """
    ## BUT CANNOT SEEK ON A ZipExtFile WHICH = OPEN_XML_FILE
    ## WILL NEED TO USE ORIGINAL METHOD OF SEARCHING THROUGH LINES
    #xml_file = zip_file.namelist()[0]
    #with zip_file.open(xml_file, 'r') as open_xml_file:
        #open_xml_file.seek(start_offset)
        #data_buffer = [open_xml_file.readline()]
        #for line in open_xml_file:
            ## If line is a new XML declaration
            #if line.startswith(b'<?xml '):
                #return b''.join(data_buffer)
            #data_buffer.append(line)
        #return b''.join(data_buffer)


class USGrants(BasePatentDataSource):
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

    def get_archive_list(self):
        """ Generate metadata for individual publications. """

        # We have a lot of separate xml sections in each zip file

        # How do we quickly search and retrieve data from these files?

        print("Getting archive file list - may take a few minutes\n")
        # Iterate through subdirs as so? >
        for subdirectory in utils.get_immediate_subdirectories(self.path):
            print("Generating list for :", subdirectory)
            filtered_files = [
                f for f in self.first_level_files
                if subdirectory in os.path.split(f) and "SUPP" not in f
            ]
            for filename in filtered_files:
                # OK up to here
                pass
                # Do we save publication number and classification with
                # File start and end lines?

                names = self.get_archive_names(filename)
                for name in names:
                    match = self.PUB_FORMAT.search(name)
                    if match and name.lower().endswith(self.exten):
                        data = (
                            match.group(0),
                            match.group(1),
                            int(match.group(2)),
                            int(match.group(3)),
                            match.group(4),
                            filename,
                            name
                        )
                        self.c.execute((
                            'INSERT OR IGNORE INTO files'
                            ' (pub_no, countrycode, year, number, '
                            'kindcode, filename, name) '
                            'VALUES (?,?,?,?,?,?,?)'),
                            data
                        )
                self.conn.commit()

            # re_strip_pi = re.compile('<\?xml [^?>]+\?>', re.M)
            # data = '<root>' + z.open(z.namelist()[0], 'r').read() + '</root>'
            # match = re_strip_pi.search(data)
            # data = re_strip_pi.sub('', data)
            # tree = etree.fromstring(match.group() + data)
            # return tree

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
