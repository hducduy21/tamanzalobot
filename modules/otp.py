import requests
import re
from zlapi.models import Message
from config import API_QUAN_LY, CONNECTION_TIMEOUT

des = {
    'version': "1.0.9",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Kiểm tra text và lấy dữ liệu từ link tương ứng"
}

def handle_check_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handle the .otpchatgpt command to check text and retrieve data from the corresponding link."""
    if not message or not message.strip():
        client.replyMessage(
            Message(text="❗ Vui lòng cung cấp từ khóa để kiểm tra."),
            message_object, thread_id, thread_type
        )
        return

    # Split input to remove command prefix (e.g., ".otpchatgpt")
    parts = message.strip().split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        client.replyMessage(
            Message(text="❗ Vui lòng cung cấp từ khóa sau lệnh `.otpchatgpt`."),
            message_object, thread_id, thread_type
        )
        return

    keyword = parts[1].strip().lower()

    try:
        # Call API to fetch data from Google Sheets (columns K and L)
        response = requests.get(API_QUAN_LY, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            client.replyMessage(
                Message(text="⚠️ Dữ liệu API không đúng định dạng."),
                message_object, thread_id, thread_type
            )
            return

        for entry in data:
            # Check if entry is valid and matches keyword in column K (index 0)
            if (
                isinstance(entry, list) and
                len(entry) >= 2 and
                entry[0] is not None and
                str(entry[0]).strip().lower() == keyword
            ):
                link = entry[1]
                if not link or not isinstance(link, str):
                    client.replyMessage(
                        Message(text=f"⚠️ Link cho từ khóa `{keyword}` không hợp lệ."),
                        message_object, thread_id, thread_type
                    )
                    return

                try:
                    # Fetch data from the link
                    link_response = requests.get(link, timeout=CONNECTION_TIMEOUT)
                    link_response.raise_for_status()

                    try:
                        link_data = link_response.json()
                        # Check if data is a list and has the expected structure
                        if (
                            isinstance(link_data, list) and
                            len(link_data) > 0 and
                            isinstance(link_data[0], list) and
                            len(link_data[0]) >= 4
                        ):
                            data_text = str(link_data[0][3])
                        else:
                            data_text = link_response.text
                    except ValueError:
                        data_text = link_response.text

                    # Extract OTP (4-8 digits)
                    otp_match = re.search(r'\b\d{4,8}\b', data_text)
                    if otp_match:
                        otp = otp_match.group(0)
                        message_text = f"✅ OTP của bạn là: {otp}"
                    else:
                        message_text = "⚠️ Không tìm thấy OTP trong dữ liệu."

                    client.replyMessage(
                        Message(text=message_text),
                        message_object, thread_id, thread_type, ttl=50000
                    )
                    return

                except requests.exceptions.RequestException as e:
                    client.replyMessage(
                        Message(text=f"❌ Không thể truy cập link từ khóa `{keyword}`: {str(e)}"),
                        message_object, thread_id, thread_type
                    )
                    return

        client.replyMessage(
            Message(text=f"🔍 Không tìm thấy từ khóa `{keyword}` trong hệ thống."),
            message_object, thread_id, thread_type
        )

    except requests.exceptions.RequestException as e:
        client.replyMessage(
            Message(text=f"🚫 Lỗi khi kết nối đến API: {str(e)}"),
            message_object, thread_id, thread_type
        )
    except Exception as e:
        client.replyMessage(
            Message(text=f"❌ Lỗi không xác định: {str(e)}"),
            message_object, thread_id, thread_type
        )

def get_mitaizl():
    return {
        'otpchatgpt': handle_check_command
    }