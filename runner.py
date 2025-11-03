import json
import time
import requests
import random
import os
import sys
from datetime import datetime
import threading
import schedule
import logging
import traceback
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RUNNERS_DIR = "/var/www/runners"
PROXIES_FILE = "proxies.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class Runner:
    def __init__(self, runner_id):
        self.runner_id = runner_id
        self.runner_file = os.path.join(RUNNERS_DIR, f"{runner_id}.json")
        self.load_runner_data()
        self.proxies = self.load_proxies()
        self.current_proxy = None
        self.running = True
        self.first_run = True
        self.session = self.create_session()
        self.last_activity = datetime.now()

    def create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def load_runner_data(self):
        with open(self.runner_file, 'r') as f:
            self.runner_data = json.load(f)

    def save_runner_data(self):
        with open(self.runner_file, 'w') as f:
            json.dump(self.runner_data, f, indent=4)

        user_file = os.path.join("/var/www/users", f"{self.runner_data['userID']}.json")
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)

            for runner in user_data.get('runners', []):
                if runner['runnerID'] == self.runner_id:
                    runner['status'] = self.runner_data['status']
                    runner['total_request'] = self.runner_data.get('total_request', 0)
                    runner['last_request'] = self.runner_data.get('last_request')
                    runner['running_since'] = self.runner_data.get('running_since')
                    runner['request_history'] = self.runner_data.get('request_history', [])
                    runner['Changes'] = self.runner_data.get('Changes', [])
                    break

            with open(user_file, 'w') as f:
                json.dump(user_data, f, indent=4)

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
            proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            response = self.session.get('https://www.google.com', proxies=proxies, timeout=10)
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

    def add_request_record(self, status, response_code=None):
        if 'request_history' not in self.runner_data:
            self.runner_data['request_history'] = []
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'response_code': response_code
        }
        
        self.runner_data['request_history'].append(record)
        self.save_runner_data()

    def add_change(self, change):
        if 'Changes' not in self.runner_data:
            self.runner_data['Changes'] = []
        timestamp = datetime.now().isoformat()
        self.runner_data['Changes'].append(f"[{timestamp}] {change}")
        self.save_runner_data()

    def compare_roblox_responses(self, old_response, new_response):
        changes = []
        if old_response.get('display_name') is not None and old_response.get('display_name') != new_response.get('display_name'):
            changes.append(f"display_name changed to '{new_response.get('display_name')}' (was '{old_response.get('display_name')}')")
        if old_response.get('description') is not None and old_response.get('description') != new_response.get('description'):
            changes.append(f"description changed to '{new_response.get('description')}' (was '{old_response.get('description')}')")
        if old_response.get('following') is not None and old_response.get('following') != new_response.get('following'):
            changes.append(f"following changed to {new_response.get('following')} (was {old_response.get('following')})")
        if old_response.get('friends') is not None and old_response.get('friends') != new_response.get('friends'):
            changes.append(f"friends changed to {new_response.get('friends')} (was {old_response.get('friends')})")
        
        old_groups = set([group['name'] for group in old_response.get('groups', [])]) if old_response.get('groups') else set()
        new_groups = set([group['name'] for group in new_response.get('groups', [])]) if new_response.get('groups') else set()
        if old_groups and old_groups != new_groups:
            added = new_groups - old_groups
            removed = old_groups - new_groups
            if added:
                changes.append(f"groups added: {', '.join(added)}")
            if removed:
                changes.append(f"groups removed: {', '.join(removed)}")
        
        old_badges = set(old_response.get('roblox_badges', [])) if old_response.get('roblox_badges') else set()
        new_badges = set(new_response.get('roblox_badges', [])) if new_response.get('roblox_badges') else set()
        if old_badges and old_badges != new_badges:
            added = new_badges - old_badges
            removed = old_badges - new_badges
            if added:
                changes.append(f"badges added: {', '.join(added)}")
            if removed:
                changes.append(f"badges removed: {', '.join(removed)}")
        return changes

    def compare_tiktok_responses(self, old_response, new_response):
        changes = []
        if old_response.get('DisplayName') is not None and old_response.get('DisplayName') != new_response.get('DisplayName'):
            changes.append(f"DisplayName changed to '{new_response.get('DisplayName')}' (was '{old_response.get('DisplayName')}')")
        if old_response.get('Bio') is not None and old_response.get('Bio') != new_response.get('Bio'):
            changes.append(f"Bio changed to '{new_response.get('Bio')}' (was '{old_response.get('Bio')}')")
        if old_response.get('BioLink') is not None and old_response.get('BioLink') != new_response.get('BioLink'):
            changes.append(f"BioLink changed to '{new_response.get('BioLink')}' (was '{old_response.get('BioLink')}')")
        if old_response.get('Country') is not None and old_response.get('Country') != new_response.get('Country'):
            changes.append(f"Country changed to '{new_response.get('Country')}' (was '{old_response.get('Country')}')")
        if old_response.get('Language') is not None and old_response.get('Language') != new_response.get('Language'):
            changes.append(f"Language changed to '{new_response.get('Language')}' (was '{old_response.get('Language')}')")
        if old_response.get('Followers') is not None and old_response.get('Followers') != new_response.get('Followers'):
            changes.append(f"Followers changed to {new_response.get('Followers')} (was {old_response.get('Followers')})")
        if old_response.get('Following') is not None and old_response.get('Following') != new_response.get('Following'):
            changes.append(f"Following changed to {new_response.get('Following')} (was {old_response.get('Following')})")
        if old_response.get('Friends') is not None and old_response.get('Friends') != new_response.get('Friends'):
            changes.append(f"Friends changed to {new_response.get('Friends')} (was {old_response.get('Friends')})")
        if old_response.get('Likes') is not None and old_response.get('Likes') != new_response.get('Likes'):
            changes.append(f"Likes changed to {new_response.get('Likes')} (was {old_response.get('Likes')})")
        if old_response.get('Videos') is not None and old_response.get('Videos') != new_response.get('Videos'):
            changes.append(f"Videos changed to {new_response.get('Videos')} (was {old_response.get('Videos')})")
        if old_response.get('Private') is not None and old_response.get('Private') != new_response.get('Private'):
            old_priv = "Private" if old_response.get('Private') else "Public"
            new_priv = "Private" if new_response.get('Private') else "Public"
            changes.append(f"Account changed from {old_priv} to {new_priv}")
        if old_response.get('Verified') is not None and old_response.get('Verified') != new_response.get('Verified'):
            old_ver = "Verified" if old_response.get('Verified') else "Not Verified"
            new_ver = "Verified" if new_response.get('Verified') else "Not Verified"
            changes.append(f"Verification status changed from {old_ver} to {new_ver}")
        if old_response.get('NewAccount') is not None and old_response.get('NewAccount') != new_response.get('NewAccount'):
            old_new = "New Account" if old_response.get('NewAccount') else "Not New Account"
            new_new = "New Account" if new_response.get('NewAccount') else "Not New Account"
            changes.append(f"Account status changed from {old_new} to {new_new}")
        if old_response.get('NameUpdated') is not None and old_response.get('NameUpdated') != new_response.get('NameUpdated'):
            changes.append(f"NameUpdated changed to '{new_response.get('NameUpdated')}' (was '{old_response.get('NameUpdated')}')")
        if old_response.get('UsernameUpdated') is not None and old_response.get('UsernameUpdated') != new_response.get('UsernameUpdated'):
            changes.append(f"UsernameUpdated changed to '{new_response.get('UsernameUpdated')}' (was '{old_response.get('UsernameUpdated')}')")
        return changes

    def make_request_with_proxy(self, url):
        response = None
        request_status = "Failed"
        response_code = None
        
        try:
            if self.current_proxy:
                proxies = {'http': f'http://{self.current_proxy}', 'https': f'http://{self.current_proxy}'}
                try:
                    response = self.session.get(url, proxies=proxies, timeout=30)
                except requests.exceptions.RequestException:
                    self.current_proxy = self.find_working_proxy()
                    if self.current_proxy:
                        return self.make_request_with_proxy(url)
                    else:
                        response = self.session.get(url, timeout=30)
            else:
                response = self.session.get(url, timeout=30)
                
            response_code = response.status_code
            if response_code == 200:
                request_status = "Successful"
            elif response_code == 429:
                request_status = "Rate-Limited"
            else:
                request_status = "Failed"
                    
            self.runner_data['last_request'] = datetime.now().isoformat()
            self.runner_data['total_request'] = self.runner_data.get('total_request', 0) + 1
            self.save_runner_data()
        except Exception as e:
            logging.error(f"Request error: {e}")
            request_status = "Failed"
        
        self.add_request_record(request_status, response_code)
        return response

    def roblox_monitoring_job(self):
        try:
            self.last_activity = datetime.now()
            username = self.runner_data['usernameID']
            roblox_url = f"https://api.vaul3t.org/v1/osint/roblox?username={username}&cache=false"
            response = self.make_request_with_proxy(roblox_url)
            if response and response.status_code == 200:
                current_data = response.json()
                if 'cache' in self.runner_data and not self.first_run:
                    changes = self.compare_roblox_responses(self.runner_data['cache'], current_data)
                    for change in changes:
                        self.add_change(change)
                self.runner_data['cache'] = current_data
                self.save_runner_data()
                if 'user_id' in current_data:
                    avatar_url = f"https://avatar.roblox.com/v1/users/{current_data['user_id']}/avatar"
                    avatar_response = self.make_request_with_proxy(avatar_url)
                    if avatar_response and avatar_response.status_code == 200:
                        avatar_data = avatar_response.json()
                        if 'avatar_cache' in self.runner_data and not self.first_run:
                            avatar_changes = self.compare_roblox_responses(self.runner_data['avatar_cache'], avatar_data)
                            for change in avatar_changes:
                                self.add_change(f"Avatar: {change}")
                        self.runner_data['avatar_cache'] = avatar_data
                        self.save_runner_data()
            self.update_status('Active')
            self.first_run = False
            logging.info(f"Roblox monitoring completed for {username}")
        except Exception as e:
            logging.error(f"Error in Roblox monitoring: {e}")
            logging.error(traceback.format_exc())
            self.add_change(f"Error: {str(e)}")
            self.update_status('Error')
            self.first_run = False

    def tiktok_monitoring_job(self):
        try:
            self.last_activity = datetime.now()
            username = self.runner_data['usernameID']
            clean_username = username.replace('@', '')
            tiktok_url = f"https://api.vaul3t.org/v1/osint/tiktok?username={clean_username}&cache=false"
            response = self.make_request_with_proxy(tiktok_url)
            if response and response.status_code == 200:
                current_data = response.json()
                if 'cache' in self.runner_data and not self.first_run:
                    changes = self.compare_tiktok_responses(self.runner_data['cache'], current_data)
                    for change in changes:
                        self.add_change(change)
                self.runner_data['cache'] = current_data
                self.save_runner_data()
            elif response and response.status_code != 200:
                self.add_change(f"TikTok API returned status code: {response.status_code}")
            self.update_status('Active')
            self.first_run = False
            logging.info(f"TikTok monitoring completed for {username}")
        except Exception as e:
            logging.error(f"Error in TikTok monitoring: {e}")
            logging.error(traceback.format_exc())
            self.add_change(f"Error: {str(e)}")
            self.update_status('Error')
            self.first_run = False

    def health_check(self):
        time_since_last = datetime.now() - self.last_activity
        if time_since_last.total_seconds() > 600:
            logging.warning(f"Runner {self.runner_id} appears stuck - restarting job")
            if self.runner_data['service'] == 'Roblox':
                self.roblox_monitoring_job()
            elif self.runner_data['service'] == 'TikTok':
                self.tiktok_monitoring_job()

    def start_scheduler(self):
        interval = int(self.runner_data['request_every'])
        if self.runner_data['service'] == 'Roblox':
            schedule.every(interval).minutes.do(self.roblox_monitoring_job)
        elif self.runner_data['service'] == 'TikTok':
            schedule.every(interval).minutes.do(self.tiktok_monitoring_job)
        
        schedule.every(10).minutes.do(self.health_check)
        
        self.current_proxy = self.find_working_proxy()
        self.update_status('Active')
        logging.info(f"Started {self.runner_data['service']} runner for {self.runner_data['usernameID']} every {interval} minutes")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
                logging.error(traceback.format_exc())
                time.sleep(60)

def start_runner(runner_id):
    try:
        runner = Runner(runner_id)
        runner.start_scheduler()
    except Exception as e:
        logging.error(f"Failed to start runner {runner_id}: {e}")
        logging.error(traceback.format_exc())

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
            logging.info(f"Started runner thread for {runner_id}")
        
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logging.info("Shutting down runners...")
            for thread in threads:
                thread.join(timeout=5)

if __name__ == "__main__":
    main()
