# Website Change Detection System

A comprehensive website monitoring system that provides real-time notifications when changes occur on tracked websites. Built with Python and Flask, this application offers an intuitive web interface and Telegram notifications for instant alerts.

## Features

- 🔍 Automated website content tracking
- ⏰ Scheduled checks (4 times daily)
- 📱 Real-time Telegram notifications
- 💻 Interactive web dashboard
- 🎨 Responsive design with gradient UI
- 🔄 Manual check capability
- 📊 Change history tracking

## Prerequisites

- Python 3.11+
- PostgreSQL database
- Telegram Bot Token and Chat ID
- Modern web browser
- Internet connection

## Local Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd website-monitor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root with the following variables:
   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/website_monitor
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   FLASK_SECRET_KEY=your_secret_key
   ```

4. **Database setup**
   - Create a PostgreSQL database named `website_monitor`
   - The application will automatically create the required tables on first run

5. **Initialize sample websites (optional)**
   ```bash
   python init_db.py
   ```

## Running the Application

1. **Start the Flask server**
   ```bash
   python main.py
   ```
   The application will be available at `http://localhost:5001`

2. **Automatic website checks**
   The system automatically checks websites four times daily:
   - 8:00 AM PST
   - 11:00 AM PST
   - 3:00 PM PST
   - 7:00 PM PST

## Usage Guide

1. **Adding a website**
   - Click the "Add Website" button in the navigation bar
   - Enter the website URL (including https://)
   - Click "Add Website" to start monitoring

2. **Monitoring websites**
   - View all monitored websites on the dashboard
   - Each website card shows:
     - Last check time
     - Last change detection time
     - Current status
     - Quick actions (Check Now, Visit Site, Delete)

3. **Manual checks**
   - Click "Check Now" on any website card to perform an immediate check
   - Results appear instantly on the dashboard

4. **Telegram notifications**
   You'll receive notifications when:
   - Website content changes are detected
   - Errors occur during website checks

## Troubleshooting

1. **Database Connection Issues**
   - Verify PostgreSQL is running
   - Check DATABASE_URL environment variable
   - Ensure database user has proper permissions

2. **Telegram Notifications**
   - Verify bot token is correct
   - Ensure bot is added to the chat
   - Check chat ID is correct

3. **Website Monitoring Issues**
   - Verify website URL is accessible
   - Check if website allows content extraction
   - Review error messages in the dashboard

## Development Notes

- The application uses APScheduler for automated checks
- Flask debug mode is enabled by default
- All times are displayed in PST (Pacific Standard Time)
- Website content is extracted using Trafilatura

For deployment instructions on Namecheap shared hosting, see [notes.md](notes.md).

## Support

For issues and questions, please open an issue in the repository.
