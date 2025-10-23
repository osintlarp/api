from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
import requests
import random
import time
import threading
import os

app = Flask(__name__)

USER_PRESENCE_MAP = {0: "Offline", 1: "Online", 2: "In-Game", 3: "In-Studio", 4: "Invisible"}

RATE_LIMIT_COUNT = 10
RATE_LIMIT_WINDOW_SECONDS = 30 * 60

_requests_store = {}
_store_lock = threading.Lock()

PROXIES_FILE = "proxies.txt"
ROBLOSEC_FILE = "robloxsec.txt"
PROXIES = []
SINGLE_ROBLOSEC = None
PROXY_INDEX = 0
_proxy_lock = threading.Lock()

def load_proxies():
    global PROXIES
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [l.strip() for l in f if l.strip()]
    else:
        PROXIES = []

def load_roblosec():
    global SINGLE_ROBLOSEC
    SINGLE_ROBLOSEC = None
    if os.path.exists(ROBLOSEC_FILE):
        with open(ROBLOSEC_FILE, "r", encoding="utf-8") as f:
            for line in f:
                token = line.strip()
                if token:
                    SINGLE_ROBLOSEC = token
                    break

load_proxies()
load_roblosec()

def get_next_proxy():
    global PROXY_INDEX
    with _proxy_lock:
        if not PROXIES:
            return None
        proxy = PROXIES[PROXY_INDEX % len(PROXIES)]
        PROXY_INDEX += 1
        return proxy

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

def get_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return random.choice(user_agents)

