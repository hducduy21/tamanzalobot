from zlapi.models import Message, MultiMsgStyle, MessageStyle
from datetime import datetime
import re
import requests
import json
from config import GOOGLE_AI_API_KEY, CONNECTION_TIMEOUT
des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Xem bói bài Tarot và Tử Vi dựa trên họ tên, ngày sinh và câu hỏi của bạn"
}

# Gemini API configuration
GEMINI_API_KEY = GOOGLE_AI_API_KEY  # Replace with your actual API key
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
# Note: Using gemini-1.5-flash as gemini-2.0-flash may not be available; adjust model as needed

def validate_inputs(full_name, birth_date, topic):
    # Validate full name (non-empty)
    if not full_name or full_name.strip() == "":
        raise ValueError("Vui lòng cung cấp họ và tên đầy đủ")

    # Validate birth date format (DD-MM-YYYY)
    if not re.match(r'^\d{2}-\d{2}-\d{4}$', birth_date):
        raise ValueError("Định dạng ngày sinh không hợp lệ. Vui lòng nhập theo định dạng DD-MM-YYYY (ví dụ: 15-06-1990)")

    try:
        birth_date_obj = datetime.strptime(birth_date, '%d-%m-%Y')
        if birth_date_obj > datetime.now():
            raise ValueError("Ngày sinh không thể là ngày trong tương lai")
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError("Định dạng ngày sinh không hợp lệ. Vui lòng nhập theo định dạng DD-MM-YYYY")
        raise e

    # Validate topic (non-empty)
    if not topic or topic.strip() == "":
        raise ValueError("Vui lòng cung cấp chủ đề muốn hỏi (ví dụ: tình yêu, sự nghiệp, tài chính)")

