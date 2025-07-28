import asyncio
import os
from dotenv import load_dotenv
from loguru import logger
from src.database.models import init_db, Daycare
from src.outreach.email_sender import EmailSender

async def test_specific_email_sending():
    # Initialize database
    session = init_db()
    
    # Initialize email sender
    email_sender = EmailSender(session)
    
    # Get a specific daycare with a valid email
    daycare = session.query(Daycare).filter(
        Daycare.email != None,
        Daycare.email != '',
        Daycare.last_contacted == None
    ).first()
    
    if not daycare:
        logger.error("No daycare with valid email found")
        return
    
    logger.info(f"Testing email to: {daycare.name} <{daycare.email}>")
    
    # Send email to this specific daycare
    results = await email_sender.send_batch([daycare], 'daycare')
    
    # Log result
    logger.info(f"Result: {results}")
    
    if results and results[0].get('status') == 'success':
        logger.info(f"Success! Email sent to {daycare.name}")
    else:
        logger.error(f"Failed to send email to {daycare.name}")
        if results:
            logger.error(f"Error details: {results[0].get('error', 'Unknown error')}")

if __name__ == "__main__":
    # Configure logger
    logger.add("logs/test_specific_email.log", level="DEBUG")
    
    # Run test
    asyncio.run(test_specific_email_sending())