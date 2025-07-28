import os
from openai import OpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def test_openai_connection():
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL')
    
    print(f"API Key: {'*' * (len(api_key) - 8) + api_key[-8:] if api_key else 'Not set'}")
    print(f"Base URL: {base_url if base_url else 'Default'}")
    
    try:
        # Initialize the client
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        
        # Test connection
        models = client.models.list()
        print('\nOpenAI API connection successful!')
        print(f'Available models: {[model.id for model in models.data[:3]]}\n')
        return True
    except Exception as e:
        print(f'\nError connecting to OpenAI API: {type(e).__name__}: {str(e)}\n')
        return False

if __name__ == "__main__":
    test_openai_connection()