import requests
import threading
import time
import json
import os
from datetime import datetime
from zlapi.models import Message, ThreadType
from config import API_QUAN_LY, CONNECTION_TIMEOUT
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

des = {
    'version': "1.0.9",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Kiểm tra key và lấy giá trị tương ứng từ API"
}

# Cache configuration
CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache", "passnet_cache.json")
CACHE_EXPIRE_SECONDS = 300  # Cache hết hạn sau 5 phút

def create_session_with_retry():
    """Tạo session với retry logic"""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504, 408],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def load_cache():
    """Load data từ cache file"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            # Kiểm tra cache còn hạn không
            cache_time = cache.get('timestamp', 0)
            if time.time() - cache_time < CACHE_EXPIRE_SECONDS:
                print(f"🔍 [DEBUG] Sử dụng cache ({len(cache.get('data', {}))} codes, age: {int(time.time() - cache_time)}s)")
                return cache.get('data', {})
            else:
                print(f"🔍 [DEBUG] Cache hết hạn, cần fetch mới")
    except Exception as e:
        print(f"❌ [DEBUG] Lỗi load cache: {e}")
    return None

def save_cache(data_dict):
    """Lưu data vào cache file"""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        cache = {
            'timestamp': time.time(),
            'data': data_dict
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"✅ [DEBUG] Đã lưu cache: {len(data_dict)} codes")
    except Exception as e:
        print(f"❌ [DEBUG] Lỗi save cache: {e}")

def fetch_data_from_api():
    """Fetch data từ API và convert thành dict để tìm kiếm nhanh"""
    try:
        api_url = API_QUAN_LY
        print(f"🔍 [DEBUG] Đang fetch từ API: {api_url}")
        
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
        print(f"🔍 [DEBUG] API Status: {response.status_code} (took {elapsed_time:.2f}s)")
        response.raise_for_status()
        
        data = response.json()
        print(f"🔍 [DEBUG] API trả về {len(data)} entries")
        
        # Convert list thành dict để tìm kiếm O(1) thay vì O(n)
        data_dict = {}
        for entry in data:
            if len(entry) >= 2 and entry[0] and entry[0] != "Mã hàng":
                code = str(entry[0]).strip().lower()
                password = str(entry[1]).strip()
                data_dict[code] = password
        
        print(f"🔍 [DEBUG] Đã convert thành dict: {len(data_dict)} codes")
        
        # Lưu cache
        save_cache(data_dict)
        
        return data_dict
        
    except Exception as e:
        print(f"❌ [DEBUG] Lỗi fetch API: {type(e).__name__}: {e}")
        return None

def get_data():
    """Lấy data từ cache hoặc API"""
    # Thử load từ cache trước
    data = load_cache()
    if data is not None:
        return data
    
    # Nếu không có cache, fetch từ API
    return fetch_data_from_api()

def auto_unsend_message(client, message_obj, thread_id, thread_type, delay=30):
    """Tự động gỡ tin nhắn sau một khoảng thời gian."""
    current_time = datetime.now().strftime("%H:%M:%S")
    unsend_time = datetime.fromtimestamp(datetime.now().timestamp() + delay).strftime("%H:%M:%S")
    
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

    username = parts[1].strip().lower()
    print(f"🔍 [DEBUG] Code user nhập: '{username}'")

    if not username:
        client.replyMessage(Message(text="❗ Code không được để trống."), message_object, thread_id, thread_type)
        return

    try:
        # Lấy data (từ cache hoặc API)
        data = get_data()
        
        if data is None:
            client.replyMessage(Message(text="🚫 Không thể kết nối đến API. Vui lòng thử lại sau."), message_object, thread_id, thread_type)
            return
        
        print(f"🔍 [DEBUG] Tổng số codes: {len(data)}")
        print(f"🔍 [DEBUG] Code '{username}' có trong data: {username in data}")
        
        # Tìm code trực tiếp trong dict (O(1) thay vì O(n))
        if username in data:
            password = data[username]
            reply = f"✅ Mật khẩu của bạn là:\n{password}"
            print(f"✅ [DEBUG] TÌM THẤY! Code: '{username}', Password: '{password[:20]}...'")
            print(f"📋 User {author_id} đã lấy mật khẩu cho code: {username}")
            msg = client.replyMessage(Message(text=reply), message_object, thread_id, thread_type)
            if msg:
                auto_unsend_message(client, msg, thread_id, thread_type, 30)
        else:
            # Tìm các code tương tự để gợi ý
            similar_codes = [c for c in data.keys() if username in c or c in username][:5]
            print(f"🔍 [DEBUG] Codes tương tự: {similar_codes}")
            print(f"❌ User {author_id} tìm code '{username}' - Không tìm thấy")
            
            reply = f"❌ Không tìm thấy code '{username}' trong hệ thống."
            if similar_codes:
                reply += f"\n💡 Bạn có ý tìm: {', '.join(similar_codes)}?"
            client.replyMessage(Message(text=reply), message_object, thread_id, thread_type)

    except Exception as e:
        import traceback
        print(f"❌ [DEBUG] Lỗi: {type(e).__name__}: {str(e)}")
        print(f"❌ [DEBUG] Traceback:\n{traceback.format_exc()}")
        client.replyMessage(Message(text=f"❌ Lỗi không xác định: {str(e)}"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'passnet': handle_renewpass_command
    }
