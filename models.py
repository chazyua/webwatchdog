import os
import secrets
from datetime import datetime, timedelta
from app import db
import uuid
from sqlalchemy import UUID, String, TypeDecorator
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Use UUID in production
UUIDType = UUID

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # OAuth related fields
    oauth_provider = db.Column(db.String(20), nullable=True)  # 'google' or None for email
    oauth_id = db.Column(db.String(255), nullable=True)

    # User preferences
    # Telegram notification settings
    telegram_chat_id = db.Column(db.String(100), nullable=True)
    telegram_bot_token = db.Column(db.String(100), nullable=True)
    
    # Email notification settings
    email_notifications_enabled = db.Column(db.Boolean, default=False)
    notification_email = db.Column(db.String(255), nullable=True)  # Optional different email for notifications
    
    # Schedule settings - stored as cron expressions
    schedule_1 = db.Column(db.String(50), nullable=True, default="0 8 * * *")  # Default: 8am daily
    schedule_2 = db.Column(db.String(50), nullable=True)
    schedule_3 = db.Column(db.String(50), nullable=True)
    schedule_4 = db.Column(db.String(50), nullable=True)
    
    # Relationships
    websites = db.relationship('Website', backref='user', lazy=True, 
                             cascade='all, delete-orphan')

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Return the user ID as a unicode string"""
        return str(self.id)

class Website(db.Model):
    __tablename__ = 'websites'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    url = db.Column(db.String, nullable=False)
    last_checked = db.Column(db.DateTime(timezone=True))
    last_content_hash = db.Column(db.String)
    status = db.Column(db.String, default='pending')  # pending, success, error
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    
    # User foreign key
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Add relationship to checks with cascade delete
    checks = db.relationship('Check', backref='website', lazy=True, 
                           cascade='all, delete-orphan',
                           order_by='desc(Check.check_time)')
    
    __table_args__ = (
        db.UniqueConstraint('url', 'user_id', name='uq_website_url_user'),
    )

class Check(db.Model):
    __tablename__ = 'checks'

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    website_id = db.Column(UUIDType, db.ForeignKey('websites.id', ondelete='CASCADE'), nullable=False)
    check_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    status = db.Column(db.String, nullable=False)  # success, error, changed
    content_hash = db.Column(db.String)
    error_message = db.Column(db.String)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

class PasswordReset(db.Model):
    __tablename__ = 'password_resets'
    
    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUIDType, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    expires_at = db.Column(db.DateTime(timezone=True))
    used = db.Column(db.Boolean, default=False)
    
    # Relationship with User model
    user = db.relationship('User', backref=db.backref('password_resets', lazy=True))
    
    def __init__(self, user_id, token=None, expires_in_hours=24):
        self.user_id = user_id
        self.token = token or secrets.token_urlsafe(32)
        self.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
    def is_valid(self):
        """Check if the token is valid (not expired and not used)"""
        # Ensure both datetimes are timezone-aware or timezone-naive for comparison
        now = datetime.utcnow()
        expires = self.expires_at
        
        # Make both naive for comparison
        if expires.tzinfo:
            expires = expires.replace(tzinfo=None)
            
        return not self.used and expires > now