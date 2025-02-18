from app import app, db
from models import Website

def init_websites():
    initial_websites = [
        "https://chaze.net",
        "https://google.com"
    ]

    try:
        for url in initial_websites:
            # Check if website already exists
            existing = Website.query.filter_by(url=url).first()
            if not existing:
                website = Website(url=url)
                db.session.add(website)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

if __name__ == "__main__":
    with app.app_context():
        init_websites()