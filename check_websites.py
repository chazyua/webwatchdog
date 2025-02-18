from app import app
from monitor import WebsiteMonitor

def check_all_websites():
    """Manually run website checks"""
    monitor = WebsiteMonitor(
        telegram_bot_token=app.config["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=app.config["TELEGRAM_CHAT_ID"]
    )
    
    from models import Website
    with app.app_context():
        websites = Website.query.all()
        for website in websites:
            try:
                monitor.check_website(website)
            except Exception as e:
                print(f"Error checking website {website.url}: {str(e)}")

if __name__ == "__main__":
    check_all_websites()
