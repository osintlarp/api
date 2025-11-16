from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_cors import cross_origin
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from functools import wraps
from tiktok import get_tiktok_data
from instagram import fetch_instagram_data
from reddit import fetch_reddit_user, report_reddit_user
from datetime import datetime
from filelock import FileLock
import json
import roblox
import github  
import utils
import hashlib
import os
import random
import requests
import string
import subprocess
import threading
from roblox import report_user

app = Flask(__name__)
BYPASS_TOKEN = "BOT-QWPPXCYNNMJUWGAG-X"
USER_DIR = "/var/www/users"
MAP_DIR = os.path.join(os.path.expanduser("~"), "map")
MAP_FILE = os.path.join(MAP_DIR, "user_map.json")
ROBLOSECURITY = ".ROBLOSECURITY=_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhACIhwKBGR1aWQSFDExNDEyNzEzMzM3MjY2OTQzOTExKAE.3evn987phyHfKAw38v6x42_qFlwBIRvnH7PhNRIJKPjkIvvRUe1i00ZygupYIgq1Wk89HNG4xjxUz1XQhumdNGYF8OjypxjHulo5S1RZLvgmJuy0awwk4JJ4tt9PDKsUbY1nwwThUUkDavnAmTti1z4iBxkaw-CsHqyVQ6BuRa7L2eP_cNtgELmY3N9avNYcug7jhO9tn14ZnW0RzZMb3naHE7dnNR68sygtjNLtLBEFr-jkK_Vs5Tc8aXlFq_c_-Fjok9be1wof5cxSOef4S7uNpsElc8HJPChle62nCEJffWbdx9KdYb1jREbUBxExmPIHHk5AOHzXmnyqlo7sinhyrSIbkrwsC58tffebYbgrlT-O0x0XfI_1d3ZSWlutsrNb303mcU6tU7cbRESYmTRyt-QIDNzypa5XUSOH3lAQy_J1OIqWGjZ5b2cfVF1xf1tEdKEXcWvWFadCzpwjIxk5vpEYsOBkL2PuRcb14upo1KjpJqDfPnIqoa1AM4au0DyF84_N8M-dRnAyV6UTrFIZNYWBk8lv7d9D2l1jWTh1x_UqUvmU5YdumOp22aLQeaB8fa7204ob05NjTsXqPkX9zVEeD75Fv8BnwJ1ua0QYN6u3PEjBD-gqTfVXLF3v2g95A_CklChP46XRPKvYGywoAm8dOUBaq8XcKfelhZ-K3GfesQhrK9-wFGI67-qebZ4PIPqt0J4fMAy883oiz8XFLNgEicSYlkOpt5UZVRFptG0cqsfF683-I6NXVA1PGsWsDQ"
CSFR = "tXNcRQFHmFiP"

API_LIMIT_ACCOUNT_FREE = 200
API_LIMIT_ACCOUNT_VIP = 800
API_LIMIT_ACCOUNT_LARP = 1500
API_LIMIT_ACCOUNT_MOD = 2000
API_LIMIT_ACCOUNT_ADMIN = 3000

CORS(app)

def get_csrf_token():
    url = "https://apis.roblox.com/abuse-reporting/v2/abuse-report"
    headers = {
        "content-type": "application/json;charset=utf-8",
        "accept": "application/json, text/plain, */*",
        "sec-fetch-site": "same-site",
        "priority": "u=3, i",
        "accept-language": "en-US,en;q=0.9",
        "sec-fetch-mode": "cors",
        "origin": "https://www.roblox.com",
        "user-agent": "Mozilla/5.0 (iPhone; iPhone17,5; CPU iPhone OS 26.1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Mobile/9B176 ROBLOX iOS App 2.698.937 Hybrid RobloxApp/2.698.937 (GlobalDist; AppleAppStore)",
        "referer": "https://www.roblox.com/"
    }
    cookies = {".ROBLOSECURITY": ROBLOSECURITY}
    r = requests.post(url, headers=headers, cookies=cookies)
    return r.headers.get("x-csrf-token")


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
    default_limits=["150 per 10 minutes"]
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

