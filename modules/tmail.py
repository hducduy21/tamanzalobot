import requests
import random
import string
import re
from zlapi.models import Message
import time

des = {
    'version': "1.0.0",
    'credits': "Inspired by Nguyễn Liên Mạnh",
    'description': "Tạo email tạm thời và kiểm tra OTP từ email mới nhất"
}

BASE_URL = "https://api.mail.tm"

def generate_random_username(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def get_domain(retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(f"{BASE_URL}/domains")
            response.raise_for_status()
            data = response.json()
            domains = data.get('hydra:member', [])
            if domains:
                return domains[0]['domain']
            return None
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return None
    return None

def create_account(username=None, retries=3):
    domain = get_domain()
    if not domain:
        return "Không thể lấy danh sách domain!"

    username = username or generate_random_username()
    email = f"{username}@{domain}"
    password = username  # Password matches username

    payload = {
        "address": email,
        "password": password
    }

    for attempt in range(retries):
        try:
            response = requests.post(f"{BASE_URL}/accounts", json=payload)
            response.raise_for_status()
            account_data = response.json()
            return {
                "email": account_data['address'],
                "password": password,
                "id": account_data['id']
            }
        except requests.exceptions.RequestException as e:
            if response.status_code == 422:
                return "Tên người dùng không hợp lệ hoặc domain không đúng!"
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return f"Đã có lỗi khi tạo tài khoản: {str(e)}"
    return "Không thể tạo tài khoản!"

def get_token(email, password, retries=3):
    payload = {
        "address": email,
        "password": password
    }

    for attempt in range(retries):
        try:
            response = requests.post(f"{BASE_URL}/token", json=payload)
            response.raise_for_status()
            token_data = response.json()
            return token_data['token']
        except requests.exceptions.RequestException as e:
            if response.status_code == 401:
                return None
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return None
    return None

def get_latest_email(token, retries=3):
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(retries):
        try:
            response = requests.get(f"{BASE_URL}/messages?page=1", headers=headers)
            response.raise_for_status()
            messages = response.json().get('hydra:member', [])
            if messages:
                return messages[0]  # Latest email
            return None
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return None
    return None

def extract_otp(email_id, token, retries=3):
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(retries):
        try:
            response = requests.get(f"{BASE_URL}/messages/{email_id}", headers=headers)
            response.raise_for_status()
            email_data = response.json()
            text = email_data.get('text', '')
            html = ' '.join(email_data.get('html', []))
            content = text + ' ' + html
            otp_match = re.search(r'\b\d{4,6}\b', content)
            return otp_match.group(0) if otp_match else "Không tìm thấy OTP!"
        except requests.exceptions.RequestException:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return "Đã có lỗi khi lấy nội dung email!"
    return "Không thể lấy nội dung email!"

def handle_create_email_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    username = text[1] if len(text) > 1 else None

    account_info = create_account(username)
    if isinstance(account_info, dict):
        msg = (
            f"[ Tạo email thành công ]\n"
            f"📧 Email: {account_info['email']}\n"
            f"🔑 .checkemail {account_info['password']} để kiểm tra OTP"
        )
    else:
        msg = account_info

    client.replyMessage(Message(text=msg), message_object, thread_id, thread_type,ttl=100000)

def handle_check_email_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    if len(text) < 2:
        error_message = Message(text="Vui lòng nhập username của email!")
        client.sendMessage(error_message, thread_id, thread_type,ttl=10000)
        return

    username = text[1]
    domain = get_domain()
    if not domain:
        client.replyMessage(Message(text="Không thể lấy danh sách domain!"), message_object, thread_id, thread_type,ttl=10000)
        return

    email = f"{username}@{domain}"
    token = get_token(email, username)  # Password is same as username
    if not token:
        client.replyMessage(Message(text="Không thể xác thực tài khoản! Kiểm tra username."), message_object, thread_id, thread_type,ttl=10000)
        return

    latest_email = get_latest_email(token)
    if not latest_email:
        client.replyMessage(Message(text="Không có email nào trong hộp thư!"), message_object, thread_id, thread_type,ttl=10000)
        return

    otp = extract_otp(latest_email['id'], token)
    client.replyMessage(Message(text=f"[ OTP mới nhất trong 30s ]\n{otp}"), message_object, thread_id, thread_type,ttl=30000)

def get_mitaizl():
    return {
        'createemail': handle_create_email_command,
        'checkemail': handle_check_email_command
    }