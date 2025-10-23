from flask import Flask, request, jsonify, make_response
from functools import wraps
import time
from collections import defaultdict
import roblox
import os

app = Flask(__name__)

roblox.load_roblosec()
roblox.load_proxies()

RATE_LIMIT = 10
RATE_PERIOD = 30 * 60
requests_log = defaultdict(list)

ALLOWED_ORIGINS = {
    "https://vaul3t.org",
    "https://api.vaul3t.org"
}

def parse_bool(qs_value, default=True):
    if qs_value is None:
        return default
    return qs_value.lower() not in ("0", "false", "no")

def rate_limited(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        now = time.time()
        requests_log[ip] = [t for t in requests_log[ip] if now - t < RATE_PERIOD]
        if len(requests_log[ip]) >= RATE_LIMIT:
            return jsonify({"error": f"Rate limit exceeded ({RATE_LIMIT} per 30 min)"}), 429
        requests_log[ip].append(now)
        return func(*args, **kwargs)
    return wrapper

@app.before_request
def check_origin_and_options():
    origin = request.headers.get("Origin")
    if request.method == "OPTIONS":
        if origin and origin not in ALLOWED_ORIGINS:
            return jsonify({"error": "Origin not allowed"}), 403
        resp = make_response()
        resp.headers["Access-Control-Allow-Origin"] = origin if origin else ""
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        resp.headers["Access-Control-Max-Age"] = "3600"
        return resp
    if origin:
        if origin not in ALLOWED_ORIGINS:
            return jsonify({"error": "Origin not allowed"}), 403

@app.after_request
def add_cors_header(response):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response

@app.route("/v1/osint/roblox", methods=["GET", "OPTIONS"])
@rate_limited
def osint_roblox():
    if request.method == "OPTIONS":
        return jsonify({}), 204

    username = request.args.get("username")
    if not username:
        return jsonify({"error": "username parameter required"}), 400

    options = {
        "friends": parse_bool(request.args.get("friends"), True),
        "followers": parse_bool(request.args.get("followers"), True),
        "following": parse_bool(request.args.get("following"), True),
        "friends_list": parse_bool(request.args.get("friends_list"), False),
        "followers_list": parse_bool(request.args.get("followers_list"), False),
        "following_list": parse_bool(request.args.get("following_list"), False),
        "previous_usernames": parse_bool(request.args.get("previous_usernames"), True),
        "groups": parse_bool(request.args.get("groups"), True),
        "about_me": parse_bool(request.args.get("about_me"), True),
        "presence": parse_bool(request.args.get("presence"), True),
    }

    try:
        data = roblox.get_user_info(username, options)
        if isinstance(data, dict) and data.get("error"):
            status = 429 if "Rate-Limited" in data.get("error") else 400
            data.setdefault("used_account_token", roblox.SINGLE_ROBLOSEC is not None)
            return jsonify(data), status
        if not data:
            return jsonify({"error": "User not found", "used_account_token": roblox.SINGLE_ROBLOSEC is not None}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "used_account_token": roblox.SINGLE_ROBLOSEC is not None}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

