import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import tempfile
from datetime import datetime
import csv
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.models import init_db, Daycare, Influencer
from loguru import logger

load_dotenv()

# Configure logger
logger.add("logs/fix_export.log", rotation="10 MB", level="DEBUG")

def export_to_csv(session: Session, target_type: str, region: str = None) -> dict:
    """
    Export contacts to CSV file with improved error handling and path management.
    
    Args:
        session: Database session
        target_type: Type of contacts to export ('daycare' or 'influencer')
        region: Optional region filter
        
    Returns:
        Dictionary with export results
    """
    try:
        logger.info(f"Starting export of {target_type}s to CSV")
        
        # Create query based on target type
        if 'daycare' in target_type:
            query = session.query(Daycare)
            if region and region.lower() not in ['all regions', 'all countries']:
                query = query.filter(Daycare.region == region)
            contacts = query.all()
            
            # Define fields for CSV
            fieldnames = ['id', 'name', 'address', 'city', 'email', 'phone', 'website', 'region', 'source', 
                         'last_contacted', 'email_opened', 'email_replied', 'created_at', 'updated_at']
            
        elif 'influencer' in target_type:
            query = session.query(Influencer)
            if region and region.lower() not in ['all regions', 'all countries']:
                query = query.filter(Influencer.country == region)
            contacts = query.all()
            
            # Define fields for CSV
            fieldnames = ['id', 'name', 'platform', 'follower_count', 'country', 'email', 'bio', 'contact_page', 
                         'niche', 'last_contacted', 'email_opened', 'email_replied', 'engagement_rate', 
                         'created_at', 'updated_at']
        else:
            error_msg = f"Unsupported target_type: {target_type}. Use 'daycare' or 'influencer'."
            logger.error(error_msg)
            return {"error": error_msg}
        
        if not contacts:
            error_msg = f"No {target_type}s found matching your criteria."
            logger.warning(error_msg)
            return {"error": error_msg}
        
        logger.info(f"Found {len(contacts)} {target_type}s to export")
        
        # Create a temporary file with proper error handling
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{target_type}s_export_{timestamp}.csv"
        
        # Try system temp directory first
        try:
            system_temp = tempfile.gettempdir()
            filepath = os.path.join(system_temp, filename)
            logger.info(f"Attempting to create CSV at: {filepath}")
            
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
            
            # Verify file was created
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File was not created at {filepath}")
                
            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully created CSV at {filepath} (size: {file_size} bytes)")
            
            # Read file to verify content
            with open(filepath, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                logger.info(f"CSV header: {first_line}")
            
            return {
                "success": True,
                "message": f"Successfully exported {len(contacts)} {target_type}s to CSV",
                "file_path": filepath,
                "file_name": filename,
                "contact_count": len(contacts)
            }
            
        except Exception as e:
            logger.error(f"Error creating CSV in temp directory: {str(e)}")
            
            # Fallback to project directory
            try:
                logger.info("Falling back to project directory for CSV export")
                project_dir = os.path.abspath(os.path.dirname(__file__))
                filepath = os.path.join(project_dir, "data", filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                logger.info(f"Attempting to create CSV at: {filepath}")
                
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
                
                # Verify file was created
                if not os.path.exists(filepath):
                    raise FileNotFoundError(f"File was not created at {filepath}")
                    
                file_size = os.path.getsize(filepath)
                logger.info(f"Successfully created CSV at {filepath} (size: {file_size} bytes)")
                
                return {
                    "success": True,
                    "message": f"Successfully exported {len(contacts)} {target_type}s to CSV",
                    "file_path": filepath,
                    "file_name": filename,
                    "contact_count": len(contacts)
                }
                
            except Exception as e2:
                logger.error(f"Error creating CSV in project directory: {str(e2)}")
                return {"error": f"Failed to create CSV file: {str(e2)}"}
    
    except Exception as e:
        logger.error(f"Error in export contacts: {str(e)}")
        return {"error": f"Export failed: {str(e)}"}


def test_export():
    """
    Test the export functionality with both daycare and influencer data.
    """
    try:
        # Initialize database session
        logger.info("Initializing database session...")
        session = init_db()
        
        # Test daycare export
        logger.info("Testing daycare export...")
        daycare_result = export_to_csv(session, 'daycare')
        
        if 'error' in daycare_result:
            logger.error(f"Daycare export failed: {daycare_result['error']}")
            print(f"❌ Daycare export failed: {daycare_result['error']}")
        else:
            logger.info(f"Daycare export successful: {daycare_result['file_path']}")
            print(f"✅ Daycare export successful: {daycare_result['file_path']}")
        
        # Test influencer export
        logger.info("Testing influencer export...")
        influencer_result = export_to_csv(session, 'influencer')
        
        if 'error' in influencer_result:
            logger.error(f"Influencer export failed: {influencer_result['error']}")
            print(f"❌ Influencer export failed: {influencer_result['error']}")
        else:
            logger.info(f"Influencer export successful: {influencer_result['file_path']}")
            print(f"✅ Influencer export successful: {influencer_result['file_path']}")
        
        return daycare_result, influencer_result
        
    except Exception as e:
        logger.error(f"Error in test_export: {str(e)}")
        print(f"❌ Error in test_export: {str(e)}")
        return None, None
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    print("=== Testing CSV Export Functionality ===\n")
    daycare_result, influencer_result = test_export()
    
    print("\n=== Export Test Results ===")
    if daycare_result and 'success' in daycare_result:
        print(f"Daycare Export: ✅ SUCCESS")
        print(f"- File: {daycare_result['file_path']}")
        print(f"- Exported {daycare_result['contact_count']} daycares")
    else:
        print("Daycare Export: ❌ FAILED")
    
    if influencer_result and 'success' in influencer_result:
        print(f"\nInfluencer Export: ✅ SUCCESS")
        print(f"- File: {influencer_result['file_path']}")
        print(f"- Exported {influencer_result['contact_count']} influencers")
    else:
        print("\nInfluencer Export: ❌ FAILED")