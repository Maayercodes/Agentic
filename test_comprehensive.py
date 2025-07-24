import os
import asyncio
import sys
from loguru import logger
from src.database.models import init_db
from src.ai_assistant.assistant import AIAssistant

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/test_comprehensive.log", rotation="500 KB", level="DEBUG")

async def test_normal_operation():
    """Test normal operation with valid API key and base URL"""
    logger.info("\n=== TESTING NORMAL OPERATION ===")
    session = init_db()
    assistant = AIAssistant(session)
    result = await assistant.process_command("Find all influencers in France")
    success = 'error' not in result
    logger.info(f"Normal operation test: {'✅ PASSED' if success else '❌ FAILED'}")
    return success

async def test_invalid_api_key():
    """Test with invalid API key"""
    logger.info("\n=== TESTING INVALID API KEY ===")
    # Save original API key
    original_api_key = os.environ.get('OPENAI_API_KEY')
    
    try:
        # Set invalid API key
        os.environ['OPENAI_API_KEY'] = 'invalid_key'
        
        session = init_db()
        assistant = AIAssistant(session)
        result = await assistant.process_command("Find all influencers in France")
        
        logger.info(f"Result: {result}")
        
        # Check if the result contains API key error information
        success = 'error' in result and ('API key' in result.get('error', '') or 'api key' in result.get('error', '').lower())
        logger.info(f"Invalid API key test: {'✅ PASSED' if success else '❌ FAILED'}")
        return success
    finally:
        # Restore original API key
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key
        else:
            os.environ.pop('OPENAI_API_KEY', None)

async def test_connection_error():
    """Test with invalid base URL causing connection error"""
    logger.info("\n=== TESTING CONNECTION ERROR ===")
    # Save original base URL
    original_base_url = os.environ.get('OPENAI_BASE_URL')
    
    try:
        # Set invalid base URL
        os.environ['OPENAI_BASE_URL'] = 'https://nonexistent-api-endpoint.example.com/v1'
        
        session = init_db()
        assistant = AIAssistant(session)
        result = await assistant.process_command("Find all influencers in France")
        
        # Check if the result contains connection error information
        success = 'error' in result and 'connect' in result.get('error', '').lower() and result.get('status') == 'connection_error'
        logger.info(f"Connection error test: {'✅ PASSED' if success else '❌ FAILED'}")
        return success
    finally:
        # Restore original base URL
        if original_base_url:
            os.environ['OPENAI_BASE_URL'] = original_base_url
        else:
            os.environ.pop('OPENAI_BASE_URL', None)

async def test_railway_environment():
    """Test Railway environment detection and handling"""
    logger.info("\n=== TESTING RAILWAY ENVIRONMENT ===")
    # Save original environment variables
    original_base_url = os.environ.get('OPENAI_BASE_URL')
    railway_env = os.environ.get('RAILWAY_ENVIRONMENT')
    
    try:
        # Simulate Railway environment
        os.environ['RAILWAY_ENVIRONMENT'] = 'true'
        os.environ['OPENAI_BASE_URL'] = 'https://nonexistent-api-endpoint.example.com/v1'
        
        session = init_db()
        assistant = AIAssistant(session)
        result = await assistant.process_command("Find all influencers in France")
        
        # Check if the result contains Railway-specific error information
        success = result.get('environment') == 'railway' and 'Railway' in result.get('suggestion', '')
        logger.info(f"Railway environment test: {'✅ PASSED' if success else '❌ FAILED'}")
        return success
    finally:
        # Restore original environment variables
        if original_base_url:
            os.environ['OPENAI_BASE_URL'] = original_base_url
        else:
            os.environ.pop('OPENAI_BASE_URL', None)
            
        if railway_env:
            os.environ['RAILWAY_ENVIRONMENT'] = railway_env
        else:
            os.environ.pop('RAILWAY_ENVIRONMENT', None)

async def test_missing_api_key():
    """Test with missing API key"""
    logger.info("\n=== TESTING MISSING API KEY ===")
    # Save original API key
    original_api_key = os.environ.get('OPENAI_API_KEY')
    
    try:
        # Remove API key
        os.environ.pop('OPENAI_API_KEY', None)
        
        session = init_db()
        try:
            assistant = AIAssistant(session)
            result = await assistant.process_command("Find all influencers in France")
        except Exception as e:
            # If initialization fails, consider it a successful test since we're expecting failure
            logger.info(f"Expected error occurred: {str(e)}")
            return True
        
        logger.info(f"Result: {result}")
        
        # Check if the result contains missing API key error information
        success = 'error' in result and ('API key' in result.get('error', '') or 'api key' in result.get('error', '').lower())
        logger.info(f"Missing API key test: {'✅ PASSED' if success else '❌ FAILED'}")
        return success
    finally:
        # Restore original API key
        if original_api_key:
            os.environ['OPENAI_API_KEY'] = original_api_key

async def run_all_tests():
    """Run all tests and report results"""
    tests = [
        ("Normal operation", test_normal_operation),
        ("Invalid API key", test_invalid_api_key),
        ("Missing API key", test_missing_api_key),
        ("Connection error", test_connection_error),
        ("Railway environment", test_railway_environment)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            logger.error(f"Error running {name} test: {str(e)}")
            results[name] = False
    
    # Print summary
    logger.info("\n=== TEST SUMMARY ===")
    all_passed = True
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name}: {status}")
        if not result:
            all_passed = False
    
    logger.info(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return results

if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    print("\nComprehensive testing completed. Check logs for details.")