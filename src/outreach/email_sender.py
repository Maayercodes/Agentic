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

    async def send_batch(self, targets: List[Union[Daycare, Influencer]], target_type: str) -> List[Dict[str, Any]]:
        results = []

        for target in targets:
            try:
                email = getattr(target, 'email', None)
                if not email or not email.strip():
                    raise ValueError("Target has no valid email address.")

                language = 'fr' if (getattr(target, 'region', '') or '').strip().upper() == 'FRANCE' else 'en'
                subject, body = self._generate_email_content(target, target_type, language)

                success = await self._send_email(email.strip(), subject, body)

                if success:
                    self._record_outreach(target, target_type, subject, body, language)
                    results.append({
                        "target": target.name,
                        "email": email,
                        "status": "success"
                    })
                else:
                    results.append({
                        "target": target.name,
                        "email": email,
                        "status": "failed"
                    })

            except Exception as e:
                logger.error(f"Error sending email to {getattr(target, 'name', 'Unknown')}: {str(e)}")
                results.append({
                    "target": getattr(target, 'name', 'Unknown'),
                    "email": getattr(target, 'email', 'Unknown'),
                    "status": "error",
                    "error": str(e)
                })

        return results

    def _generate_email_content(self, target: Union[Daycare, Influencer], target_type: str, language: str) -> tuple:
        template_name = f"{target_type}_{language}.html"
        subject_template_name = f"subject_{target_type}_{language}.txt"

        template = self.template_env.get_template(template_name)
        subject_template = self.template_env.get_template(subject_template_name)

        context = {
            "recipient_name": getattr(target, 'name', 'there'),
            "sender_name": self.sender_name or "Our Team"
        }

        if target_type == 'daycare':
            context.update({
                "city": getattr(target, 'city', 'your city'),
                "region": getattr(target, 'region', 'your region')
            })
        elif target_type == 'influencer':
            context.update({
                "platform": getattr(target, 'platform', 'your platform'),
                "niche": getattr(target, 'niche', 'your niche')
            })
        else:
            raise ValueError(f"Unsupported target_type: {target_type}")

        subject = subject_template.render(context)
        body = template.render(context)

        return subject, body

    async def _send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = recipient_email

            msg.attach(MIMEText(body, 'html'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            logger.error(f"SMTP error for {recipient_email}: {str(e)}")
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
