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
RUNNERS_DIR = "/var/www/runners"
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

def start_runner_process(runner_id):
    try:
        subprocess.Popen(['python3', 'runner.py', runner_id])
        print(f"Started runner process: {runner_id}")
    except Exception as e:
        print(f"Error starting runner process: {e}")

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
        
        runner_id = generate_runner_id()
        runner_data = {
            'runnerName': generate_runner_name(),
            'runnerID': runner_id,
            'jobID': generate_job_id(),
            'userID': user_id,
            'serviceID': '',
            'running_since': '',
            'service': '',
            'usernameID': '',
            'creationDATE': datetime.now().isoformat(),
            'status': 'pending',
            'total_request': 0,
            'last_request': None
        }

        if 'runners' not in user_data:
            user_data['runners'] = []

        user_data['runners'].append(runner_data)

        if not save_user_data(user_id, user_data):
            return jsonify({
                'success': False,
                'message': 'Failed to save user data'
            }), 500
        
        runner_file_path = os.path.join('/var/www/runners', f"{runner_id}.json")
        os.makedirs('/var/www/runners', exist_ok=True)
        with open(runner_file_path, 'w') as f:
            json.dump(runner_data, f, indent=4)
        
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
                
                runner_data = runner.copy()
                runner_data['Changes'] = []
                runner_data['cache'] = {}
                runner_data['avatar_cache'] = {}
                
                os.makedirs(RUNNERS_DIR, exist_ok=True)
                runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
                with open(runner_file, 'w') as f:
                    json.dump(runner_data, f, indent=4)
                
                threading.Thread(target=start_runner_process, args=(runner_id,)).start()
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

