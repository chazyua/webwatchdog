# WebWatchDog - Website Monitoring System
# Updated for Python 3.12.3 compatibility with user-based architecture

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting WebWatchDog application initialization...")

# Import the app and database after logging is configured
from app import app, db, login_manager, init_scheduler
from models import User, Website, Check

# Import the consolidated database utilities module
import db_utils

# Import routes to ensure they're registered
import routes

# The auth and settings blueprints are already registered in app.py

if __name__ == "__main__":
    logger.info("Starting WebWatchDog server...")
    
    # Initialize the scheduler and attach it to the app context
    try:
        logger.info("Initializing scheduler with user-specific schedules...")
        app.scheduler = init_scheduler()
        logger.info("Scheduler initialization complete and attached to application context")
    except Exception as e:
        logger.error(f"Error initializing scheduler: {str(e)}")
    
    try:
        app.run(host="0.0.0.0", port=5001, debug=True)
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")