# -*- coding: utf-8 -*-

from patentdata.corpus.baseclasses import BasePatentDataSource

import os
import pickle
import patentdata.utils as utils
from patentdata.corpus.uspto.grants import get_multiple_xml_by_offset

import zipfile
from pymongo import MongoClient
from patentdata.xmlparser import XMLDoc
from patentdata.models.patentdoc import PatentDoc

# Will need to move database parameters into a separate config file
client = MongoClient(os.environ.get('MONGOIP'), 27017)
db = client.patent_db


class MongoDataSource(BasePatentDataSource):
    """ Data source that uses mongo DB documents."""

    def get_patentdoc(self, publication_number):
        """ Return a Patent Doc object corresponding
        to a publication number.

        Publication number is a string like "US08847966B2" """
        try:
            return PatentDoc.load_from_dict(
                db.patents.find_one({"number": publication_number})
            )
        except Exception as e:
            print("Cannot retrieve Patent Document.")
            print(e)
            return None

    def patentdoc_generator(self, publication_numbers=None, sample_size=None):
        """ Return a generator that provides Patent Doc objects.
        publication_numbers is a list or iterator that provides a
        limiting group of publication numbers.
        sample_size limits results to a random sample of size sample_size"""
        if publication_numbers:
            for pub_no in publication_numbers:
                yield self.get_patentdoc(self, pub_no)

        if sample_size:
            cursor = db.patents.aggregate(
                [{"$sample": {"size": sample_size}}],
                allowDiskUse=True
            )
            for document in cursor:
                yield PatentDoc.load_from_dict(document)

        if not publication_numbers and not sample_size:
            cursor = db.patents.find()
            for document in cursor:
                yield PatentDoc.load_from_dict(document)


def to_mongo(path=None, records=None):
    """ Convert stored and zipped XML records from USGrants
    to Mongodb Documents.


    TODO: generalise to other datasources."""

    rec_savefile = "saved_records.pkl"
    pro_savefile = "processed_records.pkl"

    if path and records:
        with open(rec_savefile, "wb") as f:
            data = (path, records)
            pickle.dump(data, f)
    else:
        # See if we can load existing records
        if os.path.isfile(rec_savefile):
            with open(rec_savefile, "rb") as f:
                path, records = pickle.load(f)
        else:
            print("No saved records")
            return None

    if os.path.isfile(pro_savefile):
        with open(pro_savefile, "rb") as f:
            processed_files = pickle.load(f)
    else:
        processed_files = []

    # Filter to get unprocessed records
    records_to_process = [
        (i, fn, o) for i, fn, o in records if fn not in processed_files
        ]

    filename_groups = utils.group_filenames(records_to_process)

    # We can save per filename

    # For each filename group
    for filename in filename_groups.keys():
        if filename.lower().endswith(".zip"):
            offsets = [o for _, o in filename_groups[filename]]
            print("Processing {0} files in {1}".format(
                len(offsets), filename
            ))
            with zipfile.ZipFile(
                os.path.join(path, filename), 'r'
            ) as z:
                for filedata in get_multiple_xml_by_offset(z, offsets):
                    try:
                        doc = XMLDoc(filedata).to_patentdoc()
                        db.patents.insert_one(doc.as_dict())
                    except Exception as e:
                        print(e)

        processed_files.append(filename)
        with open(pro_savefile, "wb") as f:
            pickle.dump(processed_files, f)


class CorpusSentenceIterator:
    """ Iterator to return sentences from files in filelist
    from datasource. """

    def __init__(self, add_claims=True, sample_size=None):
        """ Initialise with a datasource and filelist. """
        self.mdb = MongoDataSource()
        self.sample_size = sample_size
        self.add_claims = add_claims

    def __iter__(self):
        """ Iterate through files. """
        pdg = self.mdb.patentdoc_generator(sample_size=self.sample_size)
        for doc in pdg:
            try:
                for paragraph in doc.description.paragraphs:
                    for sentence in paragraph.sentences:
                        # yield sentence.filtered_tokens
                        yield sentence.bag_of_words(
                            clean_non_words=True,
                            clean_stopwords=False,
                            stem_words=False
                        )
                    if self.add_claims:
                        for claim in doc.claimset.claims:
                            yield claim.bag_of_words(
                                clean_non_words=True,
                                clean_stopwords=False,
                                stem_words=False
                            )
            except:
                print("Error processing doc - {0}".format(doc.number))
