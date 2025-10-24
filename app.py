from flask import Flask, jsonify, request, abort
import roblox
import instagram
import utils

app = Flask(__name__)

@app.route('/v1/osint/roblox')
def get_roblox_osint():
    identifier = request.args.get('id') or request.args.get('username')
    if not identifier:
        return jsonify({'error': 'Missing "id" or "username" query parameter'}), 400
        
    options = {}
    for key in roblox.ALL_OPTION_KEYS:
        if request.args.get(key, 'true').lower() == 'false':
            options[key] = False
        else:
            options[key] = True

    try:
        user_info = roblox.get_user_info(identifier, **options)
        if not user_info:
            return jsonify({'error': 'User not found'}), 404
        if user_info.get('error'):
            return jsonify(user_info), 500
            
        return jsonify(user_info)
    except Exception as e:
        print(f"Error in roblox endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@app.route('/v1/osint/instagram')
def get_instagram_osint():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Missing "username" query parameter'}), 400
        
    try:
        info = instagram.get_instagram_info(username)
        if info.get('error'):
            if 'User not found' in info.get('error'):
                 return jsonify(info), 404
            return jsonify(info), 500
            
        return jsonify(info)
    except Exception as e:
        print(f"Error in instagram endpoint: {e}")
        return jsonify({'error': 'An internal server error occurred'}), 500

if __name__ == '__main__':
    utils.load_proxies()
    app.run(debug=True, port=5000)

