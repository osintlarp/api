from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
import requests
import random
import time
import threading
import os

app = Flask(__name__)

USER_PRESENCE_MAP = {
    0: "Offline",
    1: "Online",
    2: "In-Game",
    3: "In-Studio",
    4: "Invisible"
}

RATE_LIMIT_COUNT = 10
RATE_LIMIT_WINDOW_SECONDS = 30 * 60

_requests_store = {}
_store_lock = threading.Lock()

PROXIES_FILE = "proxies.txt"
PROXIES = []
PROXY_INDEX = 0
_proxy_lock = threading.Lock()

def load_proxies():
    global PROXIES
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [l.strip() for l in f if l.strip()]
    else:
        PROXIES = []

load_proxies()

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

def try_request(method, url, headers=None, json_payload=None, params=None, max_retries=3, timeout=15):
    headers = headers or {}
    retries = 0
    initial_rate_limited = False
    while retries < max_retries:
        try:
            if method.lower() == "get":
                r = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.lower() == "post":
                r = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
            else:
                return None, False
        except requests.RequestException:
            retries += 1
            time.sleep(1)
            continue
        if r.status_code == 200:
            return r, False
        if r.status_code == 429:
            initial_rate_limited = True
            break
        retries += 1
        time.sleep(1)
    if initial_rate_limited:
        if not PROXIES:
            return None, True
        for _ in range(len(PROXIES)):
            proxy = get_next_proxy()
            if not proxy:
                break
            proxy_url = f"http://{proxy}"
            proxies = {"http": proxy_url, "https": proxy_url}
            try:
                if method.lower() == "get":
                    r = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
                else:
                    r = requests.post(url, headers=headers, json=json_payload, proxies=proxies, timeout=timeout)
                if r.status_code == 200:
                    return r, False
                if r.status_code == 429:
                    time.sleep(1)
                    continue
                time.sleep(0.5)
                continue
            except requests.RequestException:
                time.sleep(0.5)
                continue
        return None, True
    return None, False

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {'User-Agent': get_user_agent()}
    r, rate_limited = try_request("get", url, headers=headers)
    if rate_limited and not r:
        return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
    if r and r.status_code == 200:
        data = r.json()
        if data.get('data'):
            first = data['data'][0]
            return first.get('id') or first.get('userId')
    try:
        url = f"https://www.roblox.com/users/profile?username={username}"
        headers = {'User-Agent': get_user_agent()}
        r, rate_limited = try_request("get", url, headers=headers)
        if rate_limited and not r:
            return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
        if r and r.status_code == 200 and 'users' in r.url:
            parts = r.url.split('/')
            for i, part in enumerate(parts):
                if part == 'users' and i + 1 < len(parts):
                    user_id = parts[i + 1]
                    if user_id.isdigit():
                        return user_id
    except Exception:
        pass
    return None

