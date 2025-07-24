import os
import dotenv
from sqlalchemy import create_engine, text, inspect

# Load environment variables
dotenv.load_dotenv()
db_url = os.getenv("DATABASE_URL")

if not db_url:
    raise ValueError("Please set the DATABASE_URL environment variable.")

# Create engine
engine = create_engine(db_url, pool_pre_ping=True)

# Check if the table exists and the column type
with engine.connect() as conn:
    # Check if the table exists
    inspector = inspect(engine)
    if 'daycares' not in inspector.get_table_names():
        print("Table 'daycares' does not exist.")
        exit(0)
    
    # Get column info
    columns = inspector.get_columns('daycares')
    region_column = next((col for col in columns if col['name'] == 'region'), None)
    
    if not region_column:
        print("Column 'region' does not exist in table 'daycares'.")
        exit(0)
    
    print(f"Current 'region' column type: {region_column['type']}")
    
    # Check if there are any records in the table
    result = conn.execute(text('SELECT COUNT(*) FROM daycares'))
    count = result.scalar()
    print(f"Number of records in daycares table: {count}")
    
    # Alter the column type to VARCHAR
    try:
        # First create a backup of existing data if there are records
        if count > 0:
            print("Creating backup of existing data...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daycares_backup AS 
                SELECT * FROM daycares
            """))
            print("Backup created successfully.")
        
        # Alter the column type
        print("Altering 'region' column type to VARCHAR...")
        conn.execute(text("""
            ALTER TABLE daycares 
            ALTER COLUMN region TYPE VARCHAR 
            USING region::VARCHAR
        """))
        print("Column type altered successfully.")
        
        # Verify the change
        inspector = inspect(engine)
        columns = inspector.get_columns('daycares')
        region_column = next((col for col in columns if col['name'] == 'region'), None)
        print(f"New 'region' column type: {region_column['type']}")
        
    except Exception as e:
        print(f"Error altering column type: {e}")
        
        # If there was a backup created, suggest recovery
        if count > 0:
            print("\nTo restore from backup, you can run:")
            print("""DROP TABLE daycares; ALTER TABLE daycares_backup RENAME TO daycares;""")