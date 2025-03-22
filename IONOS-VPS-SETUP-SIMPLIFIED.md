# IONOS VPS Setup Guide (Comprehensive)

This guide provides a detailed approach to deploying WebWatchDog on an IONOS VPS using direct PostgreSQL connection. This guide is compatible with Python 3.12.3 and optimized for stability and security.

## Prerequisites

- IONOS VPS with Ubuntu 22.04 LTS
- Root access to the VPS
- Python 3.12.3 (installation instructions included below)
- Basic knowledge of Linux commands
- Domain name (optional, but recommended for SSL)
- Telegram Bot Token (required for notifications)
- Email account credentials (optional, for email notifications)
- Google OAuth credentials (optional, for social login)

## Setup Steps

### 1. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y build-essential libssl-dev zlib1g-dev \
libncurses5-dev libncursesw5-dev libreadline-dev libsqlite3-dev \
libgdbm-dev libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev \
libffi-dev libgdbm-compat-dev tk-dev libssh-dev curl \
nginx postgresql postgresql-contrib ufw

# Set up a basic firewall
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

### 2. Install Python 3.12.3

```bash
# Download Python 3.12.3
cd /tmp
curl -O https://www.python.org/ftp/python/3.12.3/Python-3.12.3.tgz

# Extract and compile Python
tar -xzf Python-3.12.3.tgz
cd Python-3.12.3
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall

# Verify Python installation
python3.12 --version  # Should output: Python 3.12.3

# Create symlinks (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/local/bin/python3.12 1
sudo update-alternatives --install /usr/bin/pip3 pip3 /usr/local/bin/pip3.12 1

# Update pip
python3.12 -m pip install --upgrade pip
```

### 3. Configure PostgreSQL

```bash
# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create a database user and database for the application
sudo -u postgres psql -c "CREATE USER webwatchdog WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "CREATE DATABASE webwatchdog OWNER webwatchdog;"
sudo -u postgres psql -c "ALTER USER webwatchdog WITH SUPERUSER;"

# Configure PostgreSQL to listen on all interfaces (only if direct external access is needed)
# Edit postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
# Update listen_addresses line to:
# listen_addresses = '*'

# Edit pg_hba.conf to allow access from specific IPs
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add the following line (for specific IP):
# host    all             all             your_ip_address/32         scram-sha-256
# Or for testing (NOT recommended for production):
# host    all             all             0.0.0.0/0                  scram-sha-256

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 4. Clone and Set Up WebWatchDog

```bash
# Create application directory
mkdir -p /var/www/webwatchdog
cd /var/www/webwatchdog

# Clone the repository
git clone https://github.com/yourusername/webwatchdog.git .

# Create virtual environment with Python 3.12
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r clean_requirements.txt  # Optimized for Python 3.12.3 with direct DB connection

# Create .env file
cp .env.example .env
nano .env
```

Configure the `.env` file with all required connection parameters:

```
# PostgreSQL Database Connection Parameters
PGHOST=localhost
PGPORT=5432
PGDATABASE=webwatchdog
PGUSER=webwatchdog
PGPASSWORD=your_secure_password

# Telegram notification settings (required for website change alerts)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
# Note: TELEGRAM_CHAT_ID is set per user in the settings panel

# Email notification settings (optional but recommended)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # Use app password for Gmail
SMTP_FROM=your_email@gmail.com

# Google OAuth settings (optional, for social login)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTH_REDIRECT_URI=https://your-domain.com/auth/google/callback

# Flask configuration
FLASK_SECRET_KEY=your_random_secret_key  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
FLASK_DEBUG=False  # Always set to False in production

# Logging settings (optional)
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, or CRITICAL
```

### 5. Set Up Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Create a systemd service file
sudo nano /etc/systemd/system/webwatchdog.service
```

Add the following content to the service file:

```ini
[Unit]
Description=WebWatchDog Web Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/webwatchdog
Environment="PATH=/var/www/webwatchdog/venv/bin"
ExecStart=/var/www/webwatchdog/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Set permissions
sudo chown -R www-data:www-data /var/www/webwatchdog

# Start and enable the service
sudo systemctl start webwatchdog
sudo systemctl enable webwatchdog
```

### 6. Configure Nginx

```bash
# Create Nginx server block
sudo nano /etc/nginx/sites-available/webwatchdog
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your_domain.com;  # Replace with your domain or VPS IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/webwatchdog /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Set Up Background Tasks

```bash
# Create a scheduler service
sudo nano /etc/systemd/system/webwatchdog-scheduler.service
```

Add the following content:

```ini
[Unit]
Description=WebWatchDog Website Check Scheduler
After=network.target postgresql.service webwatchdog.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/webwatchdog
Environment="PATH=/var/www/webwatchdog/venv/bin"
ExecStart=/var/www/webwatchdog/venv/bin/python check_websites.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start and enable the scheduler service
sudo systemctl start webwatchdog-scheduler
sudo systemctl enable webwatchdog-scheduler
```

### 8. Set Up SSL (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your_domain.com
```

## Verification

1. Check the status of services:
   ```bash
   sudo systemctl status webwatchdog
   sudo systemctl status webwatchdog-scheduler
   sudo systemctl status postgresql
   sudo systemctl status nginx
   ```

2. View application logs:
   ```bash
   sudo journalctl -u webwatchdog -f
   sudo journalctl -u webwatchdog-scheduler -f
   ```

3. Verify the application is running by visiting your domain or server IP in a browser.

## Troubleshooting

1. Check PostgreSQL connection:
   ```bash
   sudo -u www-data psql -h localhost -U webwatchdog -d webwatchdog -c "SELECT 1"
   ```

2. Test network connectivity:
   ```bash
   sudo nc -zv localhost 5432  # Test PostgreSQL connectivity
   ```

3. Check for database errors:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

4. Verify file permissions:
   ```bash
   sudo chown -R www-data:www-data /var/www/webwatchdog
   sudo chmod -R 755 /var/www/webwatchdog
   ```

5. Restart services after configuration changes:
   ```bash
   sudo systemctl restart webwatchdog webwatchdog-scheduler nginx postgresql
   ```

## Maintenance

1. Update application:
   ```bash
   cd /var/www/webwatchdog
   git pull
   source venv/bin/activate
   pip install -r clean_requirements.txt  # Use optimized requirements for Python 3.12.3
   sudo systemctl restart webwatchdog webwatchdog-scheduler
   ```

2. Database backup:
   ```bash
   sudo -u postgres pg_dump webwatchdog > webwatchdog_backup_$(date +%Y%m%d).sql
   ```

3. Regular system updates:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```