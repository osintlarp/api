import json
import os
import time
from utils import try_request, get_user_agent

GITHUB_TOKEN = "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"

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": get_user_agent(),
    "Authorization": f"Bearer {GITHUB_TOKEN}"
}

API_BASE_URL = "https://api.github.com/users"

CACHE_DIR = "_CACHE_GITHUB_OS_"
CACHE_DURATION_SECONDS = 6 * 60 * 60
os.makedirs(CACHE_DIR, exist_ok=True)

ALL_OPTION_KEYS = ['user_info', 'followers_list', 'following_list', 'subscriptions', 'repos']

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

def _clean_data(data):
    if isinstance(data, dict):
        return {
            key: _clean_data(value)
            for key, value in data.items()
            if not key.endswith('_url') and key not in ['url', 'node_id', 'gravatar_id']
        }
    elif isinstance(data, list):
        return [_clean_data(item) for item in data]
    else:
        return data

def _fetch_github_data(endpoint):
    url = f"{API_BASE_URL}/{endpoint}"
    response, error = try_request("get", url, headers=GITHUB_HEADERS)
    
    if error:
        return None, {"error": error}
    
    if response.status_code == 404:
        return None, {"error": "User or resource not found"}
        
    if response.status_code != 200:
        return None, {"error": f"GitHub API returned status {response.status_code}", "details": response.text}
        
    try:
        return response.json(), None
    except json.JSONDecodeError:
        return None, {"error": "Failed to decode JSON response from GitHub"}

def _filter_data(full_data, options):
    filtered_result = {}
    for key in ALL_OPTION_KEYS:
        if options.get(key, True):
            filtered_result[key] = full_data.get(key)
    return filtered_result

def get_github_info(username, use_cache=True, **options):
    if not username:
        return {"error": "No username provided"}

    if use_cache:
        cached_data = read_from_cache(username)
        if cached_data:
            return _filter_data(cached_data, options)

    full_data = {}

    if options.get('user_info', True):
        user_data, error = _fetch_github_data(username)
        if error:
            return error
        full_data["user_info"] = _clean_data(user_data)
    else:
        full_data["user_info"] = {"message": "Data not requested"}

    if options.get('followers_list', True):
        followers_data, error = _fetch_github_data(f"{username}/followers")
        if error:
            print(f"Warning: Could not fetch followers for {username}. Error: {error}")
            followers_data = []
        full_data["followers_list"] = _clean_data(followers_data)
    
    if options.get('following_list', True):
        following_data, error = _fetch_github_data(f"{username}/following")
        if error:
            print(f"Warning: Could not fetch following for {username}. Error: {error}")
            following_data = []
        full_data["following_list"] = _clean_data(following_data)

    if options.get('subscriptions', True):
        subscriptions_data, error = _fetch_github_data(f"{username}/subscriptions")
        if error:
            print(f"Warning: Could not fetch subscriptions for {username}. Error: {error}")
            subscriptions_data = []
        full_data["subscriptions"] = _clean_data(subscriptions_data)

    if options.get('repos', True):
        repos_data, error = _fetch_github_data(f"{username}/repos")
        if error:
            print(f"Warning: Could not fetch repos for {username}. Error: {error}")
            repos_data = []
        full_data["repos"] = _clean_data(repos_data)

    if use_cache:
        write_to_cache(username, full_data)
    
    return _filter_data(full_data, options)


