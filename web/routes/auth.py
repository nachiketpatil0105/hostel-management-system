from flask import Blueprint, request, jsonify
import jwt
import datetime
from werkzeug.security import check_password_hash
from web.utils import get_db_connection, SECRET_KEY, log_audit

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('user') or not data.get('password'):
        return jsonify({"error": "Missing parameters"}), 401

    username = data.get('user')
    password_attempt = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT uc.password_hash, m.member_id, r.role_name
        FROM user_credentials uc
        JOIN members m ON uc.member_id = m.member_id
        JOIN roles r ON m.role_id = r.role_id
        WHERE uc.username = %s
    """
    cursor.execute(query, (username,))
    user_record = cursor.fetchone()

    if user_record and check_password_hash(user_record['password_hash'].strip(), password_attempt):

        # Update last_login timestamp
        cursor.execute(
            "UPDATE user_credentials SET last_login = NOW() WHERE member_id = %s",
            (user_record['member_id'],)
        )
        conn.commit()
        cursor.close()
        conn.close()

        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        token_payload = {
            'username': username,
            'member_id': user_record['member_id'],
            'role': user_record['role_name'],
            'exp': expiration_time
        }
        token = jwt.encode(token_payload, SECRET_KEY, algorithm='HS256')

        log_audit(user_record['member_id'], user_record['role_name'], "User logged in successfully")
        return jsonify({
            "message": "Login successful",
            "session_token": token
        }), 200

    cursor.close()
    conn.close()

    log_audit(None, "Unknown", "Failed login attempt")
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route('/isAuth', methods=['GET'])
def is_auth():
    token = None

    if 'Authorization' in request.headers:
        token = request.headers['Authorization'].split(" ")[1]
    elif request.is_json and 'session_token' in request.get_json():
        token = request.get_json()['session_token']

    if not token:
        return jsonify({"error": "No session found"}), 401

    try:
        decoded_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        expiry_datetime = datetime.datetime.utcfromtimestamp(decoded_data['exp'])
        return jsonify({
            "message": "User is authenticated",
            "username": decoded_data['username'],
            "role": decoded_data['role'],
            "expiry": expiry_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Session expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid session token"}), 401
