# OAuth and Email Notifications Setup Guide

This guide provides detailed instructions for configuring Google OAuth login and email notifications in WebWatchDog.

## Google OAuth Setup

Google OAuth allows users to sign in to your WebWatchDog application using their Google accounts. Here's how to set it up:

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click "New Project"
4. Enter a project name (e.g., "WebWatchDog") and click "Create"
5. Select your new project from the dropdown once it's created

### 2. Configure OAuth Consent Screen

1. From the left navigation menu, go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (unless you're using Google Workspace) and click "Create"
3. Fill in the required information:
   - App name: "WebWatchDog"
   - User support email: Your email address
   - Developer contact information: Your email address
4. Click "Save and Continue"
5. On the Scopes screen, click "Add or Remove Scopes"
6. Add the following scopes:
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
7. Click "Save and Continue"
8. Add test users if you're still in testing mode, then click "Save and Continue"
9. Review your settings and click "Back to Dashboard"

### 3. Create OAuth Client ID

1. From the left navigation menu, go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" and select "OAuth client ID"
3. For Application type, select "Web application"
4. Name: "WebWatchDog Web Client"
5. Authorized JavaScript origins: Add your domain(s)
   - For local development: `http://localhost:5001`
   - For production: `https://your-domain.com`
6. Authorized redirect URIs: Add your callback URLs
   - For local development: `http://localhost:5001/auth/google/callback`
   - For production: `https://your-domain.com/auth/google/callback`
7. Click "Create"
8. Note your Client ID and Client Secret (you'll need these for configuration)

### 4. Update Environment Variables

Add the following to your `.env` file:

```
# Google OAuth settings
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_REDIRECT_URI=http://localhost:5001/auth/google/callback  # Change for production
```

### 5. Verify Configuration

1. Restart your application
2. Go to the login page
3. You should now see a "Sign in with Google" button
4. Test the login flow to ensure it works correctly

## Email Notifications Setup

Email notifications allow WebWatchDog to send alerts when website changes are detected. Here's how to set up email notifications:

### 1. Configure Gmail for SMTP Access (Recommended)

If using Gmail:

1. Go to your [Google Account](https://myaccount.google.com/)
2. Go to "Security"
3. Enable "2-Step Verification" if not already enabled
4. Go to "App passwords" (you'll only see this if 2-Step Verification is enabled)
5. Select "Mail" and "Other (Custom name)"
6. Enter "WebWatchDog" and click "Generate"
7. Google will generate a 16-character app password - copy this password

### 2. Update Environment Variables

Add the following to your `.env` file:

```
# Email notification settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
```

If using another email provider:
- Replace the SMTP server and port with your provider's details
- Use your regular email password if the server doesn't require app passwords

### 3. User Settings Configuration

For each user who wants to receive email notifications:

1. Log in to WebWatchDog
2. Go to Settings
3. Enable "Email Notifications"
4. Enter the email address to receive notifications or leave blank to use account email
5. Click "Save Settings"

### 4. Test Email Notifications

1. Add a website to monitor
2. Manually check the website by clicking "Check Now"
3. Verify that notifications are sent when changes are detected

## Troubleshooting

### OAuth Issues

1. Check Redirect URI:
   - Ensure the configured redirect URI exactly matches what's in Google Cloud Console
   - Check for any trailing slashes or http/https mismatches

2. Check Credentials:
   - Verify that CLIENT_ID and CLIENT_SECRET are correct
   - Check that they're properly set in your environment variables

3. Check Browser Console:
   - Look for any JavaScript errors during the OAuth flow

### Email Notification Issues

1. Check SMTP Settings:
   - Verify server, port, username, and password are correct
   - Test your SMTP credentials with a simple Python script

2. Check Application Logs:
   - Look for specific error messages related to email sending
   - Check for authentication or connection timeout issues

3. Check Email Provider Restrictions:
   - Some providers may block automated emails
   - Gmail may block "less secure apps" unless using app passwords

4. Firewall Issues:
   - Ensure your server allows outgoing connections on the SMTP port (usually 587 or 465)

## Maintenance

1. Google OAuth:
   - Client IDs and secrets don't expire unless revoked
   - Regularly check the Google Cloud Console for any policy updates

2. Email:
   - App passwords may need to be regenerated if you change your Google account password
   - Some email providers may require periodic password updates

## Security Considerations

1. Store all credentials securely:
   - Never commit credentials to version control
   - Use environment variables or secure vaults for production

2. Use HTTPS for all OAuth redirects:
   - In production, always use HTTPS URLs for redirects
   - Consider using a service like Let's Encrypt for free SSL certificates

3. Limit permissions:
   - Only request the OAuth scopes you need
   - For email, use dedicated service accounts when possible