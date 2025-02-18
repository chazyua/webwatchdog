import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import paramiko
import socket
import time
from sshtunnel import SSHTunnelForwarder

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

        # Clean up and validate database configuration
        self.db_host = '127.0.0.1'  # Local address for SSH tunnel
        self.db_port = 5432  # PostgreSQL default port
        self.db_name = os.environ['DB_NAME'].strip()
        self.db_username = os.environ['DB_USERNAME'].strip()
        self.db_password = os.environ['DB_PASSWORD'].strip()

        logger.info(f"Database configuration: host={self.db_host}, port={self.db_port}, database={self.db_name}, username={self.db_username}")

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

    def start_tunnel(self, max_retries=3, retry_delay=5):
        """Start SSH tunnel to the remote database"""
        if not all([os.environ.get(key) for key in ['SSH_HOST', 'SSH_USERNAME', 'SSH_PASSWORD']]):
            logger.info("No SSH configuration found, skipping tunnel creation")
            return True

        for attempt in range(max_retries):
            try:
                logger.info(f"Starting SSH tunnel (attempt {attempt + 1}/{max_retries})...")

                # Namecheap specific SSH port
                ssh_port = 21098

                # Test SSH connectivity first
                try:
                    logger.info(f"Testing TCP connection to {os.environ['SSH_HOST']}:{ssh_port}...")
                    sock = socket.create_connection((os.environ['SSH_HOST'], ssh_port), timeout=10)
                    sock.close()
                    logger.info(f"Successfully connected to {os.environ['SSH_HOST']}:{ssh_port}")
                except Exception as e:
                    logger.error(f"Failed to connect to SSH host: {str(e)}")
                    raise

                # Configure SSH tunnel with minimal required settings
                self.tunnel = SSHTunnelForwarder(
                    ssh_address_or_host=(os.environ['SSH_HOST'], ssh_port),
                    ssh_username=os.environ['SSH_USERNAME'],
                    ssh_password=os.environ['SSH_PASSWORD'],
                    remote_bind_address=('127.0.0.1', 5432),  # PostgreSQL default port
                    local_bind_address=('127.0.0.1', 0),  # Let system assign local port
                    set_keepalive=10.0
                )

                logger.info("Starting tunnel...")
                self.tunnel.start()

                if not self.tunnel.is_active:
                    raise Exception("Tunnel did not become active")

                logger.info(f"SSH tunnel established on local port {self.tunnel.local_bind_port}")
                return True

            except Exception as e:
                logger.error(f"Failed to establish SSH tunnel: {str(e)}")
                if self.tunnel:
                    try:
                        self.tunnel.close()
                    except:
                        pass
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logger.error("Max retries reached for SSH tunnel")
                    raise

    def connect(self):
        """Connect to the database through SSH tunnel"""
        try:
            # Establish SSH tunnel
            if not self.start_tunnel():
                raise Exception("Failed to establish SSH tunnel")

            # Use local tunnel port for database connection
            if self.tunnel and self.tunnel.is_active:
                logger.info(f"Using tunneled connection on port {self.tunnel.local_bind_port}")
                db_url = (
                    f"postgresql://{self.db_username}:{self.db_password}@"
                    f"127.0.0.1:{self.tunnel.local_bind_port}/{self.db_name}"
                )
            else:
                raise Exception("No active tunnel for database connection")

            # Create database engine with optimized settings
            self.engine = create_engine(
                db_url,
                echo=True,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={
                    "application_name": "website_monitor",
                    "client_encoding": "utf8",
                    "connect_timeout": 10,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5
                }
            )

            # Create session factory
            self.Session = sessionmaker(bind=self.engine)

            # Test connection
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                logger.info("Database connection test successful")

            return self.Session()

        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            if self.engine:
                self.engine.dispose()
            raise

    def close(self):
        """Close the database connection and SSH tunnel"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
        if self.tunnel and self.tunnel.is_active:
            self.tunnel.close()
            logger.info("SSH tunnel closed")

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