import asyncio
import os
from dotenv import load_dotenv
from loguru import logger
from src.ai_assistant.assistant import AIAssistant
from src.database.models import init_db

async def test_email_sending():
    # Initialize database and assistant
    session = init_db()
    assistant = AIAssistant(session=session)
    
    # Test command
    command = "Send outreach email to 1 random daycare"
    
    # Process command
    logger.info(f"Processing command: {command}")
    result = await assistant.process_command(command)
    
    # Log result
    logger.info(f"Result: {result}")
    
    if 'error' in result:
        logger.error(f"Error: {result['error']}")
    else:
        logger.info(f"Success! Sent {result.get('messages_sent', 0)} emails.")
        logger.info(f"Details: {result.get('details', {})}")

if __name__ == "__main__":
    # Configure logger
    logger.add("logs/test_email_debug.log", level="DEBUG")
    
    # Run test
    asyncio.run(test_email_sending())