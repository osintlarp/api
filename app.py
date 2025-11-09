from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_cors import cross_origin
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from functools import wraps
from tiktok import get_tiktok_data
from instagram import fetch_instagram_data
from datetime import datetime
import json
import roblox
import github  
import utils
import hashlib
import os
import random
import string
import subprocess
import threading

app = Flask(__name__)
BYPASS_TOKEN = "BOT-QWPPXCYNNMJUWGAG-X"
USER_DIR = "/var/www/users"
MAP_DIR = os.path.join(os.path.expanduser("~"), "map")
MAP_FILE = os.path.join(MAP_DIR, "user_map.json")

API_LIMIT_ACCOUNT_FREE = 200
API_LIMIT_ACCOUNT_VIP = 800
API_LIMIT_ACCOUNT_LARP = 1500
API_LIMIT_ACCOUNT_MOD = 2000
API_LIMIT_ACCOUNT_ADMIN = 3000

CORS(app)

def dynamic_key_func():
    if getattr(request, "_bypass_limiter", False):
        return None
    ip = get_remote_address()
    import hashlib
    return hashlib.sha256(ip.encode()).hexdigest()

def load_user_map():
    try:
        if os.path.exists(MAP_FILE):
            with open(MAP_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def bypass_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization") or request.headers.get("X-Api-Token")
        if token == BYPASS_TOKEN:
            request._bypass_limiter = True
        return f(*args, **kwargs)
    return decorated

limiter = Limiter(
    key_func=dynamic_key_func,
    default_limits=["300 per hour"]
)
limiter.init_app(app)

def load_endpoints():
    with open('endpoints.json', 'r') as f:
        return json.load(f)

def load_announcements():
    with open('announcements.json', 'r') as f:
        return json.load(f)

def validate_session(user_id, session_token):
    try:
        user_file = os.path.join(USER_DIR, f"{user_id}.json")
        if not os.path.exists(user_file):
            return False
        
        with open(user_file, 'r') as f:
            user_data = json.load(f)
        
        return user_data.get('session_token') == session_token
    except Exception as e:
        print(f"Error validating session: {e}")
        return False

def load_user_data(user_id):
    try:
        user_file = os.path.join(USER_DIR, f"{user_id}.json")
        if not os.path.exists(user_file):
            return None
        
        with open(user_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading user data: {e}")
        return None

def save_user_data(user_id, user_data):
    try:
        user_file = os.path.join(USER_DIR, f"{user_id}.json")
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving user data: {e}")
        return False

def find_user_by_api_key(api_key):
    if not api_key:
        return (None, None, None)
    try:
        user_map = load_user_map()
        for _, entry in user_map.items():
            if isinstance(entry, dict) and entry.get('api_key') == api_key:
                filename = entry.get('filename')
                user_id = entry.get('userID') or entry.get('username')
                full_path = os.path.join(USER_DIR, filename)
                return (user_id, filename, full_path)
    except:
        pass
    try:
        for fname in os.listdir(USER_DIR):
            if fname.endswith('.json'):
                full_path = os.path.join(USER_DIR, fname)
                with open(full_path, 'r') as f:
                    data = json.load(f)
                if data.get('api_key') == api_key:
                    return (data.get('userID'), fname, full_path)
    except:
        pass
    return (None, None, None)

def requireAPI(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Missing Authorization header"}), 401

        if not os.path.exists(MAP_FILE):
            return jsonify({"error": "User map not found"}), 500

        with open(MAP_FILE, "r") as map_file:
            try:
                user_map = json.load(map_file)
            except Exception:
                return jsonify({"error": "Failed to read user map"}), 500

        matched_user = None
        for user_entry in user_map.values():
            if user_entry.get("api_key") == token:
                matched_user = user_entry
                break

        if not matched_user:
            return jsonify({"error": "Invalid API key"}), 403

        filename = matched_user.get("filename")
        if not filename:
            return jsonify({"error": "User file not defined"}), 500

        user_file = os.path.join(USER_DIR, filename)
        if not os.path.exists(user_file):
            return jsonify({"error": "User file not found"}), 404

        with open(user_file, "r") as userfile:
            try:
                user_data = json.load(userfile)
            except Exception:
                return jsonify({"error": "Failed to read user data"}), 500

        if user_data.get("isBanned", False):
            return jsonify({"error": "User is banned"}), 403

        account_type = user_data.get("account_type", "Free").upper()
        usage = user_data.get("TokenUsage", 0)

        limit = {
            "Free": API_LIMIT_ACCOUNT_FREE,
            "VIP": API_LIMIT_ACCOUNT_VIP,
            "LARP": API_LIMIT_ACCOUNT_LARP,
            "Moderator": API_LIMIT_ACCOUNT_MOD,
            "Admin": API_LIMIT_ACCOUNT_ADMIN
        }.get(account_type, API_LIMIT_ACCOUNT_FREE)

        if usage >= limit:
            return jsonify({"error": "API limit reached"}), 429

        user_data["TokenUsage"] = usage + 1
        with open(user_file, "w") as userfile:
            json.dump(user_data, userfile, indent=4)

        return f(*args, **kwargs)
    return wrapper

@app.route('/v1/osint/roblox')
@limiter.limit("300/hour")
@bypass_token
@requireAPI
def get_roblox_osint():
    identifier = request.args.get('id') or request.args.get('username')
    if not identifier:
        return jsonify({'error': 'Missing "id" or "username" query parameter'}), 400
        
    use_cache = request.args.get('cache', 'true').lower() != 'false'
    
    options = {key: request.args.get(key, 'true').lower() != 'false' for key in roblox.ALL_OPTION_KEYS}

    try:
        user_info = roblox.get_user_info(identifier, use_cache=use_cache, **options)
        if not user_info:
            return jsonify({'error': 'User not found'}), 404
        if user_info.get('error'):
            if 'User not found' in user_info.get('error'):
                return jsonify(user_info), 404
            return jsonify(user_info), 500
            
        return jsonify(user_info)
    except Exception as e:
        print(f"Error in roblox endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@app.route('/v1/osint/github')
@limiter.limit("300/hour")
@requireAPI
def get_github_osint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400

    use_cache = request.args.get('cache', 'true').lower() != 'false'
    options = {key: request.args.get(key, 'true').lower() != 'false' for key in github.ALL_OPTION_KEYS}

    try:
        github_data = github.get_github_info(username, use_cache=use_cache, **options)
        
        if github_data.get('error'):
            error_msg = github_data.get('error', '').lower()
            if 'not found' in error_msg:
                return jsonify(github_data), 404
            if 'rate_limited' in error_msg:
                return jsonify({'error': 'rate_limited'}), 429
            return jsonify(github_data), 500
            
        return jsonify(github_data)
        
    except Exception as e:
        print(f"Error in github endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@app.route("/v1/osint/tiktok", methods=["GET"])
@limiter.limit("300/hour")
@bypass_token
@requireAPI
def osint_tiktok():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "error": "Missing 'username' parameter"}), 400

    force_proxy = request.args.get("force_proxy", "false").lower() == "true"

    data, status = get_tiktok_data(username, ForceProxy=force_proxy)
    return jsonify(data), status

@app.route("/v1/osint/instagram", methods=["GET", "OPTIONS"])
@limiter.limit("300/hour")
@requireAPI
def osint_instagram():
    username = request.args.get("username")
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400
        
    data, status = fetch_instagram_data(username)
    return jsonify(data), status

@app.route('/v1/api_endpoints', methods=['GET'])
def api_endpoints():
    endpoints = load_endpoints()
    return jsonify(endpoints)

@app.route('/v1/announcements', methods=['GET'])
def announcements():
    data = load_announcements()
    return jsonify(data)

@app.route('/v1/users', methods=['GET'])
@limiter.limit("300/hour")
def get_user_data():
    session_token = request.args.get('sessionToken')
    if not session_token:
        return jsonify({'error': 'Missing sessionToken parameter'}), 400

    try:
        user_files = [f for f in os.listdir(USER_DIR) if f.endswith('.json')]
        user_data = None

        for user_file in user_files:
            file_path = os.path.join(USER_DIR, user_file)
            with open(file_path, 'r') as f:
                current_user_data = json.load(f)
                if current_user_data.get('session_token') == session_token:
                    user_data = current_user_data
                    break

        if not user_data:
            return jsonify({'error': 'Invalid session token'}), 401

        response_data = {
            'userID': user_data.get('userID'),
            'username': user_data.get('username'),
            'api_key': user_data.get('api_key'),
            'tokenUsage': user_data.get('TokenUsage'),
            'accountType': user_data.get('account_type')
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"Error in user data endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500


if __name__ == '__main__':
    utils.load_proxies()
    os.makedirs(USER_DIR, exist_ok=True)
    app.run(debug=True, port=5000)
