import hashlib
import trafilatura
import logging
import asyncio
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Bot
from sqlalchemy import and_, or_
from app import db
from models import Website, Check

class WebsiteMonitor:
    def __init__(self, telegram_bot_token, telegram_chat_id):
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.bot = None
        if telegram_bot_token and telegram_chat_id:
            try:
                self.bot = Bot(token=telegram_bot_token)
                logging.info("Telegram bot initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Telegram bot: {str(e)}")
                self.bot = None
        else:
            logging.warning("Telegram bot not initialized - missing credentials")

    def get_content_hash(self, content):
        """Generate hash of content, with logging for debugging"""
        if not content:
            logging.warning("Empty content received for hashing")
            return None

        # Remove excessive whitespace and normalize
        content = ' '.join(content.split())
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        logging.debug(f"Generated content hash: {content_hash[:8]}...")
        return content_hash

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

            count = delete_query.count()
            if count > 0:
                delete_query.delete(synchronize_session=False)
                logging.info(f"Deleted {count} old checks for website {website_id}")

            db.session.commit()
            logging.info("Cleanup of old checks completed successfully")

        except Exception as e:
            logging.error(f"Error during cleanup of old checks: {str(e)}")
            db.session.rollback()

    def check_website(self, website):
        try:
            logging.info(f"Checking website: {website.url}")
            content = self.fetch_website_content(website.url)

            if not content:
                raise Exception("No content extracted from website")

            current_hash = self.get_content_hash(content)
            if not current_hash:
                raise Exception("Failed to generate content hash")

            # Log comparison for debugging
            logging.info(f"Previous hash: {website.last_content_hash[:8] if website.last_content_hash else 'None'}")
            logging.info(f"Current hash: {current_hash[:8]}")

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

                    try:
                        # Create and run an event loop for the async notification
                        notification_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(notification_loop)
                        notification_loop.run_until_complete(self.send_telegram_notification(
                            f"🔔 Change detected on {website.url}\n"
                            f"Time: {pst_time.strftime('%Y-%m-%d %I:%M:%S %p PST')}"
                        ))
                        notification_loop.close()
                    except Exception as e:
                        logging.error(f"Error sending change notification: {str(e)}")
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
                logging.info(f"Database updated - Website hash: {website.last_content_hash[:8]}, Check status: {check.status}")

                # Clean up old checks after successful update
                self.cleanup_old_checks(website.id)

            except Exception as e:
                logging.error(f"Error committing database changes: {str(e)}")
                db.session.rollback()
                raise

            logging.info(f"Successfully updated website status for {website.url} (changed: {has_changed})")

        except Exception as e:
            error_msg = str(e)
            logging.error(f"Error checking website {website.url}: {error_msg}")
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
            db.session.commit()

            try:
                # Create and run an event loop for the async notification
                error_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(error_loop)
                error_loop.run_until_complete(self.send_telegram_notification(
                    f"❌ Error checking {website.url}\n"
                    f"Time: {pst_time.strftime('%Y-%m-%d %I:%M:%S %p PST')}\n"
                    f"Error: {error_msg}"
                ))
                error_loop.close()
            except Exception as notify_error:
                logging.error(f"Error sending error notification: {str(notify_error)}")