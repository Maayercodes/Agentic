import asyncio
import os
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

async def test_connection_error():
    try:
        # Save original values
        original_api_key = os.environ.get('OPENAI_API_KEY')
        original_base_url = os.environ.get('OPENAI_BASE_URL')
        
        # Set valid API key but invalid base URL to simulate connection error
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        os.environ['OPENAI_BASE_URL'] = 'https://nonexistent-api-endpoint.example.com/v1'
        
        logger.info("Initializing database session")
        session = init_db()
        
        logger.info("Creating AI Assistant with invalid base URL")
        assistant = AIAssistant(session)
        
        logger.info("Testing process_command with connection error")
        result = await assistant.process_command('Find all influencers in France')
        
        logger.info(f"Result with connection error: {result}")
        
        # Restore original values
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            del os.environ['OPENAI_API_KEY']
            
        if original_base_url:
            os.environ['OPENAI_BASE_URL'] = original_base_url
        else:
            if 'OPENAI_BASE_URL' in os.environ:
                del os.environ['OPENAI_BASE_URL']
            
        return result
    except Exception as e:
        logger.error(f"Test failed: {type(e).__name__}: {str(e)}")
        # Restore original values
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            del os.environ['OPENAI_API_KEY']
            
        if original_base_url:
            os.environ['OPENAI_BASE_URL'] = original_base_url
        else:
            if 'OPENAI_BASE_URL' in os.environ:
                del os.environ['OPENAI_BASE_URL']
        raise

if __name__ == "__main__":
    logger.info("Starting connection error test")
    try:
        result = asyncio.run(test_connection_error())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")