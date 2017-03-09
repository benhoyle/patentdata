import os
import json
from datetime import datetime

# Define name and path for SQLite3 DB
db_name = "patentcache.db"
db_path = os.path.join(os.getcwd(), db_name)

# Create DB
from sqlalchemy import create_engine
engine = create_engine('sqlite:///' + db_path, echo=False)

# Setup imports
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

# Define Class for Excluded Matter Case Details
from sqlalchemy import Column, String, Integer

class Base(object):
    """ Extensions to Base class. """
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id =  Column(Integer, primary_key=True)

Base = declarative_base(cls=Base)

    
class RegisterCache(Base):
    """ Model for storing a cached register page. """
    # Publication number in EPODOC format
    pub_no = Column(String(128))
    
    raw_response = Column(String)
    
    def __init__(self, number, response):
        self.pub_no = number
        self.storeresponse(response)
    
    def storeresponse(self, data):
        """ Convert data from JSON to string and store. """
        self.raw_response = json.dumps(data)
        
    def loadresponse(self):
        """ Load JSON from saved string. """
        return json.loads(self.raw_response)
    
# Create new DB    
Base.metadata.create_all(engine)

# Setup SQLAlchemy session
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)