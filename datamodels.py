import os
from datetime import datetime

# Define name and path for SQLite3 DB
db_name = "patentdata.db"
db_path = os.path.join(os.getcwd(), db_name)

# Create DB
from sqlalchemy import create_engine
engine = create_engine('sqlite:///' + db_path, echo=False)

# Setup imports
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship

# Define Class for Excluded Matter Case Details
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, \
                        ForeignKey

class Base(object):
    """ Extensions to Base class. """
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id =  Column(Integer, primary_key=True)
    
    def as_dict(self):
        """ Return object as a dictionary. """
        temp_dict = {}
        temp_dict['object_type'] = self.__class__.__name__
        for c in self.__table__.columns:
            cur_attr = getattr(self, c.name)
            # If datetime generate string representation
            if isinstance(cur_attr, datetime):
                cur_attr = cur_attr.strftime('%d %B %Y')
            temp_dict[c.name] = cur_attr
        return temp_dict
    
    def populate(self, data):
        """ Populates matching attributes of class instance. 
        param dict data: dict where for each entry key, value equal attributename, attributevalue."""
        for key, value in data.items():
            if hasattr(self, key):
                # Convert string dates into datetimes
                if isinstance(getattr(self, key), datetime) or str(self.__table__.c[key].type) == 'DATE':
                    value = datetime.strptime(value, "%d %B %Y")
                setattr(self, key, value)

Base = declarative_base(cls=Base)

class PatentSearch(Base):
    """ Model for a patent entity search, e.g. an applicant search. """
    # name - actual full name of applicant or company
    name = Column(String(256))
    
    # name used for search
    searched_name = Column(String(256))
    
    total_results = Column(Integer)
    
    # Should we also be storing the search string and the range?
    
    # Relationship defining search results
    publications = relationship("PatentPublication", backref="patentsearch")
    
class PatentPublication(Base):
    """ Model for a patent publication. """
    # Publication number in EPODOC format
    pub_no = Column(String(128))
    
    # Foreign key for associated search
    search_id = Column(Integer, ForeignKey('patentsearch.id'))
    
    # Raw agent and classification data
    raw_agent = Column(String(256))
    raw_agent_first_address = Column(String(256))
    raw_agent_country = Column(String(256))
    raw_classification = Column(String(256))
    
# Create new DB    
Base.metadata.create_all(engine)

# Setup SQLAlchemy session
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)