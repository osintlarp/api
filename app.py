from flask import Flask, jsonify, request
import time
import threading
import os
from roblox import load_proxies, load_roblosec, get_user_info
app = Flask(__name__)

RATE_LIMIT_COUNT = 10
RATE_LIMIT_WINDOW_SECONDS = 30 * 60

_requests_store = {}
_store_lock = threading.Lock()

load_proxies()
load_roblosec()

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
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    with _store_lock:
        timestamps = _requests_store.get(client_ip, [])
        timestamps = [t for t in timestamps if t > window_start]
        if len(timestamps) >= RATE_LIMIT_COUNT:
            retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0])) if timestamps else RATE_LIMIT_WINDOW_SECONDS
            return True, retry_after
        timestamps.append(now)
        _requests_store[client_ip] = timestamps
        return False, 0

def parse_bool_param(name, default=True):
    val = request.args.get(name)
    if val is None:
        return default
    return val.lower() not in ("0", "false", "no")

@app.before_request
def before_request():
    if request.endpoint == "roblox_lookup":
        client_ip = get_client_ip()
        limited, retry_after = is_rate_limited(client_ip)
        if limited:
            return jsonify({"error": "rate_limited", "retry_after_seconds": retry_after}), 429

@app.route("/v1/osint/roblox", methods=["GET"])
def roblox_lookup():
    identifier = request.args.get("username") or request.args.get("id")
    if not identifier:
        return jsonify({"error": "Missing ?username= or ?id="}), 400
    options = {
        "groups": parse_bool_param("groups", True),
        "friends": parse_bool_param("friends", True),
        "followers": parse_bool_param("followers", True),
        "followings": parse_bool_param("followings", True),
        "friends_list": parse_bool_param("friends_list", True),
        "followers_list": parse_bool_param("followers_list", True),
        "following_list": parse_bool_param("following_list", True),
        "previous_usernames": parse_bool_param("previous_usernames", True),
        "about_me": parse_bool_param("about_me", True),
        "presence": parse_bool_param("presence", True)
    }
    data = get_user_info(identifier, options)
    if isinstance(data, dict) and data.get("error"):
        status = 429 if "Rate-Limited" in data.get("error") else 400
        return jsonify(data), status
    if data:
        return jsonify(data)
    return jsonify({"error": "User not found", "used_account_token": (os.path.exists("robloxsec.txt") and open("robloxsec.txt").read().strip() != "")}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
