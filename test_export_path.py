import os
import tempfile
from datetime import datetime
import csv

def test_export_path():
    # Get the system temp directory
    system_temp = tempfile.gettempdir()
    print(f"System temp directory: {system_temp}")
    
    # Create a test file in the temp directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_export_{timestamp}.csv"
    filepath = os.path.join(system_temp, filename)
    
    try:
        # Try to write to the file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['test', 'header'])
            writer.writerow(['test', 'data'])
        
        # Check if the file exists
        if os.path.exists(filepath):
            print(f"Successfully created file at: {filepath}")
            # Read the file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"File content: {content}")
            # Clean up
            os.remove(filepath)
            print("File removed successfully")
            return True
        else:
            print(f"File creation failed. File does not exist at: {filepath}")
            return False
    except Exception as e:
        print(f"Error creating file: {str(e)}")
        return False

# Try with project directory as alternative
def test_project_directory():
    # Use the current directory
    project_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"Project directory: {project_dir}")
    
    # Create a test file in the project directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_export_{timestamp}.csv"
    filepath = os.path.join(project_dir, filename)
    
    try:
        # Try to write to the file
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['test', 'header'])
            writer.writerow(['test', 'data'])
        
        # Check if the file exists
        if os.path.exists(filepath):
            print(f"Successfully created file at: {filepath}")
            # Read the file content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"File content: {content}")
            # Clean up
            os.remove(filepath)
            print("File removed successfully")
            return True
        else:
            print(f"File creation failed. File does not exist at: {filepath}")
            return False
    except Exception as e:
        print(f"Error creating file: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing export path...")
    temp_success = test_export_path()
    
    if not temp_success:
        print("\nTrying project directory as alternative...")
        project_success = test_project_directory()
        
        if project_success:
            print("\nRecommendation: Use project directory for exports instead of system temp directory")
        else:
            print("\nBoth system temp and project directory tests failed. Check file permissions.")
    else:
        print("\nSystem temp directory is working correctly for file exports")