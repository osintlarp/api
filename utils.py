import requests
import random
import time
import threading
from requests.auth import HTTPBasicAuth

PROXIES_FILE = "proxies.txt"
PROXIES = []
PROXY_INDEX = 0
_proxy_lock = threading.Lock()

def load_proxies():
    global PROXIES
    try:
        with open(PROXIES_FILE, "r", encoding="utf-8") as f:
            PROXIES = [l.strip() for l in f if l.strip()]
    except:
        PROXIES = []

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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
    ]
    return random.choice(user_agents)


def try_request(method, url, headers=None, json_payload=None, form_data=None, cookies=None, params=None, max_retries=3, timeout=15, use_proxies=False):
    if headers is None:
        headers = {}
    if not any(k.lower() == "authorization" for k in headers.keys()):
        oauth_h = get_oauth_headers()
        oauth_h.update(headers)
        headers = oauth_h
    retries = 0
    while retries < max_retries:
        try:
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
                return None, "Unsupported method"
            return r, None
        except requests.RequestException:
            retries += 1
            time.sleep(1)
    if use_proxies and PROXIES:
        for _ in range(len(PROXIES)):
            proxy = get_next_proxy()
            if not proxy:
                continue
            proxy_url = f"http://{proxy}"
            proxies = {"http": proxy_url, "https": proxy_url}
            try:
                if method.lower() == "get":
                    r = requests.get(url, headers=headers, cookies=cookies, params=params, proxies=proxies, timeout=timeout, allow_redirects=True)
                elif method.lower() == "post":
                    if json_payload is not None:
                        r = requests.post(url, headers=headers, cookies=cookies, json=json_payload, proxies=proxies, timeout=timeout, allow_redirects=True)
                    elif form_data is not None:
                        r = requests.post(url, headers=headers, cookies=cookies, data=form_data, proxies=proxies, timeout=timeout, allow_redirects=True)
                    else:
                        continue
                return r, None
            except requests.RequestException:
                continue
    return None, "All retries/proxies failed"
