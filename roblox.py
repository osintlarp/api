from bs4 import BeautifulSoup
import requests
import random
import time
import threading
import os

USER_PRESENCE_MAP = {0: "Offline", 1: "Online", 2: "In-Game", 3: "In-Studio", 4: "Invisible"}

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

def get_next_proxy():
    global PROXY_INDEX
    with _proxy_lock:
        if not PROXIES:
            return None
        proxy = PROXIES[PROXY_INDEX % len(PROXIES)]
        PROXY_INDEX += 1
        return proxy

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
    used_token = False
    cookie_dict = {}
    if SINGLE_ROBLOSEC:
        used_token = True
        cookie_dict = {".ROBLOSECURITY": SINGLE_ROBLOSEC}
        headers["Cookie"] = headers.get("Cookie", f".ROBLOSECURITY={SINGLE_ROBLOSEC}")
    headers["User-Agent"] = headers.get("User-Agent") or get_user_agent()
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
            resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies=cookie_dict, proxies=proxies, timeout=15)
            if resp.status_code in (401, 403) and "x-csrf-token" in resp.headers:
                headers["x-csrf-token"] = resp.headers["x-csrf-token"]
                retries += 1
                continue
            if resp.status_code == 200:
                return resp, None, used_token
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
            return None, "Rate-Limited by Roblox ? Proxies not responding", used_token
        for _ in range(len(PROXIES)):
            proxy = get_next_proxy()
            if not proxy:
                break
            proxy_url = f"http://{proxy}"
            proxies = {"http": proxy_url, "https": proxy_url}
            try:
                resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies=cookie_dict, proxies=proxies, timeout=15)
                if resp.status_code in (401, 403) and "x-csrf-token" in resp.headers:
                    headers["x-csrf-token"] = resp.headers["x-csrf-token"]
                    resp = requests.request(method, url, headers=headers, json=json_payload, params=params, cookies=cookie_dict, proxies=proxies, timeout=15)
                if resp.status_code == 200:
                    return resp, None, used_token
                if resp.status_code == 429:
                    time.sleep(0.5)
                    continue
            except requests.RequestException:
                time.sleep(0.2)
                continue
        return None, "Rate-Limited by Roblox ? Proxies not responding", used_token
    return None, "Failed to fetch", used_token

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {"User-Agent": get_user_agent()}
    r, err, used = roblox_request("GET", url, headers=headers)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    if r and r.status_code == 200:
        data = r.json()
        if data.get("data"):
            first = data["data"][0]
            return (first.get("id") or first.get("userId")) , used
    url = f"https://www.roblox.com/users/profile?username={username}"
    headers = {"User-Agent": get_user_agent()}
    r, err, used = roblox_request("GET", url, headers=headers)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    if r and r.status_code == 200 and "users" in r.url:
        parts = r.url.split("/")
        for i, part in enumerate(parts):
            if part == "users" and i + 1 < len(parts):
                user_id = parts[i + 1]
                if user_id.isdigit():
                    return user_id, used
    return None, used

