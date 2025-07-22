from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from loguru import logger
from ..database.models import Daycare, Influencer, Region, Platform
from ..outreach.email_sender import EmailSender
import asyncio

load_dotenv()

class AIAssistant:
    def __init__(self, session: Session):
        self.session = session
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-3.5-turbo"
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        self.email_sender = EmailSender(session)

    async def _analyze_intent(self, command: str) -> Dict[str, Any]:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Analyze this marketing command and return JSON with:\n"
                            "- \"action\": \"search_influencers\", \"search_daycares\", or \"send_outreach\"\n"
                            "- \"params\": {relevant parameters including \"target_type\" for outreach commands}"
                        )
                    },
                    {"role": "user", "content": command}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            if not response.choices or not response.choices[0].message.content:
                raise ValueError("OpenAI response missing choices or content")
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Intent analysis failed: {str(e)}")
            raise

    async def process_command(self, command: str) -> Dict[str, Any]:
        try:
            intent = await self._analyze_intent(command)

            # Add fallback for missing 'target_type'
            if intent['action'] == 'send_outreach':
                if 'target_type' not in intent['params']:
                    if 'daycare' in command.lower():
                        intent['params']['target_type'] = 'daycare'
                    elif 'influencer' in command.lower():
                        intent['params']['target_type'] = 'influencer'

            if intent['action'] == 'search_influencers':
                return await self._handle_influencer_search(intent['params'])
            elif intent['action'] == 'search_daycares':
                return await self._handle_daycare_search(intent['params'])
            elif intent['action'] == 'send_outreach':
                return await self._handle_outreach(intent['params'])
            else:
                return {"error": "Unsupported command"}
        except Exception as e:
            logger.error(f"Command processing failed: {str(e)}")
            return {"error": str(e)}

    async def _handle_influencer_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self.session.query(Influencer)
        if 'country' in params:
            query = query.filter(Influencer.country == params['country'])
        if 'min_followers' in params:
            query = query.filter(Influencer.follower_count >= params['min_followers'])
        influencers = query.all()
        return {
            "influencers": [
                {
                    "name": inf.name,
                    "platform": inf.platform.value,
                    "followers": inf.follower_count,
                    "country": inf.country
                } for inf in influencers
            ]
        }

    async def _handle_daycare_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self.session.query(Daycare)
        if 'city' in params:
            query = query.filter(func.lower(Daycare.city) == params['city'].lower())
        if 'limit' in params:
            query = query.limit(params['limit'])
        daycares = query.all()
        return {
            "daycares": [
                {
                    "name": dc.name,
                    "city": dc.city,
                    "region": dc.region.value
                } for dc in daycares
            ]
        }

    async def _handle_outreach(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle outreach campaign commands."""
        try:
            raw_target_type = params.get('target_type', '').lower().strip()

            # Normalize target_type by keyword matching
            if 'daycare' in raw_target_type:
                target_type = 'daycare'
            elif 'influencer' in raw_target_type:
                target_type = 'influencer'
            else:
                raise ValueError(f"Unsupported target_type: {raw_target_type}")

            count = int(params.get('count', 10))
            region = params.get('region')

            if target_type == 'daycare':
                query = self.session.query(Daycare).filter(Daycare.last_contacted == None)
                if region:
                    query = query.filter(Daycare.region == region)
                targets = query.order_by(func.random()).limit(count).all()

            elif target_type == 'influencer':
                targets = (
                    self.session.query(Influencer)
                    .filter(Influencer.last_contacted == None)
                    .order_by(func.random())
                    .limit(count)
                    .all()
                )

            results = await self.email_sender.send_batch(targets, target_type)

            return {
                "success": True,
                "messages_sent": len(results),
                "details": results
            }

        except Exception as e:
            logger.error(f"Error in outreach campaign: {str(e)}")
            return {"error": str(e)}



# Testable script (optional)
if __name__ == '__main__':
    from ..database.models import init_db

    async def main():
        session = init_db()
        assistant = AIAssistant(session)
        commands = [
            "Find all influencers in France with 10k+ followers",
            "List top 10 daycares in New York",
            "Send outreach email to 50 random USA daycares"
        ]
        for command in commands:
            try:
                result = await assistant.process_command(command)
                print(f"Command: {command}")
                print(f"Result: {result}\n")
            except Exception as e:
                print(f"Error processing '{command}': {str(e)}")

    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "Event loop is closed" not in str(e):
            raise
