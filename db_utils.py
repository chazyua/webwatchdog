"""
Consolidated Database Utilities Module
Provides centralized database management functions including:
- Database connection testing
- Schema migrations
- Table creation and updates
- Utility functions for database operations
"""
import os
import logging
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
from app import app, db

logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection with detailed logging"""
    try:
        from database import db_connection
        logger.info("========== DATABASE CONNECTION TEST ==========")
        success = db_connection.test_connection()
        if success:
            logger.info("Database connection test successful")
        else:
            logger.error("Database connection test failed")
        logger.info("=============================================")
        return success
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def run_migration(migration_name, migration_function):
    """
    Generic migration runner that handles app context and logging
    
    Args:
        migration_name: Name of the migration for logging
        migration_function: Function to run the actual migration SQL
    """
    logger.info(f"Starting migration: {migration_name}")
    
    try:
        with app.app_context():
            conn = db.engine.connect()
            transaction = conn.begin()
            
            try:
                # Run the specific migration function
                migration_function(conn)
                
                # Commit the transaction
                transaction.commit()
                logger.info(f"Migration '{migration_name}' completed successfully")
                return True
            
            except Exception as e:
                transaction.rollback()
                logger.error(f"Migration '{migration_name}' failed: {str(e)}")
                return False
            
            finally:
                conn.close()
                
    except Exception as e:
        logger.error(f"Error during migration '{migration_name}': {str(e)}")
        return False

# Migration function implementations
def add_telegram_bot_token(conn):
    """Add telegram_bot_token column to users table"""
    # Check if column already exists
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'telegram_bot_token'"
    ))
    
    if result.fetchone() is None:
        # Add column
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN telegram_bot_token VARCHAR(100)"
        ))
        logger.info("Added telegram_bot_token column to users table")
    else:
        logger.info("telegram_bot_token column already exists")

def add_email_notifications(conn):
    """Add email notification columns to users table"""
    # Check if email_notifications_enabled column exists
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'email_notifications_enabled'
    """))
    
    if result.fetchone() is None:
        # Add the email_notifications_enabled column
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN email_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE
        """))
        logger.info("Added email_notifications_enabled column to users table")
    else:
        logger.info("email_notifications_enabled column already exists")
        
    # Check if notification_email column exists
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'notification_email'
    """))
    
    if result.fetchone() is None:
        # Add the notification_email column
        conn.execute(text("""
            ALTER TABLE users 
            ADD COLUMN notification_email VARCHAR(255)
        """))
        logger.info("Added notification_email column to users table")
    else:
        logger.info("notification_email column already exists")

def cleanup_old_checks(website_id=None):
    """
    Cleanup old check records for a specific website or all websites
    
    Args:
        website_id: Optional ID of specific website to clean up. If None, cleans all.
    """
    from monitor import WebsiteMonitor
    from models import Website
    
    monitor = WebsiteMonitor()
    
    with app.app_context():
        if website_id:
            # Clean up for a specific website
            try:
                monitor.cleanup_old_checks(website_id)
                logger.info(f"Cleaned up old checks for website ID {website_id}")
            except Exception as e:
                logger.error(f"Error cleaning up checks for website ID {website_id}: {str(e)}")
        else:
            # Clean up for all websites
            websites = Website.query.all()
            for website in websites:
                try:
                    monitor.cleanup_old_checks(website.id)
                    logger.info(f"Cleaned up old checks for {website.url}")
                except Exception as e:
                    logger.error(f"Error cleaning up checks for {website.url}: {str(e)}")

def check_websites(website_id=None, user_id=None):
    """
    Check websites for changes
    
    Args:
        website_id: Optional specific website ID to check
        user_id: Optional specific user ID to check websites for
    """
    from monitor import WebsiteMonitor
    from models import Website, User
    
    # Configure the monitor with either global or user-specific settings
    if user_id:
        # Get user's Telegram settings
        with app.app_context():
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User ID {user_id} not found")
                return False
                
            monitor = WebsiteMonitor(
                telegram_bot_token=user.telegram_bot_token,
                telegram_chat_id=user.telegram_chat_id,
                email_notifications_enabled=user.email_notifications_enabled,
                notification_email=user.notification_email or user.email
            )
    else:
        # Use global settings from app config
        monitor = WebsiteMonitor(
            telegram_bot_token=app.config.get("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=app.config.get("TELEGRAM_CHAT_ID")
        )
    
    with app.app_context():
        if website_id:
            # Check a specific website
            website = Website.query.get(website_id)
            if not website:
                logger.error(f"Website ID {website_id} not found")
                return False
                
            # If user_id provided, verify the website belongs to that user
            if user_id and str(website.user_id) != str(user_id):
                logger.error(f"Website ID {website_id} does not belong to user {user_id}")
                return False
                
            try:
                monitor.check_website(website)
                logger.info(f"Checked website: {website.url}")
                return True
            except Exception as e:
                logger.error(f"Error checking website {website.url}: {str(e)}")
                return False
        else:
            # Check all websites or all websites for a specific user
            query = Website.query
            if user_id:
                query = query.filter(Website.user_id == user_id)
                
            websites = query.all()
            success_count = 0
            error_count = 0
            
            for website in websites:
                try:
                    monitor.check_website(website)
                    logger.info(f"Checked website: {website.url}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error checking website {website.url}: {str(e)}")
                    error_count += 1
            
            logger.info(f"Website check complete. Success: {success_count}, Errors: {error_count}")
            return success_count > 0 and error_count == 0

# Command line interface for direct script usage
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db_utils.py [test|migrate|check|cleanup]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "test":
        print("Testing database connection...")
        if test_database_connection():
            print("Database connection is working correctly.")
            sys.exit(0)
        else:
            print("Database connection test failed.")
            sys.exit(1)
            
    elif command == "migrate":
        # Run all migrations
        migrations = [
            ("add_telegram_bot_token", add_telegram_bot_token),
            ("add_email_notifications", add_email_notifications)
        ]
        
        success = True
        for name, func in migrations:
            if not run_migration(name, func):
                success = False
                
        sys.exit(0 if success else 1)
        
    elif command == "check":
        # Check websites
        from models import Website
        
        # Parse additional args
        website_id = None
        user_id = None
        
        if len(sys.argv) > 2:
            if sys.argv[2].startswith("--website="):
                website_id = sys.argv[2].split("=")[1]
            elif sys.argv[2].startswith("--user="):
                user_id = sys.argv[2].split("=")[1]
                
        if len(sys.argv) > 3:
            if sys.argv[3].startswith("--website="):
                website_id = sys.argv[3].split("=")[1]
            elif sys.argv[3].startswith("--user="):
                user_id = sys.argv[3].split("=")[1]
        
        print(f"Checking websites{f' for website_id={website_id}' if website_id else ''}{f' for user_id={user_id}' if user_id else ''}...")
        success = check_websites(website_id, user_id)
        sys.exit(0 if success else 1)
        
    elif command == "cleanup":
        # Clean up old checks
        website_id = None
        if len(sys.argv) > 2 and sys.argv[2].startswith("--website="):
            website_id = sys.argv[2].split("=")[1]
            
        print(f"Cleaning up old checks{f' for website_id={website_id}' if website_id else ''}...")
        cleanup_old_checks(website_id)
        sys.exit(0)
        
    else:
        print(f"Unknown command: {command}")
        print("Available commands: test, migrate, check, cleanup")
        sys.exit(1)