import os
import logging
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from database import DatabaseConnection, get_db_session
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Base = declarative_base()

# Initialize Flask and SQLAlchemy
app = Flask(__name__)
db = SQLAlchemy(model_class=Base)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret-key")

# Get database connection through SSH tunnel
database_connection = DatabaseConnection()
try:
    session = get_db_session()
    app.config["SQLALCHEMY_DATABASE_URI"] = session.bind.url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
except Exception as e:
    logger.error(f"Failed to establish database connection: {str(e)}")
    raise

# Configure Telegram (optional)
app.config["TELEGRAM_BOT_TOKEN"] = os.environ.get("TELEGRAM_BOT_TOKEN")
app.config["TELEGRAM_CHAT_ID"] = os.environ.get("TELEGRAM_CHAT_ID")

if not app.config["TELEGRAM_BOT_TOKEN"] or not app.config["TELEGRAM_CHAT_ID"]:
    logger.warning("Telegram configuration is missing. Notifications will not work.")

# Initialize database
db.init_app(app)

def init_scheduler():
    scheduler = BackgroundScheduler()
    
    def check_db_health():
        """Periodic database health check"""
        try:
            with app.app_context():
                session = get_db_session()
                with session.begin():
                    session.execute(text('SELECT 1'))  # Now text() is available
                logger.info("Database health check passed")
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            database_connection.close()  # Force reconnection on next request

    # Check database health every 30 seconds
    scheduler.add_job(
        check_db_health,
        'interval',
        seconds=30,
        id='db_health_check'
    )

    def check_all_websites():
        from monitor import WebsiteMonitor
        monitor = WebsiteMonitor(
            telegram_bot_token=app.config["TELEGRAM_BOT_TOKEN"],
            telegram_chat_id=app.config["TELEGRAM_CHAT_ID"]
        )
        try:
            from models import Website
            with app.app_context():
                websites = Website.query.all()
                for website in websites:
                    try:
                        monitor.check_website(website)
                    except Exception as e:
                        logger.error(f"Error checking website {website.url}: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching websites: {str(e)}")

    # Schedule website checks
    scheduler.add_job(
        check_all_websites,
        CronTrigger(hour='8,11,15,19', timezone='America/Los_Angeles')
    )

    scheduler.start()
    logger.info("Scheduler started successfully with website checks and database health checks")
    return scheduler

# Create all database tables
with app.app_context():
    try:
        import models  # noqa: F401
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise

# Import routes after db initialization
from routes import *  # noqa: F401, E402

# Start the scheduler after everything is initialized
scheduler = init_scheduler()