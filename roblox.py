from bs4 import BeautifulSoup
import time
import os
import json
from datetime import datetime, timezone
from utils import try_request, get_user_agent

USER_PRESENCE_MAP = {
    0: "Offline",
    1: "Online",
    2: "In-Game",
    3: "In-Studio",
    4: "Invisible"
}

ROBLOX_BADGE_TABLE = {
    1: "Administrator",
    2: "Friendship",
    3: "Combat Initiation",
    4: "Warrior",
    5: "Bloxxer",
    6: "Homestead",
    7: "Bricksmith",
    8: "Inviter",
    12: "Veteran",
    14: "Ambassador",
    17: "Official Model Maker",
    18: "Welcome To The Club"
}

CACHE_DIR = "_CACHE_ROBLOX_OS_"
CACHE_DURATION_SECONDS = 6 * 60 * 60
os.makedirs(CACHE_DIR, exist_ok=True)

ALL_OPTION_KEYS = [
    'user_id', 'alias', 'display_name', 'description', 'is_banned',
    'has_verified_badge', 'friends', 'followers', 'following', 'join_date',
    'account_age', 'roblox_badges', 'previous_usernames', 'groups', 'about_me', 
    'friends_list', 'followers_list', 'following_list', 'presence_status',
    'last_location', 'current_place_id', 'last_online_timestamp'
]

def sanitize_filename(filename):
    if not filename:
        return None
    return "".join(c for c in filename if c.isalnum() or c in ('_', '-')).rstrip()

def read_from_cache(username):
    filename = sanitize_filename(username)
    if not filename:
        return None
        
    filepath = os.path.join(CACHE_DIR, f"{filename}.json")
    
    if not os.path.exists(filepath):
        return None
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if time.time() - data.get('timestamp', 0) < CACHE_DURATION_SECONDS:
            return data.get('info')
    except Exception as e:
        print(f"Error reading from cache file {filepath}: {e}")
        return None
    
    return None

def write_to_cache(username, info):
    filename = sanitize_filename(username)
    if not filename:
        print("Failed to write to cache: Invalid username for filename.")
        return
        
    filepath = os.path.join(CACHE_DIR, f"{filename}.json")
    data = {'timestamp': time.time(), 'info': info}
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to write to cache file {filepath}: {e}")

