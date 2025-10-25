from flask import Flask, jsonify, request, abort
import roblox
import snapchat
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


if __name__ == '__main__':
    utils.load_proxies()
    app.run(debug=True, port=5000)
