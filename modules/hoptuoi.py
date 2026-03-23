from zlapi.models import Message
from config import CONNECTION_TIMEOUT
import requests
from requests.exceptions import RequestException
import re
from datetime import datetime

des = {
    'version': "1.0.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Xem mức độ hợp tuổi của hai người dựa trên ngày sinh"
}

def validate_date(date_str):
    """Kiểm tra và chuẩn hóa ngày sinh."""
    pattern = r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$'
    if not re.match(pattern, date_str):
        return False, None

    date_str = date_str.replace('/', '-')
    try:
        parsed_date = datetime.strptime(date_str, '%d-%m-%Y')
        if not (1900 <= parsed_date.year <= 2100):
            return False, None
        formatted_date = parsed_date.strftime('%d-%m-%Y')
        return True, formatted_date
    except ValueError:
        return False, None

def handle_hoptuoi_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        args = message.strip().split()
        if len(args) < 3:
            raise ValueError("💡 *Cú pháp đúng:* hoptuoi ngày_sinh_1 ngày_sinh_2\n🧡 Ví dụ: `hoptuoi 01-01-2000 01-01-2000`\n(*Chấp nhận `-` hoặc `/`*)")

        male_date, female_date = args[1], args[2]

        is_valid_male, formatted_male_date = validate_date(male_date)
        is_valid_female, formatted_female_date = validate_date(female_date)

        if not (is_valid_male and is_valid_female):
            raise ValueError("❌ Một hoặc cả hai ngày sinh không hợp lệ!\n\n💡 Hãy kiểm tra lại định dạng:\n`DD-MM-YYYY` hoặc `DD/MM/YYYY`\n\n📌 Ví dụ: `hoptuoi 01-01-2000 05-05-2001`")

        api_url = f"https://api.hungdev.id.vn/phongthuy/hop-tuoi?maleDateOfBirth={formatted_male_date}&femaleDateOfBirth={formatted_female_date}&apikey=6b6bbf"
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }

        response = requests.get(api_url, headers=headers, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()
        json_data = response.json()

        if not json_data.get('success') or not isinstance(json_data.get('data'), str):
            raise ValueError("⚠️ API trả về dữ liệu không hợp lệ hoặc không có kết quả!")

        result = json_data['data'].strip()
        if not result:
            raise ValueError("⚠️ Không nhận được kết quả từ API.")

        max_length = 1900
        if len(result) > max_length:
            result = result[:max_length] + "\n\n🧡 *[Kết quả đã được rút gọn do quá dài]*"

        beautified_message = f"""
🔮 *KẾT QUẢ XEM HỢP TUỔI:*

👦 Ngày sinh Nam: {formatted_male_date}
👧 Ngày sinh Nữ: {formatted_female_date}

———————————
{result}
———————————

💡 Lưu ý: Chỉ mang tính chất tham khảo, hãy tin vào tình cảm và sự cố gắng của cả hai nhé! 🧡
"""

        client.sendMessage(Message(text=beautified_message), thread_id, thread_type)

    except RequestException as e:
        client.sendMessage(Message(text=f"⚠️ Lỗi khi gọi API:\n{str(e)}"), thread_id, thread_type)
    except ValueError as e:
        client.sendMessage(Message(text=str(e)), thread_id, thread_type)
    except Exception as e:
        client.sendMessage(Message(text=f"🚨 Đã xảy ra lỗi không xác định:\n{str(e)}"), thread_id, thread_type)

def get_mitaizl():
    return {
        'hoptuoi': handle_hoptuoi_command
    }
