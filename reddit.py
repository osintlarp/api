import requests
import json
import random
import string
from utils import try_request

url = "https://gql-fed.reddit.com/"

def x_reddit_device_id():
    hex_chars = string.hexdigits.upper()[:16]
    sections = [8, 4, 4, 4, 12]
    parts = [''.join(random.choice(hex_chars) for _ in range(n)) for n in sections]
    return '-'.join(parts)

def reddit_p_device_id():
    hex_chars = string.hexdigits.lower()[:16]
    return ''.join(random.choice(hex_chars) for _ in range(96))

def fetch_reddit_user(username, use_proxies=False, ForceProxy=False):
    headers = {
        "client-vendor-id": x_reddit_device_id(),
        "cookie": "edgebucket=H7RBDpLbhbgfNnhiMR",
        "user-agent": "Reddit/Version 2025.44.0/Build 616760/iOS Version 26.1 (Build 23B85)",
        "device-name": "iPhone17,5",
        "x-apollo-operation-id": "4366cc6caf256da315f9f7451aaea820f389ea7a904d791fc6bd2b13cc72b835",
        "x-reddit-loid": "000000001v22r3g3ka.2.1754421570762.Z0FBQUFBQnBDUU1sRHVlWXU4ejk5Z2dralIwSHlsZWZqenZCWWd2NllVVkFUZ2xwYVlvUFc5M3loeERqNjh5Vml6NktvcUs3VGhwdG1fejAxV1Y1OHNfZlpSQ1Rwa011TGY2Qnk3cGdjbXEzRWRVTkU3YnRldlhjNzNxQWYzallKQk9sdXRiMUJoY2k",
        "x-apollo-operation-name": "GetRedditorByNameApollo",
        "x-reddit-session": "BFa78Ua9Gsgec67e4R.2.1762804212214.51cb8bca167cf02952513682f66ddecaa89750acce409525a32fc538ccd1ddf7-DlWLd0pvEwe1tmcbPEHWAMgplU1FX41GZbMDQvhtLu_W05b_i1DyDAm0liZ1IHGwBZ0QF7WYV6bzv0osgNemyg",
        "x-reddit-width": "390",
        "x-dev-ad-id": "00000000-0000-0000-0000-000000000000",
        "apollographql-client-name": "com.reddit.Reddit-apollo-ios",
        "reddit-user_id": "1v22r3g3ka",
        "priority": "u=3",
        "apollographql-client-version": "2025.44.0-616760",
        "x-reddit-compression": "1",
        "x-reddit-p-device-id": reddit_p_device_id(),
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IlNIQTI1NjpzS3dsMnlsV0VtMjVmcXhwTU40cWY4MXE2OWFFdWFyMnpLMUdhVGxjdWNZIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyIiwiZXhwIjoxNzYyODkwNjEyLjY1NTg2OCwiaWF0IjoxNzYyODA0MjEyLjY1NTg2OCwianRpIjoiWDZJRTl6Nl9Pc0Z4bEpST1AwNHIwb2ZOZmp3YzRBIiwiY2lkIjoiTE5EbzlrMW84VUFFVXciLCJsaWQiOiJ0Ml8xdjIycjNnM2thIiwiYWlkIjoidDJfMXYyMnIzZzNrYSIsImF0IjoxLCJsY2EiOjE3NTQ0MjE1NzA3NjIsInNjcCI6ImVKeGtrZEdPdERBSWhkLUZhNV9nZjVVX20wMXRjWWFzTFFhb2szbjdEVm9jazczeXdQbmF3dkVfWUUyMHdnUWJFVXlRY3ViZXpGVnIzRnZHaXMwVUpzaUNwZEFoc1pBVHk1cElZSUlucWJHOFlRSXEySXpNNVVvNzF0VFNBMkdDeWlWelctaHhhUk9hdTdIbzJZbXJLcGVWQnpYbXFsd2EyN2lGN1lseFptTzFJUlhYNVZRbWFWa29uOFdMZm55bi10WS1mNmJmaFBaa1dGRTFQZEE3Z3FrY240M0ZGOU8wLTN0cTByTjF3YUwyWGc5Uy0xeVAzYlhQbW9WbTVfWnpQSDl0Sk9OeVhKcWZ5ZjdkOVV2b3dDUFB5NHc2Z0JGci1GR0dIVm1IZjlVQlZDNG95VmlDLURRQ3VYTDU5bC1DN1pyMHIzRTc0b3R2UnR6MGh0LWFnWG91UVJ6Nk5MNS1Bd0FBX18tcWVkNF8iLCJyY2lkIjoiOTgzLWJ4d0taZVh6TmFKcEJvRWhDMU5ONGg2REhPMDVIMzFtTmRfSHpPZyIsImZsbyI6MiwiZGEiOnsic3QiOjIsImVjIjozfX0.nPfORWgMbO6ZMj-W2zXbjD3cbKKF1vhiQr7xhseq8gduJkfmQy9L80zrvNQDKfaKfUtsT8jNZl_bygF8hSD1DbZAJ3kSrofu-J35tbPY9VjLNz7AWhG6qyvh7Ktr_wkVj9G7ZP69vuvrYUJRf1yamhdrFM9PKxEzWfDttvgryhELfUCUsk96HsfXEHTDAeL4mFLdzTGuyWGdP5fnWdL8fBFr2qcMMIp9xq_Efu2sdZonDwme3V3Ig6MbgMiy-g_hoE97xnZcWoED1ki_YyedQsPr-SPNDVsEzAdZQfj2o9wlLZCI80f9AGucG3nVdsJkoI41ROXHAnKJ7Wj8fYUWcA",
        "accept-language": "en;q=1",
        "x-reddit-dpr": "3",
        "accept": "multipart/mixed;deferSpec=20220824,application/json",
        "content-type": "application/json",
        "x-apollo-operation-type": "query"
    }

    payload = {
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "4366cc6caf256da315f9f7451aaea820f389ea7a904d791fc6bd2b13cc72b835",
                "version": 1
            }
        },
        "operationName": "GetRedditorByNameApollo",
        "variables": {
            "includeProfile": True,
            "includeVerificationStatus": True,
            "name": username
        }
    }

    response, error = try_request(
        method="post",
        url=url,
        headers=headers,
        json_payload=payload,
        timeout=20,
        use_proxies=use_proxies,
        ForceProxy=ForceProxy
    )

    if error: 
        print(f"Error fetching {username}: {error}")
        return None
    try:
        return response.json()
    except Exception:
        print(f"Invalid JSON response for {username}.")
        return None

