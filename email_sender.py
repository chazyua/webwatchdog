"""
Email Notification Module for WebWatchDog
Handles sending email notifications when website changes are detected
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def send_change_notification(user_email, website_url, check_time=None):
    """
    Send an email notification when a website change is detected
    
    Args:
        user_email (str): Email address to send notification to
        website_url (str): URL of the website that changed
        check_time (datetime, optional): Time when the change was detected
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not user_email:
        logger.warning("No email provided for notification")
        return False
    
    try:
        # Get SMTP configuration from environment variables or use defaults
        smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        sender_email = os.environ.get('SENDER_EMAIL', smtp_username)
        
        # Check if SMTP credentials are configured
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
            logger.error("SMTP configuration is incomplete. Email notifications are disabled.")
            return False
        
        # Format the check time
        check_time_str = check_time.strftime('%A, %B %d, %Y at %I:%M %p') if check_time else datetime.utcnow().strftime('%A, %B %d, %Y at %I:%M %p')
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = f"WebWatchDog <{sender_email}>"
        msg['To'] = user_email
        msg['Subject'] = f"🔔 Change Detected on {website_url}"
        
        # Email body
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
                <h2 style="color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px;">Website Change Alert</h2>
                
                <p>Hello,</p>
                
                <p>WebWatchDog has detected changes on a website you're monitoring:</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #28a745; margin: 15px 0;">
                    <p><strong>Website:</strong> <a href="{website_url}" style="color: #007bff; text-decoration: none;">{website_url}</a></p>
                    <p><strong>Detected:</strong> {check_time_str}</p>
                </div>
                
                <p>Please visit the website to review the changes.</p>
                
                <p>Thank you for using WebWatchDog!</p>
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; font-size: 12px; color: #777;">
                    <p>This is an automated message from WebWatchDog. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML content
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        logger.info(f"Email notification sent to {user_email} for {website_url}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")
        return False


def test_email_configuration():
    """
    Test email configuration by sending a test email
    
    Returns:
        dict: Status of the test with message
    """
    try:
        # Get SMTP configuration from environment variables
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = os.environ.get('SMTP_PORT')
        smtp_username = os.environ.get('SMTP_USERNAME')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        sender_email = os.environ.get('SENDER_EMAIL', smtp_username)
        test_recipient = os.environ.get('TEST_EMAIL', smtp_username)
        
        # Check if all required configuration is available
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
            return {
                'success': False,
                'message': "Email configuration is incomplete. Please check environment variables."
            }
        
        # Create a test message
        msg = MIMEMultipart()
        msg['From'] = f"WebWatchDog <{sender_email}>"
        msg['To'] = test_recipient
        msg['Subject'] = "WebWatchDog Email Test"
        
        body = f"""
        <html>
        <body>
            <p>This is a test email from WebWatchDog to verify email notification configuration.</p>
            <p>If you received this email, your email notification system is working properly.</p>
            <p>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
        return {
            'success': True,
            'message': f"Test email sent successfully to {test_recipient}"
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f"Failed to send test email: {str(e)}"
        }


if __name__ == "__main__":
    # Setup basic logging configuration for testing
    logging.basicConfig(level=logging.INFO)
    
    # Test sending an email
    result = test_email_configuration()
    logger.info(f"Email test result: {result['message']}")