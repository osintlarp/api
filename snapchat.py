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
        "Sec-Ch-Ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"90\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Accept": "*/*",
        "Origin": "https://accounts.snapchat.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://accounts.snapchat.com/",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close"
    }
    
    cookies = {
        "xsrf_token": token
    }
    
    data = {
        'phone_country_code': country_code,
        'phone_number': local_number,
        'xsrf_token': token
    }
    
    url = 'https://accounts.snapchat.com/accounts/validate_phone_number'
    
    response, error = try_request("post", url, headers=headers, cookies=cookies, form_data=data, timeout=15)
    
    if error:
        return {
            'error': f'Request failed: {error}',
            'phone_number': original_phone,
            'country_code': country_code,
            'local_number': local_number,
            'valid': False
        }
    
    if response:
        if response.status_code != 200:
            return {
                'error': f'HTTP Error {response.status_code}',
                'phone_number': original_phone,
                'response_text': response.text[:200] if response.text else 'Empty response',
                'valid': False
            }
        
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
                'error': f'Failed to parse JSON response: {str(e)}',
                'phone_number': original_phone,
                'response_preview': response.text[:500] if response.text else 'No response content',
                'status_code': response.status_code,
                'valid': False
            }
    else:
        return {
            'error': 'No response received from Snapchat',
            'phone_number': original_phone,
            'valid': False
        }
