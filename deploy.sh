#!/bin/bash
# WebWatchDog Deployment Script (Direct PostgreSQL Connection)
# This script automates the deployment process to an IONOS VPS

# Exit on any error
set -e

# Configuration
APP_NAME="webwatchdog"
DEPLOY_DIR="/var/www/$APP_NAME"
GIT_REPO="https://github.com/yourusername/webwatchdog.git"  # Update this
REMOTE_USER="root"  # Or your SSH user
REMOTE_HOST="your-vps-ip-or-hostname"  # Update this

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${YELLOW}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if we have remote access
print_step "Checking SSH connection"
if ssh -q $REMOTE_USER@$REMOTE_HOST exit; then
    print_success "SSH connection to $REMOTE_HOST successful"
else
    print_error "Failed to connect to $REMOTE_HOST. Please check your SSH configuration."
    exit 1
fi

# Deploy application
print_step "Deploying WebWatchDog to $REMOTE_HOST"

# Create target directory if it doesn't exist
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $DEPLOY_DIR"
print_success "Deployment directory created"

# Clone or update the repository
ssh $REMOTE_USER@$REMOTE_HOST "
if [ -d $DEPLOY_DIR/.git ]; then
    cd $DEPLOY_DIR && git pull
    echo 'Repository updated'
else
    rm -rf $DEPLOY_DIR/*
    git clone $GIT_REPO $DEPLOY_DIR
    echo 'Repository cloned'
fi
"
print_success "Code repository updated"

# Set up virtual environment
ssh $REMOTE_USER@$REMOTE_HOST "
cd $DEPLOY_DIR
if [ ! -d venv ]; then
    python3 -m venv venv
    echo 'Virtual environment created'
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo 'Dependencies installed'
"
print_success "Virtual environment and dependencies set up"

# Copy configuration files if they don't exist
print_step "Setting up configuration"
ssh $REMOTE_USER@$REMOTE_HOST "
cd $DEPLOY_DIR
if [ ! -f .env ]; then
    cp .env.example .env
    echo 'Created .env file from example. Please update it with your credentials.'
else
    echo '.env file already exists, skipping'
fi
"
print_success "Configuration files prepared"

# Set up systemd service files
print_step "Setting up system services"
ssh $REMOTE_USER@$REMOTE_HOST "
# Create web service file
cat > /etc/systemd/system/${APP_NAME}.service << 'EOF'
[Unit]
Description=WebWatchDog Web Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$DEPLOY_DIR
Environment=\"PATH=$DEPLOY_DIR/venv/bin\"
ExecStart=$DEPLOY_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create scheduler service file
cat > /etc/systemd/system/${APP_NAME}-scheduler.service << 'EOF'
[Unit]
Description=WebWatchDog Website Check Scheduler
After=network.target postgresql.service ${APP_NAME}.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=$DEPLOY_DIR
Environment=\"PATH=$DEPLOY_DIR/venv/bin\"
ExecStart=$DEPLOY_DIR/venv/bin/python check_websites.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and restart services
systemctl daemon-reload
systemctl enable ${APP_NAME}.service ${APP_NAME}-scheduler.service
systemctl restart ${APP_NAME}.service ${APP_NAME}-scheduler.service

# Set proper permissions
chown -R www-data:www-data $DEPLOY_DIR
chmod -R 755 $DEPLOY_DIR
"
print_success "System services configured"

# Set up Nginx configuration
print_step "Configuring Nginx"
ssh $REMOTE_USER@$REMOTE_HOST "
# Create Nginx config file
cat > /etc/nginx/sites-available/$APP_NAME << 'EOF'
server {
    listen 80;
    server_name _;  # Replace with your domain if available

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Enable the site
if [ ! -L /etc/nginx/sites-enabled/$APP_NAME ]; then
    ln -s /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
fi

# Test and restart Nginx
nginx -t && systemctl restart nginx
"
print_success "Nginx configured"

# Check service status
print_step "Checking service status"
ssh $REMOTE_USER@$REMOTE_HOST "
echo 'Web service status:'
systemctl status ${APP_NAME}.service --no-pager | head -n 5

echo 'Scheduler service status:'
systemctl status ${APP_NAME}-scheduler.service --no-pager | head -n 5

echo 'Nginx status:'
systemctl status nginx --no-pager | head -n 5
"

# Display final message
echo
print_success "WebWatchDog has been deployed successfully to $REMOTE_HOST"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update the .env file on the server with your database credentials:"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'nano $DEPLOY_DIR/.env'"
echo
echo "2. If you have a domain name, configure it in the Nginx configuration:"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'nano /etc/nginx/sites-available/$APP_NAME'"
echo
echo "3. To set up SSL with Let's Encrypt, run:"
echo "   ssh $REMOTE_USER@$REMOTE_HOST 'apt install -y certbot python3-certbot-nginx && certbot --nginx -d yourdomain.com'"
echo
echo "4. Visit your WebWatchDog at: http://$REMOTE_HOST/"
echo