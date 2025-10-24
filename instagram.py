import json
import collections
from bs4 import BeautifulSoup
from utils import try_request, get_user_agent

collections.Callable = collections.abc.Callable

def _tiny_url(url):
    apiurl = "http://tinyurl.com/api-create.php?url="
    r, err = try_request("get", apiurl + url)
    if not err and r:
        return r.text
    return url

def _extract_hash_tags(stri):
    return [part[1:] for part in stri.split() if part.startswith("#")]

def get_instagram_info(username):
    profile_url = f"https://www.instagram.com/{username}"
    headers = {"User-Agent": get_user_agent()}
    
    profile_page_html, err = try_request("get", profile_url, headers=headers)
    if err:
        return {'error': err}
    if not profile_page_html:
        return {'error': 'Failed to retrieve Instagram profile page.'}

    soup = BeautifulSoup(profile_page_html.text, "html.parser")
    more_data_scripts = soup.find_all("script", attrs={"type": "text/javascript"})
    
    data = None
    try:
        for script in more_data_scripts:
            if script.string and script.string.startswith('window._sharedData ='):
                json_text = script.string[21:].strip(';')
                data = json.loads(json_text)
                break
        
        if not data:
             return {'error': 'Could not find profile data JSON on page. Instagram structure may have changed.'}
        
        p_data = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]
    except Exception as e:
        print(f"Error parsing Instagram JSON: {e}")
        return {'error': 'Failed to parse Instagram data. Page structure may have changed.'}

    user_info = {
        "username": p_data.get("username"),
        "name": p_data.get("full_name"),
        "url": f"instagram.com/{p_data.get('username')}",
        "followers": p_data.get("edge_followed_by", {}).get("count"),
        "following": p_data.get("edge_follow", {}).get("count"),
        "posts": p_data.get("edge_owner_to_timeline_media", {}).get("count"),
        "bio": p_data.get("biography", "").replace("\n", ", "),
        "external_url": p_data.get("external_url"),
        "is_private": p_data.get("is_private"),
        "is_verified": p_data.get("is_verified"),
        "profile_pic_url": _tiny_url(p_data.get("profile_pic_url_hd")),
        "is_business_account": p_data.get("is_business_account"),
        "connected_fb_page": p_data.get("connected_fb_page"),
        "is_joined_recently": p_data.get("is_joined_recently"),
        "business_category_name": p_data.get("business_category_name"),
    }

    raw_tags = []
    tag_lis = []
    posts = []
    
    if not user_info["is_private"]:
        try:
            for post_edge in p_data.get("edge_owner_to_timeline_media", {}).get("edges", []):
                post = post_edge.get("node", {})
                caption = ""
                
                try:
                    caption_node = post.get("edge_media_to_caption", {}).get("edges", [{}])[0].get("node", {})
                    caption = caption_node.get("text", "")
                    raw_tags.append(_extract_hash_tags(caption))
                except IndexError:
                    pass
                
                post_data = {
                    "picture_url": _tiny_url(post.get("thumbnail_resources", [{}])[0].get("src")),
                    "caption": caption,
                    "comments": post.get("edge_media_to_comment", {}).get("count"),
                    "comments_disabled": post.get("comments_disabled"),
                    "timestamp": post.get("taken_at_timestamp"),
                    "likes": post.get("edge_liked_by", {}).get("count"),
                    "location": post.get("location"),
                    "accessibility_caption": post.get("accessibility_caption"),
                    "post_url": f"https://instagram.com/p/{post.get('shortcode')}"
                }
                posts.append(post_data)

            for tag_group in raw_tags:
                tag_lis.extend(tag_group)
            
            common_tags = dict(collections.Counter(tag_lis).most_common(10))

        except Exception as e:
            print(f"Error parsing Instagram posts: {e}")
            
    return {
        "user_info": user_info,
        "most_used_tags": common_tags if 'common_tags' in locals() else {},
        "posts": posts
    }
