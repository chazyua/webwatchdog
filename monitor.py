import hashlib
import trafilatura
import logging
import asyncio
import requests
import contextlib
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Bot
from sqlalchemy import and_, or_
from app import db
from models import Website, Check
from email_sender import send_change_notification

class WebsiteMonitor:
    def __init__(self, telegram_bot_token=None, telegram_chat_id=None, email_notifications_enabled=False, notification_email=None):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.email_notifications_enabled = email_notifications_enabled
        self.notification_email = notification_email
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Initialize Telegram bot if credentials are provided
        self.bot = None
        if telegram_bot_token and telegram_chat_id:
            try:
                self.bot = Bot(token=telegram_bot_token)
                logging.info("Telegram bot initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Telegram bot: {str(e)}")
                self.bot = None
        else:
            logging.info("Telegram bot not initialized - missing credentials")

    def get_content_hash(self, content):
        """Generate hash of content"""
        if not content:
            logging.warning("Empty content received for hashing")
            return None

        # Remove excessive whitespace and normalize
        content = ' '.join(content.split())
        return hashlib.sha256(content.encode()).hexdigest()

    def fetch_website_content(self, url):
        try:
            logging.info(f"Fetching content from {url}")

            # Try with requests first to get the raw HTML
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            html_content = response.text

            # Try trafilatura first
            downloaded = trafilatura.load_html(html_content)
            content = trafilatura.extract(downloaded)

            # If trafilatura fails, try basic HTML extraction
            if not content:
                logging.warning(f"Trafilatura failed for {url}, trying fallback method")
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'lxml')

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text and normalize whitespace
                content = ' '.join(soup.get_text().split())

            if not content:
                raise Exception("Failed to extract content using both methods")

            logging.info(f"Successfully fetched content from {url} (length: {len(content)})")
            return content

        except requests.exceptions.RequestException as e:
            logging.error(f"Request error for {url}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error fetching content for {url}: {str(e)}")
            raise

    async def send_telegram_notification(self, message):
        """Send a message using the Telegram bot"""
        try:
            if self.bot and self.telegram_chat_id:
                logging.info("Sending Telegram notification...")
                try:
                    await self.bot.send_message(
                        chat_id=self.telegram_chat_id,
                        text=message,
                        parse_mode='HTML'
                    )
                    logging.info("Telegram notification sent successfully")
                except Exception as e:
                    logging.error(f"Error sending Telegram message: {str(e)}")
            else:
                logging.warning("Telegram notification skipped - bot not configured")
        except Exception as e:
            logging.error(f"Error in send_telegram_notification: {str(e)}")

    def cleanup_old_checks(self, website_id):
        """Keep only the last 3 checks for a website, always preserving the most recent change detection."""
        try:
            # Keep the most recent 'changed' status check
            latest_change = Check.query.filter(
                and_(
                    Check.website_id == website_id,
                    Check.status == 'changed'
                )
            ).order_by(Check.check_time.desc()).first()

            checks_to_keep_ids = []
            if latest_change:
                checks_to_keep_ids.append(latest_change.id)

            # Get the 3 most recent checks (excluding the latest change if it exists)
            recent_checks = Check.query.filter(
                and_(
                    Check.website_id == website_id,
                    Check.id.notin_(checks_to_keep_ids) if checks_to_keep_ids else True
                )
            ).order_by(Check.check_time.desc()).limit(3).all()

            checks_to_keep_ids.extend([check.id for check in recent_checks])

            # Delete all other checks for this website
            delete_query = Check.query.filter(
                and_(
                    Check.website_id == website_id,
                    Check.id.notin_(checks_to_keep_ids)
                )
            )

            # Only run the delete if there are checks to remove
            count = delete_query.count()
            if count > 0:
                delete_query.delete(synchronize_session=False)
                logging.info(f"Deleted {count} old checks for website {website_id}")
                db.session.commit()
            
            logging.info("Cleanup of old checks completed successfully")

        except Exception as e:
            logging.error(f"Error during cleanup of old checks: {str(e)}")
            db.session.rollback()
            # Continue with operation, don't fail the entire check because cleanup failed

    def check_website(self, website):
        """Check a website for changes, with proper database session handling"""
        # Initialize timezone for error notifications
        pst_time = datetime.now(ZoneInfo('America/Los_Angeles'))
        
        try:
            logging.info(f"Checking website: {website.url}")
            content = self.fetch_website_content(website.url)

            if not content:
                raise Exception("No content extracted from website")

            current_hash = self.get_content_hash(content)
            if not current_hash:
                raise Exception("Failed to generate content hash")

            # Compare content hashes
            if website.last_content_hash:
                logging.debug(f"Hash comparison: {website.last_content_hash[:8]} vs {current_hash[:8]}")
            else:
                logging.debug("No previous hash available for comparison")

            # Create check record with UTC timestamp
            check = Check(
                website_id=website.id,
                status='success',
                content_hash=current_hash,
                check_time=datetime.utcnow()
            )

            # Compare hashes and detect changes
            has_changed = False
            if website.last_content_hash:
                has_changed = website.last_content_hash != current_hash
                if has_changed:
                    check.status = 'changed'
                    pst_time = datetime.now(ZoneInfo('America/Los_Angeles'))
                    logging.info(f"Change detected for {website.url}")

                    # Send Telegram notification if configured
                    if self.telegram_chat_id and self.telegram_bot_token:
                        try:
                            # Create and run an event loop for the async notification
                            with contextlib.closing(asyncio.new_event_loop()) as notification_loop:
                                asyncio.set_event_loop(notification_loop)
                                notification_loop.run_until_complete(self.send_telegram_notification(
                                    f"🔔 Change detected on {website.url}\n"
                                    f"Time: {pst_time.strftime('%Y-%m-%d %I:%M:%S %p PST')}"
                                ))
                        except Exception as e:
                            logging.error(f"Error sending Telegram notification: {str(e)}")
                    
                    # Send email notification if enabled
                    if self.email_notifications_enabled and self.notification_email:
                        try:
                            logging.info(f"Sending email notification to {self.notification_email}")
                            email_sent = send_change_notification(
                                self.notification_email, 
                                website.url, 
                                check_time=check.check_time
                            )
                            if email_sent:
                                logging.info(f"Email notification sent successfully to {self.notification_email}")
                            else:
                                logging.warning(f"Failed to send email notification to {self.notification_email}")
                        except Exception as e:
                            logging.error(f"Error sending email notification: {str(e)}")
            else:
                logging.info(f"First check for {website.url}, setting initial hash")

            # Always update the website's last content hash and status with UTC timestamp
            website.last_checked = datetime.utcnow()
            website.last_content_hash = current_hash
            website.status = 'success'

            try:
                # Add and commit changes in the correct order
                db.session.add(check)
                db.session.add(website)
                db.session.commit()
                logging.info("Database changes committed successfully")

                # Verify the update by refreshing from database
                db.session.refresh(website)
                db.session.refresh(check)

                # Clean up old checks after successful update using a try-except to isolate failures
                try:
                    self.cleanup_old_checks(website.id)
                except Exception as cleanup_error:
                    logging.error(f"Cleanup error (non-fatal): {str(cleanup_error)}")
                    # Don't let cleanup errors affect the main operation

            except Exception as db_error:
                logging.error(f"Error committing database changes: {str(db_error)}")
                try:
                    db.session.rollback()
                except:
                    pass
                raise

            logging.info(f"Successfully updated website status for {website.url} (changed: {has_changed})")
            return has_changed

        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error checking website {website.url}: {error_msg}")
            
            try:
                # Create a fresh check record for the error
                check = Check(
                    website_id=website.id,
                    status='error',
                    error_message=error_msg,
                    check_time=datetime.utcnow()
                )

                # Update website status
                website.status = 'error'
                website.last_checked = datetime.utcnow()

                # Add and commit changes
                db.session.add(check)
                db.session.add(website)  # Make sure website changes are saved
                
                # Use a short transaction
                db.session.commit()
                logging.info(f"Error status recorded for {website.url}")
                
                # Send notifications about the error
                
                # Send Telegram notification if configured
                if self.telegram_chat_id and self.telegram_bot_token:
                    try:
                        # Create and run an event loop for the async notification
                        with contextlib.closing(asyncio.new_event_loop()) as error_loop:
                            asyncio.set_event_loop(error_loop)
                            error_loop.run_until_complete(self.send_telegram_notification(
                                f"❌ Error checking {website.url}\n"
                                f"Time: {pst_time.strftime('%Y-%m-%d %I:%M:%S %p PST')}\n"
                                f"Error: {error_msg}"
                            ))
                    except Exception as notify_error:
                        logging.error(f"Error sending Telegram error notification: {str(notify_error)}")
                        
                # Send email notification if enabled
                if self.email_notifications_enabled and self.notification_email:
                    try:
                        logging.info(f"Sending error email notification to {self.notification_email}")
                        # For errors, we use the same notification function but add error context
                        email_sent = send_change_notification(
                            self.notification_email, 
                            f"{website.url} (Error: {error_msg[:50]}...)", 
                            check_time=check.check_time
                        )
                        if email_sent:
                            logging.info(f"Error email notification sent successfully to {self.notification_email}")
                        else:
                            logging.warning(f"Failed to send error email notification to {self.notification_email}")
                    except Exception as e:
                        logging.error(f"Error sending error email notification: {str(e)}")
                    
            except Exception as db_error:
                logging.error(f"Failed to record error status: {str(db_error)}")
                try:
                    db.session.rollback()
                except:
                    pass
            
            return False