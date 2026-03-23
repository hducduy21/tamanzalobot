from zlapi.models import Message
from config import CONNECTION_TIMEOUT
import requests
from requests.exceptions import RequestException
import re
from datetime import datetime

des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Hùng",
    'description': "Xem phong thủy số điện thoại dựa theo ngày sinh"
}

def validate_date(date_str):
    """Kiểm tra ngày sinh hợp lệ."""
    pattern = r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$'
    if not re.match(pattern, date_str):
        return False, None
    date_str = date_str.replace('/', '-')
    try:
        parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
        if not (1900 <= parsed_date.year <= 2100):
            return False, None
        return True, parsed_date.strftime('%d-%m-%Y')
    except ValueError:
        return False, None

def validate_phone(phone):
    """Kiểm tra số điện thoại hợp lệ."""
    return re.match(r'^\d{9,12}$', phone) is not None

def handle_xemsdt_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        args = message.strip().split()
        if len(args) < 3:
            raise ValueError("💡 *Cú pháp:* xemsdt số_điện_thoại ngày_sinh\n📱 Ví dụ: `xemsdt 0123456789 01-01-2000`")

        phone, date_str = args[1], args[2]
        if not validate_phone(phone):
            raise ValueError("❌ Số điện thoại không hợp lệ!\nYêu cầu: từ 9 đến 12 số.")

        is_valid_date, formatted_date = validate_date(date_str)
        if not is_valid_date:
            raise ValueError("❌ Ngày sinh không hợp lệ!\nĐịnh dạng hợp lệ: `DD-MM-YYYY` hoặc `DD/MM/YYYY`.")

        api_url = f"https://api.hungdev.id.vn/phongthuy/sdt?phone={phone}&dateOfBirth={formatted_date}&apikey=6b6bbf"
        response = requests.get(api_url, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()
        json_data = response.json()

        if not json_data.get('success'):
            raise ValueError("⚠️ API không trả về dữ liệu hợp lệ.")

        result = json_data['data'].strip()
        if len(result) > 1900:
            result = result[:1900] + "\n\n🧡 *Kết quả đã rút gọn do quá dài.*"

        beautified = f"""
📱 *PHONG THỦY SỐ ĐIỆN THOẠI:*

🔢 Số điện thoại: {phone}
🎂 Ngày sinh: {formatted_date}

———————————
{result}
———————————

💡 *Chỉ mang tính tham khảo, chọn số cũng cần hợp duyên!* 🧡
"""
        client.sendMessage(Message(text=beautified), thread_id, thread_type)

    except RequestException as e:
        client.sendMessage(Message(text=f"⚠️ Lỗi khi kết nối API: {str(e)}"), thread_id, thread_type)
    except ValueError as e:
        client.sendMessage(Message(text=str(e)), thread_id, thread_type)
    except Exception as e:
        client.sendMessage(Message(text=f"🚨 Có lỗi xảy ra:\n{str(e)}"), thread_id, thread_type)

def get_mitaizl():
    return {
        'xemsdt': handle_xemsdt_command
    }
