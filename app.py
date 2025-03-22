"""
WebWatchDog - Website Monitoring Application
Main Flask application module
Updated for Python 3.12.3 compatibility with user authentication
"""
import os
import uuid
import logging
import pytz
import json
import urllib.parse
from flask import Flask, g, request, make_response, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()  # Also output to console
    ]
)

logger = logging.getLogger(__name__)

# Import database module for initialization
from database import Base, get_db_session, db_connection

# Initialize Flask and SQLAlchemy
app = Flask(__name__)
db = SQLAlchemy(model_class=Base)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = "auth.login"
login_manager.login_message = None  # Disable default flash message - we'll handle this with JS toasts

# Toast message utility function
def set_toast_message(response, message, type="info"):
    """
    Sets a toast message in a cookie to be displayed on the next page load
    
    Args:
        response: Flask response object
        message: Message text to display
        type: Toast type (info, success, warning, error)
    """
    toast_data = json.dumps({"message": message, "type": type})
    # Ensure cookie is accessible to JavaScript (httponly=False) and URL encode the value
    encoded_data = urllib.parse.quote(toast_data)
    response.set_cookie('toast_message', encoded_data, max_age=30, httponly=False, samesite='Strict', path='/')
    return response

# Store toast messages in the session to be rendered in templates
def set_toast_message_in_session(message, type="info"):
    """Store toast message in session"""
    session['toast_message'] = message
    session['toast_type'] = type

# Function to convert flashed messages to toast messages
@app.after_request
def process_toast_messages(response):
    """Process flash messages and convert them to toast messages"""
    # Only process on HTML responses
    if response.mimetype == 'text/html':
        # Get any messages from flash and convert to toasts
        flashed_messages = session.pop('_flashes', [])
        if flashed_messages:
            # Get the first message (most recent)
            category, message = flashed_messages[0]
            
            # Map Flask message categories to toast types
            toast_type = 'info'
            if category == 'success': toast_type = 'success'
            if category in ('danger', 'error'): toast_type = 'error'
            if category == 'warning': toast_type = 'warning'
            
            # Store the toast message in session
            set_toast_message_in_session(message, toast_type)
    
    return response

# Add toast messages from session to all templates
@app.context_processor
def inject_toast_messages():
    """Inject toast messages into all templates"""
    toast_message = session.pop('toast_message', None)
    toast_type = session.pop('toast_type', 'info')
    return dict(toast_message=toast_message, toast_type=toast_type)

# Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default-secret-key")

# OAuth configurations for Google
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET")
app.config["OAUTHLIB_INSECURE_TRANSPORT"] = os.environ.get("OAUTHLIB_INSECURE_TRANSPORT", "0")

# Get database URL for direct connection
try:
    database_url = db_connection.get_db_url()
    logger.info(f"Using database URL: {database_url}")
except Exception as e:
    logger.error(f"Failed to get database URL: {str(e)}")
    raise Exception("Cannot get database URL")

# Configure SQLAlchemy with direct database connection
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 60,
    "pool_pre_ping": True,
    "connect_args": {
        "application_name": "website_monitor",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "connect_timeout": 10
    }
}

# Configure Telegram (optional)
app.config["TELEGRAM_BOT_TOKEN"] = os.environ.get("TELEGRAM_BOT_TOKEN")
app.config["TELEGRAM_CHAT_ID"] = os.environ.get("TELEGRAM_CHAT_ID")

if not app.config["TELEGRAM_BOT_TOKEN"] or not app.config["TELEGRAM_CHAT_ID"]:
    logger.warning("Telegram configuration is missing. Notifications will not work.")

# Initialize database
db.init_app(app)

# Initialize login manager after app is created
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    from models import User
    return User.query.get(user_id)

# Add database session management
@app.teardown_appcontext
def close_db_session(exception=None):
    """Close database session when request context ends"""
    session = g.pop('db_session', None)
    if session is not None:
        session.close()

def init_scheduler():
    """Initialize the background scheduler for user-specific website checks"""
    try:
        # Shutdown existing scheduler if it exists
        if hasattr(app, 'scheduler') and app.scheduler:
            try:
                app.scheduler.shutdown()
                logger.info("Existing scheduler shut down")
            except Exception as e:
                logger.error(f"Error shutting down existing scheduler: {str(e)}")
                
        # Create new scheduler with explicit timezone configuration
        # Use US Pacific Time as the primary timezone for scheduling
        import pytz
        scheduler_timezone = pytz.timezone('America/Los_Angeles')  # PST/PDT timezone
        logger.info(f"Initializing scheduler with timezone: {scheduler_timezone} (US Pacific Time)")
        
        # Configure scheduler with timezone and job defaults
        scheduler = BackgroundScheduler(
            timezone=scheduler_timezone,
            job_defaults={
                'coalesce': True,       # Combine multiple waiting instances
                'max_instances': 1,     # Only allow one instance to run at a time
                'misfire_grace_time': 60 * 10  # Allow 10 minutes of misfires
            }
        )
        
        def check_websites_for_user(user_id=None, telegram_bot_token=None, telegram_chat_id=None):
            """Check websites for a specific user or all websites if user_id is None"""
            
            # Create fresh application context for this job
            with app.app_context():
                try:
                    # Import models within the function to avoid circular imports
                    from models import Website, User
                    from monitor import WebsiteMonitor
                    
                    if user_id:
                        # Check websites for a specific user
                        user = User.query.get(user_id)
                        if not user:
                            logger.error(f"User {user_id} not found for scheduled check")
                            return
                        
                        # Use user's telegram chat ID if available, otherwise use the one passed in
                        user_telegram_chat_id = user.telegram_chat_id or telegram_chat_id
                        
                        # Initialize monitor with user-specific settings for both Telegram and email
                        monitor = WebsiteMonitor(
                            telegram_bot_token=telegram_bot_token,
                            telegram_chat_id=user_telegram_chat_id,
                            email_notifications_enabled=user.email_notifications_enabled,
                            notification_email=user.notification_email or user.email
                        )
                        
                        # Get only this user's websites
                        websites = Website.query.filter_by(user_id=user_id).all()
                        logger.info(f"Checking {len(websites)} websites for user {user.username} (ID: {user_id})")
                    else:
                        # Legacy mode: check all websites (for backward compatibility)
                        # Initialize monitor with global telegram settings
                        # For legacy mode, we don't enable email notifications
                        monitor = WebsiteMonitor(
                            telegram_bot_token=app.config["TELEGRAM_BOT_TOKEN"],
                            telegram_chat_id=app.config["TELEGRAM_CHAT_ID"],
                            email_notifications_enabled=False,
                            notification_email=None
                        )
                        
                        # Get all websites
                        websites = Website.query.all()
                        logger.info(f"Checking {len(websites)} websites (global check)")
                    
                    # Check each website and properly close session after each one
                    for website in websites:
                        try:
                            monitor.check_website(website)
                            # Sleep a brief moment between website checks to avoid overwhelming the database
                            import time
                            time.sleep(1)
                        except Exception as e:
                            logger.error(f"Error checking website {website.url}: {str(e)}")
                            # Continue with next website even if this one fails
                            
                except Exception as e:
                    logger.error(f"Error in scheduled website check: {str(e)}")
                finally:
                    # Make sure everything is properly cleaned up
                    db.session.remove()

        # First, add default global checks at fixed times (for backward compatibility)
        scheduler.add_job(
            check_websites_for_user,
            CronTrigger(
                hour='8,15,19', 
                minute='0', 
                timezone=scheduler_timezone  # Use same timezone as the rest of the scheduler
            ),
            id='global_check',
            name='Global Website Check',
            replace_existing=True
        )
        
        # Then, try to add user-specific schedule jobs from the database
        with app.app_context():
            try:
                from models import User
                
                # Get all active users and set up their schedules
                users = User.query.filter_by(is_active=True).all()
                logger.info(f"Setting up schedules for {len(users)} active users")
                
                for user in users:
                    # Skip users without schedules
                    if not any([user.schedule_1, user.schedule_2, user.schedule_3, user.schedule_4]):
                        logger.info(f"User {user.username} has no schedules defined, skipping")
                        continue
                    
                    user_id_str = str(user.id)
                    
                    # Add each of the user's schedules if defined
                    schedule_fields = [
                        (user.schedule_1, "1"), 
                        (user.schedule_2, "2"), 
                        (user.schedule_3, "3"), 
                        (user.schedule_4, "4")
                    ]
                    
                    for schedule, num in schedule_fields:
                        if not schedule:
                            continue
                            
                        # Parse cron expression
                        try:
                            parts = schedule.split()
                            if len(parts) != 5:  # must have 5 parts: minute, hour, day, month, day_of_week
                                logger.error(f"Invalid cron expression for user {user.username}: {schedule}")
                                continue
                                
                            minute, hour, day, month, day_of_week = parts
                            
                            scheduler.add_job(
                                check_websites_for_user,
                                CronTrigger(
                                    minute=minute, 
                                    hour=hour, 
                                    day=day, 
                                    month=month, 
                                    day_of_week=day_of_week,
                                    timezone=scheduler_timezone  # Explicitly use the scheduler timezone
                                ),
                                kwargs={
                                    'user_id': user_id_str,
                                    'telegram_bot_token': app.config["TELEGRAM_BOT_TOKEN"],
                                    'telegram_chat_id': user.telegram_chat_id or app.config["TELEGRAM_CHAT_ID"]
                                },
                                id=f'user_{user_id_str}_schedule_{num}',
                                name=f'User {user.username} Schedule {num}',
                                replace_existing=True
                            )
                            logger.info(f"Added schedule {num} for user {user.username}: {schedule}")
                        except Exception as e:
                            logger.error(f"Error setting up schedule {num} for user {user.username}: {str(e)}")
            except Exception as e:
                logger.error(f"Error setting up user schedules: {str(e)}")

        scheduler.start()
        logger.info("Scheduler started successfully with global and user-specific website checks")
        return scheduler
    except Exception as e:
        logger.error(f"Failed to initialize scheduler: {str(e)}")
        return None

