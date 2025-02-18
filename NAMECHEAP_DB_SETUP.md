# Setting Up PostgreSQL Database on Namecheap

This guide provides step-by-step instructions for setting up a PostgreSQL database on Namecheap's hosting service.

## 1. Purchase Database Hosting

1. Go to [Namecheap.com](https://www.namecheap.com)
2. Navigate to Hosting > Database Hosting
3. Select "PostgreSQL Hosting"
4. Choose a plan based on your needs:
   - Starter (1GB) for small projects
   - Professional (5GB) for medium-sized applications
   - Enterprise (10GB+) for larger applications

## 2. Access cPanel

1. After purchase, go to your Namecheap dashboard
2. Click "Manage" next to your database hosting
3. Click "Go to cPanel"
4. Login with your credentials

## 3. Create Database

1. In cPanel, locate "PostgreSQL Databases"
2. Click "Create Database"
3. Enter database name (only lowercase letters, numbers, and underscores)
4. Click "Create"

## 4. Create Database User

1. Still in PostgreSQL Databases section
2. Go to "Add New User"
3. Enter username (lowercase letters, numbers, underscores)
4. Enter a strong password
   - At least 12 characters
   - Mix of uppercase, lowercase, numbers, symbols
5. Save these credentials securely

## 5. Grant User Permissions

1. Under "Manage User Privileges"
2. Select your database and user
3. Grant necessary privileges:
   - SELECT, INSERT, UPDATE, DELETE for basic operations
   - CREATE, ALTER for schema modifications
4. Click "Make Changes"

## 6. Get Connection Details

Your connection details will be in this format:
```
Host: pgsqlXX.namecheap.com (XX will be your server number)
Port: 5432
Database: your_database_name
Username: your_username
Password: your_password
```

## 7. Enable Remote Access

1. Go to "Remote MySQL/PostgreSQL" in cPanel
2. Add your application's IP address
   - For Replit: Use the IP shown in your Repl
   - For local development: Your IP address
3. Click "Add Host"

## 8. Test Connection

Test the connection using psql:
```bash
psql -h pgsqlXX.namecheap.com -U your_username -d your_database_name
```

Or using Python:
```python
import psycopg2

conn = psycopg2.connect(
    dbname="your_database_name",
    user="your_username",
    password="your_password",
    host="pgsqlXX.namecheap.com",
    port="5432"
)
```

## 9. Environment Variables

In your application, use environment variables for the connection:

```python
DATABASE_URL = "postgresql://username:password@pgsqlXX.namecheap.com:5432/dbname"
```

## 10. Troubleshooting

1. **Connection Refused**
   - Check if IP is whitelisted
   - Verify port 5432 is not blocked

2. **Authentication Failed**
   - Double-check username/password
   - Ensure proper case sensitivity

3. **Database Does Not Exist**
   - Verify database name
   - Check user has access to database

## 11. Best Practices

1. Regular Backups
   - Use cPanel's backup tools
   - Schedule automated backups

2. Security
   - Use strong passwords
   - Limit IP access
   - Regularly update user permissions

3. Monitoring
   - Check database size regularly
   - Monitor connection limits
   - Watch for slow queries

## 12. Support

For additional help:
1. Namecheap Support: support.namecheap.com
2. PostgreSQL Docs: postgresql.org/docs/
