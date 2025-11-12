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
    client_vendor_id = generate_uuid()
    reddit_device_id = client_vendor_id  
    reddit_p_id = reddit_p_device_id()

    headers = {
        "client-vendor-id": client_vendor_id,
        "user-agent": "Reddit/Version 2025.44.0/Build 616760/iOS Version 26.1 (Build 23B85)",
        "device-name": "iPhone17,5",
        "x-apollo-operation-id": "4366cc6caf256da315f9f7451aaea820f389ea7a904d791fc6bd2b13cc72b835",
        "x-reddit-loid": "0000000021pen6hl4f.2.1762805671832.Z0FBQUFBQnBFa2Z4NnhzNGpfbFZKSnFaR1R1Mmc2XzhaZlBvOHZkZ3FrdnJCTktfVkxsZHo3OHpUd0NPNTF3aTBxOGJPUndHeV90TGdKemdIaFJIRmhrVXBJZnd4X250Y201TmR0N2Zia05IdzA5QXo4T3U5bHdSNTYwME40bmU0dHdqWXozNDBTSkk",
        "x-apollo-operation-name": "GetRedditorByNameApollo",
        "x-reddit-session": "dTJrL56ShilKprgAOO.2.1762938428995.51cb8bca167cf02952513682f66ddecaa89750acce409525a32fc538ccd1ddf7-aPG5EqecwrtOo_TTXWfRydAfdduGPpdqdQDmvT3BccVuKZryyOLvRJhoRvzxfLoSErXfNarBLi5bRsDKutLY3g",
        "x-reddit-width": "390",
        "x-dev-ad-id": "00000000-0000-0000-0000-000000000000",
        "apollographql-client-name": "com.reddit.Reddit-apollo-ios",
        "reddit-user_id": "21pen6hl4f",
        "priority": "u=3",
        "apollographql-client-version": "2025.44.0-616760",
        "x-reddit-compression": "1",
        "x-reddit-p-device-id": reddit_p_id,
        "authorization": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IlNIQTI1NjpzS3dsMnlsV0VtMjVmcXhwTU40cWY4MXE2OWFFdWFyMnpLMUdhVGxjdWNZIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyIiwiZXhwIjoxNzYyOTc3NzY3LjQ1MjY3NSwiaWF0IjoxNzYyODkxMzY3LjQ1MjY3NSwianRpIjoidU9JcVRNaGdIZlpsR1A1Y29oQmgxX180elQ2cFFnIiwiY2lkIjoiTE5EbzlrMW84VUFFVXciLCJsaWQiOiJ0Ml8yMXBlbjZobDRmIiwiYWlkIjoidDJfMjFwZW42aGw0ZiIsImF0IjoxLCJsY2EiOjE3NjI4MDU2NzE4MzIsInNjcCI6ImVKeGtrZEdPdERBSWhkLUZhNV9nZjVVX20wMXRjWWFzTFFhb2szbjdEVm9jazczeXdQbmF3dkVfWUUyMHdnUWJFVXlRY3ViZXpGVnIzRnZHaXMwVUpzaUNwZEFoc1pBVHk1cElZSUlucWJHOFlRSXEySXpNNVVvNzF0VFNBMkdDeWlWelctaHhhUk9hdTdIbzJZbXJLcGVWQnpYbXFsd2EyN2lGN1lseFptTzFJUlhYNVZRbWFWa29uOFdMZm55bi10WS1mNmJmaFBaa1dGRTFQZEE3Z3FrY240M0ZGOU8wLTN0cTByTjF3YUwyWGc5Uy0xeVAzYlhQbW9WbTVfWnpQSDl0Sk9OeVhKcWZ5ZjdkOVV2b3dDUFB5NHc2Z0JGci1GR0dIVm1IZjlVQlZDNG95VmlDLURRQ3VYTDU5bC1DN1pyMHIzRTc0b3R2UnR6MGh0LWFnWG91UVJ6Nk5MNS1Bd0FBX18tcWVkNF8iLCJyY2lkIjoiQXMzMTdNSkhmemM4RGxYNnh5X1dhMTlHR3hvSXUtV3lHaFB6V0tUYzI4WSIsImZsbyI6MiwiZGEiOnsic3QiOjEsImFhdCI6MTc2Mjg5MTM2N319.V33mASl6mW1tGNRKW531S6Q7Ok6g3DTz13Ypp8L2QsvuWS_Xu7QhNBLmyCOdxK7DNomeqy2G6HUKqlHw4Fzyywf3eOpm7bqjfQyzShicvQc4lzjGdN6Dxj6wUYhwkQt2dMr3tY4itAY6VDawMNc4Ko4bbCCILZY4rfDAtkSHU8Ey40PTzmJr1MyRgwL4fgV3202oOtMegVeUmIXlAWuRHXVrLFQSce_w-681ekgJ7EjQPS4CkqbP9yDp9m6fc6CWiGw0cDWpI1nKisTyjgjR0JS_vHgU_eBA3c8RHFqvl9i8xMxZ0Im4ciJrZvAVfrpysHXys5BncHJpRyCxLdrZ-g",
        "accept-language": "en;q=1",
        "x-reddit-device-id": reddit_device_id,
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
            "includeVerificationStatus": False,
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
        print(f"[fetch_reddit_user] Error fetching {username}: {error}")
        return None

    try:
        return response.json()
    except Exception:
        print(f"Invalid JSON response for {username}")
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
