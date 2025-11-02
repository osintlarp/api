import json
import time
import requests
import random
import os
import sys
from datetime import datetime
import threading
import schedule

RUNNERS_DIR = "/var/www/runners"
PROXIES_FILE = "proxies.txt"

class Runner:
    def __init__(self, runner_id):
        self.runner_id = runner_id
        self.runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
        self.load_runner_data()
        self.proxies = self.load_proxies()
        self.current_proxy = None
        self.running = True
        
    def load_runner_data(self):
        with open(self.runner_file, 'r') as f:
            self.runner_data = json.load(f)
            
    def save_runner_data(self):
        with open(self.runner_file, 'w') as f:
            json.dump(self.runner_data, f, indent=4)
            
    def load_proxies(self):
        if os.path.exists(PROXIES_FILE):
            with open(PROXIES_FILE, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        return []
    
    def get_random_proxy(self):
        if self.proxies:
            return random.choice(self.proxies)
        return None
    
    def test_proxy(self, proxy):
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            response = requests.get('https://www.google.com', proxies=proxies, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def find_working_proxy(self):
        for proxy in self.proxies:
            if self.test_proxy(proxy):
                return proxy
        return None
    
    def update_status(self, status):
        self.runner_data['status'] = status
        self.save_runner_data()
        
        user_file = os.path.join("/var/www/users", f"{self.runner_data['userID']}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            
            for runner in user_data.get('runners', []):
                if runner['runnerID'] == self.runner_id:
                    runner['status'] = status
                    break
            
            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=4)
    
    def add_change(self, change):
        if 'Changes' not in self.runner_data:
            self.runner_data['Changes'] = []
        
        timestamp = datetime.now().isoformat()
        self.runner_data['Changes'].append(f"[{timestamp}] {change}")
        self.save_runner_data()
    
    def compare_responses(self, old_response, new_response):
        changes = []
        
        if old_response.get('followers') != new_response.get('followers'):
            changes.append(f"followers Changed value to {new_response.get('followers')} = last value {old_response.get('followers')}")
        
        if old_response.get('following') != new_response.get('following'):
            changes.append(f"following Changed value to {new_response.get('following')} = last value {old_response.get('following')}")
        
        if old_response.get('friends') != new_response.get('friends'):
            changes.append(f"friends Changed value to {new_response.get('friends')} = last value {old_response.get('friends')}")
        
        old_groups = set([group['name'] for group in old_response.get('groups', [])])
        new_groups = set([group['name'] for group in new_response.get('groups', [])])
        
        if old_groups != new_groups:
            added = new_groups - old_groups
            removed = old_groups - new_groups
            if added:
                changes.append(f"groups Added: {', '.join(added)}")
            if removed:
                changes.append(f"groups Removed: {', '.join(removed)}")
        
        old_badges = set(old_response.get('roblox_badges', []))
        new_badges = set(new_response.get('roblox_badges', []))
        
        if old_badges != new_badges:
            added = new_badges - old_badges
            removed = old_badges - new_badges
            if added:
                changes.append(f"badges Added: {', '.join(added)}")
            if removed:
                changes.append(f"badges Removed: {', '.join(removed)}")
        
        return changes
    
    def make_request_with_proxy(self, url):
        if self.current_proxy:
            proxies = {
                'http': f'http://{self.current_proxy}',
                'https': f'http://{self.current_proxy}'
            }
            try:
                response = requests.get(url, proxies=proxies, timeout=30)
                return response
            except requests.exceptions.RequestException:
                self.current_proxy = self.find_working_proxy()
                if self.current_proxy:
                    return self.make_request_with_proxy(url)
                else:
                    return requests.get(url, timeout=30)
        else:
            return requests.get(url, timeout=30)
    
    def roblox_monitoring_job(self):
        try:
            username = self.runner_data['usernameID']
            
            roblox_url = f"https://api.vaul3t.org/v1/osint/roblox?username={username}&cache=false"
            response = self.make_request_with_proxy(roblox_url)
            
            if response.status_code == 200:
                current_data = response.json()
                
                if 'cache' in self.runner_data:
                    changes = self.compare_responses(self.runner_data['cache'], current_data)
                    for change in changes:
                        self.add_change(change)
                
                self.runner_data['cache'] = current_data
                self.save_runner_data()
                
                if 'user_id' in current_data:
                    avatar_url = f"https://avatar.roblox.com/v1/users/{current_data['user_id']}/avatar"
                    avatar_response = self.make_request_with_proxy(avatar_url)
                    
                    if avatar_response.status_code == 200:
                        avatar_data = avatar_response.json()
                        
                        if 'avatar_cache' in self.runner_data:
                            avatar_changes = self.compare_responses(self.runner_data['avatar_cache'], avatar_data)
                            for change in avatar_changes:
                                self.add_change(f"Avatar: {change}")
                        
                        self.runner_data['avatar_cache'] = avatar_data
                        self.save_runner_data()
            
            self.update_status('Active')
            
        except Exception as e:
            print(f"Error in Roblox monitoring: {e}")
            self.add_change(f"Error: {str(e)}")
            self.update_status('Error')
    
    def start_scheduler(self):
        interval = int(self.runner_data['request_every'])
        
        if self.runner_data['service'] == 'Roblox':
            schedule.every(interval).minutes.do(self.roblox_monitoring_job)
        
        self.current_proxy = self.find_working_proxy()
        if self.current_proxy:
            print(f"Using proxy: {self.current_proxy}")
            self.update_status('Active')
        else:
            print("No working proxy found, running without proxy")
            self.update_status('Active')
        
        while self.running:
            schedule.run_pending()
            time.sleep(1)

def start_runner(runner_id):
    runner = Runner(runner_id)
    runner.start_scheduler()

def load_all_runners():
    if not os.path.exists(RUNNERS_DIR):
        os.makedirs(RUNNERS_DIR)
        return []
    
    runners = []
    for filename in os.listdir(RUNNERS_DIR):
        if filename.endswith('.json'):
            runner_id = filename[:-5]
            runners.append(runner_id)
    return runners

def main():
    if len(sys.argv) > 1:
        runner_id = sys.argv[1]
        start_runner(runner_id)
    else:
        runners = load_all_runners()
        threads = []
        
        for runner_id in runners:
            thread = threading.Thread(target=start_runner, args=(runner_id,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            print(f"Started runner: {runner_id}")
        
        print(f"Total runners running: {len(runners)}")
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Stopping all runners...")

if __name__ == "__main__":
    main()
