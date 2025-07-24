import asyncio
import os
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

async def test_restore():
    try:
        # Clear any custom base URL that might have been set
        if 'OPENAI_BASE_URL' in os.environ:
            del os.environ['OPENAI_BASE_URL']
        
        logger.info("Initializing database session")
        session = init_db()
        
        logger.info("Creating AI Assistant with normal configuration")
        assistant = AIAssistant(session)
        
        logger.info("Testing process_command after restoring environment")
        result = await assistant.process_command('Find all influencers in France')
        
        logger.info(f"Result after restoring environment: {result}")
        return result
    except Exception as e:
        logger.error(f"Test failed: {type(e).__name__}: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting restore test")
    try:
        result = asyncio.run(test_restore())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")