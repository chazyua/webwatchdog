# WebWatchDog (WWD)

WebWatchDog is an advanced web content monitoring system that provides real-time tracking and automated notifications for website changes across multiple domains, with intelligent monitoring capabilities.

## Features

- **Website Change Detection**: Monitor multiple websites for content changes
- **Secure Database Storage**: PostgreSQL database for reliable data persistence
- **Multi-channel Notifications**: Get notified via Telegram and Email when changes are detected
- **User Account System**: Individual accounts with personal website lists
- **Responsive Dashboard**: User-friendly interface to monitor all websites
- **Custom Scheduling**: Set personalized check schedules for your websites
- **Detailed Change Logs**: Track when and how websites change
- **Efficient Content Extraction**: Uses trafilatura for accurate content extraction
- **Automatic Record Retention**: Keeps history organized with automatic cleanup
- **Robust Database Connectivity**: Direct PostgreSQL connection for improved reliability
- **OAuth Integration**: Simple sign-in with Google account

## Tech Stack

- Python 3.12.3 
- Flask web framework
- SQLAlchemy ORM for database management
- PostgreSQL database with direct connection
- Trafilatura for web content extraction
- BeautifulSoup and lxml for fallback parsing
- Telegram Bot API for notifications
- SMTP email notifications
- Flask-Login for user authentication
- OAuth for social login
- APScheduler for custom check schedules
- Responsive web design with Bootstrap 5
- JavaScript for dynamic updates
- Feather Icons for UI elements

## Project Structure

The codebase is organized with a clean, modular structure:

- **app.py**: Core application setup and configuration
- **main.py**: Entry point with server startup
- **models.py**: Database models and schema definitions
- **routes.py**: Web routes and API endpoints
- **auth.py**: Authentication logic and OAuth integration
- **monitor.py**: Website checking and content comparison
- **db_utils.py**: Consolidated database utilities
- **user_settings.py**: User preference management
- **database.py**: Database connection management
- **email_sender.py**: Email notification system

## Local Development Setup

### Prerequisites

- Python 3.12.3 or higher
- PostgreSQL database (local or remote)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/webwatchdog.git
   cd webwatchdog
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   # Database Configuration (for local development)
   # Individual connection parameters
   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=webwatchdog
   PGUSER=postgres
   PGPASSWORD=your_password
   
   # Alternatively, use a full connection URL
   # DATABASE_URL=postgresql://postgres:your_password@localhost:5432/webwatchdog

   # Telegram notification settings (required for website checks)
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   # Note: TELEGRAM_CHAT_ID is set per user in the settings panel
   
   # Email notification settings (optional)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password  # Use app password for Gmail
   SMTP_FROM=your_email@gmail.com
   
   # Google OAuth settings (optional, for social login)
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   OAUTH_REDIRECT_URI=http://localhost:5001/auth/google/callback

   # Flask configuration
   FLASK_SECRET_KEY=your_secret_key
   FLASK_DEBUG=True
   ```

5. Create the PostgreSQL database:
   ```bash
   createdb webwatchdog  # Or use pgAdmin/another tool to create the database
   ```

6. Initialize the database:
   ```bash
   python init_db.py
   ```

7. Add a test user (optional):
   ```bash
   # Open a Python shell
   python
   ```
   
   ```python
   from app import app, db
   from models import User
   import uuid
   
   with app.app_context():
      # Create a test admin user
      admin = User(
         id=uuid.uuid4(),
         username='admin',
         email='admin@example.com'
      )
      admin.set_password('your_secure_password')
      db.session.add(admin)
      db.session.commit()
      print(f"Admin user created with ID: {admin.id}")
   ```

8. Run the application:
   ```bash
   python main.py
   ```

9. Open your browser and navigate to http://localhost:5001

### Setting Up Telegram Bot (Required for Notifications)

1. Talk to the [BotFather](https://t.me/botfather) on Telegram
2. Send the command `/newbot` and follow instructions to create a new bot
3. Copy the provided API token to your `.env` file as `TELEGRAM_BOT_TOKEN`
4. Start a chat with your new bot
5. To get your Chat ID, talk to [userinfobot](https://t.me/userinfobot)
6. Enter the Chat ID in your WebWatchDog user settings

## Adding Websites to Monitor

1. Open your browser and go to http://localhost:5001
2. Click on the "Add Website" button
3. Enter the URL of the website you want to monitor
4. Click "Add"

## Running Tests

```bash
pytest tests/
```

## Production Deployment

For production deployment to an IONOS VPS with direct PostgreSQL connections, refer to the [IONOS-VPS-SETUP-SIMPLIFIED.md](IONOS-VPS-SETUP-SIMPLIFIED.md) file. 

The deployment script [deploy.sh](deploy.sh) can be used to automate most of the deployment process.

## Additional Configuration

### OAuth and Email Setup

For detailed instructions on setting up Google OAuth for social login and configuring email notifications, refer to the [OAUTH-EMAIL-SETUP-GUIDE.md](OAUTH-EMAIL-SETUP-GUIDE.md) file.

## Recent Improvements

The project has undergone significant improvements focused on code quality and maintainability:

1. **Consolidated Database Utilities**: Centralized all database operations in `db_utils.py` to reduce code duplication
2. **Enhanced Error Handling**: Improved error handling throughout the application for better reliability
3. **Optimized Logging**: Reduced excessive debug logging and implemented production-appropriate logging levels
4. **Improved Documentation**: Updated documentation to reflect the current state of the project
5. **Performance Optimization**: Optimized database queries and connection management
6. **Multi-channel Notifications**: Added email notification support alongside Telegram
7. **User Settings Refinement**: Enhanced user settings and preference management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Trafilatura](https://github.com/adbar/trafilatura) for web content extraction
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Bootstrap](https://getbootstrap.com/) for frontend styling
- [Flask-Login](https://flask-login.readthedocs.io/) for authentication
- [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot) for Telegram notifications
- [APScheduler](https://apscheduler.readthedocs.io/) for task scheduling
- [Feather Icons](https://feathericons.com/) for beautiful UI icons
- [BeautifulSoup](https://beautiful-soup-4.readthedocs.io/) for HTML parsing
- [Authlib](https://authlib.org/) for OAuth implementation