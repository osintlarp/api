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

app = Flask(__name__)
BYPASS_TOKEN = "BOT-QWPPXCYNNMJUWGAG-X"
USER_DIR = "/var/www/users"
RUNNER_LIMIT = 1


CORS(app)

def dynamic_key_func():
    if getattr(request, "_bypass_limiter", False):
        return None
    ip = get_remote_address()
    import hashlib
    return hashlib.sha256(ip.encode()).hexdigest()

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

def generate_runner_name():
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(8))

def generate_runner_id():
    return ''.join(random.choice(string.digits) for i in range(30))

def generate_job_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(24))

@app.route('/v1/osint/roblox')
@limiter.limit("300/hour")
@bypass_token
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
def osint_tiktok():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "error": "Missing 'username' parameter"}), 400

    force_proxy = request.args.get("force_proxy", "false").lower() == "true"

    data, status = get_tiktok_data(username, ForceProxy=force_proxy)
    return jsonify(data), status

@app.route("/v1/osint/instagram", methods=["GET", "OPTIONS"])
@limiter.limit("300/hour")
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

@app.route('/v1/runner/create_runner', methods=['GET'])
def create_runner():
    try:
        user_id = request.args.get('userID')
        session_token = request.args.get('sessionToken')
        
        if not user_id or not session_token:
            return jsonify({
                'success': False,
                'message': 'Missing userID or sessionToken'
            }), 400
        
        if not validate_session(user_id, session_token):
            return jsonify({
                'success': False,
                'message': 'Invalid session token'
            }), 401
        
        user_data = load_user_data(user_id)
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        runners = user_data.get('runners', [])
        if len(runners) >= RUNNER_LIMIT:
            return jsonify({
                'success': False,
                'message': f'Runner limit reached. Maximum {RUNNER_LIMIT} runner(s) allowed.'
            }), 400
        
        runner_data = {
            'runnerName': generate_runner_name(),
            'runnerID': generate_runner_id(),
            'jobID': generate_job_id(),
            'userID': user_id,
            'serviceID': '',
            'running_since': '',
            'service': '',
            'usernameID': '',
            'creationDATE': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        if 'runners' not in user_data:
            user_data['runners'] = []
        
        user_data['runners'].append(runner_data)
        
        if not save_user_data(user_id, user_data):
            return jsonify({
                'success': False,
                'message': 'Failed to save user data'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Runner created successfully',
            'runner': runner_data
        })
        
    except Exception as e:
        print(f"Error creating runner: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@app.route('/v1/runner/activate_runner', methods=['POST'])
def activate_runner():
    try:
        user_id = request.args.get('userID')
        session_token = request.args.get('sessionToken')
        runner_id = request.args.get('runnerID')
        service = request.args.get('service')
        username = request.args.get('Username')
        request_every = request.args.get('RequestEvery')
        
        if not user_id or not session_token or not runner_id or not service or not username or not request_every:
            return jsonify({
                'success': False,
                'message': 'Missing required parameters'
            }), 400
        
        if not validate_session(user_id, session_token):
            return jsonify({
                'success': False,
                'message': 'Invalid session token'
            }), 401
        
        user_data = load_user_data(user_id)
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        runners = user_data.get('runners', [])
        runner_found = False
        
        for runner in runners:
            if runner.get('runnerID') == runner_id:
                runner['service'] = service
                runner['usernameID'] = username
                runner['request_every'] = request_every
                runner['running_since'] = datetime.now().isoformat()
                runner['status'] = 'Starting'
                runner_found = True
                break
        
        if not runner_found:
            return jsonify({
                'success': False,
                'message': 'Runner not found'
            }), 404
        
        if not save_user_data(user_id, user_data):
            return jsonify({
                'success': False,
                'message': 'Failed to save user data'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Runner activated successfully'
        })
        
    except Exception as e:
        print(f"Error activating runner: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@app.route('/v1/runner/request_runner', methods=['GET'])
def request_runner():
    try:
        user_id = request.args.get('userID')
        session_token = request.args.get('sessionToken')
        
        if not user_id or not session_token:
            return jsonify({
                'success': False,
                'message': 'Missing userID or sessionToken'
            }), 400
        
        if not validate_session(user_id, session_token):
            return jsonify({
                'success': False,
                'message': 'Invalid session token'
            }), 401
        
        user_data = load_user_data(user_id)
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        runners = user_data.get('runners', [])
        
        return jsonify({
            'success': True,
            'runners': runners
        })
        
    except Exception as e:
        print(f"Error requesting runners: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


if __name__ == '__main__':
    utils.load_proxies()
    app.run(debug=True, port=5000)

