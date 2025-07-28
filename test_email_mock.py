import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime
from src.database.models import init_db, Daycare, OutreachHistory
from loguru import logger

# Configure logger
logger.add("logs/email_mock_test.log", rotation="10 MB", level="DEBUG")

def test_email_mock():
    try:
        # Initialize database session
        logger.info("Initializing database session...")
        session = init_db()
        
        # Check if we have the required environment variables
        logger.info("Checking email configuration...")
        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not gmail_user or not gmail_password:
            logger.error("Missing email credentials in environment variables")
            print("❌ Missing email credentials. Please check your .env file.")
            return False
        
        print(f"📧 Using email account: {gmail_user}")
        
        # Get a test daycare with a valid email
        logger.info("Fetching test daycare with valid email from database...")
        test_daycare = session.query(Daycare).filter(Daycare.email.isnot(None), Daycare.email != '').first()
        
        if not test_daycare:
            # Create a test daycare if none exists with valid email
            logger.info("No daycares with valid email found, creating a test daycare...")
            test_daycare = Daycare(
                name="Test Daycare",
                email=gmail_user,  # Send to ourselves for testing
                region="USA",
                city="Test City",
                address="123 Test Street",
                website="https://example.com",
                source="test_script"
            )
            session.add(test_daycare)
            session.commit()
            logger.info(f"Created test daycare with ID: {test_daycare.id}")
        elif not test_daycare.email or test_daycare.email.strip() == '':
            # Update the existing daycare with a valid email
            logger.info(f"Updating daycare {test_daycare.name} with valid email...")
            test_daycare.email = gmail_user  # Send to ourselves for testing
            session.commit()
            logger.info(f"Updated test daycare with ID: {test_daycare.id}")
        
        # Mock sending an email by creating an OutreachHistory record
        logger.info(f"Mocking email send to: {test_daycare.email}")
        print(f"📤 Mocking email send to: {test_daycare.email}")
        
        # Create subject and body for the mock email
        subject = "Test Email from AI Marketing Outreach"
        body = "This is a test email to verify the email functionality is working properly."
        
        # Create an OutreachHistory record
        history = OutreachHistory(
            target_type="daycare",
            target_id=test_daycare.id,
            email_subject=subject,
            email_content=body,
            sent_at=datetime.utcnow(),
            language="en"
        )
        
        # Update the daycare's last_contacted field
        test_daycare.last_contacted = datetime.utcnow()
        
        # Save to database
        session.add(history)
        session.commit()
        
        logger.info(f"Successfully created OutreachHistory record with ID: {history.id}")
        print(f"✅ Successfully created OutreachHistory record with ID: {history.id}")
        
        # Verify the record was created
        record = session.query(OutreachHistory).filter_by(id=history.id).first()
        
        if record:
            logger.info("Mock email test successful!")
            print("✅ Mock email test successful!")
            return True
        else:
            logger.error("Failed to create OutreachHistory record")
            print("❌ Failed to create OutreachHistory record")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_email_mock: {str(e)}")
        print(f"❌ Error: {str(e)}")
        if 'session' in locals():
            session.rollback()
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    print("=== Mock Email Test ===\n")
    load_dotenv()
    success = test_email_mock()
    
    if success:
        print("\n✅ Email database functionality is working!")
        print("\nNote: Actual SMTP email sending could not be tested due to network restrictions.")
        print("However, the database functionality for recording email outreach is working correctly.")
        exit(0)
    else:
        print("\n❌ Email mock test failed!")
        exit(1)