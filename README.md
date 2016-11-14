A bag of functions and datamodels for playing around with patent data.

See ```requirements.txt``` for dependencies.

## EPO OPS Data

The functions in ```patentdata.py``` help with automating applicant searches
using the EPO OPS service.

To use the EPO OPS service you need to enter your consumer key and secret in a 
```config.ini``` file in the ```data``` directory. These should be entered as follows:
```
[Login Parameters]
C_KEY=xxxxxxxxxxxxxxxxxxxxx
C_SECRET=bbbbbbbbbbbbbbbbbbb
```

## USPTO Data

The functions in ```corpus.py``` can be used to help parse downloaded USPTO patent data.

These functions can parse and extract the compressed files in situ without needing extraction.

Download data from 2001 to 2015 [here](https://www.google.com/googlebooks/uspto-patents-applications-text-with-embedded-images.html).

Initialise a corpus by passing the path of the data directory, e.g.:
```
import corpus
c = corpus.USPublications("/path/to/downloaded/data/2005")
```

This will perform a first level of file scanning. It is recommended to generate
separate objects for each year. (There are a lot of files!)

### Lazy Retrieval Options

There are a number of methods that allow you to retrieve patentdata without storing
large arrays in memory. 

For example:
```
xml_generator = c.iter_xml()
```
creates a generator that iterates through the patent publications in the path.
You can use this in methods such as:
```
for xmldoc in xml_generator:
    xmldoc.title()
```
There is also a search function that takes a publication number (e.g. 'US20050123456')
as input and returns a Patent Doc object if the publication number exists, e.g.:
```
pd = c.get_patentdoc('US20050123456')
```

### Quicker Methods that Create an Index of Files

There are also quicker retrieval methods that use a list of all the separate patent files.
These methods may lead to memory errors and slow performance on older machines.

To get a list of all the files use the method:
```
c.get_archive_list()
```

(This can take a while - have a cup of tea.)

On big collections (e.g. 15 years worth) this tends to generate memory errors.

Individual publications can then be retrieved using an index. 

The files can be viewed using the attribute:
```
c.archive_file_list
```

And filedata for a particular file in the list may be retrieved by:
```
filedata = c.read_xml([index])
```
where "[index]" is replaced by an integer representing the index in archive_file_list.

### XMLDoc PatentDoc Objects

There are two objects that may be used to play with the patent data.

#### XMLDoc

The first is a wrapper for XML data called XMLDoc.

For example, text may be extracted by processing the filedata obtained above as XML.
```
xmldoc = corpus.XMLDoc(filedata)
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
These can be found in the ```corpus_models.py``` file in the ```models``` folder.
For example:
```
pd = c.get_patentdoc('US20050123456')
pd = c.get_doc(i).to_patentdoc()

pd.reading_time(reading_rate=100)
pd.description.text()
pd.claimset.get_claim(1).get_dependency_groups()
pd.claimset.get_claim(10).split_into_features()
```

Caveat: There may be a few bugs. I am testing (and building some tests) to squash these.
Package will improve with time.
