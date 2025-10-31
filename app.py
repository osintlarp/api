from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_cors import cross_origin
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from functools import wraps
from tiktok import get_tiktok_data
from instagram import fetch_instagram_data
import roblox
import github  
import utils
import hashlib

app = Flask(__name__)
BYPASS_TOKEN = "BOT-QWPPXCYNNMJUWGAG-X"

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

CORS(app, origins=["https://vaul3t.org", "https://api.vaul3t.org"])

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
@cross_origin(origins="https://vaul3t.org")
def osint_instagram():
    username = request.args.get("username")
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400
        
    data, status = fetch_instagram_data(username)
    return jsonify(data), status

if __name__ == '__main__':
    utils.load_proxies()
    app.run(debug=True, port=5000)