@app.route('/v1/runner/delete_runner', methods=['DELETE'])
def delete_runner():
    try:
        user_id = request.args.get('userID')
        session_token = request.args.get('sessionToken')
        runner_id = request.args.get('runnerID')
        
        if not user_id or not session_token or not runner_id:
            return jsonify({
                'success': False,
                'message': 'Missing userID, sessionToken, or runnerID'
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
        initial_length = len(runners)
        user_data['runners'] = [runner for runner in runners if runner.get('runnerID') != runner_id]
        
        if len(user_data['runners']) == initial_length:
            return jsonify({
                'success': False,
                'message': 'Runner not found'
            }), 404
        
        runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
        if os.path.exists(runner_file):
            os.remove(runner_file)
        
        if not save_user_data(user_id, user_data):
            return jsonify({
                'success': False,
                'message': 'Failed to save user data'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Runner deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting runner: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@app.route('/runner_data/<runner_id>')
def get_runner_data(runner_id):
    try:
        runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
        if os.path.exists(runner_file):
            with open(runner_file, 'r') as f:
                return jsonify(json.load(f))
        else:
            return jsonify({'error': 'Runner not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import json
import time
import requests
import random
import os
import sys
from datetime import datetime
import threading
import schedule

RUNNERS_DIR = "/var/www/runners"
PROXIES_FILE = "proxies.txt"

class Runner:
    def __init__(self, runner_id):
        self.runner_id = runner_id
        self.runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
        self.load_runner_data()
        self.proxies = self.load_proxies()
        self.current_proxy = None
        self.running = True

    def load_runner_data(self):
        with open(self.runner_file, 'r') as f:
            self.runner_data = json.load(f)

    def save_runner_data(self):
        with open(self.runner_file, 'w') as f:
            json.dump(self.runner_data, f, indent=4)

        # Aktualisiere die User-JSON
        user_file = os.path.join("/var/www/users", f"{self.runner_data['userID']}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)

            # Finde den Runner in der User-JSON und aktualisiere ihn
            for runner in user_data.get('runners', []):
                if runner['runnerID'] == self.runner_id:
                    # Aktualisiere alle Felder, die sich geändert haben könnten
                    runner['status'] = self.runner_data['status']
                    runner['total_request'] = self.runner_data.get('total_request', 0)
                    runner['last_request'] = self.runner_data.get('last_request')
                    runner['running_since'] = self.runner_data.get('running_since')
                    break

            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=4)

    def load_proxies(self):
        if os.path.exists(PROXIES_FILE):
            with open(PROXIES_FILE, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def get_random_proxy(self):
        if self.proxies:
            return random.choice(self.proxies)
        return None

    def test_proxy(self, proxy):
        try:
            proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            response = requests.get('https://www.google.com', proxies=proxies, timeout=10)
            return response.status_code == 200
        except:
            return False

    def find_working_proxy(self):
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                return proxy
        return None

    def update_status(self, status):
        self.runner_data['status'] = status
        self.save_runner_data()

    def add_change(self, change):
        if 'Changes' not in self.runner_data:
            self.runner_data['Changes'] = []
        timestamp = datetime.now().isoformat()
        self.runner_data['Changes'].append(f"[{timestamp}] {change}")
        self.save_runner_data()

    def compare_responses(self, old_response, new_response):
        changes = []
        if old_response.get('display_name') != new_response.get('display_name'):
            changes.append(f"display_name changed to '{new_response.get('display_name')}' (was '{old_response.get('display_name')}')")
        if old_response.get('description') != new_response.get('description'):
            changes.append(f"description changed to '{new_response.get('description')}' (was '{old_response.get('description')}')")
        if old_response.get('following') != new_response.get('following'):
            changes.append(f"following changed to {new_response.get('following')} (was {old_response.get('following')})")
        if old_response.get('friends') != new_response.get('friends'):
            changes.append(f"friends changed to {new_response.get('friends')} (was {old_response.get('friends')})")
        old_groups = set([group['name'] for group in old_response.get('groups', [])])
        new_groups = set([group['name'] for group in new_response.get('groups', [])])
        if old_groups != new_groups:
            added = new_groups - old_groups
            removed = old_groups - new_groups
            if added:
                changes.append(f"groups added: {', '.join(added)}")
            if removed:
                changes.append(f"groups removed: {', '.join(removed)}")
        old_badges = set(old_response.get('roblox_badges', []))
        new_badges = set(new_response.get('roblox_badges', []))
        if old_badges != new_badges:
            added = new_badges - old_badges
            removed = old_badges - new_badges
            if added:
                changes.append(f"badges added: {', '.join(added)}")
            if removed:
                changes.append(f"badges removed: {', '.join(removed)}")
        return changes

    def make_request_with_proxy(self, url):
        response = None
        if self.current_proxy:
            proxies = {'http': f'http://{self.current_proxy}', 'https': f'http://{self.current_proxy}'}
            try:
                response = requests.get(url, proxies=proxies, timeout=30)
            except requests.exceptions.RequestException:
                self.current_proxy = self.find_working_proxy()
                if self.current_proxy:
                    return self.make_request_with_proxy(url)
                else:
                    response = requests.get(url, timeout=30)
        else:
            response = requests.get(url, timeout=30)
        if response is not None:
            self.runner_data['last_request'] = datetime.now().isoformat()
            self.runner_data['total_request'] = self.runner_data.get('total_request', 0) + 1
            self.save_runner_data()
        return response

    def roblox_monitoring_job(self):
        try:
            username = self.runner_data['usernameID']
            roblox_url = f"https://api.vaul3t.org/v1/osint/roblox?username={username}&cache=false"
            response = self.make_request_with_proxy(roblox_url)
            if response.status_code == 200:
                current_data = response.json()
                if 'cache' in self.runner_data:
                    changes = self.compare_responses(self.runner_data['cache'], current_data)
                    for change in changes:
                        self.add_change(change)
                self.runner_data['cache'] = current_data
                self.save_runner_data()
                if 'user_id' in current_data:
                    avatar_url = f"https://avatar.roblox.com/v1/users/{current_data['user_id']}/avatar"
                    avatar_response = self.make_request_with_proxy(avatar_url)
                    if avatar_response.status_code == 200:
                        avatar_data = avatar_response.json()
                        if 'avatar_cache' in self.runner_data:
                            avatar_changes = self.compare_responses(self.runner_data['avatar_cache'], avatar_data)
                            for change in avatar_changes:
                                self.add_change(f"Avatar: {change}")
                        self.runner_data['avatar_cache'] = avatar_data
                        self.save_runner_data()
            self.update_status('Active')
        except Exception as e:
            print(f"Error in Roblox monitoring: {e}")
            self.add_change(f"Error: {str(e)}")
            self.update_status('Error')

    def start_scheduler(self):
        interval = int(self.runner_data['request_every'])
        if self.runner_data['service'] == 'Roblox':
            schedule.every(interval).minutes.do(self.roblox_monitoring_job)
        self.current_proxy = self.find_working_proxy()
        self.update_status('Active')
        while self.running:
            schedule.run_pending()
            time.sleep(1)

def start_runner(runner_id):
    runner = Runner(runner_id)
    runner.start_scheduler()

def load_all_runners():
    if not os.path.exists(RUNNERS_DIR):
        os.makedirs(RUNNERS_DIR)
        return []
    runners = []
    for filename in os.listdir(RUNNERS_DIR):
        if filename.endswith('.json'):
            runner_id = filename[:-5]
            runners.append(runner_id)
    return runners

def main():
    if len(sys.argv) > 1:
        runner_id = sys.argv[1]
        start_runner(runner_id)
    else:
        runners = load_all_runners()
        threads = []
        for runner_id in runners:
            thread = threading.Thread(target=start_runner, args=(runner_id,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()

if __name__ == '__main__':
    utils.load_proxies()
    os.makedirs(USER_DIR, exist_ok=True)
    os.makedirs(RUNNERS_DIR, exist_ok=True)
    
    subprocess.Popen(['python3', 'runner.py'])
    
    app.run(debug=True, port=5000)
