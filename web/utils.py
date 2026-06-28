import os
import logging
from functools import wraps

import jwt
import mysql.connector
from flask import jsonify, request


# ==========================================================
# CONFIGURATION
# ==========================================================

SECRET_KEY = os.getenv("SECRET_KEY", "stayease_super_secret_key_2026")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "stayease")
}


# ==========================================================
# LOGGER SETUP
# ==========================================================

LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "audit.log"),
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s : %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_db_connection():
    """Returns a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        logger.error(f"Database Connection Error: {err}")
        raise


# ==========================================================
# AUDIT LOGGER — writes to both file and DB audit_logs table
# ==========================================================

def log_audit(member_id, role, action, entity_name="general", entity_id=None):
    logger.info(
        f"MemberID={member_id} | Role={role} | Action={action}"
    )
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (member_id, action, entity_name, entity_id, ip_address)
            VALUES (%s, %s, %s, %s, %s)
        """, (member_id, action, entity_name, entity_id, request.remote_addr))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass  # Never let audit failure break the main request


# ==========================================================
# JWT DECORATOR
# ==========================================================

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({
                "success": False,
                "message": "Authorization token missing."
            }), 401

        try:
            token = auth_header.split()[1]
        except IndexError:
            return jsonify({
                "success": False,
                "message": "Invalid Authorization header."
            }), 401

        try:
            current_user = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired."
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid token."
            }), 401

        return f(current_user, *args, **kwargs)

    return decorated
