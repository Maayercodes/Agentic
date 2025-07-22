import os
import dotenv
import requests
from serpapi import GoogleSearch
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, text, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from datetime import datetime

# --- Load environment variables ---
dotenv.load_dotenv()
api_key = os.getenv("SERPAPI_API_KEY")
db_url = os.getenv("DATABASE_URL")

if not api_key:
    raise ValueError("Please set the SERPAPI_API_KEY environment variable.")
if not db_url:
    raise ValueError("Please set the DATABASE_URL environment variable.")

# --- Setup SQLAlchemy ---
Base = declarative_base()
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)


# --- Define table structure ---
class Daycare(Base):
    __tablename__ = "daycares"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    address = Column(String)
    city = Column(String)
    email = Column(String)
    phone = Column(String)
    website = Column(String)
    region = Column(String)
    source = Column(String)
    last_contacted = Column(DateTime, nullable=True)
    email_opened = Column(Boolean, nullable=True)
    email_replied = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    rating = Column(Float)
    reviews = Column(Integer)

# --- ALTER TABLE to add missing columns dynamically ---
def add_missing_columns(engine):
    inspector = inspect(engine)
    columns = inspector.get_columns('daycares')
    existing_column_names = [col['name'] for col in columns]

    type_map = {
        String: 'VARCHAR',
        Integer: 'INTEGER',
        Float: 'FLOAT',
        Boolean: 'BOOLEAN',
        DateTime: 'TIMESTAMP'
    }

    for column in Daycare.__table__.columns:
        if column.name not in existing_column_names:
            col_type = type_map.get(type(column.type), 'VARCHAR')
            alter_stmt = f"ALTER TABLE daycares ADD COLUMN {column.name} {col_type}"
            with engine.connect() as conn:
                conn.execute(text(alter_stmt))

add_missing_columns(engine)


# --- Boolean cleaner ---
def boolify(value):
    if value in [True, "true", "True", 1, "1"]:
        return True
    return False


# --- Helper to convert city to lat,lng ---
def get_city_lat_lng(city):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json"},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        results = response.json()
        if results:
            lat = results[0]["lat"]
            lon = results[0]["lon"]
            return f"{lat},{lon}"
    except Exception as e:
        print(f"❌ Failed to get lat/lng for city {city}: {e}")
    return None


# --- Scraper Class ---
class DaycareGoogleMapsScraper:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def scrape(self, query: str, location: str, num_results: int = 20):
        if not isinstance(location, str) or ',' not in location:
            raise ValueError("Location must be a string in 'lat,lng' format, e.g., '40.7128,-74.0060'")

        ll_formatted = f"@{location.strip()},14z"

        params = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "hl": "en",
            "ll": ll_formatted,
            "api_key": self.api_key
        }

        print(f"🌍 Using parameters for API call: {params}")

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            print("📡 Raw API response received.")
            daycares = []
            if "local_results" in results:
                print(f"✅ Found {len(results['local_results'])} local results.")
                for place in results["local_results"][:num_results]:
                    daycare = {
                    "name": place.get("title"),
                    "address": place.get("address"),
                    "phone": place.get("phone"),
                    "rating": place.get("rating"),
                    "reviews": place.get("reviews"),
                    "email": place.get("email"),  # Attempt to get email directly from API response
                    "website": place.get("website")  # Also get website for fallback
                }
                    daycares.append(daycare)
            else:
                print("⚠️ No local_results found in API response.")
            return daycares
        except Exception as e:
            print(f"❌ Error during API call or parsing: {e}")
            return []

    def save_to_database(self, daycares: list):
        session = SessionLocal()
        try:
            for data in daycares:
                email = data.get("email")
                if not email and data.get("website"):
                    email = self.scrape_email_from_website(data.get("website"))

                daycare_entry = Daycare(
                    name=data.get("name"),
                    address=data.get("address"),
                    phone=data.get("phone"),
                    rating=float(data.get("rating")) if data.get("rating") else None,
                    reviews=int(data.get("reviews")) if data.get("reviews") else None,
                    email=email,
                    website=data.get("website"),
                    email_opened=boolify(data.get("email_opened")),
                    email_replied=boolify(data.get("email_replied")),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(daycare_entry)
            session.commit()
            print("💾 All daycare data saved to the database.")
        except Exception as e:
            session.rollback()
            print(f"❌ Failed to save data: {e}")
        finally:
            session.close()

    def scrape_all(self, cities: list, query: str = "daycare centers", num_results: int = 20):
        all_results = []
        for city in cities:
            coords = get_city_lat_lng(city)
            if coords:
                print(f"📍 Scraping for city: {city} at {coords}")
                daycares = self.scrape(query=query, location=coords, num_results=num_results)
                all_results.extend(daycares)
                self.save_to_database(daycares)
            else:
                print(f"⚠️ Skipping city {city} due to missing coordinates.")
        return all_results


    def scrape_email_from_website(self, website_url: str) -> str:
        """Fallback method to scrape email from the business website and common subpages with retries, increased timeout, and URL sanitization."""
        import time
        import re
        from urllib.parse import urlparse, urlunparse, parse_qs, urljoin

        def sanitize_url(url):
            parsed = urlparse(url)
            # Remove common tracking query parameters
            query = parse_qs(parsed.query)
            filtered_query = {k: v for k, v in query.items() if not k.lower().startswith(('utm_', 'fbclid', 'gclid'))}
            new_query = '&'.join([f'{k}={v[0]}' for k, v in filtered_query.items()])
            sanitized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
            return sanitized

        def try_scrape(url):
            max_retries = 3
            timeout = 15
            sanitized = sanitize_url(url)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.get(sanitized, timeout=timeout, headers=headers)
                    if response.status_code == 200:
                        email_pattern = r'[\w\.-]+@[\w\.-]+\.[\w]{2,}'
                        match = re.search(email_pattern, response.text)
                        if match:
                            return match.group(0)
                        else:
                            print(f"\u26a0\ufe0f No email found on website {sanitized}.")
                            return None
                    elif response.status_code == 404:
                        print(f"\u26a0\ufe0f 404 Not Found for {sanitized}, skipping to next URL.")
                        return None
                    elif 500 <= response.status_code < 600:
                        print(f"\u26a0\ufe0f Server error {response.status_code} from {sanitized}, retrying...")
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)  # exponential backoff
                            continue
                        else:
                            print(f"\u274c Max retries reached for server errors on {sanitized}. Skipping.")
                            return None
                    else:
                        print(f"\u26a0\ufe0f Received status code {response.status_code} from {sanitized}.")
                        return None
                except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError) as e:
                    print(f"\u274c Attempt {attempt} - Failed to scrape email from website {sanitized}: {e}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)  # exponential backoff
                        continue
                    else:
                        print(f"\u274c Max retries reached for {sanitized}. Skipping.")
                        return None
                except Exception as e:
                    print(f"\u274c Unexpected error scraping email from website {sanitized}: {e}")
                    return None
            return None

        # Try homepage first
        email = try_scrape(website_url)
        if email:
            return email

        # Try common subpages if homepage fails
        common_subpages = ['/contact', '/contact-us', '/about', '/about-us', '/info', '/info/contact']
        for subpage in common_subpages:
            full_url = urljoin(website_url, subpage)
            email = try_scrape(full_url)
            if email:
                return email

        return None



# --- Main Run ---
if __name__ == "__main__":
    scraper = DaycareGoogleMapsScraper(api_key)
    cities = ["New York", "San Francisco"]
    scraper.scrape_all(cities)