def get_previous_usernames(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
    headers = {"User-Agent": get_user_agent()}
    r, err, used = roblox_request("GET", url, headers=headers)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    if r and r.status_code == 200:
        return [entry["name"] for entry in r.json().get("data", [])], used
    return [], used

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {"User-Agent": get_user_agent()}
    r, err, used = roblox_request("GET", url, headers=headers)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    groups = []
    if r and r.status_code == 200:
        for group in r.json().get("data", []):
            g = group.get("group", {})
            groups.append({"name": g.get("name"), "link": f"https://www.roblox.com/groups/{g.get('id')}", "members": g.get("memberCount")})
    return groups, used

def get_about_me(user_id):
    url = f"https://www.roblox.com/users/{user_id}/profile"
    headers = {"User-Agent": get_user_agent()}
    r, err, used = roblox_request("GET", url, headers=headers)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    if r and r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        about_me = soup.find("span", class_="profile-about-content-text linkify")
        if about_me:
            return about_me.text.strip(), used
        about_me_div = soup.find("div", class_="profile-about-content")
        if about_me_div:
            span = about_me_div.find("span")
            if span:
                return span.text.strip(), used
    return "Not available", used

def get_entity_list(user_id, entity_type):
    endpoint_map = {
        "friends_list": "friends",
        "followers_list": "followers",
        "following_list": "followings"
    }
    actual_endpoint = endpoint_map.get(entity_type)
    if not actual_endpoint:
        return []

    entities = set()
    cursor = ""
    headers = {"User-Agent": get_user_agent()}
    cookies = {".ROBLOSECURITY": SINGLE_ROBLOSEC} if SINGLE_ROBLOSEC else {}

    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{actual_endpoint}?limit=100&cursor={cursor}"
        response = requests.get(url, headers=headers, cookies=cookies)
        if response.status_code != 200:
            break
        data = response.json()
        for entity in data.get("data", []):
            if "displayName" in entity:
                name = entity.get("displayName") or entity.get("username", "No Name")
                entity_id = entity.get("id", "")
            elif "name" in entity:
                name = entity["name"]
                entity_id = entity["id"]
            elif "user" in entity and isinstance(entity["user"], dict):
                user_data = entity["user"]
                name = user_data.get("displayName") or user_data.get("name", "No Name")
                entity_id = user_data.get("id", "")
            else:
                name = "Unknown"
                entity_id = entity.get("id", "")
            if entity_id:
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
    r, err, used = roblox_request("POST", url, headers=headers, json_payload=payload)
    if err and r is None:
        return {"error": err, "used_account_token": used}
    if r and r.status_code == 200:
        data = r.json()
        if data.get("userPresences"):
            p = data["userPresences"][0]
            pt = p.get("userPresenceType")
            return {"status": USER_PRESENCE_MAP.get(pt, f"Unknown ({pt})"), "last_location": p.get("lastLocation", "N/A"), "place_id": p.get("placeId"), "last_online": p.get("lastOnline")}, used
    return None, used

def get_user_info(identifier, options):
    used_flags = {"used_account_token": False}
    if identifier.isdigit():
        user_id = identifier
        search_used = False
    else:
        res = search_by_username(identifier)
        if isinstance(res, dict) and res.get("error"):
            return res
        user_id, search_used = res
        used_flags["used_account_token"] = used_flags["used_account_token"] or (isinstance(res, tuple) and res[1])
    if not user_id:
        return None
    headers = {"User-Agent": get_user_agent()}
    user_url = f"https://users.roblox.com/v1/users/{user_id}"
    r, err, used = roblox_request("GET", user_url, headers=headers)
    used_flags["used_account_token"] = used_flags["used_account_token"] or used
    if err and r is None:
        return {"error": err, "used_account_token": used_flags["used_account_token"]}
    if not r or r.status_code != 200:
        return None
    u = r.json()
    def count(url):
        r, err, used = roblox_request("GET", url, headers=headers)
        used_flags["used_account_token"] = used_flags["used_account_token"] or used
        if err and r is None:
            return {"error": err, "used_account_token": used_flags["used_account_token"]}
        if r and r.status_code == 200:
            return r.json().get("count", 0)
        return 0
    fcount = count(f"https://friends.roblox.com/v1/users/{user_id}/friends/count") if options.get("friends", True) else None
    fo_count = count(f"https://friends.roblox.com/v1/users/{user_id}/followers/count") if options.get("followers", True) else None
    fi_count = count(f"https://friends.roblox.com/v1/users/{user_id}/followings/count") if options.get("following", True) else None
    def maybe_list(name):
        if options.get(name, False):
            l, used = get_entity_list(user_id, name)
            used_flags["used_account_token"] = used_flags["used_account_token"] or used
            return l
        return []
    friends_list = maybe_list("friends_list")
    followers_list = maybe_list("followers_list")
    following_list = maybe_list("following_list")
    previous_usernames, used = get_previous_usernames(user_id) if options.get("previous_usernames", True) else ([], False)
    used_flags["used_account_token"] = used_flags["used_account_token"] or used
    groups, used = get_groups(user_id) if options.get("groups", True) else ([], False)
    used_flags["used_account_token"] = used_flags["used_account_token"] or used
    about_me, used = get_about_me(user_id) if options.get("about_me", True) else ("Not available", False)
    used_flags["used_account_token"] = used_flags["used_account_token"] or used
    presence_info, used = get_presence(user_id) if options.get("presence", True) else (None, False)
    used_flags["used_account_token"] = used_flags["used_account_token"] or used
    return {
        "user_id": user_id,
        "alias": u["name"],
        "display_name": u.get("displayName"),
        "description": u.get("description", ""),
        "is_banned": u.get("isBanned", False),
        "has_verified_badge": u.get("hasVerifiedBadge", False),
        "friends": fcount,
        "followers": fo_count,
        "following": fi_count,
        "join_date": u.get("created"),
        "previous_usernames": previous_usernames,
        "groups": groups,
        "about_me": about_me,
        "friends_list": friends_list,
        "followers_list": followers_list,
        "following_list": following_list,
        "presence": presence_info,
        **used_flags
    }
