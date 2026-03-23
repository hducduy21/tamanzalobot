import requests
import threading
import time
from datetime import datetime
from zlapi.models import Message, ThreadType
from config import API_QUAN_LY, CONNECTION_TIMEOUT
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

des = {
    'version': "1.0.8",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Kiểm tra key và lấy giá trị tương ứng từ API"
}

def create_session_with_retry():
    """Tạo session với retry logic"""
    session = requests.Session()
    retry = Retry(
        total=3,  # Số lần retry
        backoff_factor=1,  # Đợi 1s, 2s, 4s giữa các lần retry
        status_forcelist=[500, 502, 503, 504, 408],  # Retry với các status code này
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

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
    print(f"🔍 [DEBUG] Code user nhập: '{username}'")
    print(f"🔍 [DEBUG] Code sau lower(): '{username.lower()}'")
    print(f"🔍 [DEBUG] Độ dài code: {len(username)}")
    print(f"🔍 [DEBUG] Bytes của code: {username.encode('utf-8')}")

    if not username:
        client.replyMessage(Message(text="❗ Code không được để trống."), message_object, thread_id, thread_type)
        return

    try:
        api_url = API_QUAN_LY
        print(f"🔍 [DEBUG] API URL: {api_url}")
        print(f"🔍 [DEBUG] Đang kết nối API... (timeout: {CONNECTION_TIMEOUT}s)")
        
        # Sử dụng session với retry
        session = create_session_with_retry()
        start_time = time.time()
        
        response = session.get(
            api_url, 
            timeout=CONNECTION_TIMEOUT,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
        )
        
        elapsed_time = time.time() - start_time
        print(f"🔍 [DEBUG] API Status Code: {response.status_code} (took {elapsed_time:.2f}s)")
        response.raise_for_status()

        try:
            data = response.json()
            print(f"🔍 [DEBUG] API trả về {len(data)} entries")
            print(f"🔍 [DEBUG] Kiểu dữ liệu: {type(data)}")
            print(f"🔍 [DEBUG] 5 entries đầu tiên:")
            for i, entry in enumerate(data[:5]):
                print(f"    Entry {i}: {entry} (type: {type(entry)})")
        except ValueError as ve:
            print(f"❌ [DEBUG] Lỗi parse JSON: {ve}")
            print(f"❌ [DEBUG] Raw response: {response.text[:500]}")
            client.replyMessage(Message(text="⚠️ Dữ liệu trả về không hợp lệ (không phải JSON)."), message_object, thread_id, thread_type)
            return

        # Bỏ qua hàng tiêu đề (nếu có)
        data = [entry for entry in data if len(entry) >= 2 and entry[0] != "Mã hàng"]
        print(f"🔍 [DEBUG] Sau khi lọc tiêu đề: {len(data)} entries")

        # Log tất cả các code có trong data
        all_codes = []
        for entry in data:
            if len(entry) >= 2 and entry[0]:
                code = str(entry[0]).strip().lower()
                all_codes.append(code)
        print(f"🔍 [DEBUG] Tổng số codes: {len(all_codes)}")
        print(f"🔍 [DEBUG] 20 codes đầu tiên: {all_codes[:20]}")
        print(f"🔍 [DEBUG] Code '{username.lower()}' có trong list: {username.lower() in all_codes}")
        
        # Tìm các code tương tự
        similar_codes = [c for c in all_codes if username.lower() in c or c in username.lower()]
        print(f"🔍 [DEBUG] Codes tương tự với '{username}': {similar_codes[:10]}")

        found = False
        for idx, entry in enumerate(data):
            # Kiểm tra hàng có dữ liệu hợp lệ không (bỏ qua hàng trống)
            if len(entry) < 2 or not entry[0] or not entry[1]:
                continue

            entry_code = str(entry[0]).strip().lower()
            
            # Debug so sánh
            if idx < 10:  # Chỉ log 10 entries đầu
                print(f"🔍 [DEBUG] So sánh: '{entry_code}' == '{username.lower()}' ? {entry_code == username.lower()}")

            # Chuyển entry[0] thành chuỗi để xử lý cả trường hợp số và chuỗi
            if entry_code == username.lower():
                password = str(entry[1]).strip()
                reply = f"✅ Mật khẩu của bạn là:\n{password}"
                print(f"✅ [DEBUG] TÌM THẤY! Code: '{entry[0]}', Password: '{password[:20]}...'")
                print(f"📋 User {author_id} đã lấy mật khẩu cho code: {username}")
                msg = client.replyMessage(Message(text=reply), message_object, thread_id, thread_type)
                if msg:
                    auto_unsend_message(client, msg, thread_id, thread_type, 30)
                found = True
                return

        if not found:
            print(f"❌ [DEBUG] KHÔNG TÌM THẤY code '{username}' trong {len(all_codes)} codes")
            print(f"❌ User {author_id} tìm code '{username}' - Không tìm thấy")
            client.replyMessage(Message(text=f"❌ Không tìm thấy code '{username}' trong hệ thống."), message_object, thread_id, thread_type)

    except requests.exceptions.Timeout as e:
        print(f"⏱️ [DEBUG] Timeout sau {CONNECTION_TIMEOUT}s: {str(e)}")
        client.replyMessage(Message(text=f"⏱️ API quá chậm, vui lòng thử lại sau."), message_object, thread_id, thread_type)
    except requests.exceptions.ConnectionError as e:
        print(f"🚫 [DEBUG] Lỗi kết nối: {type(e).__name__}: {str(e)}")
        print(f"🚫 Lỗi kết nối API cho user {author_id}: {str(e)}")
        client.replyMessage(Message(text=f"🚫 Không thể kết nối đến API. Vui lòng thử lại sau."), message_object, thread_id, thread_type)
    except requests.exceptions.RequestException as e:
        print(f"🚫 [DEBUG] Lỗi request: {type(e).__name__}: {str(e)}")
        print(f"🚫 Lỗi kết nối API cho user {author_id}: {str(e)}")
        client.replyMessage(Message(text=f"🚫 Lỗi khi kết nối đến API: {str(e)}"), message_object, thread_id, thread_type)
    except Exception as e:
        import traceback
        print(f"❌ [DEBUG] Lỗi không xác định: {type(e).__name__}: {str(e)}")
        print(f"❌ [DEBUG] Traceback:\n{traceback.format_exc()}")
        print(f"❌ Lỗi không xác định cho user {author_id}: {str(e)}")
        client.replyMessage(Message(text=f"❌ Lỗi không xác định: {str(e)}"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'passnet': handle_renewpass_command
    }
