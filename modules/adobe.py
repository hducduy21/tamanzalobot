import requests
from zlapi.models import Message
import json

des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Kiểm tra và xác minh địa chỉ email, truy xuất thông tin liên quan"
}

API_URL = "http://fix.tuthay.io.vn/fix-email"

def fetch_email_info(email, retries=3):
    """
    Gửi yêu cầu đến API Fix-Email để kiểm tra và lấy thông tin email.
    """
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "email": email
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        if retries > 0:
            time.sleep(1)
            return fetch_email_info(email, retries - 1)
        return f"Đã có lỗi xảy ra khi kiểm tra email: {str(e)}"

    # Xử lý kết quả trả về
    if not data.get('is_valid', False):
        return (
            f"[ Kiểm tra Email ]\n"
            f"📧 Email: {data.get('mail', 'Không có thông tin')}\n"
            f"❌ Email không hợp lệ!"
        )

    if data.get('statusFam') == "not_found":
        return (
            f"[ Kiểm tra Email ]\n"
            f"📧 Email: {data.get('mail', 'Không có thông tin')}\n"
            f"✅ Email hợp lệ nhưng không tồn tại trong hệ thống."
        )

    # Format ngày hết hạn
    dueday = data.get('dueday', 'Không có thông tin')
    try:
        dueday = datetime.strptime(dueday, "%Y-%m-%dT%H:%M:%SZ").strftime("%d/%m/%Y %H:%M:%S")
    except:
        pass

    # Xây dựng thông tin trả về
    msg = (
        f"[ Kiểm tra Email ]\n"
        f"📧 Email gốc: {data.get('mail', 'Không có thông tin')}\n"
        f"📧 Email chuẩn hóa: {data.get('fixed_email', 'Không có thông tin')}\n"
        f"✅ Hợp lệ: {data.get('is_valid', False)}\n"
        f"👥 Tên đội: {data.get('teamName', 'Không có thông tin')}\n"
        f"🔗 Liên kết đội: {data.get('linkfam', 'Không có thông tin')}\n"
        f"📊 Trạng thái đội: {format_status_fam(data.get('statusFam', 'Không có thông tin'))}\n"
        f"📈 Trạng thái thành viên: {format_status(data.get('status', 'Không có thông tin'))}\n"
        f"📅 Ngày hết hạn: {dueday}"
    )
    return msg

def format_status_fam(status):
    """
    Chuyển đổi trạng thái family thành mô tả dễ hiểu.
    """
    status_map = {
        "0": "Đang hoạt động",
        "1": "Đang hoạt động",
        "2": "Hết hạn",
        "3": "Đã xóa",
        "not_found": "Không tìm thấy"
    }
    return status_map.get(status, "Không xác định")

def format_status(status):
    """
    Chuyển đổi trạng thái thành viên thành mô tả dễ hiểu.
    """
    status_map = {
        "0": "Không hoạt động",
        "1": "Đang hoạt động"
    }
    return status_map.get(status, "Không xác định")

def handle_email_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh kiểm tra email từ người dùng.
    """
    text = message.split()
    if len(text) < 2:
        error_message = Message(text="Vui lòng nhập địa chỉ email cần kiểm tra.")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    email = text[1]
    email_info = fetch_email_info(email)
    client.replyMessage(Message(text=f"{email_info}"), message_object, thread_id, thread_type)

def get_mitaizl():
    """
    Đăng ký lệnh kiểm tra email.
    """
    return {
        'adobe': handle_email_command
    }