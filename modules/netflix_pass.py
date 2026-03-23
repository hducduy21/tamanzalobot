import requests
from zlapi.models import Message
import json
from config import API_LISTKH, CONNECTION_TIMEOUT
import logging
from datetime import datetime
import re
import html

# ================== LOG CONFIG ==================
# Tạo logger riêng để tránh conflict với các module khác
logger = logging.getLogger('netflix_pass')
logger.setLevel(logging.DEBUG)

# Kiểm tra xem logger đã có handlers chưa
if not logger.handlers:
    # Tạo formatter
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # File handler với mode append
    file_handler = logging.FileHandler("netflix_pass.log", mode='a', encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Thêm handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Ngăn log propagate lên root logger
    logger.propagate = False

# Sử dụng logger này thay vì logging module
logging = logger
 
# ================== CHECK QUYỀN ==================
def is_admin_or_adm(author_id):
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        admin = config.get('admin')
        adm_list = config.get('adm', [])
        return str(author_id) == str(admin) or str(author_id) in [str(a) for a in adm_list]
    except Exception as e:
        logging.error(f"Lỗi đọc seting.json: {e}")
        return False

# ================== META ==================
des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Lấy link đặt lại mật khẩu Netflix từ mã và gửi cho người dùng (chỉ admin/adm)"
}

# ================== MAIN HANDLER ==================
def handle_netflix_pass_command(message, message_object, thread_id, thread_type, author_id, client):
    logging.info(f"Người dùng {author_id} gọi lệnh netflix_pass | Nội dung: {message}")

    text = message.split()
    if len(text) < 2:
        logging.warning("Thiếu mã kiểm tra")
        client.replyMessage(
            Message(text="Vui lòng nhập mã cần kiểm tra!"),
            message_object, thread_id, thread_type
        )
        return

    ma = text[1]
    logging.info(f"Mã được nhập: {ma}")

    if not is_admin_or_adm(author_id):
        logging.warning(f"User {author_id} không có quyền sử dụng lệnh")
        client.replyMessage(
            Message(text="Bạn không có quyền sử dụng lệnh này!"),
            message_object, thread_id, thread_type
        )
        return

    # ================== API 1 ==================
    try:
        logging.info(f"Gọi API_LISTKH: {API_LISTKH}")
        data1 = requests.get(API_LISTKH, timeout=CONNECTION_TIMEOUT).json()
    except Exception as e:
        logging.error(f"Lỗi gọi API_LISTKH: {e}")
        client.replyMessage(
            Message(text="Không thể truy cập dữ liệu!"),
            message_object, thread_id, thread_type
        )
        return

    for item in data1:
        if item.get("A") == ma:
            url2 = item.get("C")
            logging.info(f"Tìm thấy mã {ma} | URL dữ liệu 2: {url2}")

            if not url2:
                logging.warning("Không có URL dữ liệu tiếp theo")
                client.replyMessage(
                    Message(text="Không tìm thấy URL dữ liệu tiếp theo!"),
                    message_object, thread_id, thread_type
                )
                return

            # ================== API 2 ==================
            try:
                logging.info(f"Gọi API dữ liệu 2: {url2}")
                data2 = requests.get(url2, timeout=CONNECTION_TIMEOUT).json()
            except Exception as e:
                logging.error(f"Lỗi gọi API dữ liệu 2: {e}")
                client.replyMessage(
                    Message(text="Không thể truy cập dữ liệu 2!"),
                    message_object, thread_id, thread_type
                )
                return

            # ================== TÌM LINK ==================
            # data2 là mảng các object với keys: "Chủ đề", "Người gửi", "Thời gian", "Nội dung chính", "Link Netflix Reset"
            logging.info(f"Bắt đầu tìm link trong {len(data2)} email(s)")
            for idx, item in enumerate(data2):
                if not isinstance(item, dict):
                    logging.warning(f"Item {idx} không phải dict, bỏ qua")
                    continue
                
                # Lấy thời gian từ object
                time_str = item.get("Thời gian", "Không rõ thời gian")
                try:
                    time_fmt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    time_str_fmt = time_fmt.strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    time_str_fmt = time_str
                
                # Ưu tiên: Kiểm tra field "Link Netflix Reset" trước
                link_reset = item.get("Link Netflix Reset", "")
                logging.debug(f"Email {idx}: Kiểm tra 'Link Netflix Reset' = {link_reset[:50] if link_reset else 'None'}...")
                if link_reset and link_reset.strip():
                    # Decode HTML entities (ví dụ: &amp; -> &)
                    link = html.unescape(link_reset.strip())
                    logging.info(f"✅ Tìm thấy link reset từ field 'Link Netflix Reset': {link}")
                    client.replyMessage(
                        Message(text=f"Link đặt lại mật khẩu Netflix: {link}\nThời gian: {time_str_fmt}"),
                        message_object, thread_id, thread_type
                    )
                    return
                
                # Fallback: Tìm link trong "Nội dung chính"
                content = item.get("Nội dung chính", "")
                if not content or "http" not in content:
                    logging.debug(f"Email {idx}: Không có 'Nội dung chính' hoặc không chứa http, bỏ qua")
                    continue

                # Tìm link reset Netflix trong nội dung
                logging.debug(f"Email {idx}: Kiểm tra 'Nội dung chính' (độ dài: {len(content)})")
                if "Link xác minh / đặt lại mật khẩu" in content or "Link đặt lại mật khẩu" in content or "Link xác minh:" in content:
                    logging.info(f"Email {idx}: Phát hiện nội dung có link reset Netflix")

                    # Pattern để tìm link: "Link xác minh / đặt lại mật khẩu: https://..." hoặc "Link xác minh: https://..."
                    match = re.search(
                        r"Link xác minh(?:\s*/\s*đặt lại mật khẩu)?:\s*(https?://[^\s>]+)",
                        content
                    )

                    if match:
                        link = match.group(1).rstrip('>')  # Loại bỏ ký tự > ở cuối nếu có
                        logging.info(f"✅ Tìm thấy link reset từ nội dung: {link}")
                        client.replyMessage(
                            Message(text=f"Link đặt lại mật khẩu Netflix: {link}\nThời gian: {time_str_fmt}"),
                            message_object, thread_id, thread_type
                        )
                        return

                    # Fallback: tìm bất kỳ link nào sau "Link xác minh" hoặc "Link đặt lại mật khẩu"
                    parts = content.split("Link xác minh")
                    if len(parts) > 1:
                        # Tìm URL đầu tiên sau dấu :
                        url_match = re.search(r"https?://[^\s>]+", parts[1])
                        if url_match:
                            link = url_match.group(0).rstrip('>')
                            logging.info(f"✅ Tìm thấy link reset (fallback từ nội dung): {link}")
                            client.replyMessage(
                                Message(text=f"Link đặt lại mật khẩu Netflix: {link}\nThời gian: {time_str_fmt}"),
                                message_object, thread_id, thread_type
                            )
                            return

            logging.warning(f"Đã duyệt qua {len(data2)} email(s) nhưng không tìm thấy link reset Netflix")
            client.replyMessage(
                Message(text="Không có link đổi pass, thử lại sau!"),
                message_object, thread_id, thread_type
            )
            return

    logging.warning(f"Không tìm thấy mã {ma} trong dữ liệu")
    client.replyMessage(
        Message(text="Không tìm thấy mã trong dữ liệu!"),
        message_object, thread_id, thread_type
    )

# ================== EXPORT ==================
def get_mitaizl():
    return {
        'netflix_pass': handle_netflix_pass_command
    }
