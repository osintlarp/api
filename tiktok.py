from utils import try_request

def get_tiktok_data(username, ForceProxy=True):
    if not username:
        return {"success": False, "error": "Missing 'username' parameter"}, 400

    api_url = "https://tiktok-proxy-6uacic33j-telegram4.vercel.app/api"
    params = {"username": username}

    r, err = try_request(
        method="get",
        url=api_url,
        params=params,
        ForceProxy=ForceProxy
    )

    if err or not r:
        return {"success": False, "error": str(err)}, 500

    try:
        return r.json(), 200
    except Exception:
        return {"success": False, "error": "Invalid JSON response"}, 500
