import json
from utils import try_request, get_user_agent

GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": get_user_agent()
}

API_BASE_URL = "https://api.github.com/users"

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

def get_github_info(username):
    if not username:
        return {"error": "No username provided"}

    user_data, error = _fetch_github_data(username)
    if error:
        return error
    
    followers_data, error = _fetch_github_data(f"{username}/followers")
    if error:
        print(f"Warning: Could not fetch followers for {username}. Error: {error}")
        followers_data = []

    following_data, error = _fetch_github_data(f"{username}/following")
    if error:
        print(f"Warning: Could not fetch following for {username}. Error: {error}")
        following_data = []

    subscriptions_data, error = _fetch_github_data(f"{username}/subscriptions")
    if error:
        print(f"Warning: Could not fetch subscriptions for {username}. Error: {error}")
        subscriptions_data = []

    repos_data, error = _fetch_github_data(f"{username}/repos")
    if error:
        print(f"Warning: Could not fetch repos for {username}. Error: {error}")
        repos_data = []

    final_response = {
        "user_info": _clean_data(user_data),
        "followers": _clean_data(followers_data),
        "following": _clean_data(following_data),
        "subscriptions": _clean_data(subscriptions_data),
        "repos": _clean_data(repos_data)
    }
    
    return final_response
