Patent Data
=============

A bag of functions and datamodels for playing around with patent data.

See ```setup.py``` for dependencies.

## USPTO Data

The functions in the ```uspto``` can be used to help parse downloaded USPTO patent data.

They include functions to handle patent publication data from 2001 and
grant data from at least 2010.

These functions can parse and extract the compressed files in situ without needing extraction.

Download data from 2001 to 2015 [here](https://www.google.com/googlebooks/uspto-patents-applications-text-with-embedded-images.html).

Store the data in a folder structure by year (e.g. all 2001 files in a folder
called '2001').

Initialise a corpus by passing the path of the data directory, e.g.:
```
from patentdata.corpus import USPublications, USGrants
c_pubs = USPublications("/path/to/downloaded/data/")
c_grants = USGrants("/path/to/downloaded/data/")
```

This will perform a first level of file scanning.

### Lazy Retrieval Options

There are a number of methods that allow you to retrieve patentdata without storing
large arrays in memory.

For example:
```
xml_generator = c_pubs.iter_xml()
```
creates a generator that iterates through the patent publications in the path.
You can use this in methods such as:
```
for xmldoc in xml_generator:
    xmldoc.title()
```

### Quicker Methods that Create an Index of Files

There are also quicker retrieval methods that use a list of all the separate patent files.
These methods may lead to memory errors and slow performance on older machines.

To  index the files, which may take a couple of days for all publications
from 2001 to 2015 (there are over 4 million patent publication), run the following:
```
c_pubs.index()
c_grants.index()
```

Progress will be indicated. Data is stored in the path passed to the object
initialisation as a SQLite database called ```fileindexes.db```. The indexing
process can be interupted and restarted with no loss of data.

There allows a search function that takes a publication number (e.g. 'US20050123456')
as input and returns a Patent Doc object if the publication number exists, e.g.:
```
pd = c_pubs.get_patentdoc('US20050123456A1')
```

### Classifications

It can be useful to retrieve batches of patent documents by classification.
For example, I often like to retrieve all documents in the 'computing' area,
which is generally indicated by section "G" and class "06".

Classifications for patent grants are indexed as part of the ```index()``` method.

For publications, as the process can take a while, it has been separated into
function ```process_classifications()```. This can take a year to index classifications
for just that year (e.g. ```process_classifications([2005, 2007])```). So usage is:
```
c_pubs.process_classifications()
```

Once classifications have been indexed, you can pass parts of a classification to
an XMLDoc or PatentDoc generator. Usage is as follows:
```
doc_generator = patentdoc_generator(
                            classification=["G", "06"],
                            publication_numbers=None, sample_size=100
                            )
patent_samples = [pd for pd in doc_generator]

doc_generator = xmldoc_generator(
                            classification=["G", "06"],
                            publication_numbers=None, sample_size=100
                            )
patent_samples = [xmldoc for xmldoc in doc_generator]
```
Sample size parameter limits the returned results to the number passed.
A list of publication numbers can also be passed instead of the classification.

## EPO Data

The functions in ```EPO``` can be used to obtain WO, EPO and UK data from
the EPO's Open Patent Services (OPS) API.

### Setup

To use the EPO OPS service you need to pass your consumer key and secret to
the EPOOPS object.
```
from patentdata.corpus import EPOOPS
epo_corpus = EPOOPS(EPOOPS_C_KEY, EPOOPS_SECRET_KEY)
```

Here are some example functions:
```
claims = epo_corpus.get_claims("EP2979166")
claims = epo_corpus.get_claims(
            "13880507.2",
            numbertype='application',
            countrycode='EP'
        )

description = epo_corpus.get_description("EP2979166")
description = epo_corpus.get_description(
            "13880507.2",
            numbertype='application',
            countrycode='EP'
        )

# Convert an application number into an EPODOC application number
epodoc_no = epo_corpus.convert_number("13880507.2", "EP")

# Convert an application number into an EPODOC publication number
pub_no = epo_corpus.get_publication_no("13880507.2", "EP")

citations = epo_corpus.get_citations("EP1000000")

patentdoc = epo_corpus.get_patentdoc("EP2979166")

doc_generator = patentdoc_generator(
                            publication_numbers=[pub1, pub2]
                            )
patent_samples = [pd for pd in doc_generator]

```

## Data Objects and Models

### XMLDoc PatentDoc Objects

There are two objects that may be used to play with the patent data.

#### XMLDoc

The first is a wrapper for XML data called XMLDoc.

For example, text may be extracted by processing the filedata obtained above as XML.
```
xmldoc = c_pubs.XMLDoc(filedata)
xmldoc.title()
xmldoc.description_text()
xmldoc.claim_text()
xmldoc.all_text()
```
This text may form the input for natural language processing analysis.

#### PatentDoc

The PatentDoc object is independent of the underlying XML.

The XMLDoc to_patentdoc() method returns a PatentDoc object from an XMLDoc object.

It has some methods for natural language processing of the patent elements.
These can be found in the ```models``` folder.
For example:
```
pd = c.get_patentdoc('US20050123456A1')
pd = c.get_doc(i).to_patentdoc()

pd.reading_time(reading_rate=100)
pd.description.text()
pd.claimset.get_claim(1).get_dependency_groups()
pd.claimset.get_claim(10).split_into_features()
```

Caveat: There may be a few bugs. I am testing (and building some tests) to squash these.
Package will improve with time.

Patent Models
=============

Additional functions and datamodels for patent data can be found in ```patentdata.model```.

Usage
--------------
``from patentdata.models import PatentDoc, Description, Claimset, Claims, Classification``

Getting a bag of words from a patent description.
::
    text = [
        ("Lorem ipsum dolor sit amet, consectetur "
            "adipiscing elit. Integer nec odio. \n"),
        ("Praesent libero 100. Sed cursus 102 ante dapibus diam. "
            "Sed nisi. \n"),
        ("Sed, dignissim lacinia, <nunc>. Curabitur tortor 2."
            "Pellentesque nibh. \n"),
        "Quisque volutpat 554 condimentum velit."
        ]
    desc = Description(text)
    desc.bag_of_words()

Provides:
::
    ['lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consecteturadipisc', 'elit',
    'integ', 'nec', 'odio', 'praesent', 'libero', 'sed', 'cursu', 'ant', 'dapibu',
    'nisi', 'sed', 'dignissim', 'lacinia', 'nunc', 'curabitur', 'tortor', 'nibh',
    'quisqu', 'volutpat', 'condimentum', 'velit']

For a complete patent document:
::
    claims = [
                Claim("Claim {0} has an x.".format(num), num)
                for num in range(1, 10)
                ]
    claimset = Claimset(claims)
    desc = Description(["one", "two", "three"])
    fig = Figures()
    classification = Classification("A")
    pd = PatentDoc(
                claimset,
                desc,
                fig,
                "Title",
                classification,
                "20010101010"
                )
    pd.reading_time()
    pd.claimset.get_claim(5).text
