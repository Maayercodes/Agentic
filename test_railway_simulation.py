import os
import asyncio
import sys
from loguru import logger
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/test_railway.log", rotation="500 KB", level="DEBUG")

async def test():
    # Save original environment variables
    original_api_key = os.environ.get('OPENAI_API_KEY')
    original_base_url = os.environ.get('OPENAI_BASE_URL')
    
    try:
        # Simulate Railway environment
        os.environ['RAILWAY_ENVIRONMENT'] = 'true'
        
        # Simulate a connection issue by setting an invalid base URL
        os.environ['OPENAI_BASE_URL'] = 'https://nonexistent-api-endpoint.example.com/v1'
        
        logger.info("Starting Railway simulation test")
        logger.info("Initializing database session")
        session = init_db()
        
        logger.info("Creating AI Assistant with simulated Railway environment")
        assistant = AIAssistant(session)
        
        logger.info("Processing command with expected connection error")
        result = await assistant.process_command("Find all influencers in France")
        
        logger.info(f"Result: {result}")
        
        # Check if the result contains Railway-specific error information
        if result.get('environment') == 'railway' and 'Railway' in result.get('suggestion', ''):
            logger.info("✅ Test PASSED: Railway environment correctly detected and handled")
        else:
            logger.error("❌ Test FAILED: Railway environment not correctly handled")
            
        return result
        
    finally:
        # Restore original environment variables
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            os.environ.pop('OPENAI_API_KEY', None)
            
        if original_base_url:
            os.environ['OPENAI_BASE_URL'] = original_base_url
        else:
            os.environ.pop('OPENAI_BASE_URL', None)
            
        # Remove Railway environment variable
        os.environ.pop('RAILWAY_ENVIRONMENT', None)
        
        logger.info("Environment variables restored")

if __name__ == "__main__":
    result = asyncio.run(test())
    print("\nTest completed. Check logs for details.")
    print(f"Result: {result}")