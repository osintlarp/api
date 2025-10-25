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
        print(f"Loaded and shuffled {len(PROXIES)} proxies.")
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
        "Mozilla/5.o (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (compatible; RedditScraper/3.0)" 
    ]
    return random.choice(user_agents)

def generate_random_token(length=22):
    return ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(length)])

def try_request(method, url, headers=None, json_payload=None, form_data=None, cookies=None, params=None, max_proxy_tries=3, timeout=10):
    if headers is None:
        headers = {'User-Agent': get_user_agent()}
    
    proxy_tries = 0
    
    while PROXIES and proxy_tries < max_proxy_tries:
        proxy = get_next_proxy()
        if not proxy:
            break 
            
        proxy_url = f"http://{proxy}"
        proxies = {"http": proxy_url, "https": proxy_url}
        proxy_tries += 1
        
        try:
            print(f"Trying request with proxy: {proxy_url} (Attempt {proxy_tries}/{max_proxy_tries})")
            r = None
            if method.lower() == "get":
                r = requests.get(url, headers=headers, cookies=cookies, params=params, proxies=proxies, timeout=timeout, allow_redirects=True)
            elif method.lower() == "post":
                if json_payload is not None:
                    r = requests.post(url, headers=headers, cookies=cookies, json=json_payload, proxies=proxies, timeout=timeout, allow_redirects=True)
                elif form_data is not None:
                    r = requests.post(url, headers=headers, cookies=cookies, data=form_data, proxies=proxies, timeout=timeout, allow_redirects=True)
                else:
                    return None, "No payload provided for POST request"
            
            if r is not None:
                if r.status_code == 200:
                    print(f"Request successful with proxy {proxy_url}.")
                    return r, None
                if r.status_code in [403, 401, 404, 429]:
                    print(f"Proxy request got status {r.status_code}. Returning response.")
                    return r, None 
                
                print(f"Proxy {proxy} failed with status {r.status_code}.")
            
        except requests.RequestException as e:
            print(f"Proxy {proxy} failed: {e}")
            continue 
    
    if PROXIES and proxy_tries > 0:
        print(f"All {proxy_tries} proxy attempts failed.")
    elif not PROXIES:
        print("No proxies loaded. Trying request directly.")
    else:
        print("Proxy attempts exhausted.")

    print("Trying request *without* proxy...")
    try:
        r_no_proxy = None
        if method.lower() == "get":
            r_no_proxy = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=timeout, allow_redirects=True)
        elif method.lower() == "post":
            if json_payload is not None:
                r_no_proxy = requests.post(url, headers=headers, cookies=cookies, json=json_payload, timeout=timeout, allow_redirects=True)
            elif form_data is not None:
                r_no_proxy = requests.post(url, headers=headers, cookies=cookies, data=form_data, timeout=timeout, allow_redirects=True)
            else:
                return None, "No payload provided for POST request"
        
        if r_no_proxy is not None:
            if r_no_proxy.status_code == 200:
                print("Request successful without proxy.")
                return r_no_proxy, None
            
            print(f"Final attempt without proxy failed. Status: {r_no_proxy.status_code}")
            return r_no_proxy, None 

    except requests.RequestException as e:
        print(f"Final attempt without proxy failed: {e}")
        return None, f"All attempts failed. Last error: {e}"
