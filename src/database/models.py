from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Enum, Text, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize SQLAlchemy base class
Base = declarative_base()

class Region(enum.Enum):
    USA = "USA"
    FRANCE = "FRANCE"

class Platform(enum.Enum):
    YOUTUBE = "YOUTUBE"
    INSTAGRAM = "INSTAGRAM"

class Daycare(Base):
    __tablename__ = 'daycares'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(500))
    # Changed from Enum(Region) to String(50) for compatibility
    region = Column(String(50), nullable=False)
    source = Column(String(100))  # e.g., 'yelp', 'care.com', etc.
    last_contacted = Column(DateTime)
    email_opened = Column(Boolean, default=False)
    email_replied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Daycare(name='{self.name}', city='{self.city}', region='{self.region}')>"

class Influencer(Base):
    __tablename__ = 'influencers'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    platform = Column(Enum(Platform), nullable=False)
    follower_count = Column(Integer)
    country = Column(String(100))
    email = Column(String(255))
    bio = Column(Text)
    contact_page = Column(String(500))
    niche = Column(String(100))  # e.g., 'parenting', 'education', 'kids'
    last_contacted = Column(DateTime)
    email_opened = Column(Boolean, default=False)
    email_replied = Column(Boolean, default=False)
    engagement_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        platform_str = self.platform.value if hasattr(self.platform, 'value') else str(self.platform)
        return f"<Influencer(name='{self.name}', platform='{platform_str}', followers='{self.follower_count}')>"

class OutreachHistory(Base):
    __tablename__ = 'outreach_history'

    id = Column(Integer, primary_key=True)
    target_type = Column(String(50))  # 'daycare' or 'influencer'
    target_id = Column(Integer, nullable=False)
    email_subject = Column(String(255))
    email_content = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    opened_at = Column(DateTime)
    replied_at = Column(DateTime)
    bounced = Column(Boolean, default=False)
    language = Column(String(10))  # 'en' or 'fr'

    def __repr__(self):
        return f"<OutreachHistory(target_type='{self.target_type}', target_id='{self.target_id}', sent_at='{self.sent_at}')>"

# Database connection setup
def init_db():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Fix for malformed DATABASE_URL that includes 'DATABASE_URL=' prefix or 'DATABASE_URL = ' format
    if database_url.startswith('DATABASE_URL='):
        database_url = database_url.replace('DATABASE_URL=', '', 1)
        print("Fixed malformed DATABASE_URL by removing prefix")
    
    # Fix for 'DATABASE_URL = ' format
    if 'DATABASE_URL =' in database_url or 'DATABASE_URL=' in database_url:
        # Use regex to extract just the connection string
        import re
        connection_match = re.search(r'postgresql://[^\s]+', database_url)
        if connection_match:
            database_url = connection_match.group(0)
            print("Fixed malformed DATABASE_URL by extracting connection string")
        else:
            print("Warning: Could not extract PostgreSQL connection string from DATABASE_URL")
    
    engine = create_engine(database_url, pool_pre_ping=True)
    
    # Ensure tables exist
    try:
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        required_tables = ['daycares', 'influencers', 'outreach_history']
        
        # Check which tables need to be created
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            # Create missing tables
            Base.metadata.create_all(engine)
            print(f"Created tables: {missing_tables}")
        else:
            print("All required tables already exist")
            
            # Check if region column needs to be updated
            try:
                columns = inspector.get_columns('daycares')
                region_column = next((col for col in columns if col['name'] == 'region'), None)
                
                if region_column and hasattr(region_column['type'], 'name') and region_column['type'].name == 'region':
                    # If region column is of type 'region', alter it to VARCHAR
                    with engine.begin() as conn:
                        conn.execute(text("""
                            ALTER TABLE daycares 
                            ALTER COLUMN region TYPE VARCHAR(50) 
                            USING region::VARCHAR
                        """))
                    print("Updated 'region' column type from ENUM to VARCHAR")
            except Exception as e:
                print(f"Warning: Could not check or update region column type: {e}")
        
        Session = sessionmaker(bind=engine)
        return Session()
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise