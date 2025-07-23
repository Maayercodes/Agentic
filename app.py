import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import streamlit.web.bootstrap as bootstrap
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def ensure_tables_exist():
    """Ensure all database tables are created before starting the app."""
    try:
        # Import database models
        from src.database.models import Base, Daycare, Influencer, OutreachHistory
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        
        logger.info(f"Connecting to database: {database_url}")
        
        # Create engine with connection pooling and health checks
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connection before using from pool
            pool_recycle=3600,   # Recycle connections after 1 hour
            connect_args={       # Set connection timeout
                'connect_timeout': 10
            }
        )
        
        # Test connection
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                logger.info("Database connection successful")
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
        
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        logger.info("Database tables created or verified successfully")
        
        # Verify tables were created
        inspector = inspect(engine)
        tables_after = inspector.get_table_names()
        logger.info(f"Tables after creation: {tables_after}")
        
        # Check for specific tables
        required_tables = ['daycares', 'influencers', 'outreach_history']
        for table in required_tables:
            if table not in tables_after:
                logger.error(f"Table '{table}' was not created!")
            else:
                logger.info(f"Table '{table}' exists")
                
        return True
    
    except Exception as e:
        logger.error(f"Error ensuring tables exist: {str(e)}")
        return False

def main():
    # Ensure database tables exist before starting the app
    if not ensure_tables_exist():
        logger.error("Failed to ensure database tables exist. Exiting.")
        sys.exit(1)
    
    # Start the Streamlit app
    logger.info("Starting Streamlit app")
    
    # Determine the script path for Streamlit
    streamlit_script_path = os.path.join("src", "ui", "app.py")
    
    # Check if the file exists
    if not os.path.exists(streamlit_script_path):
        logger.error(f"Streamlit script not found at {streamlit_script_path}")
        sys.exit(1)
    
    # Run the Streamlit app
    # Use the Streamlit CLI instead of bootstrap
    import subprocess
    
    # Build the command
    cmd = [
        sys.executable, 
        "-m", 
        "streamlit", 
        "run", 
        streamlit_script_path,
        "--server.port=8080", 
        "--server.headless=true"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()