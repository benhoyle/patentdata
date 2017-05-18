# -*- coding: utf-8 -*-

from patentdata.corpus.baseclasses import BasePatentDataSource
import patentdata.utils as utils
from patentdata.xmlparser import XMLDoc

import zipfile
import os
from six import StringIO

# from lxml import etree


def separated_xml(zip_file):
    """ Function to separate a large XML file with concatenated
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
        """ Read large XML file from Zip."""
        with zipfile.ZipFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
            for filedata in separated_xml(z):
                yield XMLDoc(filedata)

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
