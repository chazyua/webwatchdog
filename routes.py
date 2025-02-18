from flask import render_template, jsonify, request
from datetime import datetime
import logging
from app import app, db
from models import Website, Check
from monitor import WebsiteMonitor
from sqlalchemy import UUID

@app.route('/')
def dashboard():
    websites = Website.query.order_by(Website.url).all()
    return render_template('dashboard.html', websites=websites, current_year=datetime.now().year)

@app.route('/api/websites', methods=['POST'])
def add_website():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        website = Website(url=url)
        db.session.add(website)
        db.session.commit()
        return jsonify({'message': 'Website added successfully'}), 201
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding website: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/websites/<uuid:website_id>', methods=['DELETE'])
def delete_website(website_id):
    try:
        website = Website.query.get_or_404(website_id)
        logging.info(f"Deleting website {website.url} with ID {website_id}")

        try:
            # Delete all related checks first
            check_count = Check.query.filter_by(website_id=website_id).delete()
            logging.info(f"Deleted {check_count} checks for website {website_id}")
            db.session.commit()

            # Now delete the website
            db.session.delete(website)
            db.session.commit()

            logging.info(f"Website deleted successfully: {website.url}")
            return jsonify({'message': 'Website deleted successfully'}), 200

        except Exception as e:
            db.session.rollback()
            error_msg = f"Database error while deleting website {website_id}: {str(e)}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        error_msg = f"Error finding or deleting website {website_id}: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 404

@app.route('/api/websites/<uuid:website_id>/check', methods=['POST'])
def check_website(website_id):
    try:
        website = Website.query.get_or_404(website_id)
        monitor = WebsiteMonitor(
            telegram_bot_token=app.config['TELEGRAM_BOT_TOKEN'],
            telegram_chat_id=app.config['TELEGRAM_CHAT_ID']
        )
        monitor.check_website(website)

        # Refresh website data from database after check
        db.session.refresh(website)

        # Get latest check to determine if changes were detected
        latest_check = website.checks[0] if website.checks else None
        has_changed = latest_check and latest_check.status == 'changed'

        # Format the timestamp data
        last_checked_data = {
            'utc': website.last_checked.isoformat() if website.last_checked else None,
            'timestamp': website.last_checked.timestamp() if website.last_checked else None
        }

        return jsonify({
            'status': website.status,
            'last_checked': last_checked_data,
            'has_changed': has_changed,
            'message': 'Website checked successfully'
        }), 200
    except Exception as e:
        logging.error(f"Error checking website {website_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400