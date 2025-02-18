from datetime import datetime
from app import db
import uuid
from sqlalchemy import UUID

class Website(db.Model):
    __tablename__ = 'websites'

    id = db.Column(UUID, primary_key=True, default=uuid.uuid4)
    url = db.Column(db.String, unique=True, nullable=False)
    last_checked = db.Column(db.DateTime(timezone=True))
    last_content_hash = db.Column(db.String)
    status = db.Column(db.String, default='pending')  # pending, success, error
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    # Add relationship to checks with cascade delete
    checks = db.relationship('Check', backref='website', lazy=True, 
                           cascade='all, delete-orphan',
                           order_by='desc(Check.check_time)')

class Check(db.Model):
    __tablename__ = 'checks'

    id = db.Column(UUID, primary_key=True, default=uuid.uuid4)
    website_id = db.Column(UUID, db.ForeignKey('websites.id', ondelete='CASCADE'), nullable=False)
    check_time = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    status = db.Column(db.String, nullable=False)  # success, error, changed
    content_hash = db.Column(db.String)
    error_message = db.Column(db.String)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)