import logging
import time
import os
from database import DatabaseConnection
import socket
from dotenv import load_dotenv
import dns.resolver

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_connectivity():
    """Test basic network connectivity to SSH host"""
    host = os.environ['SSH_HOST']
    port = int(os.environ.get('SSH_PORT', 22))

    # First try DNS resolution with multiple record types
    try:
        logger.info(f"Testing DNS resolution for {host}...")

        # Try A record
        try:
            answers = dns.resolver.resolve(host, 'A')
            for rdata in answers:
                logger.info(f"A record found: {rdata}")
            ip_address = str(answers[0])
        except dns.resolver.NoAnswer:
            logger.warning(f"No A records found for {host}")
            try:
                # Try CNAME record as fallback
                answers = dns.resolver.resolve(host, 'CNAME')
                for rdata in answers:
                    logger.info(f"CNAME record found: {rdata}")
                # Resolve the CNAME target
                cname_target = str(answers[0].target)
                ip_answers = dns.resolver.resolve(cname_target, 'A')
                ip_address = str(ip_answers[0])
            except dns.resolver.NoAnswer:
                logger.error(f"No CNAME records found for {host}")
                return False

        logger.info(f"Successfully resolved {host} to {ip_address}")
    except Exception as e:
        logger.error(f"DNS resolution failed for {host}: {str(e)}")
        return False

    # Test TCP connection
    try:
        logger.info(f"Testing TCP connection to {host}:{port}...")
        sock = socket.create_connection((host, port), timeout=10)
        sock.close()
        logger.info(f"Successfully connected to {host}:{port}")
        return True
    except Exception as e:
        logger.error(f"TCP connection failed: {str(e)}")
        return False

def test_connection(max_retries=3, retry_delay=5):
    """Test SSH tunnel and database connection"""
    # First test basic connectivity
    if not test_basic_connectivity():
        logger.error("Basic connectivity test failed")
        return False

    db = DatabaseConnection()
    for attempt in range(max_retries):
        try:
            logger.info(f"Database connection attempt {attempt + 1}/{max_retries}")

            # Test SSH tunnel first
            if db.test_connection():
                logger.info("Successfully connected to database through SSH tunnel")
                return True

            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
        finally:
            db.close()

    return False

if __name__ == "__main__":
    if not test_connection():
        logger.error("All connection attempts failed")
        exit(1)