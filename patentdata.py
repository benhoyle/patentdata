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
from epo_ops.utils import keysearch

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
middlewares = [
    epo_ops.middlewares.Dogpile(),
    epo_ops.middlewares.Throttler(),
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

def check_list(listvar):
    """Turns single items into a list of 1."""
    if not isinstance(listvar, list):
        listvar = [listvar]
    return listvar

def safeget(dct, *keys):
    """ Recursive function to safely access nested dicts or return None. 
    param dict dct: dictionary to process
    param string keys: one or more keys"""
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct

# Define helper function to remove text in parenthesis
# From http://stackoverflow.com/questions/14596884/remove-text-between-and-in-python
def remove_bracketed(test_str):
    """ Remove bracketed text from string. """
    ret = ''
    skip1c = 0
    skip2c = 0
    for i in test_str:
        if i == '[':
            skip1c += 1
        elif i == '(':
            skip2c += 1
        elif i == ']' and skip1c > 0:
            skip1c -= 1
        elif i == ')'and skip2c > 0:
            skip2c -= 1
        elif skip1c == 0 and skip2c == 0:
            ret += i
    return ret

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
    processed_name = remove_bracketed(processed_name)   
    # Delete stopwords 
    import re
    pattern = re.compile(r'\b(' + r'|'.join(stopwords) + r')\b\s*')
    processed_name = pattern.sub('', processed_name)
    # Get rid of double spaces
    processed_name = processed_name.replace("  ", " ")
    return processed_name.strip()

# Get current year and look for publications in that year
def get_current_year():
    import datetime
    now = datetime.datetime.now()
    return now.year

def generate_search_string(company_name, year):
    """ Return cql search string given a company_name string and year. """
    return """pa="{0}" and pn=EP and pd within {1}""".format(company_name, year)

def get_search(raw_companies_list):
    """ Get search results for companies in raw_companies_list. """

    # Initialise year
    year = get_current_year()
    # Intialise data dump
    data = []
    
    for company in raw_companies_list:
        company_name = process_name(company)
        search_string = generate_search_string(company_name, year)
        logging.info("Processing {0} with Search String: {1}".format(company, search_string))
        try:
            results = registered_client.published_data_search(search_string, range_begin=1, range_end=100)
            results_json = results.json()['ops:world-patent-data']['ops:biblio-search']
           
            total_results = safeget(results_json, '@total-result-count')
            logging.info("Total results: {0}".format(total_results))
            number_objects = check_list(safeget(results_json,'ops:search-result','ops:publication-reference'))
            if number_objects:
                numbers = [safeget(result,'document-id','country','$') + safeget(result, 'document-id', 'doc-number','$') for result in number_objects]
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
    # Add here to first check cached data?
    
    register_search = registered_client.register("publication", Epodoc(number))
    result = register_search.json()
    # These can sometimes have multi entries so we'll use checklist to 
    # turn them all into a list (some with only one entry)
    raw_agents = check_list(keysearch(result,'reg:agents'))
    raw_classifications = check_list(keysearch(result,'reg:classifications-ipcr'))
    
    # Get first agent / classification
    result_dict = {
        "agent" : keysearch(raw_agents[0],'reg:name').get('$', None),
        "agent_first_address" : keysearch(raw_agents[0],'reg:address-1').get('$', None),
        "agent_country" : keysearch(raw_agents[0],'reg:country').get('$', None),
        "classification" : keysearch(raw_classifications[0],'reg:text').get('$', None)
        }
    return result_dict
    