def get_previous_usernames(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
    headers = {'User-Agent': get_user_agent()}
    r, rate_limited = try_request("get", url, headers=headers)
    if rate_limited and not r:
        return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
    if r and r.status_code == 200:
        data = r.json()
        return [entry['name'] for entry in data.get('data', [])]
    return []

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {'User-Agent': get_user_agent()}
    r, rate_limited = try_request("get", url, headers=headers)
    if rate_limited and not r:
        return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
    groups = []
    if r and r.status_code == 200:
        data = r.json()
        for group in data.get('data', []):
            grp = group.get('group', {})
            groups.append({
                'name': grp.get('name'),
                'link': f"https://www.roblox.com/groups/{grp.get('id')}",
                'members': grp.get('memberCount')
            })
    return groups

def get_about_me(user_id):
    url = f"https://www.roblox.com/users/{user_id}/profile"
    headers = {'User-Agent': get_user_agent()}
    r, rate_limited = try_request("get", url, headers=headers)
    if rate_limited and not r:
        return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
    if r and r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        about_me = soup.find('span', class_='profile-about-content-text linkify')
        if about_me:
            return about_me.text.strip()
        about_me_div = soup.find('div', class_='profile-about-content')
        if about_me_div:
            span = about_me_div.find('span')
            if span:
                return span.text.strip()
    return "Not available"

def get_entity_list(user_id, entity_type):
    entities = set()
    cursor = ""
    headers = {'User-Agent': get_user_agent()}
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{entity_type}?limit=100&cursor={cursor}"
        r, rate_limited = try_request("get", url, headers=headers)
        if rate_limited and not r:
            return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
        if not r or r.status_code != 200:
            break
        data = r.json()
        for entity in data.get('data', []):
            entity_id = entity.get('id') or entity.get('user', {}).get('id')
            name = entity.get('displayName') or entity.get('name') or entity.get('user', {}).get('displayName') or entity.get('user', {}).get('name')
            if entity_id and name:
                entities.add((name, f"https://www.roblox.com/users/{entity_id}/profile"))
        cursor = data.get('nextPageCursor')
        if not cursor:
            break
        time.sleep(0.3)
    return [{'name': n, 'url': u} for n, u in entities]

def get_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {'User-Agent': get_user_agent()}
    payload = {"userIds": [int(user_id)]}
    r, rate_limited = try_request("post", url, headers=headers, json_payload=payload)
    if rate_limited and not r:
        return {"error": "Rate-Limited by Roblox ? Proxies not responding"}
    if r and r.status_code == 200:
        data = r.json()
        if data.get("userPresences"):
            presence_data = data["userPresences"][0]
            pt = presence_data.get("userPresenceType")
            return {
                "status": USER_PRESENCE_MAP.get(pt, f"Unknown ({pt})"),
                "last_location": presence_data.get("lastLocation", "N/A"),
                "place_id": presence_data.get("placeId"),
                "last_online": presence_data.get("lastOnline")
            }
    return None

def get_user_info(identifier, **options):
    if identifier.isdigit():
        user_id = identifier
    else:
        user_id = search_by_username(identifier)
        if isinstance(user_id, dict) and user_id.get('error'):
            return {'error': user_id['error']}
            
    if not user_id:
        return None

    headers = {'User-Agent': get_user_agent()}
    user_url = f"https://users.roblox.com/v1/users/{user_id}"
    user_resp, rate_limited = try_request("get", user_url, headers=headers)
    
    if rate_limited and not user_resp:
        return {'error': "Rate-Limited by Roblox ? Proxies not responding"}
    if not user_resp or user_resp.status_code != 200:
        return None
        
    user_data = user_resp.json()

    result = {}

    if options.get('user_id', True):
        result['user_id'] = user_id
    if options.get('alias', True):
        result['alias'] = user_data.get('name')
    if options.get('display_name', True):
        result['display_name'] = user_data.get('displayName')
    if options.get('description', True):
        result['description'] = user_data.get('description', '')
    if options.get('is_banned', True):
        result['is_banned'] = user_data.get('isBanned', False)
    if options.get('has_verified_badge', True):
        result['has_verified_badge'] = user_data.get('hasVerifiedBadge', False)
    if options.get('join_date', True):
        result['join_date'] = user_data.get('created')

    def cnt(url):
        r, rl = try_request("get", url, headers=headers)
        if rl and not r:
            return 0
        if r and r.status_code == 200:
            return r.json().get('count', 0)
        return 0

    if options.get('friends', True):
        result['friends'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/friends/count")
    if options.get('followers', True):
        result['followers'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
    if options.get('following', True):
        result['following'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/followings/count")

    fetch_presence_data = any(options.get(k, True) for k in [
        'presence_status', 'last_location', 'current_place_id', 'last_online_timestamp'
    ])
    
    presence_info = None
    if fetch_presence_data:
        presence_info = get_presence(user_id)
        if isinstance(presence_info, dict) and presence_info.get('error'):
            presence_info = None

    if presence_info:
        if options.get('presence_status', True):
            result['presence_status'] = presence_info.get('status', 'N/A')
        if options.get('last_location', True):
            result['last_location'] = presence_info.get('last_location', 'N/A')
        if options.get('current_place_id', True):
            result['current_place_id'] = presence_info.get('place_id')
        if options.get('last_online_timestamp', True):
            result['last_online_timestamp'] = presence_info.get('last_online')
    elif fetch_presence_data:
        if options.get('presence_status', True):
            result['presence_status'] = 'Error fetching presence'
        if options.get('last_location', True):
            result['last_location'] = 'N/A'
        if options.get('current_place_id', True):
            result['current_place_id'] = None
        if options.get('last_online_timestamp', True):
            result['last_online_timestamp'] = 'N/A'
    
    if options.get('previous_usernames', True):
        previous_usernames = get_previous_usernames(user_id)
        if isinstance(previous_usernames, dict) and previous_usernames.get('error'):
            previous_usernames = []
        result['previous_usernames'] = previous_usernames

    if options.get('groups', True):
        groups = get_groups(user_id)
        if isinstance(groups, dict) and groups.get('error'):
            groups = []
        result['groups'] = groups

    if options.get('about_me', True):
        about_me = get_about_me(user_id)
        if isinstance(about_me, dict) and about_me.get('error'):
            about_me = "Not available"
        result['about_me'] = about_me

    if options.get('friends_list', True):
        friends = get_entity_list(user_id, "friends")
        if isinstance(friends, dict) and friends.get('error'):
            friends = []
        result['friends_list'] = friends

    if options.get('followers_list', True):
        followers = get_entity_list(user_id, "followers")
        if isinstance(followers, dict) and followers.get('error'):
            followers = []
        result['followers_list'] = followers

    if options.get('following_list', True):
        followings = get_entity_list(user_id, "followings")
        if isinstance(followings, dict) and followings.get('error'):
            followings = []
        result['following_list'] = followings
        
    return result