# Import database testing functionality
from database import test_database_connection

# Create all database tables and test database connection
with app.app_context():
    try:
        # Test database connection with detailed logging
        if not test_database_connection():
            logger.error("Database connection test failed")
            raise Exception("Cannot connect to database")
            
        # Try to use the new consolidated test module (for Python 3.12.3)
        try:
            import test_db
            logger.info("Using Python 3.12.3 compatible database test module")
        except ImportError:
            logger.warning("Python 3.12.3 database test module not available")
        
        # Import models for table creation
        import models  # noqa: F401
        
        # We're transitioning to a user-based model, so we need to handle the migration
        # Check if the tables need to be created or migrated
        from sqlalchemy import inspect, Table, Column, String, ForeignKey, text
        from sqlalchemy.dialects.postgresql import UUID
        inspector = inspect(db.engine)
        
        # First check if we need to create users table
        if 'users' not in inspector.get_table_names():
            logger.info("Users table not found. Creating users table.")
            
            # Create the users table (but not the whole schema yet)
            metadata = db.MetaData()
            
            # Define users table
            users_table = Table(
                'users', 
                metadata,
                Column('id', UUID(as_uuid=True), primary_key=True),
                Column('email', String(255), unique=True, nullable=False),
                Column('username', String(64), unique=True, nullable=False),
                Column('password_hash', String(256), nullable=True),
                Column('created_at', db.DateTime(timezone=True), default=db.func.now()),
                Column('is_active', db.Boolean, default=True, nullable=False),
                Column('oauth_provider', String(20), nullable=True),
                Column('oauth_id', String(255), nullable=True),
                Column('telegram_chat_id', String(100), nullable=True),
                Column('schedule_1', String(50), nullable=True),
                Column('schedule_2', String(50), nullable=True),
                Column('schedule_3', String(50), nullable=True),
                Column('schedule_4', String(50), nullable=True)
            )
            
            # Create the users table first
            users_table.create(db.engine)
            logger.info("Created users table successfully")
            
            # Create a default admin user
            from models import User
            admin = User(
                email="admin@example.com",
                username="admin",
                is_active=True,
                schedule_1="0 8 * * *"  # Default: 8am daily
            )
            admin.set_password("changeme")
            db.session.add(admin)
            db.session.commit()
            logger.info("Created default admin user (email: admin@example.com, password: changeme)")
        
        # Now check if we need to migrate the website table
        website_columns = [c['name'] for c in inspector.get_columns('websites')]
        if 'user_id' not in website_columns:
            logger.info("Migrating websites table to add user_id column")
            
            # Create or get the admin user to associate with existing websites
            from models import User
            admin_user = User.query.filter_by(username='admin').first()
            
            if not admin_user:
                logger.info("Admin user not found, creating default admin user for website migration")
                admin_user = User(
                    id=uuid.uuid4(),
                    email="admin@example.com",
                    username="admin",
                    is_active=True,
                    schedule_1="0 8 * * *"  # Default: 8am daily
                )
                admin_user.set_password("changeme")
                db.session.add(admin_user)
                db.session.commit()
                logger.info("Created default admin user (email: admin@example.com, password: changeme)")
                
            admin_id = str(admin_user.id)
            logger.info(f"Using admin user ID {admin_id} for website migration")
            
            # Add user_id column to existing websites table
            with db.engine.connect() as conn:
                # Add user_id column
                conn.execute(text(
                    f"ALTER TABLE websites ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE"
                ))
                
                # Update existing records to associate with the admin user
                conn.execute(text(
                    f"UPDATE websites SET user_id = '{admin_id}'"
                ))
                
                # Make user_id not nullable
                conn.execute(text(
                    "ALTER TABLE websites ALTER COLUMN user_id SET NOT NULL"
                ))
                
                # Remove uniqueness constraint on url
                conn.execute(text(
                    "ALTER TABLE websites DROP CONSTRAINT IF EXISTS websites_url_key"
                ))
                
                # Add unique constraint on (url, user_id)
                conn.execute(text(
                    "ALTER TABLE websites ADD CONSTRAINT uq_website_url_user UNIQUE (url, user_id)"
                ))
                
                # Commit the transaction
                conn.commit()
                
            logger.info("Website table migration completed successfully")
        
        # Create any missing tables and update any changed columns
        db.create_all()
        logger.info("All tables are now up to date")
        
    except Exception as e:
        logger.error(f"Failed to create or migrate database tables: {str(e)}")
        # We will NOT fallback to SQLite - just fail the application
        raise

# Import and register auth blueprint with OAuth initialization
from auth import bp as auth_bp, init_oauth
app.register_blueprint(auth_bp)

# Import and register user settings blueprint
from user_settings import bp as settings_bp
app.register_blueprint(settings_bp)

# Initialize OAuth with the Flask app if it's configured
if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
    init_oauth(app)

# Import routes after blueprints are registered
from routes import *  # noqa: F401, E402

# Note: The scheduler will be initialized in main.py