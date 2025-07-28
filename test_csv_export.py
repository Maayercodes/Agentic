import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import asyncio
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.models import init_db, Daycare, Influencer
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

# Configure logger
logger.add("logs/csv_test.log", rotation="10 MB", level="DEBUG")

async def test_csv_export():
    try:
        # Initialize database session and assistant
        logger.info("Initializing database session and assistant...")
        session = init_db()
        assistant = AIAssistant(session)
        
        # Test daycare export
        logger.info("Testing daycare export...")
        daycare_result = await assistant.process_command("Export daycares to CSV")
        
        if 'error' in daycare_result:
            logger.error(f"Daycare export failed: {daycare_result['error']}")
            print(f"❌ Daycare export failed: {daycare_result['error']}")
            daycare_success = False
        else:
            logger.info(f"Daycare export successful: {daycare_result.get('file_path', 'No file path returned')}")
            print(f"✅ Daycare export successful: {daycare_result.get('file_path', 'No file path returned')}")
            print(f"   - Exported {daycare_result.get('contact_count', 0)} daycares")
            
            # Verify file exists
            file_path = daycare_result.get('file_path')
            if file_path and os.path.exists(file_path):
                print(f"   - File exists: {file_path}")
                print(f"   - File size: {os.path.getsize(file_path)} bytes")
                daycare_success = True
            else:
                print(f"   - ❌ File does not exist: {file_path}")
                daycare_success = False
        
        # Test influencer export
        logger.info("Testing influencer export...")
        influencer_result = await assistant.process_command("Export influencers to CSV")
        
        if 'error' in influencer_result:
            logger.error(f"Influencer export failed: {influencer_result['error']}")
            print(f"❌ Influencer export failed: {influencer_result['error']}")
            influencer_success = False
        else:
            logger.info(f"Influencer export successful: {influencer_result.get('file_path', 'No file path returned')}")
            print(f"✅ Influencer export successful: {influencer_result.get('file_path', 'No file path returned')}")
            print(f"   - Exported {influencer_result.get('contact_count', 0)} influencers")
            
            # Verify file exists
            file_path = influencer_result.get('file_path')
            if file_path and os.path.exists(file_path):
                print(f"   - File exists: {file_path}")
                print(f"   - File size: {os.path.getsize(file_path)} bytes")
                influencer_success = True
            else:
                print(f"   - ❌ File does not exist: {file_path}")
                influencer_success = False
        
        return daycare_success and influencer_success
        
    except Exception as e:
        logger.error(f"Error in test_csv_export: {str(e)}")
        print(f"❌ Error in test_csv_export: {str(e)}")
        return False
    finally:
        if 'session' in locals():
            session.close()

def export_to_csv(session: Session, target_type: str) -> bool:
    try:
        # Create query based on target type
        if target_type == 'daycare':
            query = session.query(Daycare)
            contacts = query.all()
            
            # Define fields for CSV
            fieldnames = ['name', 'address', 'city', 'email', 'phone', 'website', 'region', 'source', 
                         'last_contacted', 'email_opened', 'email_replied', 'created_at', 'updated_at']
            
        elif target_type == 'influencer':
            query = session.query(Influencer)
            contacts = query.all()
            
            # Define fields for CSV
            fieldnames = ['name', 'email', 'platform', 'follower_count', 'country', 'niche', 
                         'last_contacted', 'email_opened', 'email_replied', 'created_at', 'updated_at']
        else:
            logger.error(f"Unsupported target_type: {target_type}")
            return False
        
        if not contacts:
            logger.warning(f"No {target_type}s found in the database")
            print(f"⚠️ No {target_type}s found in the database")
            return False
        
        # Create a temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_type}s_export_{timestamp}.csv"
        filepath = os.path.join(tempfile.gettempdir(), filename)
        
        # Write data to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for contact in contacts:
                row = {}
                for field in fieldnames:
                    value = getattr(contact, field, None)
                    
                    # Handle Enum values
                    if hasattr(value, 'value'):
                        value = value.value
                        
                    # Format datetime objects
                    if isinstance(value, datetime):
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                        
                    row[field] = value
                writer.writerow(row)
        
        # Verify the file was created
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully exported {len(contacts)} {target_type}s to CSV at {filepath} (size: {file_size} bytes)")
            print(f"✅ Successfully exported {len(contacts)} {target_type}s to CSV")
            print(f"📄 File: {filepath}")
            print(f"📊 File size: {file_size} bytes")
            return True
        else:
            logger.error(f"Failed to create CSV file at {filepath}")
            print(f"❌ Failed to create CSV file")
            return False
            
    except Exception as e:
        logger.error(f"Error exporting {target_type}s to CSV: {str(e)}")
        print(f"❌ Error exporting {target_type}s to CSV: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== CSV Export Test ===\n")
    load_dotenv()
    success = asyncio.run(test_csv_export())
    
    if success:
        print("\n✅ CSV export functionality is working!")
        exit(0)
    else:
        print("\n❌ CSV export functionality test failed!")
        exit(1)