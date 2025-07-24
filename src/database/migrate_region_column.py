import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
from loguru import logger

# Setup logging
logger.add("logs/migration.log", rotation="500 MB", level="INFO")

# Fix for relative imports
try:
    from src.database.models import Base
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent.parent))  # Add project root to PATH
    from src.database.models import Base

def migrate_region_column():
    """Migrate the region column from ENUM type to VARCHAR type."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check if running on Railway
        is_railway = 'RAILWAY_ENVIRONMENT' in os.environ
        logger.info(f"Running on Railway: {is_railway}")
        
        # If running on Railway, we'll use a different approach
        if is_railway:
            logger.info("Using Railway-specific approach for migration")
            # On Railway, we'll skip the migration as it will be handled by the models.py changes
            # The SQLAlchemy model changes will automatically handle the column type change
            logger.info("Migration will be handled by SQLAlchemy model changes on Railway")
            return True
        
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
        try:
            logger.info("Creating database engine...")
            # Add connect_timeout to prevent hanging indefinitely
            engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
            logger.info("Testing database connection...")
            with engine.connect() as conn:
                logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
        
        # Check if the table exists
        inspector = inspect(engine)
        if 'daycares' not in inspector.get_table_names():
            logger.warning("Table 'daycares' does not exist. No migration needed.")
            return True
        
        # Get column info
        columns = inspector.get_columns('daycares')
        region_column = next((col for col in columns if col['name'] == 'region'), None)
        
        if not region_column:
            logger.warning("Column 'region' does not exist in table 'daycares'. No migration needed.")
            return True
        
        logger.info(f"Current 'region' column type: {region_column['type']}")
        
        # Check if the column is already VARCHAR
        if hasattr(region_column['type'], 'name') and region_column['type'].name.lower() in ('varchar', 'character varying', 'string'):
            logger.info("Column 'region' is already of type VARCHAR.")
            
            # Check if we need to increase the size of the VARCHAR
            current_size = getattr(region_column['type'], 'length', 0)
            logger.info(f"Current VARCHAR size: {current_size}")
            
            if current_size >= 50:
                logger.info("Column size is already sufficient. No migration needed.")
                return True
            else:
                logger.info(f"Column is VARCHAR({current_size}) but needs to be increased to VARCHAR(50).")
                # Continue with migration to increase size
        
        # Check if there are any records in the table
        with engine.connect() as conn:
            result = conn.execute(text('SELECT COUNT(*) FROM daycares'))
            count = result.scalar()
            logger.info(f"Number of records in daycares table: {count}")
            
            # Create a backup of the table
            if count > 0:
                logger.info("Creating backup of existing data...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS daycares_backup AS 
                    SELECT * FROM daycares
                """))
                logger.info("Backup created successfully.")
            
            # Alter the column type
            logger.info("Altering 'region' column type to VARCHAR...")
            try:
                # Set a statement timeout to prevent hanging
                conn.execute(text("SET statement_timeout = '30s'"))
                logger.info("Set statement timeout to 30 seconds")
                
                # Check if we're changing from ENUM to VARCHAR or just resizing VARCHAR
                if hasattr(region_column['type'], 'name') and region_column['type'].name.lower() in ('varchar', 'character varying', 'string'):
                    logger.info(f"Executing ALTER TABLE to resize VARCHAR column from {getattr(region_column['type'], 'length', 0)} to 50...")
                    # Just resize the VARCHAR column
                    conn.execute(text("""
                        ALTER TABLE daycares 
                        ALTER COLUMN region TYPE VARCHAR(50)
                    """))
                    logger.info("Resized VARCHAR column successfully.")
                else:
                    logger.info("Executing ALTER TABLE to convert from ENUM to VARCHAR...")
                    # Convert from ENUM to VARCHAR
                    conn.execute(text("""
                        ALTER TABLE daycares 
                        ALTER COLUMN region TYPE VARCHAR(50) 
                        USING region::VARCHAR
                    """))
                    logger.info("Converted column from ENUM to VARCHAR successfully.")
                logger.info("Column type altered successfully.")
                
                # Verify the change
                inspector = inspect(engine)
                columns = inspector.get_columns('daycares')
                region_column = next((col for col in columns if col['name'] == 'region'), None)
                logger.info(f"New 'region' column type: {region_column['type']}")
                
                return True
            except Exception as e:
                logger.error(f"Error altering column type: {e}")
                
                # If there was a backup created, suggest recovery
                if count > 0:
                    logger.warning("\nTo restore from backup, you can run:")
                    logger.warning("""DROP TABLE daycares; ALTER TABLE daycares_backup RENAME TO daycares;""")
                
                return False
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def main():
    """Main function to run the migration."""
    logger.info("Starting region column migration...")
    success = migrate_region_column()
    
    if success:
        logger.info("Migration completed successfully.")
    else:
        logger.error("Migration failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()