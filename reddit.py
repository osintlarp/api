import requests
import json
import argparse
from datetime import datetime, timezone
import time
import random
from operator import itemgetter
from utils import try_request, get_oauth_headers

REDDIT_USER_AGENT = "Mozilla/5.0 (compatible; RedditScraper/3.0)"

REDDIT_CLIENT_ID = "yQ1EUQIkXK98dO0rLAMxxg"
REDDIT_CLIENT_SECRET = "srnL8PGmbCba2EY4ELaCZQy77s4sTQ"
REDDIT_USERNAME = "Remarkable_Deer_7685"
REDDIT_PASSWORD = ""

def get_comments(username, after=None):
    url = f"https://www.reddit.com/user/{username}/comments/.json"
    params = {}
    if after:
        params["after"] = after
    headers = get_oauth_headers()
    res, error = try_request("get", url, headers=headers, params=params)
    if error or not res or res.status_code != 200:
        print(f"Failed to fetch comments: {error if error else res.status_code}")
        return None, None
    try:
        data = res.json().get("data", None)
    except json.JSONDecodeError:
        return None, None
    if not data:
        return None, None
    comments = []
    for item in data["children"]:
        c = item["data"]
        comments.append({
            "comment_id": c.get("id"),
            "username": c.get("author"),
            "post_id": c.get("link_id", "").split("_")[1] if "link_id" in c else None,
            "post_title": c.get("link_title",""),
            "subreddit": c.get("subreddit",""),
            "date_created": datetime.fromtimestamp(c.get("created",0), tz=timezone.utc).isoformat(),
            "body": c.get("body",""),
            "score": c.get("score",0),
            "over_18": c.get("over_18"),
            "banned_at_utc": c.get("banned_at_utc"),
            "mod_reason_title": c.get("mod_reason_title"),
            "removal_reason": c.get("removal_reason"),
            "approved_by": c.get("approved_by"),
            "banned_by": c.get("banned_by"),
            "mod_reason_by": c.get("mod_reason_by"),
            "edited": c.get("edited")
        })
    return comments, data.get("after")

def get_submissions(username):
    url = f"https://www.reddit.com/user/{username}/submitted/.json"
    submissions = []
    after = None
    while True:
        params = {"after": after} if after else {}
        headers = get_oauth_headers()
        res, error = try_request("get", url, headers=headers, params=params)
        if error or not res or res.status_code != 200:
            print(f"Failed to fetch submissions: {error if error else res.status_code}")
            break
        try:
            res_json = res.json()
        except json.JSONDecodeError:
            break
        children = res_json.get("data", {}).get("children", [])
        if not children:
            break
        for s in children:
            d = s.get("data", {})
            submissions.append({
                "post_id": d.get("id"),
                "title": d.get("title",""),
                "subreddit": d.get("subreddit",""),
                "score": d.get("score",0),
                "created_utc": datetime.fromtimestamp(d.get("created_utc",0), tz=timezone.utc).isoformat(),
                "domain": d.get("domain","")
            })
        after = res_json.get("data", {}).get("after")
        if not after:
            break
        time.sleep(1)
    return submissions

def run_comments(username, page_limit=None):
    all_comments = []
    after = None
    page = 0
    while True:
        comments, after = get_comments(username, after)
        if not comments:
            break
        all_comments.extend(comments)
        page += 1
        if page_limit and page >= page_limit:
            break
        if not after:
            break
        time.sleep(random.randint(1,3))
    return all_comments

def filter_data(lst, key):
    dic = {}
    for e in lst:
        if key in e:
            dic[e[key]] = dic.get(e[key],0)+1
    return dic

def sort_data(dic):
    return [{"name": k, "count": v} for k,v in sorted(dic.items(), key=itemgetter(1), reverse=True)]

def average(lst):
    return round(float(sum(lst))/len(lst),2) if lst else 0.0

def account_info(username):
    url = f"https://www.reddit.com/user/{username}/about/.json"
    headers = get_oauth_headers()
    res, error = try_request("get", url, headers=headers)
    if error or not res or res.status_code != 200:
        return {"error": f"{error if error else res.status_code}"}
    try:
        d = res.json().get("data", {})
    except json.JSONDecodeError:
        return {"error": "Failed to decode account info"}
    total_karma = int(d.get("comment_karma",0)) + int(d.get("link_karma",0))
    created_ts = d.get("created_utc",0)
    if not created_ts:
        return {"error": "User not found or data incomplete"}
    return {
        "username": d.get("name"),
        "total_karma": total_karma,
        "comment_karma": d.get("comment_karma",0),
        "post_karma": d.get("link_karma",0),
        "created_utc": datetime.fromtimestamp(created_ts, tz=timezone.utc).isoformat(),
        "account_age_days": int((datetime.now(timezone.utc) - datetime.fromtimestamp(created_ts, tz=timezone.utc)).days)
    }

def analyze_user(username, page_limit=None):
    info = account_info(username)
    if info.get("error"):
        return info
    comments = run_comments(username, page_limit)
    submissions = get_submissions(username)
    stats = {
        "top_subreddits_comments": sort_data(filter_data(comments,"subreddit")),
        "top_subreddits_posts": sort_data(filter_data(submissions,"subreddit")),
        "top_domains": sort_data(filter_data(submissions,"domain")),
        "avg_comment_score": average([c["score"] for c in comments]),
        "avg_submission_score": average([s["score"] for s in submissions])
    }
    return {
        "account_info": info,
        "stats": stats,
        "comments": comments,
        "submissions": submissions
    }
