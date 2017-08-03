# -*- coding: utf-8 -*-
# Import abstract class functions
from abc import ABCMeta, abstractmethod

import sqlite3
import random
import re
import os
import patentdata.utils as utils
from patentdata.xmlparser import XMLDoc
import logging

# Configure logging
logging.basicConfig(
    filename="processing_class.log",
    format='%(asctime)s %(message)s'
)


class BasePatentDataSource(metaclass=ABCMeta):
    """ Abstract class for patent data sources. """

    @abstractmethod
    def get_patentdoc(self, publication_number):
        """ Return a Patent Doc object corresponding
        to a publication number. """
        pass

    @abstractmethod
    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Return a generator that provides Patent Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size"""
        pass


class LocalDataSource(BasePatentDataSource):
    """ Abstract class for files stored locally. """

    @abstractmethod
    def index(self, publication_number):
        """ Index the files on disk. """
        pass

    @abstractmethod
    def xmldoc_generator(self, publication_numbers=None, sample_size=None):
        """ Return a generator that provides XML Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size.

        This may be faster than returning the whole patent docs."""
        pass


class DBIndexDataSource(LocalDataSource):
    """ Super class for datasources that use an SQL DB as a file index."""

    def __init__(self, path):

        self.exten = (".zip", ".tar")
        self.path = path
        if not os.path.isdir(path):
            print("Invalid path")
            # Raise custom exception here
            return
        # Set regular expression for valid patent publication files
        self.FILE_FORMAT_RE = re.compile(r".+US\d+[A,B].+-\d+\.\w+")
        self.PUB_FORMAT = re.compile(r"(\w\w)(\d{4})(\d{7})(\w\d)")
        # Get upper level zip/tar files in path
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
                    name TEXT,
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
        try:
            self.conn.close()
        except AttributeError:
            pass

    @abstractmethod
    def index(self):
        """ Generate metadata for individual publications. """
        pass

    @abstractmethod
    def filedata_generator(self, filename, entries):
        """ Generator to return file data for each name in entries
        for a given filename. Entries is a list of form (id, X).

        Returns: id, filedata as tuple."""
        pass

    @abstractmethod
    def iter_filter_xml(self, classification, fieldname, sample_size=None):
        """ Generator to return xml that matches has classification.

        :param classification: list in form
        ["G", "61", "K", "039", "00"]. If an entry has None or
        no entry, it and its remaining entries are not filtered.
        """
        pass

    @abstractmethod
    def iter_xml(self):
        """ Generator for xml file in corpus. """
        pass

    def search_files(self, publication_number, fieldname):
        """ Return upper and lower level paths for publication.
            Returns None if no match.

            fieldname = string - either 'name' or 'start_offset'
            """
        query_string = (
            'SELECT filename, {0} FROM files WHERE pub_no=?'
            .format(fieldname)
            )
        self.c.execute(
            query_string,
            (publication_number,)
        )
        return self.c.fetchone()

    def get_records(self, classification, fieldname, sample_size=None):
        """ Retrieve a list of records filtered by passed classification
        and limited by sample_size.

        return: list of records"""
        query_string = utils.build_classification_query(
            classification,
            fieldname
            )
        records = self.c.execute(query_string).fetchall()
        no_of_records = len(records)
        print("{0} records located.".format(no_of_records))
        # Select a random subset if a sample size is provided
        if sample_size and no_of_records > sample_size:
            records = random.sample(
                    records, sample_size
                )
            print("{0} records sampled.".format(len(records)))
        return records

    def iter_read(self, filelist):
        """ Read file data for a set of files
        in filelist with (id, filename, X) entries. """

        if not filelist:
            yield None, None

        filename_groups = utils.group_filenames(filelist)

        # For each filename group
        for filename in filename_groups.keys():
            # Get set of second level files
            entries = filename_groups[filename]
            try:
                for pub_id, filedata in self.filedata_generator(
                                                    filename,
                                                    entries
                                                    ):
                    yield pub_id, filedata
            except:
                logging.exception("Exception opening file:" + str(filename))

    def patentdoc_generator(
                            self, classification=None,
                            publication_numbers=None, sample_size=None
                            ):
        """ Generator to return Patent Doc objects.

        If classification is supplied results are limited to that
        classification (of form ["G", "06"], length 1 to 5).

        If publication_numbers is supplied as list, results are limited
        to those publication numbers.

        (classification and publication filtering is XOR)

        If sample_size is provided returned documents are limited to
        this integer.
        """
        xmldoc_gen = self.xmldoc_generator(
                                            classification,
                                            publication_numbers,
                                            sample_size
                                        )
        for xmldoc in xmldoc_gen:
            yield xmldoc.to_patentdoc()

    def store_many(self, params):
        """ Store classification (['G', '06', 'K', '87', '00']) at
        rowid in database.

        params = ['G', '06', 'K', '87', '00', rowid]
        """
        query_string = """
                        UPDATE files
                        SET
                            section = ?,
                            class = ?,
                            subclass = ?,
                            maingroup = ?,
                            subgroup = ?
                        WHERE
                            ROWID = ?
                        """
        try:
            self.c.executemany(query_string, params)
            self.conn.commit()
            return True
        except:
            print("Error saving classifications")
            return False

    def get_classification(self, filedata):
        """ Return patent classifications as a list of 5 items."""
        return XMLDoc(filedata).classifications()
