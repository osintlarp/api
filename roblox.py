import requests
import json
from bs4 import BeautifulSoup
import random
import time
import os
import threading
from datetime import datetime, timedelta

USER_PRESENCE_MAP = {
    0: "Offline", 1: "Online", 2: "In-Game", 3: "In-Studio", 4: "Invisible"
}

PROXIES_FILE = "proxies.txt"
PROXIES = []
_state_lock = threading.Lock()

RATE_LIMIT_COUNT = 0
RATE_LIMIT_THRESHOLD = 5
PROXY_MODE_UNTIL = datetime.now() 
PROXY_MODE_DURATION = timedelta(minutes=15)

class RateLimitException(Exception):
    pass

def load_proxies():
    global PROXIES
    if not os.path.exists(PROXIES_FILE):
        print(f"Warning: '{PROXIES_FILE}' not found. Proxy mode will not work.")
        return
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [line.strip() for line in f if line.strip()]
        if PROXIES:
            print(f"Successfully loaded {len(PROXIES)} proxies.")
        else:
            print(f"Warning: '{PROXIES_FILE}' is empty. Proxy mode will not work.")
    except Exception as e:
        print(f"Error loading proxies: {e}")

def get_random_proxy_dict():
    if not PROXIES:
        return None
    proxy = random.choice(PROXIES)
    if not proxy.startswith(('http://', 'https://')):
        proxy = f'http://{proxy}'
    return {"http": proxy, "https": proxy}

def get_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return random.choice(user_agents)

def _make_request(method, url, headers, json_payload=None, params=None, allow_redirects=False, timeout=10):
    global RATE_LIMIT_COUNT, PROXY_MODE_UNTIL
    
    use_proxy = False
    proxies = None

    with _state_lock:
        if datetime.now() < PROXY_MODE_UNTIL:
            use_proxy = True
        elif RATE_LIMIT_COUNT >= RATE_LIMIT_THRESHOLD:
            PROXY_MODE_UNTIL = datetime.now() + PROXY_MODE_DURATION
            RATE_LIMIT_COUNT = 0 
            print(f"Rate limit threshold {RATE_LIMIT_THRESHOLD} hit. Engaging proxy mode for 15 minutes.")
            use_proxy = True

    if use_proxy:
        proxies = get_random_proxy_dict()
        if not proxies:
            print("Proxy mode active, but no proxies are loaded or available. Request will likely fail.")
    
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            json=json_payload,
            params=params,
            proxies=proxies,
            allow_redirects=allow_redirects,
            timeout=timeout
        )
    except requests.RequestException as e:
        print(f"Request exception ({e}) for {url}. Retrying...")
        raise RateLimitException() 

    if response.status_code == 200:
        return response
    
    if response.status_code == 429:
        if not use_proxy:
            with _state_lock:
                RATE_LIMIT_COUNT += 1
                print(f"Rate limit hit. Count: {RATE_LIMIT_COUNT}/{RATE_LIMIT_THRESHOLD}")
        
        wait_time = int(response.headers.get('Retry-After', 5))
        print(f"Rate limited. Waiting {wait_time} seconds...")
        time.sleep(wait_time)
        raise RateLimitException() 
    
    print(f"Request failed for {url} with status {response.status_code}. Stopping retries.")
    return None

