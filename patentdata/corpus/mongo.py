import os
import pickle
import patentdata.utils as utils
from patentdata.corpus.uspto.grants import get_multiple_xml_by_offset

import zipfile
from pymongo import MongoClient
from patentdata.xmlparser import XMLDoc


def to_mongo(path=None, records=None):
    """ Convert stored and zipped XML records to Mongodb Documents."""

    client = MongoClient('mongodb', 27017)
    db = client.patent_db

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
