from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from roblox import get_user_info

app = Flask(__name__)

RATE_LIMIT = 10
RATE_PERIOD = timedelta(minutes=30)
requests_tracker = {}

ALLOWED_ORIGINS = ["https://api.vaul3t.org"] 

def check_rate_limit(ip):
    now = datetime.now()
    tracker = requests_tracker.get(ip, [])
    tracker = [t for t in tracker if now - t < RATE_PERIOD]
    if len(tracker) >= RATE_LIMIT:
        return False
    tracker.append(now)
    requests_tracker[ip] = tracker
    return True

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/v1/osint/roblox', methods=['GET', 'OPTIONS'])
def roblox_lookup():
    if request.method == 'OPTIONS':
        return apply_cors(jsonify(success=True)), 200
        
    identifier = request.args.get('username') or request.args.get('id')
    if not identifier:
        return jsonify({'error': 'Missing ?username= or ?id='}), 400
    
    data = get_user_info(identifier)
    
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'User not found or failed to fetch data'}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
