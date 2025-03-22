from flask import render_template, jsonify, request, g, redirect, url_for, session
from datetime import datetime
import logging
from app import app, db, set_toast_message_in_session
from models import Website, Check, User
from monitor import WebsiteMonitor
from sqlalchemy import UUID
from flask_login import login_required, current_user

# Note: Blueprint registration is handled in app.py
# OAuth initialization is also handled in app.py

# Store current year in session for all templates
@app.before_request
def before_request():
    session['current_year'] = datetime.now().year
    
    # If user is authenticated, make sure their websites are filtered by user_id
    if current_user.is_authenticated:
        g.user_id = current_user.id
    else:
        g.user_id = None

@app.route('/')
def index():
    """Redirect to dashboard if logged in, otherwise show login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Display the main dashboard with the user's monitored websites"""
    try:
        # Get current user's websites, ordered by URL
        websites = Website.query.filter_by(user_id=current_user.id).order_by(Website.url).all()
        return render_template('dashboard.html', 
                              websites=websites, 
                              current_year=session.get('current_year', datetime.now().year),
                              user=current_user)
    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        # Render a simple error page instead of failing completely
        return render_template('dashboard.html', 
                              websites=[], 
                              error=str(e), 
                              current_year=session.get('current_year', datetime.now().year),
                              user=current_user)

