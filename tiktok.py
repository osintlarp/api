import os
import json
import time
from utils import try_request

CACHE_FOLDER_OS = "_CACHE_TIKTOK_OS_"
CACHE_FOLDER_CY = "_CACHE_TIKTOK_CY_"
CACHE_EXPIRY = 3600

os.makedirs(CACHE_FOLDER_OS, exist_ok=True)
os.makedirs(CACHE_FOLDER_CY, exist_ok=True)

def load_cache(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def save_cache(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_tiktok_data(username, ForceProxy=False, use_cache=True):
    cache_file_os = os.path.join(CACHE_FOLDER_OS, f"{username}.json")
    cache_file_cy = os.path.join(CACHE_FOLDER_CY, f"{username}.json")

    data_os = None
    if use_cache:
        data_os = load_cache(cache_file_os)
        if data_os and time.time() - data_os.get("_timestamp_", 0) > CACHE_EXPIRY:
            data_os = None
        elif data_os:
            data_os["usingCache"] = True
            data_os["cache"] = True
            country = data_os.get("data", {}).get("country")
            if country:
                save_cache(cache_file_cy, {"username": username, "country": country})
            return data_os, 200

    api_url = "https://tiktok-proxy-6uacic33j-telegram4.vercel.app/api"
    params = {"username": username}
    r, err = try_request(method="get", url=api_url, params=params, ForceProxy=ForceProxy)
    if err or not r:
        cached_country = load_cache(cache_file_cy)
        if cached_country:
            response = cached_country.copy()
            response["usingCache"] = True
            response["cache"] = True
            return response, 200
        return {"success": False, "error": str(err)}, 500

    try:
        data_os = r.json()
        data_os["_timestamp_"] = time.time()
        data_os["usingCache"] = False
        data_os["cache"] = False
        save_cache(cache_file_os, data_os)

        country = data_os.get("data", {}).get("country")
        if country:
            save_cache(cache_file_cy, {"username": username, "country": country})
        else:
            cached_country = load_cache(cache_file_cy)
            if cached_country:
                data_os["data"]["country"] = cached_country["country"]
                data_os["usingCache"] = True

        return data_os, 200
    except Exception:
        cached_country = load_cache(cache_file_cy)
        if cached_country:
            response = cached_country.copy()
            response["usingCache"] = True
            response["cache"] = True
            return response, 200
        return {"success": False, "error": "Invalid JSON response"}, 500
