import re
import time
import datetime
import os
import sys
import json
import configparser
import logging
import epo_ops
from epo_ops.models import Epodoc

# Import helper utilities
import utils

chars_to_delete = [".", "&", ",", "/"]
chars_to_space = ["+","-"]

company_stopwords = ["AB", "AS", "AG", "CORPORATION", "CORP", "GMBH", "CO", "COMPANY", "SA", 
                     "KG", "NV", "LIMITED", "LTD", "BV", "INC", "SAS", "OY", "SARL", "PTE", 
                     "SPA", "KK", "LP", "LLC", "EV", "PLC", "VZW", "DD", "DOO", "SNC", "OYJ", "UK"]

# Configure logging
logging.basicConfig(filename='patentdata.log', level=logging.INFO, format='%(asctime)s %(message)s')

# Load Key and Secret from config file called "config.ini" 
parser = configparser.ConfigParser()
parser.read(os.path.abspath(os.getcwd() + '/data/config.ini'))
consumer_key = parser.get('Login Parameters', 'C_KEY')
consumer_secret = parser.get('Login Parameters', 'C_SECRET')

# Intialise EPO OPS client
# Load Dogpile if it exists - if not just use Throttler
try:
    middlewares = [
        epo_ops.middlewares.Dogpile(),
        epo_ops.middlewares.Throttler(),
    ]
except:
    middlewares = [
        epo_ops.middlewares.Throttler()
    ]

registered_client = epo_ops.RegisteredClient(
    key=consumer_key, 
    secret=consumer_secret, 
    accept_type='json',
    middlewares=middlewares)

# Load country stopwords
countries = [line.strip().split("|")[1].upper() for line in open("data/countries.txt", 'r')]

# Upgrade name processing function
stopwords = company_stopwords + countries

# Import database objects to store data
import datamodels

# Import datacache models
import datacache

def process_name(name):
    """ Clean applicant name for better search."""
    # Capitalise
    name = name.upper()
    # Remove text to the right of any comma
    processed_name = name.split(',')[0]
    # Delete certain characters
    for char in chars_to_delete:
        processed_name = processed_name.replace(char, "")
    # Change certain characters to spaces
    for char in chars_to_space:
        processed_name = processed_name.replace(char, " ")
    # Remove bracketed words
    processed_name = utils.remove_bracketed(processed_name)   
    # Delete stopwords 
    import re
    pattern = re.compile(r'\b(' + r'|'.join(stopwords) + r')\b\s*')
    processed_name = pattern.sub('', processed_name)
    # Get rid of double spaces
    processed_name = processed_name.replace("  ", " ")
    return processed_name.strip()

def generate_search_string(company_name, year):
    """ Return cql search string given a company_name string and year. """
    return """pa="{0}" and pn=EP and pd within {1}""".format(company_name, year)

def get_search(raw_companies_list):
    """ Get search results for companies in raw_companies_list. """

    # Initialise year
    year = utils.get_current_year()
    # Intialise data dump
    data = []
    
    for company in raw_companies_list:
        company_name = process_name(company)
        search_string = generate_search_string(company_name, year)
        logging.info("Processing {0} with Search String: {1}".format(company, search_string))
        try:
            results = registered_client.published_data_search(search_string, range_begin=1, range_end=100)
            results_json = results.json()['ops:world-patent-data']['ops:biblio-search']
           
            total_results = utils.safeget(results_json, '@total-result-count')
            logging.info("Total results: {0}".format(total_results))
            number_objects = utils.check_list(utils.safeget(results_json,'ops:search-result','ops:publication-reference'))
            if number_objects:
                numbers = [utils.safeget(result,'document-id','country','$') + utils.safeget(result, 'document-id', 'doc-number','$') for result in number_objects]
            else:
                numbers = []
            data.append({
                    "applicant": company_name, 
                    "raw_applicant":company, 
                    "total_results":total_results, 
                    "numbers":numbers,
                    "raw_data": results_json
                })
        except KeyError:
            data.append({
                    "applicant": company_name, 
                    "raw_applicant":company, 
                    "total_results":"", 
                    "numbers":"",
                    "raw_data": results_json
                })
        except:
            logging.info("Status error: {0}".format(results.status_code))
            logging.info("Response dump: {0}".format(results.text))
            logging.info("Unexpected error:", sys.exc_info()[0])
        
        time.sleep(1)
    
    save_data("BiblioSearch", data)
        
def save_data(filename, data):
    """ Save data as a JSON file with name including 
    the current time and filename."""
    time_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_filename = "".join(["savedata/", time_string, filename, ".json"])
    with open(save_filename, 'w', encoding="utf8") as outfile:
        json.dump(data, outfile)
        
def get_register(number):
    """ Get EP Register data for a particular EP publication no. 
    (e.g. EP3065066) """
    # Add here to first check cached data? - do this externally to function?
    try:
        register_search = registered_client.register("publication", Epodoc(number))
        return register_search.json()
    except:
        return None
    