@app.route('/api/websites', methods=['POST'])
@login_required
def add_website():
    """Add a new website to monitor"""
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    # Add https:// prefix if not present
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    try:
        # Create and save new website with user_id
        website = Website(
            url=url,
            user_id=current_user.id
        )
        db.session.add(website)
        db.session.commit()
        
        # Only set toast message for non-API requests
        if not request.path.startswith('/api/'):
            # Store toast message in session
            set_toast_message_in_session('Website added successfully!', 'success')
        
        # Log the successful addition
        logging.info(f"Website added successfully by user {current_user.username}: {url}")
        
        # Return the website data so it can be added to the UI without a page refresh
        return jsonify({
            'message': 'Website added successfully',
            'id': str(website.id),
            'url': website.url,
            'status': website.status,
            'created_at': website.created_at.isoformat() if website.created_at else None,
            'last_checked': website.last_checked.isoformat() if website.last_checked else None
        }), 201
    except Exception as e:
        # Handle errors safely
        try:
            db.session.rollback()
        except:
            pass
        
        # Only set toast message for non-API requests
        if not request.path.startswith('/api/'):
            # Store toast message in session
            set_toast_message_in_session(f'Error adding website: {str(e)}', 'error')
        
        logging.error(f"Error adding website: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/websites/<uuid:website_id>', methods=['DELETE'])
@login_required
def delete_website(website_id):
    """Delete a website and all its checks"""
    try:
        # Find the website by ID and verify ownership
        website = Website.query.get_or_404(website_id)
        
        # Check if user owns this website
        if website.user_id != current_user.id:
            return jsonify({'error': 'You do not have permission to delete this website'}), 403
            
        logging.info(f"Deleting website {website.url} with ID {website_id}")

        try:
            # Delete in a single transaction with cascading
            db.session.delete(website)
            db.session.commit()
            
            # Only set toast message for non-API requests
            if not request.path.startswith('/api/'):
                # Store toast message in session
                set_toast_message_in_session(f'Website {website.url} deleted successfully!', 'success')
            
            logging.info(f"Website deleted successfully: {website.url}")
            return jsonify({'message': 'Website deleted successfully'}), 200

        except Exception as e:
            # Handle database errors
            try:
                db.session.rollback()
            except:
                pass
            error_msg = f"Database error while deleting website {website_id}: {str(e)}"
            logging.error(error_msg)
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        error_msg = f"Error finding website {website_id}: {str(e)}"
        logging.error(error_msg)
        return jsonify({'error': error_msg}), 404

@app.route('/api/websites/<uuid:website_id>/check', methods=['POST'])
@login_required
def check_website(website_id):
    """Check a specific website for changes"""
    try:
        # Find the website by ID
        website = Website.query.get_or_404(website_id)
        
        # Check if user owns this website
        if website.user_id != current_user.id:
            return jsonify({'error': 'You do not have permission to check this website'}), 403
        
        # Check if user has set up Telegram chat ID for notifications
        if not current_user.telegram_chat_id:
            return jsonify({
                'error': 'Telegram chat ID not configured',
                'message': 'Please set up your Telegram Chat ID in Settings to receive notifications about website changes.',
                'type': 'warning',
                'redirect': url_for('settings.user_settings')
            }), 400
            
        # Check if user has set up Telegram bot token
        if not current_user.telegram_bot_token:
            return jsonify({
                'error': 'Telegram bot token not configured',
                'message': 'Please set up your Telegram Bot Token in Settings to receive notifications about website changes.',
                'type': 'warning',
                'redirect': url_for('settings.user_settings')
            }), 400
        
        # Initialize monitor and run check with email notification support
        monitor = WebsiteMonitor(
            telegram_bot_token=current_user.telegram_bot_token,
            telegram_chat_id=current_user.telegram_chat_id,
            email_notifications_enabled=current_user.email_notifications_enabled,
            notification_email=current_user.notification_email or current_user.email
        )
        has_changed = monitor.check_website(website)

        # Refresh website data from database after check
        db.session.refresh(website)

        # Only set toast message for non-API requests
        if not request.path.startswith('/api/'):
            # Store toast message in session
            if has_changed:
                set_toast_message_in_session(f'Changes detected on {website.url}!', 'info')
            else:
                set_toast_message_in_session(f'Website {website.url} checked successfully', 'success')

        # Format the timestamp data for the client
        last_checked_data = {
            'utc': website.last_checked.isoformat() if website.last_checked else None,
            'timestamp': website.last_checked.timestamp() if website.last_checked else None
        }

        # Return properly formatted response
        return jsonify({
            'status': website.status,
            'last_checked': last_checked_data,
            'has_changed': has_changed,
            'message': 'Website checked successfully'
        }), 200
    except Exception as e:
        logging.error(f"Error checking website {website_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/check-all', methods=['POST'])
@login_required
def check_all_websites():
    """Check all websites for the current user"""
    try:
        # Check if user has set up Telegram chat ID for notifications
        if not current_user.telegram_chat_id:
            return jsonify({
                'error': 'Telegram chat ID not configured',
                'message': 'Please set up your Telegram Chat ID in Settings to receive notifications about website changes.',
                'type': 'warning',
                'redirect': url_for('settings.user_settings')
            }), 400
            
        # Check if user has set up Telegram bot token
        if not current_user.telegram_bot_token:
            return jsonify({
                'error': 'Telegram bot token not configured',
                'message': 'Please set up your Telegram Bot Token in Settings to receive notifications about website changes.',
                'type': 'warning',
                'redirect': url_for('settings.user_settings')
            }), 400
        
        # Get all websites for the current user
        websites = Website.query.filter_by(user_id=current_user.id).all()
        
        if not websites:
            # Store toast message in session
            set_toast_message_in_session('No websites to check', 'warning')
            return jsonify({'message': 'No websites to check'}), 200
            
        # Initialize monitor with email notification support
        monitor = WebsiteMonitor(
            telegram_bot_token=current_user.telegram_bot_token,
            telegram_chat_id=current_user.telegram_chat_id,
            email_notifications_enabled=current_user.email_notifications_enabled,
            notification_email=current_user.notification_email or current_user.email
        )
        
        website_results = []
        for website in websites:
            try:
                has_changed = monitor.check_website(website)
                # Refresh website data
                db.session.refresh(website)
                
                # Format last_checked for JSON serialization
                last_checked = None
                if website.last_checked:
                    last_checked = website.last_checked.isoformat()
                
                website_results.append({
                    'id': str(website.id),
                    'url': website.url,
                    'status': website.status,
                    'has_changed': has_changed,
                    'last_checked': last_checked
                })
            except Exception as e:
                logging.error(f"Error checking website {website.url}: {str(e)}")
                website_results.append({
                    'id': str(website.id),
                    'url': website.url,
                    'status': 'error',
                    'error': str(e)
                })
                
        # Only set toast message for non-API requests
        if not request.path.startswith('/api/'):
            # Add summary toast message for completed checks
            changes_detected = sum(1 for w in website_results if w.get('has_changed', False))
            if changes_detected > 0:
                set_toast_message_in_session(f'Changes detected on {changes_detected} of {len(websites)} websites!', 'info')
            else:
                set_toast_message_in_session(f'Checked {len(websites)} websites successfully', 'success')
            
        return jsonify({
            'message': f'Checked {len(websites)} websites',
            'websites': website_results
        }), 200
    except Exception as e:
        logging.error(f"Error in check all websites: {str(e)}")
        return jsonify({'error': str(e)}), 400
        
        
@app.route("/debug/scheduler", methods=["GET"])
@login_required
def debug_scheduler():
    """Debug endpoint to show scheduler info and run scheduled jobs"""
    # Restrict access to admin users only
    if current_user.username != 'admin':
        return jsonify({
            'status': 'error',
            'message': 'Access denied. Admin privileges required.'
        }), 403
        
    try:
        # Make sure we have the scheduler
        if not hasattr(app, 'scheduler') or not app.scheduler:
            return jsonify({
                'status': 'error',
                'message': 'Scheduler not found. It may not be initialized.'
            })
            
        # Get scheduler information
        scheduler = app.scheduler
        jobs = []
        
        # Get current user's jobs
        user_id_str = str(current_user.id)
        username = current_user.username
        
        # Collect info on all jobs
        for job in scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': str(job.next_run_time) if job.next_run_time else 'Not scheduled',
                'trigger': str(job.trigger),
                'is_user_job': job.id.startswith(f'user_{user_id_str}')
            }
            jobs.append(job_info)
            
        # Format the user's schedules
        user_schedules = []
        if current_user.schedule_1:
            user_schedules.append({
                'id': 1,
                'cron': current_user.schedule_1
            })
        if current_user.schedule_2:
            user_schedules.append({
                'id': 2,
                'cron': current_user.schedule_2
            })
        if current_user.schedule_3:
            user_schedules.append({
                'id': 3,
                'cron': current_user.schedule_3
            })
        if current_user.schedule_4:
            user_schedules.append({
                'id': 4,
                'cron': current_user.schedule_4
            })
            
        # Get current server time (important for debugging timezone issues)
        from datetime import datetime
        now = datetime.now()
        import pytz
        tz = scheduler.timezone if hasattr(scheduler, 'timezone') else pytz.UTC
        pst_tz = pytz.timezone('America/Los_Angeles')  # Add explicit PST timezone
        now_with_tz = datetime.now(tz)
        now_in_pst = datetime.now(pst_tz)
        
        # Return detailed information
        return jsonify({
            'status': 'success',
            'scheduler_info': {
                'running': scheduler.running,
                'timezone': str(tz),
                'timezone_name': 'US Pacific Time (PST/PDT)',
                'server_time': str(now),
                'scheduler_time': str(now_with_tz),
                'pacific_time': str(now_in_pst)
            },
            'user_info': {
                'id': user_id_str,
                'username': username,
                'schedules': user_schedules
            },
            'jobs': jobs
        })
        
    except Exception as e:
        logging.error(f"Error in debug_scheduler: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })
        
        
@app.route("/debug/run_checks_now", methods=["POST"])
@login_required
def run_scheduled_checks_now():
    """Debug endpoint to manually run the scheduled checks for the current user"""
    # Restrict access to admin users only
    if current_user.username != 'admin':
        return jsonify({
            'status': 'error',
            'message': 'Access denied. Admin privileges required.'
        }), 403
        
    try:
        # Import function directly from app
        from app import init_scheduler
        
        # Get user ID
        user_id = str(current_user.id)
        
        # Get current app from flask
        from flask import current_app
        
        # Create a custom function to run the check directly
        # Get the function directly from the app context
        app_obj = app
        if hasattr(current_app, '_get_current_object'):
            app_obj = current_app._get_current_object()
            
        # Create website monitor and check manually with email notification support
        from monitor import WebsiteMonitor
        monitor = WebsiteMonitor(
            telegram_bot_token=current_user.telegram_bot_token,
            telegram_chat_id=current_user.telegram_chat_id,
            email_notifications_enabled=current_user.email_notifications_enabled,
            notification_email=current_user.notification_email or current_user.email
        )
        
        # Get all websites for this user
        websites = Website.query.filter_by(user_id=current_user.id).all()
        logging.info(f"Manually checking {len(websites)} websites for user {current_user.username}")
        
        # Check each website
        for website in websites:
            try:
                monitor.check_website(website)
                logging.info(f"Manual check completed for {website.url}")
            except Exception as e:
                logging.error(f"Error in manual check for {website.url}: {str(e)}")
                # Continue with next website
        
        # Create a toast message in session
        set_toast_message_in_session('Manual check triggered successfully', 'success')
        
        return jsonify({
            'status': 'success',
            'message': 'Manually triggered website checks for your user account'
        })
        
    except Exception as e:
        logging.error(f"Error in run_scheduled_checks_now: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })