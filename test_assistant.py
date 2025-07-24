import asyncio
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant
from loguru import logger

async def test():
    try:
        logger.info("Initializing database session")
        session = init_db()
        
        logger.info("Creating AI Assistant")
        assistant = AIAssistant(session)
        
        logger.info("Testing process_command with 'Find all influencers in France'")
        result = await assistant.process_command('Find all influencers in France')
        
        logger.info(f"Result: {result}")
        return result
    except Exception as e:
        logger.error(f"Test failed: {type(e).__name__}: {str(e)}")
        raise

if __name__ == "__main__":
    logger.info("Starting assistant test")
    try:
        result = asyncio.run(test())
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")