def get_agent_class(results_json):
    """ Get agent and classification data from Register JSON. """
    # These can sometimes have multi entries so we'll use checklist to 
    # turn them all into a list (some with only one entry)
    try:
        raw_agents = utils.check_list(utils.keysearch(results_json,'reg:agents'))
        raw_classifications = utils.check_list(utils.keysearch(results_json,'reg:classifications-ipcr'))
        
        if raw_agents:
            agent_details = raw_agents[0]
        else:
            agent_details = utils.check_list(utils.keysearch(results_json,'reg:applicants'))[0]
        
        # Get first agent / classification
        result_dict = {
            "agent" : utils.keysearch(agent_details,'reg:name').get('$', None),
            "agent_first_address" : utils.keysearch(agent_details,'reg:address-1').get('$', None),
            "agent_country" : utils.keysearch(agent_details,'reg:country').get('$', None),
            "classification" : utils.keysearch(raw_classifications[0],'reg:text').get('$', None)
            }
    except:
        result_dict = None
    return result_dict

def save_register(number):
    """Save agent / class data for PatentPublication object number."""
    
    session = datamodels.Session()
    cachesession = datacache.Session()
    
    publication_number = number.pub_no
    print("Getting register data for {0}".format(publication_number))

    # Check for number in cache
    in_cache = cachesession.query(datacache.RegisterCache).filter(datacache.RegisterCache.pub_no == publication_number).first()

    if not in_cache:
        # Perform an OPS query
        print("Querying EPO OPS")
    
        json_result = get_register(publication_number)
    
        if json_result:
            # Store result in cache
            try:
                cache_to_store = datacache.RegisterCache(publication_number, json_result)
                cachesession.add(cache_to_store)
                cachesession.commit()
            except:
                print("Error saving cache")
                cachesession.rollback()
        time.sleep(1)
    else:
        # Load json from cache
        print("Loading from cache")
        json_result = in_cache.loadresponse()

    if json_result:
        # Extract agent and classification data
        result_dict = get_agent_class(json_result)
    else:
        result_dict = None
    
    if result_dict:
        # Store agent / classification details
        try:
            number.raw_agent = result_dict["agent"]
            number.raw_agent_first_address = result_dict["agent_first_address"]
            number.raw_agent_country = result_dict["agent_country"]
            number.raw_classification = result_dict["classification"]
            session.commit()
            print("Agent - {0}, {1}".format(number.raw_agent, number.raw_agent_first_address))
            print("Agent Country - {0}".format(number.raw_agent_country))
            print("Classification - {0}".format(number.raw_classification))
          
        except:
            session.rollback()
            print("Error updating Publication")
            raise
            
    session.close()

def getall_registers():
    """ Get register details for samples of each applicant in PatentSearch. """
    # Define number of samples for each applicant
    no_of_samples = 10
    
    import math
    import random
    
    session = datamodels.Session()
    
    # Cycle through companies and record agent / classification
    for entity in session.query(datamodels.PatentSearch).all():
        # Sample publication objects if greater than defined number
        if len(entity.publications) > no_of_samples:
            samples = random.sample(entity.publications,no_of_samples)
        else:
            samples = entity.publications
        
        for sample in samples:
            save_register(sample)
    
    session.close()

def get_agent_list(session):
    """ Get list of agent details. """
    name_list = session.query(datamodels.PatentPublication.raw_agent, datamodels.PatentPublication.raw_agent_first_address) \
        .filter(datamodels.PatentPublication.raw_agent != None).all()
    name_list_processed = [nl[1] if is_attorney_name(nl[0]) else nl[0] for nl in name_list]
    fd = utils.list_frequencies(name_list_processed)
    return utils.sort_freq_dist(fd)
    
def process_classification(class_string):
    """ Extract IPC classfication elements from a class_string."""
    ipc = r'[A-H][0-9][0-9][A-Z][0-9]{1,4}\/?[0-9]{1,6}' #last bit can occur 1-3 times then we have \d+\\?\d+ - need to finish this
    p = re.compile(ipc)
    classifications = [
        {
            "section" : match.group(0)[0], 
            "class" : match.group(0)[1:3],
            "subclass" : match.group(0)[3],
            "maingroup": match.group(0)[4:].split('/')[0],
            "subgroup" : match.group(0)[4:].split('/')[1]
        }
        for match in p.finditer(class_string)]
    return classifications

def is_attorney_name(text):
    """Regex match for name, returns true if attorney name format."""
    person_name = r'\A([^\d\W]|-)+,(?:\s([^\d\W]|-)+)+(?:\s[A-Z]\.)?(?:, et al)?$'
    p = re.compile(person_name, re.UNICODE)
    located = p.search(text)
    if located:
        return True
    else:
        return False
# Need datarecord for classification - done
# Then we pass an entity, retrieve publications with non-zero raw classification, for each publication - retrieve classifications and add to list as dict
    # Then process list of classification 
