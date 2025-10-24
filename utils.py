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
        print(f"Loaded {len(PROXIES)} proxies.")
    else:
        PROXIES = []
        print("No proxies.txt file found, running without proxies.")

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
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return random.choice(user_agents)

def generate_random_token(length=22):
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])

def try_request(method, url, headers=None, json_payload=None, form_data=None, params=None, max_retries=3, timeout=15):
    if headers is None:
        headers = {'User-Agent': get_user_agent()}
    
    retries = 0
    while retries < max_retries:
        try:
            if method.lower() == "get":
                r = requests.get(url, headers=headers, params=params, timeout=timeout, allow_redirects=True)
            elif method.lower() == "post":
                if json_payload is not None:
                    r = requests.post(url, headers=headers, json=json_payload, timeout=timeout, allow_redirects=True)
                elif form_data is not None:
                    r = requests.post(url, headers=headers, data=form_data, timeout=timeout, allow_redirects=True)
                else:
                    return None, "No payload provided for POST request"
            else:
                return None, "Unsupported method"
            
            if r.status_code == 200:
                return r, None
            
            print(f"Request failed (Status {r.status_code}), retrying...")
            retries += 1
            time.sleep(2)
            
        except requests.RequestException as e:
            print(f"Request exception: {e}, retrying...")
            retries += 1
            time.sleep(2)
            continue

    if not PROXIES:
        return None, f"All retries failed. Last status: {r.status_code if 'r' in locals() else 'No response'}"

    for i in range(len(PROXIES)):
        proxy = get_next_proxy()
        if not proxy:
            continue
            
        proxy_url = f"http://{proxy}"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        try:
            if method.lower() == "get":
                r = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout, allow_redirects=True)
            elif method.lower() == "post":
                if json_payload is not None:
                    r = requests.post(url, headers=headers, json=json_payload, proxies=proxies, timeout=timeout, allow_redirects=True)
                elif form_data is not None:
                    r = requests.post(url, headers=headers, data=form_data, proxies=proxies, timeout=timeout, allow_redirects=True)
                
            if r.status_code == 200:
                print("Request successful with proxy.")
                return r, None
                
        except requests.RequestException as e:
            print(f"Proxy {proxy} failed: {e}")
            continue
            
    return None, "All proxies failed"
