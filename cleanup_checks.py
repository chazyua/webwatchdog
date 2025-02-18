from app import app
from monitor import WebsiteMonitor
from models import Website

def run_cleanup():
    """Manually run cleanup of old checks for all websites"""
    monitor = WebsiteMonitor(
        telegram_bot_token=app.config["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=app.config["TELEGRAM_CHAT_ID"]
    )

    with app.app_context():
        websites = Website.query.all()
        for website in websites:
            try:
                monitor.cleanup_old_checks(website.id)
            except Exception as e:
                print(f"Error cleaning up checks for {website.url}: {str(e)}")

if __name__ == "__main__":
    run_cleanup()