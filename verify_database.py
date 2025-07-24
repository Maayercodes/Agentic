import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

# Setup logging
logger.add("logs/verify_database.log", rotation="500 MB", level="INFO")

def verify_database():
    """Verify database connection and schema."""
    try:
        # Load environment variables
        load_dotenv()
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable is not set")
            return False
        
        # Fix for malformed DATABASE_URL that includes 'DATABASE_URL=' prefix or 'DATABASE_URL = ' format
        if database_url.startswith('DATABASE_URL='):
            database_url = database_url.replace('DATABASE_URL=', '', 1)
            logger.info("Fixed malformed DATABASE_URL by removing prefix")
        
        # Fix for 'DATABASE_URL = ' format
        if 'DATABASE_URL =' in database_url or 'DATABASE_URL=' in database_url:
            # Use regex to extract just the connection string
            import re
            connection_match = re.search(r'postgresql://[^\s]+', database_url)
            if connection_match:
                database_url = connection_match.group(0)
                logger.info("Fixed malformed DATABASE_URL by extracting connection string")
            else:
                logger.warning("Could not extract PostgreSQL connection string from DATABASE_URL")
        
        logger.info(f"Connecting to database: {database_url}")
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info(f"Connection test: {result.scalar() == 1}")
        
        # Check tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tables in database: {tables}")
        
        required_tables = ['daycares', 'influencers', 'outreach_history']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")
        else:
            logger.info("All required tables exist")
        
        # Check daycare table schema
        if 'daycares' in tables:
            columns = inspector.get_columns('daycares')
            column_names = [col['name'] for col in columns]
            logger.info(f"Columns in daycares table: {column_names}")
            
            # Check region column type
            region_column = next((col for col in columns if col['name'] == 'region'), None)
            if region_column:
                logger.info(f"Region column type: {region_column['type']}")
                
                # Check if it's a problematic type
                if hasattr(region_column['type'], 'name') and region_column['type'].name == 'region':
                    logger.warning("Region column is still using ENUM type. Migration needed.")
                else:
                    logger.info("Region column type looks good")
            else:
                logger.warning("Region column not found in daycares table")
        
        # Check for sample data
        if 'daycares' in tables:
            with engine.connect() as conn:
                result = conn.execute(text('SELECT COUNT(*) FROM daycares'))
                count = result.scalar()
                logger.info(f"Number of records in daycares table: {count}")
                
                if count > 0:
                    # Sample a record to check structure
                    result = conn.execute(text('SELECT * FROM daycares LIMIT 1'))
                    sample = result.fetchone()
                    logger.info(f"Sample record: {sample}")
        
        return True
    
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

def main():
    """Main function to verify the database."""
    logger.info("Starting database verification...")
    success = verify_database()
    
    if success:
        logger.info("Database verification completed")
        print("✅ Database verification completed. Check logs/verify_database.log for details.")
    else:
        logger.error("Database verification failed")
        print("❌ Database verification failed. Check logs/verify_database.log for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()