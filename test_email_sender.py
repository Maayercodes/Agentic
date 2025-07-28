import asyncio
import os
import socket
import smtplib
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.database.models import init_db, Daycare
from src.outreach.email_sender import EmailSender
from loguru import logger

# Configure logger
logger.add("logs/email_test.log", rotation="10 MB", level="DEBUG")

async def test_smtp_connection():
    """Test the SMTP connection before attempting to send an email"""
    try:
        smtp_server = os.getenv('GMAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('GMAIL_PORT', 587))
        gmail_user = os.getenv('GMAIL_USER')
        gmail_password = os.getenv('GMAIL_APP_PASSWORD')
        
        logger.info(f"Testing SMTP connection to {smtp_server}:{smtp_port}...")
        print(f"🔄 Testing SMTP connection to {smtp_server}:{smtp_port}...")
        
        # First test if we can connect to the SMTP server
        sock = socket.create_connection((smtp_server, smtp_port), timeout=10)
        sock.close()
        
        # Now test if we can authenticate
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            
        logger.info("SMTP connection and authentication successful!")
        print("✅ SMTP connection and authentication successful!")
        return True
        
    except socket.timeout:
        logger.error(f"Timeout connecting to {smtp_server}:{smtp_port}. Check your network connection.")
        print(f"❌ Timeout connecting to {smtp_server}:{smtp_port}. Check your network connection.")
        return False
    except socket.gaierror:
        logger.error(f"DNS resolution failed for {smtp_server}. Check your network connection.")
        print(f"❌ DNS resolution failed for {smtp_server}. Check your network connection.")
        return False
    except ConnectionRefusedError:
        logger.error(f"Connection refused by {smtp_server}:{smtp_port}. The server may be down or blocked by a firewall.")
        print(f"❌ Connection refused by {smtp_server}:{smtp_port}. The server may be down or blocked by a firewall.")
        return False
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check your email credentials.")
        print("❌ SMTP authentication failed. Check your email credentials.")
        return False
    except Exception as e:
        logger.error(f"SMTP connection test failed: {str(e)}")
        print(f"❌ SMTP connection test failed: {str(e)}")
        return False

async def test_email_sending():
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
        
        # Initialize email sender
        logger.info("Initializing email sender...")
        email_sender = EmailSender(session)
        
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
        
        # Send test email
        logger.info(f"Sending test email to: {test_daycare.email}")
        print(f"📤 Sending test email to: {test_daycare.email}")
        
        results = await email_sender.send_batch(
            [test_daycare], 
            'daycare',
            custom_subject="Test Email from AI Marketing Outreach",
            custom_body="This is a test email to verify the email sending functionality is working properly."
        )
        
        # Check results
        logger.info(f"Email sending results: {results}")
        
        success = any(result.get('status') == 'success' for result in results)
        
        if success:
            logger.info("Test email sent successfully!")
            print("✅ Test email sent successfully!")
            return True
        else:
            error_messages = [result.get('error', 'Unknown error') for result in results if result.get('status') == 'error']
            logger.error(f"Failed to send test email: {error_messages}")
            print(f"❌ Failed to send test email: {error_messages}")
            return False
            
    except Exception as e:
        logger.error(f"Error in test_email_sending: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    print("=== Email Sender Test ===\n")
    load_dotenv()
    
    # First test SMTP connection
    smtp_success = asyncio.run(test_smtp_connection())
    
    if not smtp_success:
        print("\n❌ SMTP connection test failed! Cannot proceed with email test.")
        print("   Possible solutions:")
        print("   1. Check your network connection")
        print("   2. Verify that port 587 is not blocked by your firewall")
        print("   3. Confirm that your GMAIL_APP_PASSWORD is correct")
        print("   4. Try using a different network connection")
        exit(1)
    
    # If SMTP connection is successful, proceed with email test
    email_success = asyncio.run(test_email_sending())
    
    if email_success:
        print("\n✅ Email functionality is working!")
        exit(0)
    else:
        print("\n❌ Email functionality test failed!")
        exit(1)