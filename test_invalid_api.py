import asyncio
import os
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

async def test_invalid_api():
    try:
        # Save original API key
        original_api_key = os.environ.get('OPENAI_API_KEY')
        
        # Set invalid API key
        os.environ['OPENAI_API_KEY'] = 'invalid-key-for-testing'
        
        logger.info("Initializing database session")
        session = init_db()
        
        logger.info("Creating AI Assistant with invalid API key")
        assistant = AIAssistant(session)
        
        logger.info("Testing process_command with invalid API key")
        result = await assistant.process_command('Find all influencers in France')
        
        logger.info(f"Result with invalid API key: {result}")
        
        # Restore original API key
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            del os.environ['OPENAI_API_KEY']
            
        return result
    except Exception as e:
        logger.error(f"Test failed: {type(e).__name__}: {str(e)}")
        # Restore original API key
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            del os.environ['OPENAI_API_KEY']
        raise

if __name__ == "__main__":
    logger.info("Starting invalid API key test")
    try:
        result = asyncio.run(test_invalid_api())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")