def report_reddit_user(redditor_id, site_rule="SPAM_OTHER", reason_type="USERNAME", use_proxies=False, ForceProxy=False):
    headers = {
        "client-vendor-id": x_reddit_device_id(),
        "user-agent": "Reddit/Version 2025.44.0/Build 616760/iOS Version 26.1 (Build 23B85)",
        "device-name": "iPhone17,5",
        "x-apollo-operation-id": "577389bce12d6560ffd3eaa053e16b9ea41d70c9958d14a14ff72b48878c9a84",
        "x-apollo-operation-name": "ReportUserDetails",
        "x-reddit-p-device-id": reddit_p_device_id(),
        "apollographql-client-name": "com.reddit.Reddit-apollo-ios",
        "apollographql-client-version": "2025.44.0-616760",
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IlNIQTI1NjpzS3dsMnlsV0VtMjVmcXhwTU40cWY4MXE2OWFFdWFyMnpLMUdhVGxjdWNZIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyIiwiZXhwIjoxNzYyODkwNjEyLjY1NTg2OCwiaWF0IjoxNzYyODA0MjEyLjY1NTg2OCwianRpIjoiWDZJRTl6Nl9Pc0Z4bEpST1AwNHIwb2ZOZmp3YzRBIiwiY2lkIjoiTE5EbzlrMW84VUFFVXciLCJsaWQiOiJ0Ml8xdjIycjNnM2thIiwiYWlkIjoidDJfMXYyMnIzZzNrYSIsImF0IjoxLCJsY2EiOjE3NTQ0MjE1NzA3NjIsInNjcCI6ImVKeGtrZEdPdERBSWhkLUZhNV9nZjVVX20wMXRjWWFzTFFhb2szbjdEVm9jazczeXdQbmF3dkVfWUUyMHdnUWJFVXlRY3ViZXpGVnIzRnZHaXMwVUpzaUNwZEFoc1pBVHk1cElZSUlucWJHOFlRSXEySXpNNVVvNzF0VFNBMkdDeWlWelctaHhhUk9hdTdIbzJZbXJLcGVWQnpYbXFsd2EyN2lGN1lseFptTzFJUlhYNVZRbWFWa29uOFdMZm55bi10WS1mNmJmaFBaa1dGRTFQZEE3Z3FrY240M0ZGOU8wLTN0cTByTjF3YUwyWGc5Uy0xeVAzYlhQbW9WbTVfWnpQSDl0Sk9OeVhKcWZ5ZjdkOVV2b3dDUFB5NHc2Z0JGci1GR0dIVm1IZjlVQlZDNG95VmlDLURRQ3VYTDU5bC1DN1pyMHIzRTc0b3R2UnR6MGh0LWFnWG91UVJ6Nk5MNS1Bd0FBX18tcWVkNF8iLCJyY2lkIjoiOTgzLWJ4d0taZVh6TmFKcEJvRWhDMU5ONGg2REhPMDVIMzFtTmRfSHpPZyIsImZsbyI6MiwiZGEiOnsic3QiOjIsImVjIjozfX0.nPfORWgMbO6ZMj-W2zXbjD3cbKKF1vhiQr7xhseq8gduJkfmQy9L80zrvNQDKfaKfUtsT8jNZl_bygF8hSD1DbZAJ3kSrofu-J35tbPY9VjLNz7AWhG6qyvh7Ktr_wkVj9G7ZP69vuvrYUJRf1yamhdrFM9PKxEzWfDttvgryhELfUCUsk96HsfXEHTDAeL4mFLdzTGuyWGdP5fnWdL8fBFr2qcMMIp9xq_Efu2sdZonDwme3V3Ig6MbgMiy-g_hoE97xnZcWoED1ki_YyedQsPr-SPNDVsEzAdZQfj2o9wlLZCI80f9AGucG3nVdsJkoI41ROXHAnKJ7Wj8fYUWcA",
        "accept-language": "en;q=1",
        "content-type": "application/json",
        "x-apollo-operation-type": "mutation"
    }

    payload = {
        "extensions": {
            "persistedQuery": {
                "sha256Hash": "577389bce12d6560ffd3eaa053e16b9ea41d70c9958d14a14ff72b48878c9a84",
                "version": 1
            }
        },
        "operationName": "ReportUserDetails",
        "variables": {
            "input": {
                "freeText": None,
                "fromHelpDesk": False,
                "redditorId": redditor_id,
                "siteRule": site_rule,
                "userDetailType": reason_type
            }
        }
    }

    response, error = try_request(
        method="post",
        url=url,
        headers=headers,
        json_payload=payload,
        timeout=20,
        use_proxies=use_proxies,
        ForceProxy=ForceProxy
    )

    if error:
        print(f"[ReportUserDetails] Error: {error}")
        return None
    try:
        return response.json()
    except Exception:
        print("Invalid JSON response for report.")
        return None
