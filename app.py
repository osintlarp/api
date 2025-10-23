from flask import Flask, request, jsonify
from datetime import timedelta
import time
from roblox import get_user_info

app = Flask(__name__)

RATE_LIMIT = 10
RATE_PERIOD = 30*60
requests_tracker = {}

ALLOWED_ORIGINS = ["https://api.vaul3t.org"] 

def get_client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    return request.remote_addr or "unknown"

def is_rate_limited(client_ip):
    now = time.time()
    window_start = now - RATE_PERIOD
    timestamps = requests_tracker.get(client_ip, [])
    timestamps = [t for t in timestamps if t > window_start]
    if len(timestamps) >= RATE_LIMIT:
        retry_after = int(RATE_PERIOD - (now - timestamps[0]))
        return True, retry_after
    timestamps.append(now)
    requests_tracker[client_ip] = timestamps
    return False, 0

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.before_request
def before_request():
    if request.endpoint == 'roblox_lookup':
        client_ip = get_client_ip()
        limited, retry_after = is_rate_limited(client_ip)
        if limited:
            return jsonify({'error': 'rate_limited', 'retry_after_seconds': retry_after}), 429

@app.route('/v1/osint/roblox', methods=['GET'])
def roblox_lookup():
    identifier = request.args.get('username') or request.args.get('id')
    if not identifier:
        return jsonify({'error': 'Missing ?username= or ?id='}), 400
    data = get_user_info(identifier)
    if isinstance(data, dict) and data.get('error'):
        if data.get('error') == "Rate-Limited by Roblox ? Proxies not responding":
            return jsonify({'error': data.get('error')}), 429
        return jsonify({'error': data.get('error')}), 400
    if data:
        return jsonify(data)
    return jsonify({'error': 'User not found'}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
