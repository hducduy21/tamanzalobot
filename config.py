import json
import base64
import os

# Connection timeout configuration (in seconds)
CONNECTION_TIMEOUT = 120

def read_imei():
    with open('dataLogin/imei.txt', 'r') as f:
        imei = f.read().strip()
    return imei

def is_base64_encoded(data):
    try:
        base64.b64decode(data).decode('utf-8')
        return True
    except Exception:
        return False

def read_and_format_cookies():
    encCookie = read_setting_value('encCookie') == "True"
    
    with open('dataLogin/cookie.json', 'r') as f:
        data = f.read().strip()

    if is_base64_encoded(data) and not encCookie:
        decoded_data = base64.b64decode(data).decode('utf-8')
        cookies = json.loads(decoded_data)

        with open('dataLogin/cookie.json', 'w') as f:
            json.dump(cookies, f, indent=4)
        
        return cookies
    elif not is_base64_encoded(data) and encCookie:
        with open('dataLogin/cookie.json', 'r') as f:
            cookies = json.load(f)
        
        encoded_data = base64.b64encode(json.dumps(cookies).encode('utf-8')).decode('utf-8')
        
        with open('dataLogin/cookie.json', 'w') as f:
            f.write(encoded_data)
        
        return cookies
    else:
        decoded_data = base64.b64decode(data).decode('utf-8') if is_base64_encoded(data) else data
        return json.loads(decoded_data)

def read_setting_value(key):
    with open('seting.json', 'r') as f:
        settings = json.load(f)
    return settings.get(key)

def read_prefix():
    return read_setting_value('prefix')

def read_admin():
    return read_setting_value('admin')

IMEI = read_imei()
SESSION_COOKIES = read_and_format_cookies()
API_KEY = 'api_key'
SECRET_KEY = 'secret_key'
PREFIX = read_prefix()
ADMIN = read_admin()
GOOGLE_AI_API_KEY = "AIzaSyDvo-nZWUwR2xnaosWY8nYtBTSNQuLYxW0"
API_KEY = "GfQGXP86"
API_KEY_HUNG = "1328fb822741342168cbfc320865df"
API_KEY_HUNG1 = "1328fb822741342168cbfc320865df"
API_BANG_GIA ="https://script.google.com/macros/s/AKfycbw4dVHeqn3TwBy9puUHV9CdevotvzqWleJm1ybOo4UlYzcTC62qPD2TOu7wXSZPZSSA/exec"
API_QUAN_LY ="https://script.google.com/macros/s/AKfycbxtMd6l2TN2OL4C7DTGzMnscn61TQCjskZmLzAMbtrPyi8lJGDebmbZ9BTyE0AnfXn3/exec"
API_LISTKH = "https://script.google.com/macros/s/AKfycbynvoQgOC2yhPb-t3vNG6wctprG6esllzNhg-PkanuHwrWIT8NUWz7z-k1uDcrv5jTWlw/exec"