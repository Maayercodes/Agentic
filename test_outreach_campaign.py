import os
import asyncio
import sys
from loguru import logger
from src.database.models import init_db, Daycare, Influencer
from src.ai_assistant.assistant import AIAssistant
from src.outreach.email_sender import EmailSender

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")
logger.add("logs/test_outreach_campaign.log", rotation="500 KB", level="DEBUG")

async def test_email_sender_initialization():
    """Test if the EmailSender can be initialized with required environment variables"""
    logger.info("\n=== TESTING EMAIL SENDER INITIALIZATION ===\n")
    
    # Check required environment variables
    gmail_user = os.getenv('GMAIL_USER')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    
    if not gmail_user:
        logger.error("GMAIL_USER environment variable is not set")
        return False
    
    if not gmail_app_password:
        logger.error("GMAIL_APP_PASSWORD environment variable is not set")
        return False
    
    logger.info(f"GMAIL_USER is set: {gmail_user[:3]}...{gmail_user[-3:] if len(gmail_user) > 6 else ''}")
    logger.info("GMAIL_APP_PASSWORD is set: ******")
    
    try:
        session = init_db()
        email_sender = EmailSender(session)
        logger.info("✅ EmailSender initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ EmailSender initialization failed: {type(e).__name__}: {str(e)}")
        return False

async def test_email_template_loading():
    """Test if email templates can be loaded"""
    logger.info("\n=== TESTING EMAIL TEMPLATE LOADING ===\n")
    
    try:
        session = init_db()
        email_sender = EmailSender(session)
        
        # Test template loading for daycare (English)
        template_name = "daycare_en.html"
        subject_template_name = "subject_daycare_en.txt"
        
        try:
            template = email_sender.template_env.get_template(template_name)
            subject_template = email_sender.template_env.get_template(subject_template_name)
            logger.info(f"✅ Successfully loaded template: {template_name}")
            logger.info(f"✅ Successfully loaded template: {subject_template_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load template {template_name}: {str(e)}")
            return False
        
        # Test template loading for influencer (English)
        template_name = "influencer_en.html"
        subject_template_name = "subject_influencer_en.txt"
        
        try:
            template = email_sender.template_env.get_template(template_name)
            subject_template = email_sender.template_env.get_template(subject_template_name)
            logger.info(f"✅ Successfully loaded template: {template_name}")
            logger.info(f"✅ Successfully loaded template: {subject_template_name}")
        except Exception as e:
            logger.error(f"❌ Failed to load template {template_name}: {str(e)}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Template loading test failed: {type(e).__name__}: {str(e)}")
        return False

async def test_database_targets():
    """Test if there are valid targets in the database"""
    logger.info("\n=== TESTING DATABASE TARGETS ===\n")
    
    try:
        session = init_db()
        
        # Check for daycares
        daycares = session.query(Daycare).limit(5).all()
        logger.info(f"Found {len(daycares)} daycares in database")
        
        if daycares:
            for i, daycare in enumerate(daycares[:3], 1):  # Show up to 3 examples
                logger.info(f"Daycare {i}: {daycare.name}, Email: {daycare.email or 'None'}")
        
        # Check for influencers
        influencers = session.query(Influencer).limit(5).all()
        logger.info(f"Found {len(influencers)} influencers in database")
        
        if influencers:
            for i, influencer in enumerate(influencers[:3], 1):  # Show up to 3 examples
                logger.info(f"Influencer {i}: {influencer.name}, Email: {influencer.email or 'None'}")
        
        # Check if there are targets with valid emails
        valid_daycare_targets = session.query(Daycare).filter(Daycare.email != None, Daycare.email != '').count()
        valid_influencer_targets = session.query(Influencer).filter(Influencer.email != None, Influencer.email != '').count()
        
        logger.info(f"Found {valid_daycare_targets} daycares with valid emails")
        logger.info(f"Found {valid_influencer_targets} influencers with valid emails")
        
        if valid_daycare_targets == 0 and valid_influencer_targets == 0:
            logger.warning("❌ No targets with valid emails found in database")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ Database targets test failed: {type(e).__name__}: {str(e)}")
        return False

async def test_outreach_command_processing():
    """Test if the AI Assistant can process an outreach command"""
    logger.info("\n=== TESTING OUTREACH COMMAND PROCESSING ===\n")
    
    try:
        session = init_db()
        assistant = AIAssistant(session)
        
        # Test with a simple outreach command (dry run)
        command = "Send outreach email to 1 random daycare"
        logger.info(f"Processing command: '{command}'")
        
        # Process the command but don't actually send emails
        # This is just to test if the command processing works
        result = await assistant.process_command(command)
        
        if 'error' in result:
            logger.error(f"❌ Command processing failed: {result['error']}")
            return False
        
        logger.info(f"✅ Command processing successful: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ Command processing test failed: {type(e).__name__}: {str(e)}")
        return False

async def run_tests():
    """Run all tests and return overall result"""
    logger.info("Starting outreach campaign tests...\n")
    
    # Run tests
    email_sender_init = await test_email_sender_initialization()
    template_loading = await test_email_template_loading()
    database_targets = await test_database_targets()
    command_processing = await test_outreach_command_processing()
    
    # Summarize results
    logger.info("\n=== TEST SUMMARY ===\n")
    logger.info(f"Email Sender Initialization: {'✅ PASSED' if email_sender_init else '❌ FAILED'}")
    logger.info(f"Email Template Loading: {'✅ PASSED' if template_loading else '❌ FAILED'}")
    logger.info(f"Database Targets: {'✅ PASSED' if database_targets else '❌ FAILED'}")
    logger.info(f"Outreach Command Processing: {'✅ PASSED' if command_processing else '❌ FAILED'}")
    
    # Overall result
    all_passed = email_sender_init and template_loading and database_targets and command_processing
    logger.info(f"\nOverall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    # Provide recommendations
    if not all_passed:
        logger.info("\n=== RECOMMENDATIONS ===\n")
        
        if not email_sender_init:
            logger.info("- Set the GMAIL_USER and GMAIL_APP_PASSWORD environment variables")
            logger.info("  For Gmail, you need to create an App Password: https://support.google.com/accounts/answer/185833")
        
        if not template_loading:
            logger.info("- Check that all email templates exist in src/templates/emails/")
        
        if not database_targets:
            logger.info("- Add targets with valid emails to the database using the scraper tools")
            logger.info("  Run: python src/ui/cli.py scrape --source yelp --region usa")
        
        if not command_processing:
            logger.info("- Check the AI Assistant configuration and OpenAI API key")
    
    return all_passed

if __name__ == "__main__":
    logger.info("Starting outreach campaign test")
    try:
        result = asyncio.run(run_tests())
        logger.info("Test completed successfully")
        sys.exit(0 if result else 1)  # Exit with status code based on test result
    except Exception as e:
        logger.error(f"Test failed with error: {type(e).__name__}: {str(e)}")
        sys.exit(1)  # Exit with error status code