def api_usage_decorator(optional=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization")

            if optional and not token:
                return limiter.shared_limit("5 per 1 hour", scope=get_remote_address())(f)(*args, **kwargs)
            
            if not token:
                return jsonify({"error": "API key required"}), 403

            user_id, filename, user_file = find_user_by_api_key(token)
            if not user_id:
                return jsonify({"error": "Invalid API key"}), 403

            lock = FileLock(f"{user_file}.lock")
            with lock:
                try:
                    with open(user_file, "r") as fdata:
                        user_data = json.load(fdata)
                except Exception:
                    return jsonify({"error": "Failed to read user data"}), 500

                if user_data.get("isBanned", False):
                    return jsonify({"error": "User is banned"}), 403

                account_type = user_data.get("account_type", "Free").capitalize()
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

                temp_file = user_file + ".tmp"
                with open(temp_file, "w") as fdata:
                    json.dump(user_data, fdata, indent=4)
                os.replace(temp_file, user_file)

            return f(*args, **kwargs)

        return wrapper
    return decorator

@app.route('/v1/osint/roblox')
@bypass_token
@api_usage_decorator(optional=True)
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

@app.route('/v1/osint/roblox/report_user', methods=['GET'])
def report_roblox_user_direct():
    user_id = request.args.get("userID")
    if not user_id:
        return jsonify({"error": "Missing userID"}), 400

    ROBLOSECURITY = ".ROBLOSECURITY=_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhACIhwKBGR1aWQSFDExNDEyNzEzMzM3MjY2OTQzOTExKAE.3evn987phyHfKAw38v6x42_qFlwBIRvnH7PhNRIJKPjkIvvRUe1i00ZygupYIgq1Wk89HNG4xjxUz1XQhumdNGYF8OjypxjHulo5S1RZLvgmJuy0awwk4JJ4tt9PDKsUbY1nwwThUUkDavnAmTti1z4iBxkaw-CsHqyVQ6BuRa7L2eP_cNtgELmY3N9avNYcug7jhO9tn14ZnW0RzZMb3naHE7dnNR68sygtjNLtLBEFr-jkK_Vs5Tc8aXlFq_c_-Fjok9be1wof5cxSOef4S7uNpsElc8HJPChle62nCEJffWbdx9KdYb1jREbUBxExmPIHHk5AOHzXmnyqlo7sinhyrSIbkrwsC58tffebYbgrlT-O0x0XfI_1d3ZSWlutsrNb303mcU6tU7cbRESYmTRyt-QIDNzypa5XUSOH3lAQy_J1OIqWGjZ5b2cfVF1xf1tEdKEXcWvWFadCzpwjIxk5vpEYsOBkL2PuRcb14upo1KjpJqDfPnIqoa1AM4au0DyF84_N8M-dRnAyV6UTrFIZNYWBk8lv7d9D2l1jWTh1x_UqUvmU5YdumOp22aLQeaB8fa7204ob05NjTsXqPkX9zVEeD75Fv8BnwJ1ua0QYN6u3PEjBD-gqTfVXLF3v2g95A_CklChP46XRPKvYGywoAm8dOUBaq8XcKfelhZ-K3GfesQhrK9-wFGI67-qebZ4PIPqt0J4fMAy883oiz8XFLNgEicSYlkOpt5UZVRFptG0cqsfF683-I6NXVA1PGsWsDQ"

    url = "https://apis.roblox.com/abuse-reporting/v2/abuse-report"

    headers = {
        "content-type": "application/json;charset=utf-8",
        "accept": "application/json, text/plain, */*",
        "sec-fetch-site": "same-site",
        "priority": "u=3, i",
        "accept-language": "en-US,en;q=0.9",
        "sec-fetch-mode": "cors",
        "origin": "https://www.roblox.com",
        "user-agent": "Mozilla/5.0 (iPhone; iPhone17,5; CPU iPhone OS 26.1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Mobile/9B176 ROBLOX iOS App 2.698.937 Hybrid RobloxApp/2.698.937 (GlobalDist; AppleAppStore)",
        "referer": "https://www.roblox.com/",
        "x-csrf-token": "qKw8agYjPjhz",
        "sec-fetch-dest": "empty"
    }

    cookies = {
        "RBXSessionTracker": "sessionid=d5eb8db7-388e-40c9-b7df-777bed263379",
        "RBXPaymentsFlowContext": "d9cee2b1-75c3-4e2e-b697-f489120252d0",
        "_rbldh": "10748321733087359080",
        ".ROBLOSECURITY": ROBLOSECURITY,
        "GuestData": "UserID=-1342368321",
        "RBXEventTrackerV2": "CreateDate=11/11/2025 05:33:05&rbxid=9923047635&browserid=1758052144156004",
        "RBXThemeOverride": "dark",
        "__stripe_mid": "3291ce72-7dfa-4909-b618-aa5e3779da3690c2c5",
        "__stripe_sid": "e652d456-7c8d-4322-abfc-3f4d2855e82a03c175",
        "rbx-ip2": "1",
        "rbxas": "78327c2bf7908856ffe243c7589cf65d85d2dab3cacf0305d1f466363e38c7d9"
    }

    payload = {
        "tags": {
            "ENTRY_POINT": {"valueList": [{"data": "website"}]},
            "REPORTED_ABUSE_CATEGORY": {"valueList": [{"data": "dating"}]},
            "REPORTED_ABUSE_VECTOR": {"valueList": [{"data": "user_profile"}]},
            "REPORTER_COMMENT": {"valueList": [{"data": ""}]},
            "SUBMITTER_USER_ID": {"valueList": [{"data": "9926480500"}]},
            "REPORT_TARGET_USER_ID": {"valueList": [{"data": str(user_id)}]}
        }
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=json.dumps(payload))

    try:
        return jsonify({
            "status": response.status_code,
            "response": response.json()
        })
    except:
        return jsonify({
            "status": response.status_code,
            "response": response.text
        })

@app.route('/v1/osint/github')
@api_usage_decorator(optional=True)
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
@bypass_token
@api_usage_decorator(optional=True)
def osint_tiktok():
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "error": "Missing 'username' parameter"}), 400

    force_proxy = request.args.get("force_proxy", "false").lower() == "true"

    data, status = get_tiktok_data(username, ForceProxy=force_proxy)
    return jsonify(data), status

