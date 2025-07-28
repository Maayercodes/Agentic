import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime
from src.database.models import init_db, Daycare, Influencer, Platform
from loguru import logger

# Configure logger
logger.add("logs/db_test.log", rotation="10 MB", level="DEBUG")

def test_db_save():
    try:
        # Initialize database session
        logger.info("Initializing database session...")
        session = init_db()
        
        # Test daycare save
        logger.info("Testing daycare save functionality...")
        daycare_success = save_test_daycare(session)
        
        # Test influencer save
        logger.info("Testing influencer save functionality...")
        influencer_success = save_test_influencer(session)
        
        return daycare_success and influencer_success
    
    except Exception as e:
        logger.error(f"Error in test_db_save: {str(e)}")
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        if 'session' in locals():
            session.close()

def save_test_daycare(session: Session) -> bool:
    try:
        # Create a test daycare
        test_name = f"Test Daycare {datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Creating test daycare: {test_name}")
        
        test_daycare = Daycare(
            name=test_name,
            address="123 Test Street",
            city="Test City",
            email="test@example.com",
            phone="123-456-7890",
            website="https://example.com",
            region="USA",
            source="test_script",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        session.add(test_daycare)
        session.commit()
        
        # Verify the save was successful
        saved_daycare = session.query(Daycare).filter_by(name=test_name).first()
        
        if saved_daycare and saved_daycare.id:
            logger.info(f"Successfully saved test daycare with ID: {saved_daycare.id}")
            print(f"✅ Successfully saved test daycare with ID: {saved_daycare.id}")
            return True
        else:
            logger.error("Failed to save test daycare")
            print("❌ Failed to save test daycare")
            return False
            
    except Exception as e:
        logger.error(f"Error saving test daycare: {str(e)}")
        print(f"❌ Error saving test daycare: {str(e)}")
        session.rollback()
        return False

def save_test_influencer(session: Session) -> bool:
    try:
        # Create a test influencer
        test_name = f"Test Influencer {datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.info(f"Creating test influencer: {test_name}")
        
        test_influencer = Influencer(
            name=test_name,
            platform=Platform.YOUTUBE,
            follower_count=1000,
            country="USA",
            email="test@example.com",
            bio="This is a test influencer",
            niche="testing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        session.add(test_influencer)
        session.commit()
        
        # Verify the save was successful
        saved_influencer = session.query(Influencer).filter_by(name=test_name).first()
        
        if saved_influencer and saved_influencer.id:
            logger.info(f"Successfully saved test influencer with ID: {saved_influencer.id}")
            print(f"✅ Successfully saved test influencer with ID: {saved_influencer.id}")
            return True
        else:
            logger.error("Failed to save test influencer")
            print("❌ Failed to save test influencer")
            return False
            
    except Exception as e:
        logger.error(f"Error saving test influencer: {str(e)}")
        print(f"❌ Error saving test influencer: {str(e)}")
        session.rollback()
        return False

if __name__ == "__main__":
    print("=== Database Save Test ===\n")
    load_dotenv()
    success = test_db_save()
    
    if success:
        print("\n✅ Database save functionality is working!")
        exit(0)
    else:
        print("\n❌ Database save functionality test failed!")
        exit(1)