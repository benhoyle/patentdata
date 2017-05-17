# -*- coding: utf-8 -*-

# == IMPORTS ==========================================================#
import os
import logging
import re
import math
import random

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


def get_xml_path(name):
    """ Get the XML path of a file from the name. """
    file_name_section = name.rsplit('/', 1)[1].split('.')[0]
    return file_name_section + '/' + file_name_section + ".XML"


def read_nested_zip(open_zip_file, nested_name):
    """ Opens a nested_name file from passed file data of
    open_zip_file. """
    XML_path = get_xml_path(nested_name)
    try:
        with zipfile.ZipFile(open_zip_file, 'r') as nested_zip:
            with nested_zip.open(XML_path, 'r') as xml_file:
                return xml_file.read()
    except Exception:
        logging.exception(
                "Exception opening file:" +
                str(nested_name)
            )
        return None


def filedata_generator(path, filename, entries):
    """ Generator to return file data for each name in entries
    for a given filename. Entries is a list of form (id, name).

    Returns: id, filedata as tuple."""
    # For zip files
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(
            os.path.join(path, filename), 'r'
        ) as z:
            for pub_id, name in entries:
                with z.open(name, 'r') as nested_zip:
                    z2 = BytesIO(nested_zip.read())
                    yield pub_id, read_nested_zip(z2, name)

    # For tar files
    elif filename.lower().endswith(".tar"):
        with tarfile.TarFile(
            os.path.join(path, filename), 'r'
        ) as z:
            for pub_id, name in entries:
                z2 = z.extractfile(name)
                yield pub_id, read_nested_zip(z2, name)


def group_filenames(filelist):
    """ Group entries in the form (id, filename, name) by filename. """
    filename_groups = dict()
    # Get groups of filenames
    for pub_id, filename, name in filelist:
        if filename not in filename_groups.keys():
            filename_groups[filename] = list()
        filename_groups[filename].append((pub_id, name))
    return filename_groups


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
        self.PUB_FORMAT = re.compile(r"(\w\w)(\d{4})(\d{7})(\w\d)")
        # Get upper level zip/tar files in path
        self.first_level_files = utils.get_files(self.path, self.exten)

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

    def get_archive_list(self):
        """ Generate a list of lower level archive files. """

        print("Getting archive file list - may take a few minutes\n")
        # Iterate through subdirs as so? >
        for subdirectory in utils.get_immediate_subdirectories(self.path):
            print("Generating list for :", subdirectory)
            filtered_files = [
                f for f in self.first_level_files
                if subdirectory in os.path.split(f) and "SUPP" not in f
            ]
            for filename in filtered_files:
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

    def iter_read(self, filelist):
        """ Read file data for a set of files
        in filelist with (id, filename, name) entries. """

        filename_groups = group_filenames(filelist)

        # For each filename group
        for filename in filename_groups.keys():
            # Get set of second level files
            entries = filename_groups[filename]
            try:
                for pub_id, filedata in filedata_generator(
                                                    self.path,
                                                    filename,
                                                    entries
                ):
                    yield pub_id, filedata
            except Exception:
                logging.exception("Exception opening file:" + str(filename))
                yield None

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

    def iter_filter_xml(self, classification, sample_size=None):
        """ Generator to return xml that matches has classification.

        :param classification: list in form
        ["G", "61", "K", "039", "00"]. If an entry has None or
        no entry, it and its remaining entries are not filtered.
        """
        # First - build the SQL query
        class_fields = [
            'section', 'class', 'subclass', 'maingroup', 'subgroup'
            ]
        query_portion = "WHERE"

        for i in range(0, len(class_fields)):
            if i >= len(classication):
                break
            if not classification[i]:
                break
            if i > 0:
                query_portion += "AND"
            query_portion += " {0} = '{1}' ".format(
                class_fields[i],
                classification[i]
            )
        #query_portion += ")"
        # Then build final query string
        query_string = """
                        SELECT ROWID, filename, name
                        FROM files
                        {0}
                        """.format(query_portion)
        records = self.c.execute(query_string).fetchall()
        no_of_records = len(records)
        print("{0} records located.".format(no_of_records))
        # Select a random subset if a sample size is provided
        if sample_size and no_of_records > sample_size:
            records = random.sample(
                    records, sample_size
                )
        # Iterate through records and return XMLDocs
        for pub_id, filedata in iter_read(records):
            if filedata:
                yield XMLDoc(filedata)

    def search_files(self, publication_number):
        """ Return upper and lower level paths for publication.
            Returns None if no match."""
        self.c.execute(
            'SELECT filename, name FROM files WHERE pub_no=?',
            (publication_number,)
        )
        return self.c.fetchone()

    def get_patentdoc(self, publication_number):
        """ Return a PatentDoc object for a given publication number."""
        try:
            filename, name = self.search_files(publication_number)
            if filename and name:
                return XMLDoc(
                    self.read_archive_file(filename, name)
                    ).to_patentdoc()
        except:
            return None

    def get_patentcorpus(self, indexes, number_of_docs):
        """ Get a random sample of documents having a total number_of_docs."""
        """ Indexes is a list of relevant patent indexes. """
        pass
        """if len(indexes) > number_of_docs:
            indexes = random.sample(indexes, number_of_docs)
        return m.PatentCorpus(
            [self.get_doc(i).to_patentdoc() for i in indexes]
            )"""

    def get_classification(self, filedata):
        """ Return patent classifications as a list of 5 items."""
        return XMLDoc(filedata).classifications()

    def store_classification(self, rowid, classification):
        """ Store classification (['G', '06', 'K', '87', '00]) at
        rowid in database. """
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
        data = (
                classification[0],
                classification[1],
                classification[2],
                classification[3],
                classification[4],
                rowid
                )
        try:
            self.c.execute(query_string, data)
            self.conn.commit()
            return True
        except Exception:
            return False

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


    def process_classifications(self, yearlist=None):
        """ Iterate through publications and store classifications in DB.

        :param yearlist: list of years as integers,
        e.g. [2001, 2010, 2013] - if supplied will only process
        these years
        """
        # Select distinct years in DB
        years = self.c.execute('SELECT DISTINCT year FROM files').fetchall()
        if not years:
            # If no years are returned run the archive list method
            self.get_archive_list()
            years = self.c.execute('SELECT DISTINCT year FROM files').fetchall()

        # If a yearlist is supplied use to filter years
        if yearlist:
            years = [y[0] for y in years if y[0] in yearlist]
        else:
            years = [y[0] for y in years]

        for year in years:
            print("Processing year: ", year)
            # Get rows without classifications
            query_string = """
                SELECT ROWID, filename, name FROM files
                WHERE
                    year = ? AND
                    section IS NULL
                """
            records = self.c.execute(query_string, (year,)).fetchall()
            i = 0
            # filelist = [(f, n) for r, f, n in records]
            filereader = self.iter_read(records)
            params = []
            for rowid, filedata in filereader:
                # print("RID:{0}; Len FD:{1}".format(rowid, len(filedata)))
                # print(XMLDoc(filedata).title())
                # print(XMLDoc(filedata).soup)
                classifications = self.get_classification(filedata)
                # print(rowid, classifications)
                if len(classifications) > 0:
                    # For speed up batch updates to DB in transactions

                    #self.store_classification(rowid, classifications[0])
                    params.append(classifications[0] + [rowid])
                    i += 1

                    if (i % 100) == 0:
                        print(i, classifications[0])
                        self.store_many(params)
                        params = []
            if params:
                self.store_many(params)
