from utils import try_request, get_user_agent, generate_random_token

def validate_phone_number(phone_number):
    phone_number = str(phone_number).strip()
    
    original_phone = phone_number
    
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    if len(phone_number) < 3:
        return {
            'error': 'Phone number too short',
            'phone_number': original_phone,
            'valid': False
        }
    
    if phone_number.startswith('1'):
        country_code = '1'
        local_number = phone_number[1:]
    elif phone_number.startswith('44'):
        country_code = '44'
        local_number = phone_number[2:]
    elif phone_number.startswith('49'):
        country_code = '49'
        local_number = phone_number[2:]
    elif phone_number.startswith('33'):
        country_code = '33'
        local_number = phone_number[2:]
    elif phone_number.startswith('34'):
        country_code = '34'
        local_number = phone_number[2:]
    elif phone_number.startswith('39'):
        country_code = '39'
        local_number = phone_number[2:]
    elif phone_number.startswith('7'):
        country_code = '7'
        local_number = phone_number[1:]
    else:
        country_code = phone_number[:2]
        local_number = phone_number[2:]
    
    token = generate_random_token()
    
    headers = {
        'Cookie': f'xsrf_token={token}',
        'User-Agent': get_user_agent(),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    
    data = {
        'phone_country_code': country_code,
        'phone_number': local_number,
        'xsrf_token': token
    }
    
    url = 'https://accounts.snapchat.com/accounts/validate_phone_number'
    
    response, error = try_request("post", url, headers=headers, form_data=data, timeout=10)
    
    if error:
        return {
            'error': f'Request failed: {error}',
            'phone_number': original_phone,
            'country_code': country_code,
            'local_number': local_number,
            'valid': False
        }
    
    if response:
        try:
            json_data = response.json()
            status_code = json_data.get('status_code')
            
            result = {
                'phone_number': original_phone,
                'country_code': country_code,
                'local_number': local_number,
                'raw_status': status_code
            }
            
            if status_code == 'TAKEN_NUMBER':
                result.update({
                    'registered': True,
                    'status': 'registered',
                    'message': 'Phone number is registered with Snapchat'
                })
            elif status_code == 'OK':
                result.update({
                    'registered': False,
                    'status': 'available',
                    'message': 'Phone number is not registered with Snapchat'
                })
            elif status_code == 'INVALID_NUMBER':
                result.update({
                    'registered': False,
                    'status': 'invalid',
                    'message': 'Phone number format is invalid'
                })
            else:
                result.update({
                    'registered': None,
                    'status': 'unknown',
                    'message': f'Unknown status: {status_code}'
                })
            
            return result
            
        except Exception as e:
            return {
                'error': f'Failed to parse response: {str(e)}. Response text: {response.text[:100]}',
                'phone_number': original_phone,
                'valid': False
            }
    else:
        return {
            'error': 'No response received',
            'phone_number': original_phone,
            'valid': False
        }
