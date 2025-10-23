from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from roblox import get_user_info

app = Flask(__name__)

RATE_LIMIT = 10
RATE_PERIOD = timedelta(minutes=30)
requests_tracker = {}

ALLOWED_ORIGINS = ["https://api.vaul3t.org"]  # anpassen

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
    return response

@app.route("/v1/osint/roblox")
def roblox_api():
    ip = request.remote_addr
    if not check_rate_limit(ip):
        return jsonify({"error":"Rate limit exceeded"}), 429

    username = request.args.get("username")
    if not username:
        return jsonify({"error":"username required"}), 400

    options = {
        "friends": request.args.get("friends","true").lower() == "true",
        "followers": request.args.get("followers","true").lower() == "true",
        "following": request.args.get("following","true").lower() == "true",
        "friends_list": request.args.get("friends_list","false").lower() == "true",
        "followers_list": request.args.get("followers_list","false").lower() == "true",
        "following_list": request.args.get("following_list","false").lower() == "true",
        "previous_usernames": request.args.get("previous_usernames","false").lower() == "true",
        "groups": request.args.get("groups","false").lower() == "true",
        "about_me": request.args.get("about_me","false").lower() == "true",
        "presence": request.args.get("presence","false").lower() == "true"
    }

    info = get_user_info(username, options)
    if not info:
        return jsonify({"error":"User not found"}), 404
    return jsonify(info)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
