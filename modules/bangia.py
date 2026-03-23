import requests
from zlapi.models import Message
from config import API_BANG_GIA, CONNECTION_TIMEOUT
des = {
    'version': "1.0.8",
    'credits': "Nguyễn Liên Mạnh",
    'description': "banggia"
}

def handle_renewpass_command(message, message_object, thread_id, thread_type, author_id, client):
    """Lệnh banggia: ."""

    # Tách lệnh và nội dung
    parts = message.strip().split(maxsplit=1)
    if len(parts) < 2:
        client.replyMessage(Message(text="❗ Vui lòng nhập cú pháp đúng: banggia <loại sản phẩm>"), message_object, thread_id, thread_type)
        return

    username = parts[1].strip()

    try:
        api_url = API_BANG_GIA
        response = requests.get(api_url, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            client.replyMessage(Message(text="⚠️ Dữ liệu trả về không hợp lệ (không phải JSON)."), message_object, thread_id, thread_type)
            return

        for entry in data:
            if len(entry) >= 2 and entry[0].lower() == username.lower():
                password = entry[1]
                reply = f"{password}"
                client.replyMessage(Message(text=reply), message_object, thread_id, thread_type)
                return

        client.replyMessage(Message(text=f"❌ Không tìm thấy bảng giá '{username}' trong hệ thống."), message_object, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        client.replyMessage(Message(text=f"🚫 Lỗi khi kết nối đến API"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'banggia': handle_renewpass_command
    }
