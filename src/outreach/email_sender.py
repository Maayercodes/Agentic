import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Union, Any
from datetime import datetime
import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from loguru import logger

from ..database.models import Daycare, Influencer, OutreachHistory

import socket
# Load environment variables
load_dotenv()

class EmailSender:
    def __init__(self, session):
        self.session = session

        # Email config from .env
        self.smtp_server = os.getenv('GMAIL_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('GMAIL_PORT', 587))
        self.sender_email = os.getenv('GMAIL_USER')
        self.sender_name = os.getenv('EMAIL_SENDER_NAME', 'AI Outreach')
        self.password = os.getenv('GMAIL_APP_PASSWORD')

        # Sanity check
        if not self.sender_email or not self.password:
            raise ValueError("GMAIL_USER and GMAIL_APP_PASSWORD must be set in the environment.")

        # Initialize Jinja2 template engine
        self.template_env = Environment(
            loader=FileSystemLoader('src/templates/emails')
        )

    async def send_batch(self, targets: List[Union[Daycare, Influencer]], target_type: str, **kwargs) -> List[Dict[str, Any]]:
        results = []
        
        # Get custom email options if provided
        custom_subject = kwargs.get('custom_subject')
        custom_body = kwargs.get('custom_body')
        sender_email = kwargs.get('sender_email', self.sender_email)
        sender_name = kwargs.get('sender_name', self.sender_name)
        
        # Log email sending details
        logger.info(f"Sending emails to {len(targets)} {target_type}s")
        logger.info(f"Sender: {sender_name} <{sender_email}>")
        if custom_subject:
            logger.info(f"Using custom subject: {custom_subject}")
        if custom_body:
            logger.info("Using custom email body")

        for target in targets:
            try:
                email = getattr(target, 'email', None)
                if not email or not email.strip():
                    raise ValueError("Target has no valid email address.")

                language = 'fr' if (getattr(target, 'region', '') or '').strip().upper() == 'FRANCE' else 'en'
                
                # Generate email content (using custom content if provided)
                subject, body = self._generate_email_content(
                    target, 
                    target_type, 
                    language,
                    custom_subject=custom_subject,
                    custom_body=custom_body
                )

                success = await self._send_email(
                    recipient_email=email.strip(), 
                    subject=subject, 
                    body=body,
                    sender_email=sender_email,
                    sender_name=sender_name
                )

                if success:
                    self._record_outreach(target, target_type, subject, body, language)
                    results.append({
                        "target": target.name,
                        "email": email,
                        "status": "success",
                        "sender": f"{sender_name} <{sender_email}>"
                    })
                else:
                    results.append({
                        "target": target.name,
                        "email": email,
                        "status": "failed",
                        "sender": f"{sender_name} <{sender_email}>"
                    })

            except Exception as e:
                logger.error(f"Error sending email to {getattr(target, 'name', 'Unknown')}: {str(e)}")
                results.append({
                    "target": getattr(target, 'name', 'Unknown'),
                    "email": getattr(target, 'email', 'Unknown'),
                    "status": "error",
                    "error": str(e),
                    "sender": f"{sender_name} <{sender_email}>"
                })

        return results

    def _generate_email_content(self, target: Union[Daycare, Influencer], target_type: str, language: str, **kwargs) -> tuple:
        # Get custom content if provided
        custom_subject = kwargs.get('custom_subject')
        custom_body = kwargs.get('custom_body')
        
        # Set up context for template rendering
        context = {
            "recipient_name": getattr(target, 'name', 'there'),
            "sender_name": kwargs.get('sender_name', self.sender_name) or "Our Team"
        }

        if target_type == 'daycare':
            context.update({
                "city": getattr(target, 'city', 'your city'),
                "region": getattr(target, 'region', 'your region')
            })
        elif target_type == 'influencer':
            platform_value = getattr(target, 'platform', 'your platform')
            if hasattr(platform_value, 'value'):
                platform_value = platform_value.value
                
            context.update({
                "platform": platform_value,
                "niche": getattr(target, 'niche', 'your niche')
            })
        else:
            raise ValueError(f"Unsupported target_type: {target_type}")

        # Use custom content or render from templates
        if custom_subject:
            # If custom subject has placeholders, render them
            if any(marker in custom_subject for marker in ['{{', '}}']):
                from jinja2 import Template
                subject = Template(custom_subject).render(context)
            else:
                subject = custom_subject
        else:
            # Use template file
            subject_template_name = f"subject_{target_type}_{language}.txt"
            subject_template = self.template_env.get_template(subject_template_name)
            subject = subject_template.render(context)

        if custom_body:
            # If custom body has placeholders, render them
            if any(marker in custom_body for marker in ['{{', '}}']):
                from jinja2 import Template
                body = Template(custom_body).render(context)
            else:
                body = custom_body
        else:
            # Use template file
            template_name = f"{target_type}_{language}.html"
            template = self.template_env.get_template(template_name)
            body = template.render(context)

        return subject, body

    async def _send_email(self, recipient_email: str, subject: str, body: str, sender_email=None, sender_name=None) -> bool:
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
            return False

    def _record_outreach(self, target: Union[Daycare, Influencer], target_type: str,
                         subject: str, content: str, language: str) -> None:
        try:
            history = OutreachHistory(
                target_type=target_type,
                target_id=target.id,
                email_subject=subject,
                email_content=content,
                language=language
            )
            self.session.add(history)
            target.last_contacted = datetime.utcnow()
            self.session.commit()

        except Exception as e:
            self.session.rollback()
            logger.error(f"Database error when recording outreach: {str(e)}")

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
                email_content=content + f"\n\nNote: Email sending failed: {error_type}",  # Add error info to content
                language=language,
                bounced=True  # Mark as bounced since it failed to send
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
            logger.error(f"Database error when recording outreach attempt: {str(e)}")

# Optional: local testing only
if __name__ == '__main__':
    from ..database.models import init_db
    import asyncio

    async def main():
        session = init_db()
        sender = EmailSender(session)
        daycares = session.query(Daycare).limit(5).all()
        results = await sender.send_batch(daycares, 'daycare')
        print("Email sending results:", results)

    asyncio.run(main())
