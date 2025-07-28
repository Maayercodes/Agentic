import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

# Configure logger
logger.add("logs/update_assistant.log", rotation="10 MB", level="DEBUG")

def update_assistant_export_function():
    """
    Update the AI assistant's _handle_export function with the improved version.
    """
    try:
        # Path to the assistant.py file
        assistant_path = os.path.join(os.path.dirname(__file__), 'src', 'ai_assistant', 'assistant.py')
        
        # Read the current file content
        with open(assistant_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the _handle_export function
        start_marker = "async def _handle_export(self, params: Dict[str, Any]) -> Dict[str, Any]:"
        end_marker = "    def _generate_fallback_response(self, command: str) -> Dict[str, Any]:"
        
        # Split the content
        parts = content.split(start_marker)
        if len(parts) != 2:
            logger.error("Could not find _handle_export function in assistant.py")
            return False
        
        pre_function = parts[0]
        
        parts = parts[1].split(end_marker)
        if len(parts) != 2:
            logger.error("Could not find end of _handle_export function in assistant.py")
            return False
        
        post_function = end_marker + parts[1]
        
        # New implementation of _handle_export
        new_function = '''"""Handle export contacts command with improved error handling and path management."""
        try:
            import csv
            import tempfile
            import os
            from datetime import datetime
            
            logger.info(f"Starting export with params: {params}")
            
            target_type = params.get('target_type', '').lower().strip()
            export_format = params.get('format', 'csv').lower().strip()
            region = params.get('region')
            
            if export_format != 'csv':
                return {"error": f"Unsupported export format: {export_format}. Only CSV is currently supported."}
            
            # Create query based on target type
            if 'daycare' in target_type:
                query = self.session.query(Daycare)
                if region and region.lower() not in ['all regions', 'all countries']:
                    query = query.filter(Daycare.region == region)
                contacts = query.all()
                
                # Define fields for CSV
                fieldnames = ['id', 'name', 'address', 'city', 'email', 'phone', 'website', 'region', 'source', 
                             'last_contacted', 'email_opened', 'email_replied', 'created_at', 'updated_at']
                
            elif 'influencer' in target_type:
                query = self.session.query(Influencer)
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
                    project_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    data_dir = os.path.join(project_dir, "data")
                    os.makedirs(data_dir, exist_ok=True)
                    filepath = os.path.join(data_dir, filename)
                    
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
            return {"error": f"Export failed: {str(e)}"}'''
        
        # Combine the parts
        new_content = pre_function + start_marker + new_function + post_function
        
        # Create a backup of the original file
        backup_path = assistant_path + '.bak'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created backup of assistant.py at {backup_path}")
        
        # Write the updated content
        with open(assistant_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"Updated _handle_export function in {assistant_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating assistant.py: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    print("Updating AI assistant export function...")
    success = update_assistant_export_function()
    
    if success:
        print("✅ Successfully updated AI assistant export function")
        print("Restart the Streamlit application to apply the changes")
    else:
        print("❌ Failed to update AI assistant export function")
        print("Check the logs for details")