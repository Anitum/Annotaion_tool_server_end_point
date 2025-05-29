import os
import logging
import secrets

# Paths and S3 Configuration
BASE_PATH = "/home/ubuntu/runs/detect/predict5"  # Change this to your predict folder
S3_BUCKET = "a2bvideos"
S3_PREFIX = "annotation/"
UPLOAD_TIMES = ["10:00", "12:00", "13:00", "17:00", "20:00"]  # Default upload times

# API Authentication
API_KEYS = {
    "server1": "sk_live_abc123def456ghi789jkl012mno345pqr678",
    "server2": "sk_live_xyz789uvw456rst123abc456def789ghi012",
    "admin": "sk_live_admin_super_secure_key_123456789"
}

# Flask Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def generate_api_key():
    """Generate a secure API key"""
    return f"sk_live_{secrets.token_urlsafe(32)}"

def get_logger(name):
    """Get a configured logger"""
    return logging.getLogger(name)

# Environment-based overrides
if os.getenv('FLASK_ENV') == 'development':
    FLASK_DEBUG = True
    logging.getLogger().setLevel(logging.DEBUG)
