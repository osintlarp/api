import os, json
from utils import try_request

CACHE_FOLDER_OS = "_CACHE_INSTAGRAM_OS_"
os.makedirs(CACHE_FOLDER_OS, exist_ok=True)

def load_cache(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
    return None

def save_cache(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def fetch_instagram_data(username):
    if not username:
        return {"success": False, "error": "Missing username parameter"}, 400

    cache_file = os.path.join(CACHE_FOLDER_OS, f"{username}.json")

    url = "https://instagram.sujrb.workers.dev/api"
    params = {"username": username}

    r, err = try_request("get", url, params=params)

    if err or not r:
        cached = load_cache(cache_file)
        if cached:
            cached["usingCache"] = True
            return cached, 200
        return {"success": False, "error": "Failed to fetch data"}, 500

    try:
        data = r.json()
        data["usingCache"] = False
        save_cache(cache_file, data)
    except:
        cached = load_cache(cache_file)
        if cached:
            cached["usingCache"] = True
            return cached, 200
        return {"success": False, "error": "Invalid JSON response"}, 500

    return data, 200