def roblox_request(method, url, headers=None, json_payload=None, params=None, use_proxy=False, max_retries=3):
    headers = headers.copy() if headers else {}
    if not SINGLE_ROBLOSEC:
        return None, "No Roblox .ROBLOSECURITY token found"
    cookie_tuple = (".ROBLOSECURITY", SINGLE_ROBLOSEC)
    headers["User-Agent"] = headers.get("User-Agent") or get_user_agent()
    headers["Cookie"] = headers.get("Cookie", f".ROBLOSECURITY={SINGLE_ROBLOSEC}")
    retries = 0
    initial_rate_limited = False
    while retries < max_retries:
        try:
            proxies = None
            if use_proxy:
                proxy = get_next_proxy()
                if proxy:
                    proxy_url = f"http://{proxy}"
                    proxies = {"http": proxy_url, "https": proxy_url}
            resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies={cookie_tuple[0]: cookie_tuple[1]}, proxies=proxies, timeout=15)
            if resp.status_code in (401, 403) and "x-csrf-token" in resp.headers:
                headers["x-csrf-token"] = resp.headers["x-csrf-token"]
                retries += 1
                continue
            if resp.status_code == 200:
                return resp, None
            if resp.status_code == 429:
                initial_rate_limited = True
                break
            retries += 1
            time.sleep(0.5)
        except requests.RequestException:
            retries += 1
            time.sleep(0.5)
    if initial_rate_limited:
        if not PROXIES:
            return None, "Rate-Limited by Roblox ? Proxies not responding"
        for _ in range(len(PROXIES)):
            proxy = get_next_proxy()
            if not proxy:
                break
            proxy_url = f"http://{proxy}"
            proxies = {"http": proxy_url, "https": proxy_url}
            try:
                resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies={cookie_tuple[0]: cookie_tuple[1]}, proxies=proxies, timeout=15)
                if resp.status_code in (401, 403) and "x-csrf-token" in resp.headers:
                    headers["x-csrf-token"] = resp.headers["x-csrf-token"]
                    try:
                        resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies={cookie_tuple[0]: cookie_tuple[1]}, proxies=proxies, timeout=15)
                    except requests.RequestException:
                        time.sleep(0.5)
                        continue
                if resp.status_code == 200:
                    return resp, None
                if resp.status_code == 429:
                    time.sleep(0.5)
                    continue
                time.sleep(0.2)
                continue
            except requests.RequestException:
                time.sleep(0.2)
                continue
        return None, "Rate-Limited by Roblox ? Proxies not responding"
    return None, "Failed to fetch"

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {"User-Agent": get_user_agent()}
    r, err = roblox_request("GET", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        data = r.json()
        if data.get("data"):
            first = data["data"][0]
            return first.get("id") or first.get("userId")
    url = f"https://www.roblox.com/users/profile?username={username}"
    headers = {"User-Agent": get_user_agent()}
    r, err = roblox_request("GET", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200 and "users" in r.url:
        parts = r.url.split("/")
        for i, part in enumerate(parts):
            if part == "users" and i + 1 < len(parts):
                user_id = parts[i + 1]
                if user_id.isdigit():
                    return user_id
    return None

def get_previous_usernames(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
    headers = {"User-Agent": get_user_agent()}
    r, err = roblox_request("GET", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        return [entry["name"] for entry in r.json().get("data", [])]
    return []

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {"User-Agent": get_user_agent()}
    r, err = roblox_request("GET", url, headers=headers)
    if err:
        return {"error": err}
    groups = []
    if r and r.status_code == 200:
        for group in r.json().get("data", []):
            g = group.get("group", {})
            groups.append({"name": g.get("name"), "link": f"https://www.roblox.com/groups/{g.get('id')}", "members": g.get("memberCount")})
    return groups

def get_about_me(user_id):
    url = f"https://www.roblox.com/users/{user_id}/profile"
    headers = {"User-Agent": get_user_agent()}
    r, err = roblox_request("GET", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        about_me = soup.find("span", class_="profile-about-content-text linkify")
        if about_me:
            return about_me.text.strip()
        about_me_div = soup.find("div", class_="profile-about-content")
        if about_me_div:
            span = about_me_div.find("span")
            if span:
                return span.text.strip()
    return "Not available"

def get_entity_list(user_id, entity_type):
    entities = set()
    cursor = ""
    headers = {"User-Agent": get_user_agent()}
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{entity_type}?limit=100&cursor={cursor}"
        r, err = roblox_request("GET", url, headers=headers)
        if err:
            return {"error": err}
        if not r or r.status_code != 200:
            break
        data = r.json()
        for entity in data.get("data", []):
            entity_id = entity.get("id") or entity.get("user", {}).get("id")
            name = entity.get("displayName") or entity.get("name") or entity.get("user", {}).get("displayName") or entity.get("user", {}).get("name")
            if entity_id and name:
                entities.add((name, f"https://www.roblox.com/users/{entity_id}/profile"))
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        time.sleep(0.2)
    return [{"name": n, "url": u} for n, u in entities]

def get_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {"User-Agent": get_user_agent()}
    payload = {"userIds": [int(user_id)]}
    r, err = roblox_request("POST", url, headers=headers, json_payload=payload)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        data = r.json()
        if data.get("userPresences"):
            p = data["userPresences"][0]
            pt = p.get("userPresenceType")
            return {"status": USER_PRESENCE_MAP.get(pt, f"Unknown ({pt})"), "last_location": p.get("lastLocation", "N/A"), "place_id": p.get("placeId"), "last_online": p.get("lastOnline")}
    return None

def get_user_info(identifier):
    if identifier.isdigit():
        user_id = identifier
    else:
        user_id = search_by_username(identifier)
        if isinstance(user_id, dict) and user_id.get("error"):
            return user_id
    if not user_id:
        return None
    headers = {"User-Agent": get_user_agent()}
    user_url = f"https://users.roblox.com/v1/users/{user_id}"
    r, err = roblox_request("GET", user_url, headers=headers)
    if err:
        return {"error": err}
    if not r or r.status_code != 200:
        return None
    u = r.json()
    def count(url):
        r, err = roblox_request("GET", url, headers=headers)
        if err:
            return {"error": err}
        if r and r.status_code == 200:
            return r.json().get("count", 0)
        return 0
    fcount = count(f"https://friends.roblox.com/v1/users/{user_id}/friends/count")
    if isinstance(fcount, dict): return fcount
    focount = count(f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
    if isinstance(focount, dict): return focount
    fingcount = count(f"https://friends.roblox.com/v1/users/{user_id}/followings/count")
    if isinstance(fingcount, dict): return fingcount
    pres = get_presence(user_id)
    if isinstance(pres, dict) and pres.get("error"): return pres
    prev = get_previous_usernames(user_id)
    if isinstance(prev, dict): return prev
    groups = get_groups(user_id)
    if isinstance(groups, dict): return groups
    about = get_about_me(user_id)
    if isinstance(about, dict): return about
    friends = get_entity_list(user_id, "friends")
    if isinstance(friends, dict): return friends
    followers = get_entity_list(user_id, "followers")
    if isinstance(followers, dict): return followers
    following = get_entity_list(user_id, "followings")
    if isinstance(following, dict): return following
    result = {
        "user_id": user_id,
        "alias": u.get("name"),
        "display_name": u.get("displayName"),
        "description": u.get("description", ""),
        "is_banned": u.get("isBanned", False),
        "has_verified_badge": u.get("hasVerifiedBadge", False),
        "friends": fcount,
        "followers": focount,
        "following": fingcount,
        "join_date": u.get("created"),
        "previous_usernames": prev,
        "groups": groups,
        "about_me": about,
        "friends_list": friends,
        "followers_list": followers,
        "following_list": following
    }
    if pres:
        result.update({"presence_status": pres.get("status", "N/A"), "last_location": pres.get("last_location", "N/A"), "current_place_id": pres.get("place_id"), "last_online_timestamp": pres.get("last_online")})
    else:
        result.update({"presence_status": "Error fetching presence", "last_location": "N/A", "current_place_id": None, "last_online_timestamp": "N/A"})
    return result

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
    data = get_user_info(identifier)
    if isinstance(data, dict) and data.get("error"):
        if data.get("error") == "Rate-Limited by Roblox ? Proxies not responding":
            return jsonify({"error": data.get("error")}), 429
        return jsonify({"error": data.get("error")}), 400
    if data:
        return jsonify(data)
    return jsonify({"error": "User not found"}), 404

if __name__ == "__main__":
    load_proxies()
    load_roblosec()
    app.run(host="0.0.0.0", port=5000)
