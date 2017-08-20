# -*- coding: utf-8 -*-

# == IMPORTS ==========================================================#
import os
import logging
import random

from patentdata.corpus.baseclasses import DBIndexDataSource

# Libraries for Zip file processing
# Can we use czipfile for faster processing?
import zipfile
import tarfile
# from zip_open import zopen
# Python 3.5
from io import BytesIO

import patentdata.utils as utils

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
    xml_path = get_xml_path(nested_name)
    try:
        with zipfile.ZipFile(open_zip_file, 'r') as nested_zip:
            with nested_zip.open(xml_path, 'r') as xml_file:
                return xml_file.read()
    except Exception:
        logging.exception(
                "Exception opening file:" +
                str(nested_name)
            )
        return None


class USPublications(DBIndexDataSource):
    """
    Creates a new corpus object that simplifies processing of
    patent archive
    """

    def index(self):
        """ Generate a list of lower level archive files. """

        print("Getting archive file list - may take a few minutes\n")
        # Iterate through subdirs as so? >
        for subdirectory in utils.get_immediate_subdirectories(self.path):
            logging.info("Generating list for :", subdirectory)
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

    def filedata_generator(self, filename, entries):
        """ Generator to return file data for each name in entries
        for a given filename. Entries is a list of form (id, name).

        Returns: id, filedata as tuple."""
        # For zip files
        if filename.lower().endswith(".zip"):
            with zipfile.ZipFile(
                os.path.join(self.path, filename), 'r'
            ) as z:
                for pub_id, name in entries:
                    with z.open(name, 'r') as nested_zip:
                        try:
                            z2 = BytesIO(nested_zip.read())
                            yield pub_id, read_nested_zip(z2, name)
                        except:
                            logging.exception(
                                "Exception opening file:" +
                                str(name)
                            )
                            yield pub_id, None

        # For tar files
        elif filename.lower().endswith(".tar"):
            with tarfile.TarFile(
                os.path.join(self.path, filename), 'r'
            ) as z:
                for pub_id, name in entries:
                    try:
                        z2 = z.extractfile(name)
                        yield pub_id, read_nested_zip(z2, name)
                    except:
                            logging.exception(
                                "Exception opening file:" +
                                str(name)
                            )
                            yield pub_id, None


    def read_archive_file(self, filename, name):
        """ Read file data for XML_path nested
        within name archive within filename archive. """
        # Get xml file path from name
        file_name_section = name.rsplit('/', 1)[1].split('.')[0]
        xml_path = file_name_section + '/' + file_name_section + ".XML"

        try:
            # For zip files
            if filename.lower().endswith(".zip"):
                with zipfile.ZipFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
                    with z.open(name, 'r') as z2:
                        z2_filedata = BytesIO(z2.read())
                        with zipfile.ZipFile(z2_filedata, 'r') as nested_zip:
                            with nested_zip.open(xml_path, 'r') as xml_file:
                                filedata = xml_file.read()

            # For tar files
            elif filename.lower().endswith(".tar"):
                with tarfile.TarFile(
                    os.path.join(self.path, filename), 'r'
                ) as z:
                    z2 = z.extractfile(name)
                    with zipfile.ZipFile(z2) as nested_zip:
                        with nested_zip.open(xml_path) as xml_file:
                            filedata = xml_file.read()
        except:
            logging.exception("Exception opening file:" + str(xml_path))
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

    def iter_filter_xml(self, classification, sample_size=None):
        """ Generator to return xml that matches has classification.

        :param classification: list in form
        ["G", "61", "K", "039", "00"]. If an entry has None or
        no entry, it and its remaining entries are not filtered.
        """
        records = self.get_records(classification, "name", sample_size)
        filegenerator = self.iter_read(records)
        # Iterate through records and return XMLDocs
        for _, filedata in filegenerator:
            if filedata:
                yield XMLDoc(filedata)

    def get_patentcorpus(self, indexes, number_of_docs):
        """ Get a random sample of documents having a total number_of_docs."""
        """ Indexes is a list of relevant patent indexes. """
        pass
        """if len(indexes) > number_of_docs:
            indexes = random.sample(indexes, number_of_docs)
        return m.PatentCorpus(
            [self.get_doc(i).to_patentdoc() for i in indexes]
            )"""

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
            self.index()
            years = self.c.execute(
                'SELECT DISTINCT year FROM files'
                ).fetchall()

        # If a yearlist is supplied use to filter years
        if yearlist:
            years = [y[0] for y in years if y[0] in yearlist]
        else:
            years = [y[0] for y in years]

        for year in years:
            logging.info("Processing year: {0}".format(year))
            # Get rows without classifications
            query_string = """
                SELECT ROWID, filename, name FROM files
                WHERE
                    year = ? AND
                    section IS NULL
                """
            records = self.c.execute(query_string, (year,)).fetchall()
            # filelist = [(f, n) for r, f, n in records]
            filereader = self.iter_read(records)
            params = []
            i = 0
            for rowid, filedata in filereader:
                # print("RID:{0}; Len FD:{1}".format(rowid, len(filedata)))
                # print(XMLDoc(filedata).title())
                # print(XMLDoc(filedata).soup)
                if filedata:
                    classifications = self.get_classification(filedata)

                    # print(rowid, classifications)
                    if len(classifications) > 0:
                        # For speed up batch updates to DB in transactions
                        params.append(classifications[0] + [rowid])

                        if (len(params) % 100) == 0:
                            i += 100
                            logging.info(
                                "Process {0} with classifications {1}"
                                .format(i, classifications[0])
                                )
                            self.store_many(params)
                            params = []
            if params:
                self.store_many(params)

    def get_patentdoc(self, publication_number):
        """ Return a PatentDoc object for a given publication number."""
        try:
            filename, name = self.search_files(publication_number, "name")
            if filename and name:
                return XMLDoc(
                    self.read_archive_file(filename, name)
                    ).to_patentdoc()
        except:
            logging.info("Could not find publication")
            return None

    def xmldoc_generator(
                            self, classification=None,
                            publication_numbers=None, sample_size=None
                            ):
        """ Generator to return XML Doc objects.

        If classification is supplied results are limited to that
        classification (of form ["G", "06"], length 1 to 5).

        If publication_numbers is supplied as list, results are limited
        to those publication numbers.

        (classification and publication filtering is XOR)

        If sample_size is provided returned documents are limited to
        this integer.
        """
        # If parameters are passed iterate through whole datasource
        if not classification and not publication_numbers:
            if sample_size:
                query_string = (
                    "SELECT ROWID, filename, name FROM files"
                    " WHERE ROWID IN"
                    "(SELECT ROWID FROM files ORDER BY RANDOM() LIMIT ?)"
                    )
                records = self.c.execute(
                    query_string, (sample_size,)).fetchall()
            else:
                query_string = (
                    "SELECT ROWID, filename, name FROM files"
                )
                records = self.c.execute(query_string).fetchall()

            filereader = self.iter_read(records)
            for _, filedata in filereader:
                if filedata:
                    yield XMLDoc(filedata)

        # If a list of publication numbers are supplied
        if publication_numbers:
            if sample_size and len(publication_numbers) > sample_size:
                # Randomly sample down to sample_size
                publication_numbers = random.sample(
                    publication_numbers, sample_size
                )
            # Below is alternate method
            """ query_string = ("SELECT ROWID, filename, name FROM files"
                    " WHERE pub_no IN ({0})").format(
                        ', '.join(['?'] * len(publication_numbers)
                    )
            records = self.c.execute(
                    query_string, publication_numbers).fetchall()"""
            for publication_number in publication_numbers:
                result = self.get_patentdoc(publication_number)
                if result:
                    yield result
        # If a classification is supplied
        if classification:
            filegenerator = self.iter_filter_xml(classification, sample_size)
            for xmldoc in filegenerator:
                yield xmldoc


