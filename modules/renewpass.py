import requests
import threading
from datetime import datetime
from zlapi.models import Message, ThreadType
from config import API_QUAN_LY, CONNECTION_TIMEOUT

des = {
    'version': "1.0.8",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Kiểm tra key và lấy giá trị tương ứng từ API"
}

def auto_unsend_message(client, message_obj, thread_id, thread_type, delay=30):
    """Tự động gỡ tin nhắn sau một khoảng thời gian."""
    current_time = datetime.now().strftime("%H:%M:%S")
    unsend_time = datetime.fromtimestamp(datetime.now().timestamp() + delay).strftime("%H:%M:%S")
    
    # Lấy msgId từ object trả về
    msg_id = message_obj.msgId if hasattr(message_obj, 'msgId') else str(message_obj)
    cli_msg_id = message_obj.cliMsgId if hasattr(message_obj, 'cliMsgId') else msg_id
    
    print(f"⏰ [{current_time}] Tin nhắn ID: {msg_id} sẽ được gỡ sau {delay} giây (vào lúc {unsend_time})")
    
    def unsend():
        try:
            client.undoMessage(msg_id, cli_msg_id, thread_id, thread_type)
            actual_time = datetime.now().strftime("%H:%M:%S")
            print(f"✅ [{actual_time}] Đã gỡ tin nhắn ID: {msg_id} thành công!")
        except Exception as e:
            error_time = datetime.now().strftime("%H:%M:%S")
            print(f"❌ [{error_time}] Lỗi khi gỡ tin nhắn ID: {msg_id} - {str(e)}")
    
    timer = threading.Timer(delay, unsend)
    timer.daemon = True
    timer.start()

def handle_renewpass_command(message, message_object, thread_id, thread_type, author_id, client):
    """Lệnh renewpass: Trả về mật khẩu theo username từ API."""

    print(f"🔍 User {author_id} đang sử dụng lệnh passnet")
    
    # Tách lệnh và nội dung
    parts = message.strip().split(maxsplit=1)
    if len(parts) < 2:
        print(f"⚠️ User {author_id} nhập sai cú pháp")
        client.replyMessage(Message(text="❗ Vui lòng nhập cú pháp đúng: passnet <code>"), message_object, thread_id, thread_type)
        return

    username = parts[1].strip()

    if not username:
        client.replyMessage(Message(text="❗ Code không được để trống."), message_object, thread_id, thread_type)
        return

    try:
        api_url = API_QUAN_LY
        response = requests.get(api_url, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            client.replyMessage(Message(text="⚠️ Dữ liệu trả về không hợp lệ (không phải JSON)."), message_object, thread_id, thread_type)
            return

        # Bỏ qua hàng tiêu đề (nếu có)
        data = [entry for entry in data if len(entry) >= 2 and entry[0] != "Mã hàng"]

        found = False
        for entry in data:
            # Kiểm tra hàng có dữ liệu hợp lệ không (bỏ qua hàng trống)
            if len(entry) < 2 or not entry[0] or not entry[1]:
                continue

            # Chuyển entry[0] thành chuỗi để xử lý cả trường hợp số và chuỗi
            if str(entry[0]).strip().lower() == username.lower():
                password = str(entry[1]).strip()  # Chuyển mật khẩu thành chuỗi để đảm bảo đồng nhất
                reply = f"✅ Mật khẩu của bạn là:\n{password}"
                print(f"📋 User {author_id} đã lấy mật khẩu cho code: {username}")
                msg = client.replyMessage(Message(text=reply), message_object, thread_id, thread_type)
                if msg:
                    auto_unsend_message(client, msg, thread_id, thread_type, 30)
                found = True
                return

        if not found:
            print(f"❌ User {author_id} tìm code '{username}' - Không tìm thấy")
            client.replyMessage(Message(text=f"❌ Không tìm thấy code '{username}' trong hệ thống."), message_object, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        print(f"🚫 Lỗi kết nối API cho user {author_id}: {str(e)}")
        client.replyMessage(Message(text=f"🚫 Lỗi khi kết nối đến API: {str(e)}"), message_object, thread_id, thread_type)
    except Exception as e:
        print(f"❌ Lỗi không xác định cho user {author_id}: {str(e)}")
        client.replyMessage(Message(text=f"❌ Lỗi không xác định: {str(e)}"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'passnet': handle_renewpass_command
    }
