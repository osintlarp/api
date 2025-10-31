import os, re, json, requests, pycountry
from datetime import datetime, timezone
from utils import try_request

CACHE_FOLDER_CY = "_CACHE_TIKTOK_CY_"
URI_BASE = "https://www.tiktok.com/"

os.makedirs(CACHE_FOLDER_CY, exist_ok=True)

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

def get_language_name(code):
    if not code: return "N/A"
    try:
        l = pycountry.languages.get(alpha_2=code.lower())
        return l.name
    except:
        return code.upper()

def get_country_name(code):
    if not code: return "N/A"
    try:
        c = pycountry.countries.get(alpha_2=code.upper())
        return c.name
    except:
        return code.upper()

def get_country_flag(code):
    if not code or len(code) != 2: return ""
    try:
        return ''.join([chr(0x1F1E6 + ord(c.upper()) - ord('A')) for c in code])
    except:
        return ""

def convert_timestamp(ts):
    if not ts: return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d %b %Y %H:%M")

def fetch_tiktok_html(identifier):
    headers = {"user-agent": "Mozilla/5.0 (compatible; Google-Apps-Script)"}
    r = requests.get(f"{URI_BASE}@{identifier}/?lang=en", headers=headers)
    return r.text

def extract_json(html):
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', html)
    return json.loads(m.group(1)) if m else {}

def get_country_from_api(username, ForceProxy=False):
    api = "https://tiktok-proxy-6uacic33j-telegram4.vercel.app/api"
    params = {"username": username}
    r, err = try_request("get", api, params=params, ForceProxy=ForceProxy)
    if not r: return None
    try:
        return r.json().get("data", {}).get("country")
    except:
        return None

def get_tiktok_data(username, ForceProxy=False):
    u = username.lstrip("@").lower()
    cache_cy = os.path.join(CACHE_FOLDER_CY, f"{u}.json")

    try:
        html = fetch_tiktok_html(u)
        json_data = extract_json(html)
        user_info = json_data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        user = user_info["user"]
        stats = user_info["stats"]
    except:
        cc = load_cache(cache_cy)
        if cc:
            return {"username": u, "country": cc["country"], "usingCache": True}, 200
        return {"success": False, "error": "Failed to fetch user"}, 500

    country = get_country_from_api(u, ForceProxy)
    using_cache = False
    if not country:
        cc = load_cache(cache_cy)
        if cc:
            country = cc["country"]
            using_cache = True

    if country:
        save_cache(cache_cy, {"username": u, "country": country})

    region = user.get("region")
    lang = get_language_name(user.get("language"))
    country_name = get_country_name(region)
    flag = get_country_flag(region)

    create_time = user.get("createTime")
    account_age = (datetime.now(timezone.utc) - datetime.fromtimestamp(create_time, timezone.utc)) if create_time else None
    is_new = account_age.days <= 30 if account_age else False

    data = {
        "ID": user["id"],
        "Username": f"@{user['uniqueId']}",
        "DisplayName": user["nickname"],
        "Bio": user["signature"] or "No bio",
        "BioLink": user.get("bioLink", {}).get("link", "N/A"),
        "Country": country or f"{country_name} {flag}",
        "Language": lang,
        "Verified": user["verified"],
        "Private": user["privateAccount"],
        "Created": convert_timestamp(user.get("createTime")),
        "NameUpdated": convert_timestamp(user.get("nickNameModifyTime")),
        "UsernameUpdated": convert_timestamp(user.get("uniqueIdModifyTime")),
        "Following": stats["followingCount"],
        "Followers": stats["followerCount"],
        "Videos": stats["videoCount"],
        "Likes": stats["heartCount"],
        "Friends": stats["friendCount"],
        "Profile": f"{URI_BASE}@{user['uniqueId']}",
        "Avatar": user.get("avatarLarger", "N/A"),
        "NewAccount": is_new,
        "usingCache": using_cache
    }

    return data, 200
