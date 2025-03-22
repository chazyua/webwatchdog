"""
PostgreSQL Database Connection Module
Direct connection only - clean implementation
Updated for Python 3.12.3 compatibility
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define Base for models
Base = declarative_base()

# Database connection class
class DatabaseConnection:
    def __init__(self):
        self.engine = None
        self.Session = None
        
        # Get database configuration from environment variables
        self.db_host = os.environ.get('DB_HOST', os.environ.get('PGHOST', 'localhost'))
        self.db_port = os.environ.get('DB_PORT', os.environ.get('PGPORT', '5432'))
        self.db_name = os.environ.get('DB_NAME', os.environ.get('PGDATABASE', 'webwatchdog'))
        self.db_username = os.environ.get('DB_USERNAME', os.environ.get('PGUSER', 'postgres'))
        self.db_password = os.environ.get('DB_PASSWORD', os.environ.get('PGPASSWORD', ''))
        
        # Also look for a full DATABASE_URL
        self.database_url = os.environ.get('DATABASE_URL', None)
        
        # Log the database configuration (without password)
        logger.info(f"Database configuration: host={self.db_host}, port={self.db_port}, "
                   f"database={self.db_name}, username={self.db_username}")

    def test_connection(self):
        """Test database connection by executing a simple query"""
        try:
            # First ensure we have a connection
            self.connect()

            # Test the connection with a query that shows database details
            with self.engine.connect() as connection:
                version = connection.execute(text("SELECT version()")).scalar()
                current_db = connection.execute(text("SELECT current_database()")).scalar()
                current_user = connection.execute(text("SELECT current_user")).scalar()

                logger.info(f"Connected to PostgreSQL:\nVersion: {version}\nDatabase: {current_db}\nUser: {current_user}")
                
                # Try to list tables
                tables = connection.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                )).fetchall()
                logger.info("Tables in database:")
                for table in tables:
                    logger.info(f"- {table[0]}")
                    
                return True

        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    def get_db_url(self):
        """Get database URL for direct connection"""
        # If DATABASE_URL is set, use it directly
        if self.database_url:
            return self.database_url
            
        # Otherwise construct from components
        return (f"postgresql://{self.db_username}:{self.db_password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}")

    def connect(self):
        """Connect to database directly"""
        try:
            # Create new engine if needed
            if not self.engine:
                db_url = self.get_db_url()
                logger.info(f"Connecting to database via {db_url}")
                
                self.engine = create_engine(
                    db_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=60,  # Recycle connections every minute
                    pool_pre_ping=True,  # Test connections before using
                    connect_args={
                        "application_name": "website_monitor",
                        "keepalives": 1,
                        "keepalives_idle": 30,
                        "keepalives_interval": 10,
                        "keepalives_count": 5,
                        "connect_timeout": 10
                    }
                )
                self.Session = sessionmaker(bind=self.engine)

            # Test connection
            if self.Session:
                session = self.Session()
                with session.begin():
                    session.execute(text("SELECT 1"))
                return session
            else:
                logger.error("No Session available - engine initialization failed")
                raise Exception("Database engine initialization failed")

        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.close()  # Clean up on failure
            raise

    def close(self):
        """Clean up connections"""
        if self.engine:
            self.engine.dispose()
            self.engine = None

# Global database connection instance
db_connection = DatabaseConnection()

def get_db_session():
    """Get a database session"""
    try:
        return db_connection.connect()
    except Exception as e:
        logger.error(f"Failed to get database session: {str(e)}")
        raise

def test_database_connection():
    """Test database connection with detailed logging"""
    try:
        logger.info("========== DATABASE CONNECTION TEST ==========")
        success = db_connection.test_connection()
        if success:
            logger.info("Database connection test successful")
        else:
            logger.error("Database connection test failed")
        logger.info("============================================")
        return success
    except Exception as e:
        logger.error(f"Database connection test error: {str(e)}")
        return False

def init_database():
    """Initialize database connection"""
    try:
        logger.info("INITIALIZING DATABASE CONNECTION")
        logger.info("MODE: Direct PostgreSQL connection")
        
        # Test the connection
        if not test_database_connection():
            raise Exception("Database connection test failed")
        
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise Exception(f"Database initialization failed: {str(e)}")
        
def create_tables():
    """Create database tables"""
    try:
        # Import models here to avoid circular imports
        import models
        
        # Create tables
        logger.info("Creating database tables")
        
        # Create all tables defined in models module
        Base.metadata.create_all(db_connection.engine)
        
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        return False