from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
import os
import json
import requests
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
        self.model = os.getenv('OPENAI_MODEL', "gpt-3.5-turbo")
        self.max_retries = int(os.getenv('MAX_RETRIES', 3))
        self.retry_delay = 1  # Initial delay in seconds
        self.openai_base_url = os.getenv('OPENAI_BASE_URL')  # Optional custom base URL
        
        # Validate API key format
        self._validate_api_key()
        
        # Initialize the OpenAI client with optional base URL
        if self.openai_base_url:
            self.client = AsyncOpenAI(api_key=self.openai_api_key, base_url=self.openai_base_url)
            logger.info(f"Using custom OpenAI base URL: {self.openai_base_url}")
        else:
            self.client = AsyncOpenAI(api_key=self.openai_api_key)
            
        self.email_sender = EmailSender(session)
        
    async def check_api_connectivity(self):
        """Check if we can connect to the OpenAI API."""
        try:
            # Make a minimal API call to check connectivity
            response = await self.client.models.list()
            logger.info("Successfully connected to OpenAI API")
            return True
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to OpenAI API: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error checking OpenAI API connectivity: {type(e).__name__}: {str(e)}")
            return False
        
    def _validate_api_key(self):
        """Validate the OpenAI API key format and log appropriate warnings."""
        if not self.openai_api_key:
            logger.warning("OpenAI API key is not set. Please check your .env file.")
            return False
            
        if self.openai_api_key.strip() == "":
            logger.warning("OpenAI API key is empty. Please check your .env file.")
            return False
            
        # Check for common API key format patterns
        if self.openai_api_key.startswith("sk-") and len(self.openai_api_key) > 20:
            return True
        else:
            logger.warning("OpenAI API key may be malformed. It should start with 'sk-' and be at least 20 characters long.")
            return False

    async def _analyze_intent(self, command: str) -> Dict[str, Any]:
        # Check if API key is configured and valid
        if not self.openai_api_key or self.openai_api_key.strip() == "":
            logger.error("OpenAI API key is missing or empty. Please check your .env file.")
            raise ValueError("OpenAI API key is missing or empty")
            
        # Additional validation for API key format
        if not self.openai_api_key.startswith("sk-") or len(self.openai_api_key) < 20:
            logger.error("OpenAI API key appears to be malformed. It should start with 'sk-' and be at least 20 characters long.")
            raise ValueError("OpenAI API key appears to be malformed")
        
        # Initialize retry counter and last error
        retries = 0
        last_error = None
        retry_delay = self.retry_delay
        
        # Implement retry logic
        while retries <= self.max_retries:
            try:
                # Attempt to create the completion
                logger.debug(f"Attempt {retries + 1}/{self.max_retries + 1} to analyze intent")
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
                
            except (requests.exceptions.RequestException, requests.exceptions.ConnectionError) as re:
                # Handle connection errors with retry
                last_error = re
                retries += 1
                
                if retries <= self.max_retries:
                    logger.warning(f"Connection error during intent analysis (attempt {retries}/{self.max_retries}): {str(re)}")
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    # Exponential backoff
                    retry_delay *= 2
                else:
                    logger.error(f"Connection error during intent analysis after {self.max_retries} retries: {str(re)}")
                    raise ConnectionError(f"Connection error after {self.max_retries} retries: {str(re)}")
            
            except ValueError as ve:
                # Handle value errors (like missing API key or malformed response)
                logger.error(f"Intent analysis failed: {str(ve)}")
                raise
                
            except json.JSONDecodeError as je:
                # Handle JSON parsing errors
                logger.error(f"Failed to parse OpenAI response: {str(je)}")
                raise ValueError(f"Failed to parse OpenAI response: {str(je)}")
                
            except Exception as e:
                # Handle other unexpected errors
                logger.error(f"Intent analysis failed with unexpected error: {type(e).__name__}: {str(e)}")
                raise

    async def process_command(self, command: str) -> Dict[str, Any]:
        try:
            # Check API connectivity first
            if not await self.check_api_connectivity():
                return {
                    "error": "Unable to connect to OpenAI API. Please check your internet connection and API configuration.",
                    "suggestion": "Verify your network connection and OpenAI API key configuration."
                }
                
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
        except ConnectionError as ce:
            logger.error(f"Connection error in command processing: {str(ce)}")
            return {
                "error": "Unable to connect to OpenAI API. Please check your internet connection and try again later.",
                "details": str(ce),
                "suggestion": "You can try using a simpler command or check your API configuration."
            }
        except ValueError as ve:
            if "API key" in str(ve):
                logger.error(f"API key error: {str(ve)}")
                return {
                    "error": "OpenAI API key is missing or invalid. Please check your configuration.",
                    "details": str(ve)
                }
            else:
                logger.error(f"Value error in command processing: {str(ve)}")
                return {"error": str(ve)}
        except Exception as e:
            logger.error(f"Command processing failed: {type(e).__name__}: {str(e)}")
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