@app.route("/v1/osint/instagram", methods=["GET", "OPTIONS"])
@bypass_token
@api_usage_decorator(optional=True)
def osint_instagram():
    username = request.args.get("username")
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400
        
    data, status = fetch_instagram_data(username)
    return jsonify(data), status

@app.route("/v1/osint/reddit", methods=["GET"])
@bypass_token
@api_usage_decorator(optional=True)
def reddit_user():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter is required"}), 400

    try:
        data = fetch_reddit_user(username)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/v1/osint/reddit/report_user", methods=["GET"])
@bypass_token
@api_usage_decorator(optional=False)
def reddit_report():
    redditor_id = request.args.get("userID")
    if not redditor_id:
        return jsonify({"error": "Missing 'userID' query parameter"}), 400

    site_rule = request.args.get("site_rule", "SPAM_OTHER")
    reason_type = request.args.get("reason_type", "USERNAME")
    use_proxies = request.args.get("use_proxies", "false").lower() == "true"
    force_proxy = request.args.get("force_proxy", "false").lower() == "true"

    report_result = report_reddit_user(
        redditor_id=redditor_id,
        site_rule=site_rule,
        reason_type=reason_type,
        use_proxies=use_proxies,
        ForceProxy=force_proxy
    )

    if report_result is None:
        return jsonify({"error": "Failed to report user"}), 500

    return jsonify(report_result)

@app.route('/v1/api_endpoints', methods=['GET'])
def api_endpoints():
    endpoints = load_endpoints()
    return jsonify(endpoints)

@app.route('/v1/announcements', methods=['GET'])
def announcements():
    data = load_announcements()
    return jsonify(data)


if __name__ == '__main__':
    utils.load_proxies()
    os.makedirs(USER_DIR, exist_ok=True)
    app.run(debug=True, port=5000)
