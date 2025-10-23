from bs4 import BeautifulSoup
import requests
import random
import time

USER_PRESENCE_MAP = {0: "Offline", 1: "Online", 2: "In-Game", 3: "In-Studio", 4: "Invisible"}

PROXIES_FILE = "proxies.txt"
PROXIES = []
PROXY_INDEX = 0

def load_proxies():
    global PROXIES
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        PROXIES = []

def get_next_proxy():
    global PROXY_INDEX
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

def request_with_retries(url, headers=None, max_retries=3):
    retries = 0
    while retries < max_retries:
        proxy = get_next_proxy()
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=10)
            if response.status_code == 429:
                retries += 1
                time.sleep(1)
                continue
            return response
        except requests.RequestException:
            retries += 1
            time.sleep(0.5)
    return None

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {'User-Agent': get_user_agent()}
    response = request_with_retries(url, headers)
    if response and response.status_code == 200:
        data = response.json()
        if data['data']:
            if 'id' in data['data'][0]:
                return str(data['data'][0]['id'])
            elif 'userId' in data['data'][0]:
                return str(data['data'][0]['userId'])
    try:
        url = f"https://www.roblox.com/users/profile?username={username}"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers, allow_redirects=True)
        if response.status_code == 200 and 'users' in response.url:
            parts = response.url.split('/')
            for i, part in enumerate(parts):
                if part == 'users' and i + 1 < len(parts):
                    user_id = parts[i + 1]
                    if user_id.isdigit():
                        return user_id
    except:
        pass
    return None

def get_previous_usernames(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
    headers = {'User-Agent': get_user_agent()}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [entry['name'] for entry in response.json()['data']]
    return []

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {'User-Agent': get_user_agent()}
    response = requests.get(url, headers=headers)
    groups = []
    if response.status_code == 200:
        for group in response.json()['data']:
            groups.append({
                'name': group['group']['name'],
                'link': f"https://www.roblox.com/groups/{group['group']['id']}",
                'members': group['group']['memberCount']
            })
    return groups

def get_about_me(user_id):
    url = f"https://www.roblox.com/users/{user_id}/profile"
    headers = {'User-Agent': get_user_agent()}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
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
    endpoint_map = {"friends_list":"friends","followers_list":"followers","following_list":"followings"}
    actual_endpoint = endpoint_map.get(entity_type, entity_type)
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{actual_endpoint}?limit=100&cursor={cursor}"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            break
        data = response.json()
        for entity in data.get('data', []):
            if "displayName" in entity:
                name = entity.get("displayName") or entity.get("username","No Name")
                entity_id = entity.get("id","")
            elif "name" in entity:
                name = entity["name"]
                entity_id = entity["id"]
            elif "user" in entity and isinstance(entity["user"], dict):
                user_data = entity["user"]
                name = user_data.get("displayName") or user_data.get("name","No Name")
                entity_id = user_data.get("id","")
            else:
                name = "Unknown"
                entity_id = entity.get("id","")
            if entity_id:
                entities.add((name,f"https://www.roblox.com/users/{entity_id}/profile"))
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
        time.sleep(0.2)
    return [{"name":n,"url":u} for n,u in entities]

def get_presence(user_id):
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {'User-Agent': get_user_agent()}
    payload = {"userIds":[int(user_id)]}
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            d = response.json()
            if d.get("userPresences"):
                p = d["userPresences"][0]
                pt = p.get("userPresenceType")
                return {"status": USER_PRESENCE_MAP.get(pt, f"Unknown ({pt})"),
                        "last_location": p.get("lastLocation","N/A"),
                        "place_id": p.get("placeId"),
                        "last_online": p.get("lastOnline")}
    except:
        pass
    return None

def get_user_info(identifier, options=None):
    if options is None:
        options = {}
    user_id = identifier if identifier.isdigit() else search_by_username(identifier)
    if not user_id:
        return None

    headers = {'User-Agent': get_user_agent()}
    user_response = request_with_retries(f"https://users.roblox.com/v1/users/{user_id}", headers)
    if not user_response or user_response.status_code != 200:
        return None
    u = user_response.json()

    def maybe_count(url, flag=True):
        if flag:
            r = requests.get(url, headers=headers)
            if r.status_code == 200:
                return r.json().get('count',0)
        return None

    friends_count = maybe_count(f"https://friends.roblox.com/v1/users/{user_id}/friends/count", options.get("friends", True))
    followers_count = maybe_count(f"https://friends.roblox.com/v1/users/{user_id}/followers/count", options.get("followers", True))
    following_count = maybe_count(f"https://friends.roblox.com/v1/users/{user_id}/followings/count", options.get("following", True))

    def maybe_list(name):
        return get_entity_list(user_id,name) if options.get(name, False) else []

    previous_usernames = get_previous_usernames(user_id) if options.get("previous_usernames", False) else []
    groups = get_groups(user_id) if options.get("groups", False) else []
    about_me = get_about_me(user_id) if options.get("about_me", False) else "Not available"
    presence = get_presence(user_id) if options.get("presence", False) else None

    return {
        "user_id": user_id,
        "alias": u['name'],
        "display_name": u.get("displayName"),
        "description": u.get("description",""),
        "is_banned": u.get("isBanned",False),
        "has_verified_badge": u.get("hasVerifiedBadge",False),
        "friends": friends_count,
        "followers": followers_count,
        "following": following_count,
        "join_date": u.get("created"),
        "previous_usernames": previous_usernames,
        "groups": groups,
        "about_me": about_me,
        "friends_list": maybe_list("friends_list"),
        "followers_list": maybe_list("followers_list"),
        "following_list": maybe_list("following_list"),
        "presence": presence
    }

load_proxies()

