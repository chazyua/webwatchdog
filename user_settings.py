"""
WebWatchDog - User Settings Module
Handles user preferences and configuration
"""

import json
import logging
import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, make_response
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import Optional, Length, Regexp, Email

from app import db


def mask_token(token):
    """
    Mask a token showing only the last 5 characters with *** prefix
    
    Args:
        token (str): Token to mask
        
    Returns:
        str: Masked token with *** prefix and last 5 characters visible
    """
    if not token:
        return ""
    
    if len(token) <= 5:
        return token
        
    return "***" + token[-5:]

# Create blueprint
bp = Blueprint('settings', __name__, url_prefix='/settings')

class UserSettingsForm(FlaskForm):
    """User settings form"""
    # Telegram notification settings
    telegram_chat_id = StringField('Telegram Chat ID', validators=[Optional(), Length(max=100)])
    telegram_bot_token = StringField('Telegram Bot Token', validators=[Optional(), Length(max=100)])
    
    # Email notification settings
    email_notifications_enabled = BooleanField('Enable Email Notifications')
    notification_email = StringField('Notification Email', validators=[Optional(), Email(), Length(max=255)])
    
    schedule_1 = StringField('Schedule 1 (Cron Format)', 
                           validators=[Optional(), 
                                     Regexp(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])) (\*|([0-6]))$',
                                            message='Must be a valid cron expression (e.g., "0 8 * * *" for 8:00 AM daily)')])
    
    schedule_2 = StringField('Schedule 2 (Cron Format)',
                           validators=[Optional(), 
                                     Regexp(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])) (\*|([0-6]))$',
                                            message='Must be a valid cron expression (e.g., "0 8 * * *" for 8:00 AM daily)')])
    
    schedule_3 = StringField('Schedule 3 (Cron Format)',
                           validators=[Optional(), 
                                     Regexp(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])) (\*|([0-6]))$',
                                            message='Must be a valid cron expression (e.g., "0 8 * * *" for 8:00 AM daily)')])
    
    schedule_4 = StringField('Schedule 4 (Cron Format)',
                           validators=[Optional(), 
                                     Regexp(r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])) (\*|([0-6]))$',
                                            message='Must be a valid cron expression (e.g., "0 8 * * *" for 8:00 AM daily)')])
    
    submit = SubmitField('Save Settings')

@bp.route('/', methods=['GET', 'POST'])
@login_required
def user_settings():
    """User settings page"""
    form = UserSettingsForm()
    
    # Flag to indicate if the bot token is masked
    has_masked_token = False
    masked_token = ""
    
    # Populate form with current user settings
    if request.method == 'GET':
        form.telegram_chat_id.data = current_user.telegram_chat_id
        
        # If user has a token, mask it for display
        if current_user.telegram_bot_token:
            masked_token = mask_token(current_user.telegram_bot_token)
            form.telegram_bot_token.data = masked_token
            has_masked_token = True
        else:
            form.telegram_bot_token.data = ""
            
        form.email_notifications_enabled.data = current_user.email_notifications_enabled
        form.notification_email.data = current_user.notification_email or current_user.email
        form.schedule_1.data = current_user.schedule_1
        form.schedule_2.data = current_user.schedule_2
        form.schedule_3.data = current_user.schedule_3
        form.schedule_4.data = current_user.schedule_4
    
    if form.validate_on_submit():
        # Update user settings
        current_user.telegram_chat_id = form.telegram_chat_id.data
        
        # Only update the bot token if it's a new token (not the masked version)
        token_input = form.telegram_bot_token.data
        
        if not token_input:
            # Clear the token if empty
            current_user.telegram_bot_token = ''
        elif token_input != masked_token and not token_input.startswith('***'):
            # Token is not the masked version, so update it
            current_user.telegram_bot_token = token_input
            
        current_user.email_notifications_enabled = form.email_notifications_enabled.data
        current_user.notification_email = form.notification_email.data
        current_user.schedule_1 = form.schedule_1.data
        current_user.schedule_2 = form.schedule_2.data
        current_user.schedule_3 = form.schedule_3.data
        current_user.schedule_4 = form.schedule_4.data
        
        db.session.commit()
        
        # Set toast message in session
        from app import set_toast_message_in_session
        set_toast_message_in_session('Settings updated successfully', 'success')
        return redirect(url_for('settings.user_settings'))
    
    # Pass additional context to the template
    has_bot_token = bool(current_user.telegram_bot_token)
    masked_token = mask_token(current_user.telegram_bot_token) if has_bot_token else ""
    
    return render_template('settings/user_settings.html', 
                         form=form,
                         has_bot_token=has_bot_token,
                         masked_token=masked_token)

