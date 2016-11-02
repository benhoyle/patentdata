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
c = corpus.MyCorpus("/path/to/downloaded/data/2005")
```

This will perform a first level of file scanning. It is recommended to generate
separate objects for each year. (There are a lot of files!)

To get a list of all the files use the method:
```
c.get_archive_list()
```

(This can take a while - have a cup of tea.)

Individual publications can then be retrieved using an index. 

The files can be viewed using the attribute:
```
c.archive_file_list()
```

And filedata for a particular file in the list may be retrieved by:
```
filedata = c.read_xml([index])
```
where "[index]" is replaced by an integer representing the index in archive_file_list.

Text may be extracted by processing the filedata as XML.
```
xmldoc = corpus.XMLDoc(filedata)
xmldoc.title()
xmldoc.description_text()
xmldoc.claim_text()
xmldoc.all_text() 
```
This text may form the input for natural language processing analysis.

Caveat: There may be a few bugs. I am testing (and building some tests) to squash these.
Package will improve with time.
