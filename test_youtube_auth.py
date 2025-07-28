import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

load_dotenv()

def test_youtube_api_with_key():
    """Test YouTube API with API key"""
    try:
        youtube_api_key = os.getenv('YOUTUBE_API_KEY')
        print(f"Using YouTube API key: {youtube_api_key[:5]}...")
        
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        request = youtube.channels().list(part='snippet', forUsername='GoogleDevelopers')
        response = request.execute()
        
        print("YouTube API with key successful!")
        print(f"Found {len(response.get('items', []))} channels")
        return True
    except Exception as e:
        print(f"YouTube API with key failed: {e}")
        return False

def test_youtube_api_with_adc():
    """Test YouTube API with Application Default Credentials"""
    try:
        # This will use the Application Default Credentials
        # No explicit credentials needed if properly set up
        youtube = build('youtube', 'v3')
        request = youtube.channels().list(part='snippet', forUsername='GoogleDevelopers')
        response = request.execute()
        
        print("YouTube API with ADC successful!")
        print(f"Found {len(response.get('items', []))} channels")
        return True
    except Exception as e:
        print(f"YouTube API with ADC failed: {e}")
        return False

def test_youtube_api_with_service_account():
    """Test YouTube API with service account credentials"""
    try:
        # Path to service account JSON file
        service_account_file = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not service_account_file or not os.path.exists(service_account_file):
            print(f"Service account file not found: {service_account_file}")
            return False
            
        print(f"Using service account file: {service_account_file}")
        
        # Create credentials from service account file
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/youtube.readonly']
        )
        
        # Build the YouTube API client with the credentials
        youtube = build('youtube', 'v3', credentials=credentials)
        request = youtube.channels().list(part='snippet', forUsername='GoogleDevelopers')
        response = request.execute()
        
        print("YouTube API with service account successful!")
        print(f"Found {len(response.get('items', []))} channels")
        return True
    except Exception as e:
        print(f"YouTube API with service account failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing YouTube API authentication methods...\n")
    
    # Try all authentication methods
    key_success = test_youtube_api_with_key()
    print("\n" + "-"*50 + "\n")
    
    adc_success = test_youtube_api_with_adc()
    print("\n" + "-"*50 + "\n")
    
    sa_success = test_youtube_api_with_service_account()
    
    print("\n" + "="*50)
    print("SUMMARY:")
    print(f"API Key Authentication: {'✓ SUCCESS' if key_success else '✗ FAILED'}")
    print(f"Application Default Credentials: {'✓ SUCCESS' if adc_success else '✗ FAILED'}")
    print(f"Service Account Authentication: {'✓ SUCCESS' if sa_success else '✗ FAILED'}")
    print("="*50)