@bp.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings as JSON"""
    settings = {
        # Telegram settings
        'telegram_chat_id': current_user.telegram_chat_id,
        'telegram_bot_token': mask_token(current_user.telegram_bot_token), # Mask token for security
        'has_bot_token': bool(current_user.telegram_bot_token), # Flag to indicate if user has a token
        
        # Email settings
        'email_notifications_enabled': current_user.email_notifications_enabled,
        'notification_email': current_user.notification_email,
        
        # Schedule settings
        'schedules': [
            current_user.schedule_1,
            current_user.schedule_2,
            current_user.schedule_3,
            current_user.schedule_4
        ]
    }
    return jsonify(settings)

@bp.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    """Update user settings via API"""
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    data = request.get_json()
    
    # Update Telegram settings
    if 'telegram_chat_id' in data:
        current_user.telegram_chat_id = data['telegram_chat_id']
        
    if 'telegram_bot_token' in data:
        # Only update if the token is not the masked version
        token_input = data['telegram_bot_token']
        # Get the masked token for comparison
        masked_token = mask_token(current_user.telegram_bot_token)
        
        if not token_input:
            # If empty string provided, clear the token
            current_user.telegram_bot_token = ''
        elif token_input != masked_token and not token_input.startswith('***'):
            # Token is not the masked version, so update it
            current_user.telegram_bot_token = token_input
    
    # Update schedules
    if 'schedules' in data and isinstance(data['schedules'], list):
        schedules = data['schedules']
        
        # Validate cron expressions
        cron_pattern = r'^(\*|([0-9]|1[0-9]|2[0-9]|3[0-9]|4[0-9]|5[0-9])) (\*|([0-9]|1[0-9]|2[0-3])) (\*|([1-9]|1[0-9]|2[0-9]|3[0-1])) (\*|([1-9]|1[0-2])) (\*|([0-6]))$'
        import re
        
        # Get logger for logging validation info
        logger = logging.getLogger(__name__)
        
        # Process each schedule and validate
        for i, schedule in enumerate(schedules[:4]):
            # Skip empty schedules
            if not schedule:
                if i == 0:
                    current_user.schedule_1 = ''
                elif i == 1:
                    current_user.schedule_2 = ''
                elif i == 2:
                    current_user.schedule_3 = ''
                elif i == 3:
                    current_user.schedule_4 = ''
                continue
                
            # Make sure it's a valid cron expression
            if re.match(cron_pattern, schedule):
                # Schedule is valid
                logger.info(f"Valid cron expression: {schedule}")
                if i == 0:
                    current_user.schedule_1 = schedule
                elif i == 1:
                    current_user.schedule_2 = schedule
                elif i == 2:
                    current_user.schedule_3 = schedule
                elif i == 3:
                    current_user.schedule_4 = schedule
            else:
                # Try to fix the schedule if it's missing parts
                parts = schedule.split()
                if len(parts) >= 2:  # At least minute and hour are provided
                    minute = parts[0]
                    hour = parts[1]
                    
                    # Default values for day, month, day_of_week
                    day = '*'
                    month = '*'
                    day_of_week = '*'
                    
                    if len(parts) >= 5:
                        day = parts[2]
                        month = parts[3]
                        day_of_week = parts[4]
                    
                    # Construct a valid cron expression
                    fixed_schedule = f"{minute} {hour} {day} {month} {day_of_week}"
                    
                    if re.match(cron_pattern, fixed_schedule):
                        logger.info(f"Fixed cron expression from '{schedule}' to '{fixed_schedule}'")
                        if i == 0:
                            current_user.schedule_1 = fixed_schedule
                        elif i == 1:
                            current_user.schedule_2 = fixed_schedule
                        elif i == 2:
                            current_user.schedule_3 = fixed_schedule
                        elif i == 3:
                            current_user.schedule_4 = fixed_schedule
                    else:
                        logger.error(f"Invalid cron expression and couldn't fix: {schedule}")
                else:
                    logger.error(f"Invalid cron expression format: {schedule}")
    
    # Save changes
    db.session.commit()
    
    # Restart the scheduler to apply new settings
    try:
        from app import init_scheduler
        
        # Log the schedules for debugging
        logger = logging.getLogger(__name__)
        logger.info(f"User {current_user.username} updated schedules: {current_user.schedule_1}, {current_user.schedule_2}, {current_user.schedule_3}, {current_user.schedule_4}")
        
        # Get current scheduler instance and shut it down
        from flask import current_app
        if hasattr(current_app, 'scheduler') and current_app.scheduler:
            logger.info("Shutting down existing scheduler")
            current_app.scheduler.shutdown()
        
        # Initialize and start a new scheduler
        logger.info("Starting new scheduler with updated user schedules")
        current_app.scheduler = init_scheduler()
        
        # Set toast message in session and return JSON response
        from app import set_toast_message_in_session
        set_toast_message_in_session('Settings updated successfully', 'success')
        return jsonify({'message': 'Settings updated and schedule activated'})
    except Exception as e:
        logger.error(f"Failed to restart scheduler: {str(e)}")
        return jsonify({'message': 'Settings updated but scheduler restart failed'})