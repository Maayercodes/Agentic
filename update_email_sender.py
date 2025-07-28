import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from dotenv import load_dotenv
from src.database.models import init_db
from loguru import logger

# Configure logger
logger.add("logs/update_email_sender.log", rotation="10 MB", level="DEBUG")

def update_email_sender_function():
    """
    Update the EmailSender's _send_email function to handle network issues gracefully
    and provide better feedback to the user.
    """
    try:
        # Path to the email_sender.py file
        email_sender_path = os.path.join(os.path.dirname(__file__), 'src', 'outreach', 'email_sender.py')
        
        # Read the current file content
        with open(email_sender_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the _send_email function
        start_marker = "    async def _send_email(self, recipient_email: str, subject: str, body: str, sender_email=None, sender_name=None) -> bool:"
        end_marker = "    def _record_outreach(self, target: Union[Daycare, Influencer], target_type: str,"
        
        # Split the content
        parts = content.split(start_marker)
        if len(parts) != 2:
            logger.error("Could not find _send_email function in email_sender.py")
            return False
        
        pre_function = parts[0]
        
        parts = parts[1].split(end_marker)
        if len(parts) != 2:
            logger.error("Could not find end of _send_email function in email_sender.py")
            return False
        
        post_function = end_marker + parts[1]
        
        # New implementation of _send_email with better error handling
        new_function = '''
        try:
            # Use provided sender info or default
            sender_email = sender_email or self.sender_email
            sender_name = sender_name or self.sender_name
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{sender_name} <{sender_email}>"
            msg['To'] = recipient_email

            # Determine content type (HTML or plain text)
            content_type = 'html' if '<html' in body.lower() else 'plain'
            msg.attach(MIMEText(body, content_type))

            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    # Always use the configured account for authentication
                    # even if sending from a different address
                    server.login(self.sender_email, self.password)
                    server.send_message(msg)

                logger.info(f"Email sent successfully to {recipient_email} from {sender_email}")
                return True
                
            except socket.timeout:
                logger.error(f"Timeout connecting to {self.smtp_server}:{self.smtp_port}")
                # Record the outreach attempt even if email sending fails due to network issues
                self._record_outreach_attempt(recipient_email, subject, body, "timeout")
                return False
                
            except socket.gaierror:
                logger.error(f"DNS resolution failed for {self.smtp_server}")
                self._record_outreach_attempt(recipient_email, subject, body, "dns_error")
                return False
                
            except ConnectionRefusedError:
                logger.error(f"Connection refused by {self.smtp_server}:{self.smtp_port}")
                self._record_outreach_attempt(recipient_email, subject, body, "connection_refused")
                return False
                
            except smtplib.SMTPAuthenticationError:
                logger.error("SMTP authentication failed")
                return False
                
            except Exception as smtp_error:
                logger.error(f"SMTP error: {str(smtp_error)}")
                self._record_outreach_attempt(recipient_email, subject, body, f"smtp_error: {str(smtp_error)}")
                return False

        except Exception as e:
            logger.error(f"Error preparing email for {recipient_email}: {str(e)}")
            return False'''
        
        # Add the _record_outreach_attempt method
        record_outreach_attempt_method = '''

    def _record_outreach_attempt(self, recipient_email: str, subject: str, content: str, error_type: str) -> None:
        """Record an outreach attempt even when actual email sending fails due to network issues"""
        try:
            # Try to find the target based on email
            daycare = self.session.query(Daycare).filter(Daycare.email == recipient_email).first()
            influencer = self.session.query(Influencer).filter(Influencer.email == recipient_email).first()
            
            if daycare:
                target_type = "daycare"
                target_id = daycare.id
                language = 'fr' if (daycare.region or '').strip().upper() == 'FRANCE' else 'en'
            elif influencer:
                target_type = "influencer"
                target_id = influencer.id
                language = 'fr' if (influencer.country or '').strip().upper() == 'FRANCE' else 'en'
            else:
                logger.warning(f"Could not find target with email {recipient_email} for outreach recording")
                return
            
            # Create outreach history record
            history = OutreachHistory(
                target_type=target_type,
                target_id=target_id,
                email_subject=subject,
                email_content=content,
                language=language,
                notes=f"Email sending failed: {error_type}"
            )
            self.session.add(history)
            
            # Update last_contacted timestamp
            if daycare:
                daycare.last_contacted = datetime.utcnow()
            elif influencer:
                influencer.last_contacted = datetime.utcnow()
                
            self.session.commit()
            logger.info(f"Recorded outreach attempt for {recipient_email} despite sending failure")
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"Database error when recording outreach attempt: {str(e)}")'''
        
        # Add import for socket module
        import_socket = "import socket\n"
        if "import socket" not in content:
            # Find the import section
            import_section_end = content.find("# Load environment variables")
            if import_section_end == -1:
                logger.error("Could not find import section in email_sender.py")
                return False
            
            # Add socket import
            pre_function = content[:import_section_end] + import_socket + content[import_section_end:parts[0].rfind(start_marker)]
        
        # Combine the parts
        new_content = pre_function + start_marker + new_function + record_outreach_attempt_method + post_function
        
        # Create a backup of the original file
        backup_path = email_sender_path + '.bak'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created backup of email_sender.py at {backup_path}")
        
        # Write the updated content
        with open(email_sender_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"Updated _send_email function in {email_sender_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating email_sender.py: {str(e)}")
        return False

if __name__ == "__main__":
    load_dotenv()
    print("Updating email sender function...")
    success = update_email_sender_function()
    
    if success:
        print("✅ Successfully updated email sender function")
        print("Restart the Streamlit application to apply the changes")
    else:
        print("❌ Failed to update email sender function")
        print("Check the logs for details")