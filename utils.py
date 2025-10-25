import requests
import random
import time
import threading
import os
import string

PROXIES_FILE = "proxies.txt"
PROXIES = []
PROXY_INDEX = 0
_proxy_lock = threading.Lock()

def load_proxies():
    global PROXIES
    if os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [l.strip() for l in f if l.strip()]
        random.shuffle(PROXIES) 
        print(f"Loaded and shuffled {len(PROXIES)} proxies. (Note: try_request is currently NOT using proxies)")
    else:
        PROXIES = []
        print("No proxies.txt file found.")

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
        "Mozilla/5.o (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (compatible; RedditScraper/3.0)" 
    ]
    return random.choice(user_agents)

def generate_random_token(length=22):
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])

def try_request(method, url, headers=None, json_payload=None, form_data=None, cookies=None, params=None, max_proxy_tries=3, timeout=10):
    if headers is None:
        headers = {'User-Agent': get_user_agent()}

    print(f"Attempting direct request to {url}")
    try:
        r = None
        if method.lower() == "get":
            r = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=timeout, allow_redirects=True)
        elif method.lower() == "post":
            if json_payload is not None:
                r = requests.post(url, headers=headers, cookies=cookies, json=json_payload, timeout=timeout, allow_redirects=True)
            elif form_data is not None:
                r = requests.post(url, headers=headers, cookies=cookies, data=form_data, timeout=timeout, allow_redirects=True)
            else:
                return None, "No payload provided for POST request"
        else:
            return None, f"Unsupported request method: {method}"
        
        print(f"Direct request completed with status: {r.status_code}")
        return r, None

    except requests.RequestException as e:
        print(f"Direct request failed: {e}")
        return None, f"Request failed: {e}"