def search_by_username(username):
    url = f"https://users.roblox.com/v1/users/search?keyword={username}&limit=10"
    headers = {'User-Agent': get_user_agent()}
    r, err = try_request("get", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        data = r.json()
        if data.get('data'):
            first = data['data'][0]
            for item in data.get('data'):
                if item.get('name', '').lower() == username.lower():
                    return item.get('id') or item.get('userId')
            return first.get('id') or first.get('userId')
    try:
        url = f"https://www.roblox.com/users/profile?username={username}"
        headers = {'User-Agent': get_user_agent()}
        r, err = try_request("get", url, headers=headers)
        if err:
            return {"error": err}
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
    r, err = try_request("get", url, headers=headers)
    if err:
        return {"error": err}
    if r and r.status_code == 200:
        data = r.json()
        return [entry['name'] for entry in data.get('data', [])]
    return []

def get_groups(user_id):
    url = f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
    headers = {'User-Agent': get_user_agent()}
    r, err = try_request("get", url, headers=headers)
    if err:
        return {"error": err}
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
    r, err = try_request("get", url, headers=headers)
    if err:
        return {"error": err}
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
        r, err = try_request("get", url, headers=headers)
        if err:
            return {"error": err}
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
    r, err = try_request("post", url, headers=headers, json_payload=payload)
    if err:
        return {"error": err}
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

def get_roblox_badges(user_id):
    url = f"https://accountinformation.roblox.com/v1/users/{user_id}/roblox-badges"
    headers = {'User-Agent': get_user_agent()}
    r, err = try_request("get", url, headers=headers)
    
    if err:
        return {"error": err}
        
    if r and r.status_code == 200:
        try:
            data = r.json()
            return [badge['id'] for badge in data]
        except Exception as e:
            print(f"Error parsing badges JSON for {user_id}: {e}")
            return []
    return []

def _filter_data(full_data, options):
    filtered_result = {}
    for key in ALL_OPTION_KEYS:
        if options.get(key, True):
            filtered_result[key] = full_data.get(key)
    return filtered_result

def get_user_info(identifier, use_cache=True, **options):
    cache_username = None
    full_data = None
    
    if not identifier.isdigit():
        cache_username = identifier
        if use_cache:
            cached_data = read_from_cache(cache_username)
            if cached_data:
                full_data = cached_data

    if not full_data:
        if identifier.isdigit():
            user_id = identifier
        else:
            user_id = search_by_username(identifier)
            if isinstance(user_id, dict) and user_id.get('error'):
                return {'error': user_id['error']}
                
        if not user_id:
            return {'error': 'User not found'}

        headers = {'User-Agent': get_user_agent()}
        user_url = f"https://users.roblox.com/v1/users/{user_id}"
        user_resp, err = try_request("get", user_url, headers=headers)
        
        if err:
            return {'error': err}
        if not user_resp or user_resp.status_code != 200:
            return {'error': 'Failed to fetch user data'}
            
        user_data = user_resp.json()

        if not cache_username:
            cache_username = user_data.get('name')
            if use_cache and cache_username:
                cached_data = read_from_cache(cache_username)
                if cached_data:
                    full_data = cached_data

    if not full_data:
        full_data = {}
        user_id = user_data.get('id') or user_id
        full_data['user_id'] = user_id
        full_data['alias'] = user_data.get('name')
        full_data['display_name'] = user_data.get('displayName')
        full_data['description'] = user_data.get('description', '')
        full_data['is_banned'] = user_data.get('isBanned', False)
        full_data['has_verified_badge'] = user_data.get('hasVerifiedBadge', False)
        full_data['join_date'] = user_data.get('created')
        
        full_data['account_age'] = "N/A"
        join_date_str = user_data.get('created')
        if join_date_str:
            try:
                if join_date_str.endswith('Z'):
                    join_date_str_iso = join_date_str[:-1] + '+00:00'
                else:
                    join_date_str_iso = join_date_str
                    
                join_date_obj = datetime.fromisoformat(join_date_str_iso)
                
                delta = datetime.now(timezone.utc) - join_date_obj
                total_days = delta.days
                
                if total_days < 0:
                    full_data['account_age'] = "Joined in the future?"
                else:
                    years = total_days // 365
                    days_remaining = total_days % 365
                    
                    year_str = f"{years} Year" if years == 1 else f"{years} Years"
                    day_str = f"{days_remaining} Day" if days_remaining == 1 else f"{days_remaining} Days"

                    if years > 0:
                        full_data['account_age'] = f"{year_str}, {day_str}"
                    else:
                        full_data['account_age'] = day_str
                        
            except Exception as e:
                print(f"Error parsing date {join_date_str}: {e}")
                full_data['account_age'] = "Error calculating age"

        def cnt(url):
            r, rl = try_request("get", url, headers=headers)
            if rl:
                return 0
            if r and r.status_code == 200:
                return r.json().get('count', 0)
            return 0

        full_data['friends'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/friends/count")
        full_data['followers'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/followers/count")
        full_data['following'] = cnt(f"https://friends.roblox.com/v1/users/{user_id}/followings/count")
        
        presence_info = get_presence(user_id)
        if isinstance(presence_info, dict) and presence_info.get('error'):
            presence_info = None 

        if presence_info:
            full_data['presence_status'] = presence_info.get('status', 'N/A')
            full_data['last_location'] = presence_info.get('last_location', 'N/A')
            full_data['current_place_id'] = presence_info.get('place_id')
            full_data['last_online_timestamp'] = presence_info.get('last_online')
        else:
            full_data['presence_status'] = 'Error fetching presence'
            full_data['last_location'] = 'N/A'
            full_data['current_place_id'] = None
            full_data['last_online_timestamp'] = 'N/A'
        
        previous_usernames = get_previous_usernames(user_id)
        if isinstance(previous_usernames, dict) and previous_usernames.get('error'):
            previous_usernames = [] 
        full_data['previous_usernames'] = previous_usernames

        groups = get_groups(user_id)
        if isinstance(groups, dict) and groups.get('error'):
            groups = [] 
        full_data['groups'] = groups

        about_me = get_about_me(user_id)
        if isinstance(about_me, dict) and about_me.get('error'):
            about_me = "Not available" 
        full_data['about_me'] = about_me

        friends = get_entity_list(user_id, "friends")
        if isinstance(friends, dict) and friends.get('error'):
            friends = [] 
        full_data['friends_list'] = friends

        followers = get_entity_list(user_id, "followers")
        if isinstance(followers, dict) and followers.get('error'):
            followers = [] 
        full_data['followers_list'] = followers

        followings = get_entity_list(user_id, "followings")
        if isinstance(followings, dict) and followings.get('error'):
            followings = [] 
        full_data['following_list'] = followings
        
        badge_ids = get_roblox_badges(user_id)
        if isinstance(badge_ids, dict) and badge_ids.get('error'):
            full_data['roblox_badges'] = ["Error fetching badges"] 
        else:
            full_data['roblox_badges'] = [ROBLOX_BADGE_TABLE[bid] for bid in badge_ids if bid in ROBLOX_BADGE_TABLE]
        
        if cache_username and use_cache:
            write_to_cache(cache_username, full_data)
            
    return _filter_data(full_data, options)
