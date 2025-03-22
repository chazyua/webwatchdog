"""
WebWatchDog - Authentication Module
Handles user registration, login, and OAuth integration
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app, make_response
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash
import uuid
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from authlib.integrations.flask_client import OAuth

from app import db
from models import User, PasswordReset

# Load environment variables
load_dotenv()

# Create blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')

# OAuth setup
oauth = OAuth()
google = None

def init_oauth(app):
    """Initialize OAuth with the Flask app"""
    global google
    oauth.init_app(app)
    
    # Configure Google OAuth client
    google = oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
    
    return google

class LoginForm(FlaskForm):
    """User login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')
    
class ForgotPasswordForm(FlaskForm):
    """Form for requesting password reset"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Reset Password')
    
class ResetPasswordForm(FlaskForm):
    """Form for resetting password after token validation"""
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm New Password', 
                             validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Reset Password')

class RegistrationForm(FlaskForm):
    """User registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField('Confirm Password', 
                            validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        """Check if username is already in use"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            flash('Username already in use. Please choose a different one.', 'danger')
            return False
        return True
    
    def validate_email(self, email):
        """Check if email is already in use"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            flash('Email already registered. Please use a different one or login.', 'danger')
            return False
        return True

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            # Set error toast message
            from app import set_toast_message_in_session
            set_toast_message_in_session('Invalid email or password', 'error')
            return render_template('auth/login.html', form=form)
        
        login_user(user, remember=form.remember_me.data)
        
        # Create a success response with toast message
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard')
        
        # Set welcome message toast via session
        from app import set_toast_message_in_session
        set_toast_message_in_session(f'Welcome back, {user.username}!', 'success')
        
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Validate username and email aren't already taken
        if not form.validate_username(form.username) or not form.validate_email(form.email):
            return render_template('auth/register.html', form=form)
        
        user = User(
            id=uuid.uuid4(),
            username=form.username.data,
            email=form.email.data,
            is_active=True,
            schedule_1="0 8 * * *"  # Default: 8am daily
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Set toast message in session
        from app import set_toast_message_in_session
        set_toast_message_in_session('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    
    # Set toast message in session
    from app import set_toast_message_in_session
    set_toast_message_in_session('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

@bp.route('/google')
def google_login():
    """Initiate Google OAuth login"""
    if google is None:
        from app import set_toast_message_in_session
        set_toast_message_in_session('Google login is not configured', 'error')
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('auth.google_authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@bp.route('/google/callback')
def google_authorize():
    """Handle Google OAuth callback"""
    if google is None:
        from app import set_toast_message_in_session
        set_toast_message_in_session('Google login is not configured', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token)
        
        # Get user email from OAuth response
        email = user_info.get('email')
        if not email:
            from app import set_toast_message_in_session
            set_toast_message_in_session('Could not retrieve email from Google', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user with OAuth info
            username = user_info.get('name', '').replace(' ', '_').lower()
            # Make sure username is unique by adding random chars if needed
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                id=uuid.uuid4(),
                username=username,
                email=email,
                is_active=True,
                oauth_provider='google',
                oauth_id=user_info.get('sub'),
                schedule_1="0 8 * * *"  # Default: 8am daily
            )
            db.session.add(user)
            db.session.commit()
            from app import set_toast_message_in_session
            set_toast_message_in_session('Account created with Google authentication!', 'success')
        elif not user.oauth_id:
            # Update existing email-based account to link with Google
            user.oauth_provider = 'google'
            user.oauth_id = user_info.get('sub')
            db.session.commit()
            from app import set_toast_message_in_session
            set_toast_message_in_session('Google authentication linked to your account!', 'success')
        
        # Log in the user
        login_user(user)
        return redirect(url_for('dashboard'))
    
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        from app import set_toast_message_in_session
        set_toast_message_in_session('Error during Google authentication', 'error')
        return redirect(url_for('auth.login'))
        
@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Check if user is using OAuth
            if user.oauth_provider:
                from app import set_toast_message_in_session
                set_toast_message_in_session(f'This account uses {user.oauth_provider.capitalize()} authentication. Please log in with {user.oauth_provider.capitalize()}.', 'warning')
                return redirect(url_for('auth.login'))
                
            # Delete existing reset tokens for this user
            PasswordReset.query.filter_by(user_id=user.id, used=False).delete()
            db.session.commit()
            
            # Create new reset token
            reset_token = PasswordReset(user_id=user.id)
            db.session.add(reset_token)
            db.session.commit()
            
            # Generate reset link
            reset_url = url_for('auth.reset_password', token=reset_token.token, _external=True)
            
            # In a real app, you would send an email here
            # For demo purposes, we'll just display the link
            from app import set_toast_message_in_session
            set_toast_message_in_session('A password reset link has been generated. In a production environment, this would be emailed.', 'info')
            set_toast_message_in_session(f'Reset link: {reset_url}', 'info')
        else:
            # Don't reveal if email exists for security reasons
            from app import set_toast_message_in_session
            set_toast_message_in_session('If an account exists with that email, a password reset link has been sent.', 'info')
            
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', form=form)
    
@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    # Find the token
    reset_record = PasswordReset.query.filter_by(token=token, used=False).first()
    
    # Validate token
    if not reset_record or not reset_record.is_valid():
        from app import set_toast_message_in_session
        set_toast_message_in_session('The password reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.login'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.get(reset_record.user_id)
        
        if user:
            # Update password
            user.set_password(form.password.data)
            
            # Mark token as used
            reset_record.used = True
            
            db.session.commit()
            from app import set_toast_message_in_session
            set_toast_message_in_session('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            from app import set_toast_message_in_session
            set_toast_message_in_session('User not found.', 'error')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/reset_password.html', form=form, token=token)