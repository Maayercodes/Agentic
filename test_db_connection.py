import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def test_db_connection():
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL environment variable is not set")
        return False
    
    print(f"Original DATABASE_URL: {database_url}")
    
    # Fix for malformed DATABASE_URL that includes 'DATABASE_URL=' prefix or 'DATABASE_URL = ' format
    if database_url.startswith('DATABASE_URL='):
        database_url = database_url.replace('DATABASE_URL=', '', 1)
        print("✅ Fixed malformed DATABASE_URL by removing prefix")
    
    # Fix for 'DATABASE_URL = ' format
    if 'DATABASE_URL =' in database_url or 'DATABASE_URL=' in database_url:
        # Use regex to extract just the connection string
        import re
        connection_match = re.search(r'postgresql://[^\s]+', database_url)
        if connection_match:
            database_url = connection_match.group(0)
            print("✅ Fixed malformed DATABASE_URL by extracting connection string")
        else:
            print("⚠️ Could not extract PostgreSQL connection string from DATABASE_URL")
    
    print(f"Processed DATABASE_URL: {database_url}")
    
    try:
        # Create engine
        print("Creating SQLAlchemy engine...")
        engine = create_engine(database_url, pool_pre_ping=True)
        
        # Test connection
        print("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("✅ Database connection successful!")
                return True
            else:
                print("❌ Database connection failed: Unexpected result")
                return False
    
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Database Connection Test ===")
    success = test_db_connection()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)