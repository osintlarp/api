from flask import Flask, jsonify, request, abort
import roblox
import github  
import utils

app = Flask(__name__)

@app.route('/v1/osint/roblox')
def get_roblox_osint():
    identifier = request.args.get('id') or request.args.get('username')
    if not identifier:
        return jsonify({'error': 'Missing "id" or "username" query parameter'}), 400
        
    use_cache = request.args.get('cache', 'true').lower() != 'false'
    
    options = {}
    for key in roblox.ALL_OPTION_KEYS:
        if request.args.get(key, 'true').lower() == 'false':
            options[key] = False
        else:
            options[key] = True

    try:
        user_info = roblox.get_user_info(identifier, use_cache=use_cache, **options)
        if not user_info:
            return jsonify({'error': 'User not found'}), 404
        if user_info.get('error'):
            if 'User not found' in user_info.get('error'):
                return jsonify(user_info), 404
            return jsonify(user_info), 500
            
        return jsonify(user_info)
    except Exception as e:
        print(f"Error in roblox endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@app.route('/v1/osint/github')
def get_github_osint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400

    use_cache = request.args.get('cache', 'true').lower() != 'false'
    
    options = {}
    for key in github.ALL_OPTION_KEYS:
        if request.args.get(key, 'true').lower() == 'false':
            options[key] = False
        else:
            options[key] = True

    try:
        github_data = github.get_github_info(username, use_cache=use_cache, **options)
        
        if github_data.get('error'):
            error_msg = github_data.get('error', '').lower()
            if 'not found' in error_msg:
                return jsonify(github_data), 404
            
            if 'rate_limited' in error_msg:
                return jsonify({'error': 'rate_limited'}), 429
                
            return jsonify(github_data), 500
            
        return jsonify(github_data)
        
    except Exception as e:
        print(f"Error in github endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500


if __name__ == '__main__':
    utils.load_proxies()
    app.run(debug=True, port=5000)
