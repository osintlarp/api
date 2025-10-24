import json
import re
from collections import Counter
from utils import try_request, get_user_agent

def sort_list(item_list):
    if not item_list:
        return {}
    return dict(Counter(item_list).most_common())

def find_details(text_blob):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text_blob)
    tags = re.findall(r'#(\w+)', text_blob)
    mentions = re.findall(r'@(\w+)', text_blob)
    
    return {
        'emails': list(set(emails)),
        'tags': sort_list(tags),
        'mentions': sort_list(mentions)
    }

def get_instagram_info(username):
    url = f'https://www.instagram.com/{username}/?__a=1'
    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'application/json'
    }
    
    r, err = try_request("get", url, headers=headers)
    
    if err:
        return {'error': err}
    if not r:
        return {'error': 'Failed to retrieve Instagram data'}

    try:
        data = r.json()
    except json.JSONDecodeError:
        return {'error': 'Failed to decode Instagram response. The API may be blocked or changed.'}

    if 'graphql' not in data or 'user' not in data['graphql']:
        return {'error': 'User not found or invalid response structure'}

    js = data['graphql']['user']
    
    is_private = js.get('is_private', False)
    
    usrinfo = {
        'username': js.get('username'),
        'user_id': js.get('id'),
        'name': js.get('full_name'),
        'followers': js.get('edge_followed_by', {}).get('count'),
        'following': js.get('edge_follow', {}).get('count'),
        'posts_media_count': js.get('edge_owner_to_timeline_media', {}).get('count'),
        'posts_video_count': js.get('edge_felix_video_timeline', {}).get('count'),
        'reels_count': js.get('highlight_reel_count'),
        'bio': js.get('biography', '').replace('\n', ', '),
        'external_url': js.get('external_url'),
        'is_private': is_private,
        'is_verified': js.get('is_verified'),
        'profile_pic_url': js.get('profile_pic_url_hd'),
        'is_business_account': js.get('is_business_account'),
        'is_joined_recently': js.get('is_joined_recently'),
        'business_category_name': js.get('business_category_name'),
        'category_enum': js.get('category_enum'),
        'has_guides': js.get('has_guides'),
    }

    text_blob = str(data)
    extracted_details = find_details(text_blob)
    
    usrinfo['extracted_emails'] = extracted_details['emails']
    usrinfo['extracted_tags'] = extracted_details['tags']
    usrinfo['extracted_mentions'] = extracted_details['mentions']
    
    posts = []
    if not is_private:
        total_uploads = js.get('edge_owner_to_timeline_media', {}).get('count', 0)
        max_posts_to_fetch = min(total_uploads, 12) 
        
        edges = js.get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        for i in range(min(len(edges), max_posts_to_fetch)):
            node = edges[i].get('node', {})
            post_info = {}
            child_media_list = []

            post_details = {
                'comments_count': node.get('edge_media_to_comment', {}).get('count'),
                'comments_disabled': node.get('comments_disabled'),
                'timestamp': node.get('taken_at_timestamp'),
                'likes_count': node.get('edge_liked_by', {}).get('count'),
                'location': node.get('location'),
                'caption': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', ''),
                'post_url': f"https://www.instagram.com/p/{node.get('shortcode')}/"
            }

            if 'edge_sidecar_to_children' in node:
                for child_edge in node['edge_sidecar_to_children'].get('edges', []):
                    child_node = child_edge.get('node', {})
                    media_info = {
                        'typename': child_node.get('__typename'),
                        'id': child_node.get('id'),
                        'shortcode': child_node.get('shortcode'),
                        'dimensions': child_node.get('dimensions'),
                        'image_url': child_node.get('display_url'),
                        'is_video': child_node.get('is_video'),
                        'accessibility_caption': child_node.get('accessibility_caption')
                    }
                    child_media_list.append(media_info)
            else:
                media_info = {
                    'typename': node.get('__typename'),
                    'id': node.get('id'),
                    'shortcode': node.get('shortcode'),
                    'dimensions': node.get('dimensions'),
                    'image_url': node.get('display_url'),
                    'is_video': node.get('is_video'),
                    'accessibility_caption': node.get('accessibility_caption')
                }
                child_media_list.append(media_info)
            
            post_info['media'] = child_media_list
            post_info['details'] = post_details
            posts.append(post_info)

    return {'user_info': usrinfo, 'posts': posts}
