import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import paramiko
import socket
import time
from sshtunnel import SSHTunnelForwarder
import threading

# Force reload of environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self):
        self.tunnel = None
        self.engine = None
        self.Session = None
        self._lock = threading.Lock()

        # Database Configuration
        self.db_host = '127.0.0.1'
        self.db_port = 5432
        self.db_name = os.environ['DB_NAME'].strip()
        self.db_username = os.environ['DB_USERNAME'].strip()
        self.db_password = os.environ['DB_PASSWORD'].strip()

        logger.info(f"Database configuration: host={self.db_host}, port={self.db_port}, "
                   f"database={self.db_name}, username={self.db_username}")

    def test_connection(self):
        """Test database connection by executing a simple query"""
        try:
            # First ensure we have a connection
            if not self.engine:
                self.connect()

            # Test the connection with a query that shows database details
            with self.engine.connect() as connection:
                version = connection.execute(text("SELECT version()")).scalar()
                current_db = connection.execute(text("SELECT current_database()")).scalar()
                current_user = connection.execute(text("SELECT current_user")).scalar()

                logger.info(f"Connected to PostgreSQL:\nVersion: {version}\nDatabase: {current_db}\nUser: {current_user}")
                return True

        except Exception as e:
            logger.error(f"Database connection test failed: {str(e)}")
            return False

    def ensure_tunnel(self):
        """Ensure SSH tunnel is active and restart if needed"""
        with self._lock:
            if not self.tunnel or not self.tunnel.is_active:
                if self.tunnel:
                    try:
                        self.tunnel.close()
                    except:
                        pass
                    self.tunnel = None
                
                # Configure new tunnel with supported parameters only
                self.tunnel = SSHTunnelForwarder(
                    ssh_address_or_host=(os.environ['SSH_HOST'], 21098),
                    ssh_username=os.environ['SSH_USERNAME'],
                    ssh_password=os.environ['SSH_PASSWORD'],
                    remote_bind_address=('127.0.0.1', 5432),
                    local_bind_address=('127.0.0.1', 0),
                    set_keepalive=5.0,  # Aggressive keepalive
                    compression=True
                )
                
                logger.info("Starting SSH tunnel...")
                self.tunnel.start()
                
                # Wait for tunnel to become active
                for _ in range(10):
                    if self.tunnel.is_active:
                        logger.info(f"SSH tunnel established on port {self.tunnel.local_bind_port}")
                        return True
                    time.sleep(1)
                raise Exception("Tunnel failed to become active")
            return True

    def get_db_url(self):
        """Get current database URL with active tunnel port"""
        if not self.tunnel or not self.tunnel.is_active:
            raise Exception("No active tunnel")
        return (f"postgresql://{self.db_username}:{self.db_password}@"
                f"127.0.0.1:{self.tunnel.local_bind_port}/{self.db_name}")

    def connect(self):
        """Connect to database with automatic tunnel management"""
        try:
            # Ensure tunnel is active
            self.ensure_tunnel()
            
            # Create new engine if needed
            if not self.engine:
                db_url = (
                    f"postgresql://{self.db_username}:{self.db_password}@"
                    f"127.0.0.1:{self.tunnel.local_bind_port}/{self.db_name}"
                )
                
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
            session = self.Session()
            with session.begin():
                session.execute(text("SELECT 1"))
            return session

        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.close()  # Clean up on failure
            raise

    def close(self):
        """Clean up connections"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        if self.tunnel:
            try:
                self.tunnel.close()
            except:
                pass
            self.tunnel = None

# Global database connection instance
db_connection = DatabaseConnection()

def get_db_session():
    """Get a database session through SSH tunnel"""
    try:
        return db_connection.connect()
    except Exception as e:
        logger.error(f"Failed to get database session: {str(e)}")
        raise

def init_database():
    """Initialize database connection"""
    try:
        logger.info("Initializing database connection...")
        session = get_db_session()
        logger.info("Database initialized successfully")
        return session
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise