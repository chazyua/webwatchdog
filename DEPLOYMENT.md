# Deployment Guide - Namecheap Shared Hosting

This guide outlines the steps to deploy the Website Change Detection System on Namecheap's shared hosting environment.

## Prerequisites

1. Namecheap hosting account with:
   - Python support
   - PostgreSQL database
   - SSH access enabled

2. Local development environment with:
   - Git
   - Python 3.11
   - PostgreSQL client

## Step 1: Database Setup

1. Create a PostgreSQL database through Namecheap's cPanel
2. Note down the following credentials:
   - Database name
   - Username
   - Password
   - Host
   - Port

## Step 2: SSH Access Setup

1. Enable SSH access in cPanel
2. Generate SSH key pair if not already done:
   ```bash
   ssh-keygen -t rsa -b 4096
   ```
3. Add your public key to cPanel's SSH Access interface
4. Test SSH connection:
   ```bash
   ssh username@your-domain.com
   ```

## Step 3: Application Deployment

1. Connect to your server via SSH:
   ```bash
   ssh username@your-domain.com
   ```

2. Navigate to the web root or your preferred directory:
   ```bash
   cd public_html
   ```

3. Clone the repository:
   ```bash
   git clone <repository-url> website-monitor
   cd website-monitor
   ```

4. Set up Python virtual environment:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   ```

5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Step 4: Environment Configuration

1. Create `.env` file:
   ```bash
   nano .env
   ```

2. Add the following configuration:
   ```env
   DATABASE_URL=postgresql://username:password@host:port/dbname
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   FLASK_SECRET_KEY=your_secret_key
   ```

## Step 5: Set Up Passenger WSGI

1. Create `passenger_wsgi.py`:
   ```python
   import sys, os
   INTERP = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
   if sys.executable != INTERP:
       os.execl(INTERP, INTERP, *sys.argv)

   from main import app as application
   ```

2. Configure `.htaccess`:
   ```apache
   PassengerPython /home/username/public_html/website-monitor/venv/bin/python
   ```

## Step 6: Database Initialization

1. Initialize the database:
   ```bash
   python init_db.py
   ```

## Step 7: Scheduled Tasks Setup

1. Set up cron jobs through cPanel for website checks:
   ```bash
   0 8,11,15,19 * * * cd /home/username/public_html/website-monitor && ./venv/bin/python check_websites.py
   ```

## Step 8: SSL Configuration

1. Install SSL certificate through Namecheap's cPanel
2. Enable HTTPS redirection in `.htaccess`:
   ```apache
   RewriteEngine On
   RewriteCond %{HTTPS} off
   RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
   ```

## Troubleshooting

1. Check application logs:
   ```bash
   tail -f /home/username/logs/error.log
   ```

2. Verify permissions:
   ```bash
   chmod -R 755 website-monitor
   chmod -R 777 website-monitor/logs
   ```

3. Test database connection:
   ```bash
   python test_db_connection.py
   ```

## Maintenance

1. Update application:
   ```bash
   git pull origin main
   source venv/bin/activate
   pip install -r requirements.txt
   touch tmp/restart.txt  # Restart Passenger
   ```

2. Backup database:
   ```bash
   pg_dump -U username dbname > backup.sql
   ```

## Security Considerations

1. Keep `.env` file secure and outside public web root
2. Regularly update dependencies
3. Use strong passwords for database and admin access
4. Enable firewall rules in cPanel
5. Regularly backup database and application files

## Support

For hosting-related issues, contact Namecheap support:
- Support portal: https://www.namecheap.com/support/
- Live chat: Available 24/7
- Email: support@namecheap.com

## Common Issues and Solutions

### Database Connection Issues

1. Verify database credentials in `.env`
2. Check if database server is accessible from your hosting
3. Ensure proper privileges are granted to database user
4. Test connection using `test_db_connection.py`

### Scheduling Problems

1. Verify cron job setup in cPanel
2. Check system timezone settings
3. Ensure proper file permissions for scripts
4. Review application logs for scheduler errors

### SSL Certificate Issues

1. Verify SSL installation in cPanel
2. Check `.htaccess` configuration
3. Clear browser cache after SSL changes
4. Ensure all resources load over HTTPS

### Performance Optimization

1. Enable caching when possible
2. Optimize database queries
3. Implement rate limiting for checks
4. Monitor resource usage through cPanel

## Rollback Procedure

If deployment fails or issues arise:

1. Access backup:
   ```bash
   cd /home/username/public_html
   mv website-monitor website-monitor-broken
   git clone -b v1.0 <repository-url> website-monitor
   ```

2. Restore database:
   ```bash
   psql -U username dbname < backup.sql
   ```

3. Update configuration:
   ```bash
   cp website-monitor-broken/.env website-monitor/
   ```

4. Restart application:
   ```bash
   touch tmp/restart.txt