def split_message(text, max_chars=1500):
    """Split a text into chunks of max_chars or fewer, ensuring not to break sentences."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_chunk = ""
    sentences = re.split(r'(?<=[.!?])\s+', text)  # Split on sentence boundaries

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def call_gemini_api(prompt):
    try:
        # Prepare the JSON payload for the API request
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        # Set headers
        headers = {
            "Content-Type": "application/json"
        }

        # Send POST request to Gemini API
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=CONNECTION_TIMEOUT)

        # Check for HTTP errors
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Extract the generated text from the response
        if "candidates" in data and len(data["candidates"]) > 0:
            result = data["candidates"][0]["content"]["parts"][0]["text"]
            return result
        else:
            raise ValueError("Không nhận được kết quả từ API")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Lỗi khi gọi API: {str(e)}")
    except (KeyError, ValueError) as e:
        raise Exception(f"Lỗi khi xử lý phản hồi từ API: {str(e)}")

def generate_tarot_reading(full_name, birth_date, topic):
    # Construct the prompt for tarot reading
    prompt = (
        f"{full_name}, sinh ngày {birth_date}, hỏi về {topic}. "
        "Tạo 3 số ngẫu nhiên từ 1-78, tra cứu lá bài Tarot tương ứng (bộ 78 lá), "
        "nêu ý nghĩa mỗi lá, và đưa ra bài đọc tổng quát, cá nhân hóa. "
        "Trả lời tiếng Việt, giọng điệu huyền bí, truyền cảm."
    )
    return call_gemini_api(prompt)

def generate_tuvi_reading(full_name, birth_date, topic):
    # Construct the prompt for Tử Vi reading
    prompt = (
        f"{full_name}, sinh ngày {birth_date}, hỏi về {topic}. "
        "Dựa trên ngày sinh, phân tích Tử Vi theo phong thủy Việt Nam (Can Chi, ngũ hành), "
        "và đưa ra dự đoán chi tiết, cá nhân hóa về chủ đề này. "
        "Trả lời tiếng Việt, giọng điệu huyền bí, truyền cảm."
    )
    return call_gemini_api(prompt)

def handle_tarot_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Remove the command prefix (.tarot) and trim whitespace
        input_str = message.strip().split(None, 1)[1] if len(message.split(None, 1)) > 1 else ""

        # Try splitting with '|' delimiter first
        parts = [part.strip() for part in input_str.split("|")]

        # If the '|' split doesn't yield enough parts, try splitting by spaces
        if len(parts) < 3:
            parts = input_str.split(None, 2)

        # Check if inputs are missing
        if len(parts) < 3:
            usage_msg = (
                "[ HƯỚNG DẪN SỬ DỤNG .tarot ]\n"
                "🔮 Xem bói bài Tarot dựa trên thông tin cá nhân.\n\n"
                "Cách dùng:\n"
                "- Nhập lệnh: .tarot [Họ và tên] | [DD-MM-YYYY] | [Chủ đề]\n"
                "- Hoặc: .tarot [Họ và tên] [DD-MM-YYYY] [Chủ đề]\n"
                "- Ví dụ: .tarot Nguyễn Liên Mạnh | 03-03-2004 | tình yêu\n"
                "- Ví dụ: .tarot Nguyễn Liên Mạnh 03-03-2004 tình yêu\n\n"
                "Chủ đề có thể là:\n"
                "- Tình yêu, sự nghiệp, tài chính, sức khỏe, v.v.\n\n"
                "Kết quả sẽ hiển thị:\n"
                "- 3 lá bài Tarot và ý nghĩa\n"
                "- Bài đọc tổng quát dựa trên thông tin của bạn"
            )
            style = MultiMsgStyle([
                MessageStyle(offset=0, length=len(usage_msg), style="color", color="ff6347", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="font", size="13", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="bold", auto_format=False),
                MessageStyle(offset=20, length=len(usage_msg), style="italic", auto_format=False)
            ])
            styled_message = Message(text=usage_msg, style=style)
            client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=500000)
            return

        # Extract inputs
        full_name = parts[0].strip()
        birth_date = parts[1].strip()
        topic = parts[2].strip()

        # Validate inputs
        validate_inputs(full_name, birth_date, topic)

        # Generate tarot reading
        reading = generate_tarot_reading(full_name, birth_date, topic)

        # Format the message with improved readability
        msg = (
            f"🔮 BÀI ĐỌC TAROT DÀNH CHO {full_name.upper()} 🔮\n"
            f"🌟 Ngày sinh: {birth_date}\n"
            f"🌙 Chủ đề: {topic}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{reading}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🃏 Hãy lắng nghe thông điệp từ vũ trụ!"
        )

        # Split the message into chunks if longer than 1500 characters
        msg_chunks = split_message(msg, max_chars=1500)

        # Apply styling to each chunk
        for i, chunk in enumerate(msg_chunks):
            # Add a continuation note for subsequent chunks
            if i > 0:
                chunk = f"[TIẾP TỤC]\n{chunk}"
            
            style = MultiMsgStyle([
                MessageStyle(offset=0, length=len(chunk), style="color", color="ff6347", auto_format=False),
                MessageStyle(offset=0, length=len(chunk), style="font", size="13", auto_format=False),
                MessageStyle(offset=0, length=len(chunk), style="bold", auto_format=False),
                MessageStyle(offset=20, length=len(chunk), style="italic", auto_format=False)
            ])

            # Send each chunk as a separate message
            styled_message = Message(text=chunk, style=style)
            client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=500000)

    except ValueError as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)
    except Exception as e:
        error_message = Message(text=f"Lỗi khi xem Tarot: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)

def handle_tuvi_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Remove the command prefix (.tuvi) and trim whitespace
        input_str = message.strip().split(None, 1)[1] if len(message.split(None, 1)) > 1 else ""

        # Try splitting with '|' delimiter first
        parts = [part.strip() for part in input_str.split("|")]

        # If the '|' split doesn't yield enough parts, try splitting by spaces
        if len(parts) < 3:
            parts = input_str.split(None, 2)

        # Check if inputs are missing
        if len(parts) < 3:
            usage_msg = (
                "[ HƯỚNG DẪN SỬ DỤNG .tuvi ]\n"
                "🌌 Xem Tử Vi dựa trên thông tin cá nhân.\n\n"
                "Cách dùng:\n"
                "- Nhập lệnh: .tuvi [Họ và tên] | [DD-MM-YYYY] | [Chủ đề]\n"
                "- Hoặc: .tuvi [Họ và tên] [DD-MM-YYYY] [Chủ đề]\n"
                "- Ví dụ: .tuvi Nguyễn Liên Mạnh | 03-03-2004 | tình yêu\n"
                "- Ví dụ: .tuvi Nguyễn Liên Mạnh 03-03-2004 tình yêu\n\n"
                "Chủ đề có thể là:\n"
                "- Tình yêu, sự nghiệp, tài chính, sức khỏe, v.v.\n\n"
                "Kết quả sẽ hiển thị:\n"
                "- Phân tích Tử Vi dựa trên ngày sinh\n"
                "- Dự đoán chi tiết về chủ đề của bạn"
            )
            style = MultiMsgStyle([
                MessageStyle(offset=0, length=len(usage_msg), style="color", color="ff6347", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="font", size="13", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="bold", auto_format=False),
                MessageStyle(offset=20, length=len(usage_msg), style="italic", auto_format=False)
            ])
            styled_message = Message(text=usage_msg, style=style)
            client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=500000)
            return

        # Extract inputs
        full_name = parts[0].strip()
        birth_date = parts[1].strip()
        topic = parts[2].strip()

        # Validate inputs
        validate_inputs(full_name, birth_date, topic)

        # Generate Tử Vi reading
        reading = generate_tuvi_reading(full_name, birth_date, topic)

        # Format the message with improved readability
        msg = (
            f"🌌 TỬ VI DÀNH CHO {full_name.upper()} 🌌\n"
            f"🌟 Ngày sinh: {birth_date}\n"
            f"🌙 Chủ đề: {topic}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{reading}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ Hãy để vận mệnh dẫn lối cho bạn!"
        )

        # Split the message into chunks if longer than 1500 characters
        msg_chunks = split_message(msg, max_chars=1500)

        # Apply styling to each chunk
        for i, chunk in enumerate(msg_chunks):
            # Add a continuation note for subsequent chunks
            if i > 0:
                chunk = f"[TIẾP TỤC]\n{chunk}"
            
            style = MultiMsgStyle([
                MessageStyle(offset=0, length=len(chunk), style="color", color="ff6347", auto_format=False),
                MessageStyle(offset=0, length=len(chunk), style="font", size="13", auto_format=False),
                MessageStyle(offset=0, length=len(chunk), style="bold", auto_format=False),
                MessageStyle(offset=20, length=len(chunk), style="italic", auto_format=False)
            ])

            # Send each chunk as a separate message
            styled_message = Message(text=chunk, style=style)
            client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=500000)

    except ValueError as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)
    except Exception as e:
        error_message = Message(text=f"Lỗi khi xem Tử Vi: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)

def get_mitaizl():
    return {
        'tarot': handle_tarot_command,
        'tuvi': handle_tuvi_command
    }