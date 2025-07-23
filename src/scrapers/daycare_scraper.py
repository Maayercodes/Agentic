import os
import dotenv
import requests
from serpapi import GoogleSearch
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, text, inspect
)
from sqlalchemy.orm import declarative_base, sessionmaker
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
engine = create_engine(db_url, pool_pre_ping=True)
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

# --- Create missing columns if not exist ---
def add_missing_columns(engine):
    inspector = inspect(engine)
    existing_cols = [col["name"] for col in inspector.get_columns("daycares")]
    column_types = {
        "rating": "DOUBLE PRECISION",
        "reviews": "INTEGER",
        "city": "VARCHAR",
        "region": "VARCHAR",
        "source": "VARCHAR",
        "last_contacted": "TIMESTAMP",
        "email_opened": "BOOLEAN",
        "email_replied": "BOOLEAN",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP"
    }

    with engine.begin() as conn:  # ensures commit
        for col_name, col_type in column_types.items():
            if col_name not in existing_cols:
                alter = f'ALTER TABLE daycares ADD COLUMN {col_name} {col_type}'
                try:
                    conn.execute(text(alter))
                    print(f"✅ Added missing column: {col_name}")
                except Exception as e:
                    print(f"❌ Failed to add column {col_name}: {e}")

add_missing_columns(engine)

# --- Boolean cleaner ---
def boolify(value):
    return value in [True, "true", "True", 1, "1"]

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
            raise ValueError("Location must be a string in 'lat,lng' format")

        ll_formatted = f"@{location.strip()},14z"
        params = {
            "engine": "google_maps",
            "type": "search",
            "q": query,
            "hl": "en",
            "ll": ll_formatted,
            "api_key": self.api_key
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            daycares = []
            if "local_results" in results:
                for place in results["local_results"][:num_results]:
                    daycare = {
                        "name": place.get("title"),
                        "address": place.get("address"),
                        "phone": place.get("phone"),
                        "rating": place.get("rating"),
                        "reviews": place.get("reviews"),
                        "email": place.get("email"),
                        "website": place.get("website")
                    }
                    daycares.append(daycare)
            return daycares
        except Exception as e:
            print(f"❌ Error during API call: {e}")
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
            print("💾 Data saved to database.")
        except Exception as e:
            session.rollback()
            print(f"❌ DB Save Failed: {e}")
        finally:
            session.close()

    def scrape_all(self, cities: list, query: str = "daycare centers", num_results: int = 20):
        all_results = []
        for city in cities:
            coords = get_city_lat_lng(city)
            if coords:
                print(f"📍 Scraping: {city} at {coords}")
                daycares = self.scrape(query=query, location=coords, num_results=num_results)
                all_results.extend(daycares)
                self.save_to_database(daycares)
            else:
                print(f"⚠️ Skipped city {city} (no coords)")
        return all_results

    def scrape_email_from_website(self, website_url: str) -> str:
        import time, re
        from urllib.parse import urlparse, urlunparse, parse_qs, urljoin

        def sanitize_url(url):
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            filtered_query = {k: v for k, v in query.items() if not k.lower().startswith(('utm_', 'fbclid', 'gclid'))}
            new_query = '&'.join([f'{k}={v[0]}' for k, v in filtered_query.items()])
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

        def try_scrape(url):
            headers = {"User-Agent": "Mozilla/5.0"}
            for attempt in range(3):
                try:
                    response = requests.get(sanitize_url(url), timeout=10, headers=headers)
                    if response.status_code == 200:
                        match = re.search(r'[\w\.-]+@[\w\.-]+\.[\w]{2,}', response.text)
                        if match:
                            return match.group(0)
                    elif response.status_code == 404:
                        return None
                    elif 500 <= response.status_code < 600:
                        time.sleep(2 ** attempt)
                        continue
                    return None
                except Exception:
                    time.sleep(2 ** attempt)
            return None

        email = try_scrape(website_url)
        if email:
            return email

        for sub in ['/contact', '/about', '/info']:
            full_url = urljoin(website_url, sub)
            email = try_scrape(full_url)
            if email:
                return email
        return None

# --- Run ---
if __name__ == "__main__":
    scraper = DaycareGoogleMapsScraper(api_key)
    cities = ["New York", "San Francisco"]
    scraper.scrape_all(cities)