def request_with_retries(method, url, headers, json_payload=None, params=None, allow_redirects=False, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            response = _make_request(
                method, url, headers, 
                json_payload=json_payload, 
                params=params, 
                allow_redirects=allow_redirects
            )
            return response
        
        except RateLimitException:
            retries += 1
            continue 
            
    print(f"Failed to fetch {url} after {max_retries} retries.")
    return None

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {'User-Agent': get_user_agent()}
    response = request_with_retries("get", url, headers=headers)
    
    if response and response.status_code == 200:
        data = response.json()
        if data['data']:
            if 'id' in data['data'][0]:
                return data['data'][0]['id']
            elif 'userId' in data['data'][0]:
                return data['data'][0]['userId']
    
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
    except Exception as e:
        print(f"Error in redirect search for {username}: {e}")
        pass
    
    return None

def get_previous_usernames(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history?limit=100&sortOrder=Asc"
    headers = {'User-Agent': get_user_agent()}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return [entry['name'] for entry in data['data']]
    
    return []

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {'User-Agent': get_user_agent()}
    response = requests.get(url, headers=headers)
    
    groups = []
    if response.status_code == 200:
        data = response.json()
        for group in data['data']:
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
        else:
            about_me_div = soup.find('div', class_='profile-about-content')
            if about_me_div:
                about_me_span = about_me_div.find('span')
                if about_me_span:
                    return about_me_span.text.strip()
    
    return "Not available"

def get_entity_list(user_id, entity_type):
    entities = set()  
    cursor = ""
    
    while True:
        url = f"https://friends.roblox.com/v1/users/{user_id}/{entity_type}?limit=100&cursor={cursor}"
        headers = {'User-Agent': get_user_agent()}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            for entity in data['data']:
                if 'displayName' in entity:
                    name = entity.get('displayName') or entity.get('username', 'Usuario sin nombre')
                    entity_id = entity.get('id', '')
                elif 'name' in entity:
                    name = entity['name']
                    entity_id = entity['id']
                elif 'user' in entity and isinstance(entity['user'], dict):
                    user_data = entity['user']
                    name = user_data.get('displayName') or user_data.get('name', 'Usuario sin nombre')
                    entity_id = user_data.get('id', '')
                else:
                    available_keys = list(entity.keys())
                    name = f"Usuario {available_keys}"
                    entity_id = entity.get('id', '')
                
                if entity_id:
                    entities.add((name, f"https://www.roblox.com/users/{entity_id}/profile"))
            
            cursor = data.get('nextPageCursor')
            if not cursor:
                break
        else:
            break
        
        time.sleep(1)
    
    return [{'name': name, 'url': url} for name, url in entities]

def get_presence(user_id, headers):
    url = "https://presence.roblox.com/v1/presence/users"
    payload = {"userIds": [int(user_id)]}  
    
    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("userPresences") and len(data["userPresences"]) > 0:
                    presence_data = data["userPresences"][0]
                    presence_type = presence_data.get("userPresenceType")
                    
                    return {
                        "status": USER_PRESENCE_MAP.get(presence_type, f"Unknown ({presence_type})"),
                        "last_location": presence_data.get("lastLocation", "N/A"),
                        "place_id": presence_data.get("placeId"),
                        "last_online": presence_data.get("lastOnline")
                    }
                return None
            elif response.status_code == 429:
                wait_time = int(response.headers.get('Retry-After', 5))
                print(f"Rate limited on presence API. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"Failed to get presence. Status: {response.status_code}, Response: {response.text}")
                return None
        except requests.RequestException as e:
            print(f"Error during presence request: {e}")
            time.sleep(5)
            retries += 1
    
    print("Failed to get presence after retries.")
    return None

def get_user_info(identifier):
    if identifier.isdigit():
        user_id = identifier
    else:
        user_id = search_by_username(identifier)
    
    if not user_id:
        return None
    
    user_url = f"https://users.roblox.com/v1/users/{user_id}"
    headers = {'User-Agent': get_user_agent()}
    user_response = request_with_retries(user_url, headers=headers)
    
    if user_response and user_response.status_code == 200:
        user_data = user_response.json()
        
        friends_url = f"https://friends.roblox.com/v1/users/{user_id}/friends/count"
        friends_response = requests.get(friends_url, headers=headers)
        friends_count = friends_response.json()['count'] if friends_response.status_code == 200 else 0
        
        followers_url = f"https://friends.roblox.com/v1/users/{user_id}/followers/count"
        followings_url = f"https://friends.roblox.com/v1/users/{user_id}/followings/count"
        followers_response = requests.get(followers_url, headers=headers)
        followings_response = requests.get(followings_url, headers=headers)
        followers_count = followers_response.json()['count'] if followers_response.status_code == 200 else 0
        followings_count = followings_response.json()['count'] if followings_response.status_code == 200 else 0
        
        presence_info = get_presence(user_id, headers)
        
        previous_usernames = get_previous_usernames(user_id)
        groups = get_groups(user_id)
        about_me = get_about_me(user_id)
        friends = get_entity_list(user_id, "friends")
        followers = get_entity_list(user_id, "followers")
        followings = get_entity_list(user_id, "followings")
        
        user_info_data = {
            'user_id': user_id,
            'alias': user_data['name'],
            'display_name': user_data['displayName'],
            'description': user_data.get('description', ''),
            'is_banned': user_data.get('isBanned', False),
            'has_verified_badge': user_data.get('hasVerifiedBadge', False),
            'friends': friends_count,
            'followers': followers_count,
            'following': followings_count,
            'join_date': user_data['created'],
            'previous_usernames': previous_usernames,
            'groups': groups,
            'about_me': about_me,
            'friends_list': friends,
            'followers_list': followers,
            'following_list': followings
        }
        
        if presence_info:
            user_info_data['presence_status'] = presence_info.get('status', 'N/A')
            user_info_data['last_location'] = presence_info.get('last_location', 'N/A')
            user_info_data['current_place_id'] = presence_info.get('place_id')
            user_info_data['last_online_timestamp'] = presence_info.get('last_online')
        else:
            user_info_data['presence_status'] = 'Error fetching presence'
            user_info_data['last_location'] = 'N/A'
            user_info_data['current_place_id'] = None
            user_info_data['last_online_timestamp'] = 'N/A'
        
        return user_info_data
    
    return None

load_proxies()
