from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import API_KEY_HUNG
import requests
import json
import time
import threading

des = {
    'version': "1.0.1",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Gửi câu hỏi hài hước từ API Hỏi Ngố và chờ người dùng trả lời"
}

HOINGU_API_URL = "https://api.hungdev.id.vn/games/stupid-question?apikey=" + API_KEY_HUNG
ACTIVE_QUESTIONS = {}  # {thread_id: {'question': str, 'trueAnswer': str, 'timestamp': float}}
QUESTION_TIMEOUT = 60  # seconds
LOCK = threading.Lock()

def fetch_hoingu_question():
    try:
        response = requests.get(HOINGU_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('success') or 'data' not in data:
            raise ValueError("API response invalid or unsuccessful")

        question_data = data['data']
        return {
            'question': question_data.get('question', 'Không có câu hỏi'),
            'listAnswer': question_data.get('listAnswer', 'Không có đáp án'),
            'trueAnswer': question_data.get('trueAnswer', '').upper(),
            'detail': question_data.get('detail', 'Không có giải thích')
        }
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch question from API: {str(e)}")
    except (ValueError, KeyError) as e:
        raise Exception(f"Invalid API response: {str(e)}")

def cleanup_expired_questions():
    """Remove questions older than QUESTION_TIMEOUT."""
    with LOCK:
        current_time = time.time()
        expired = [thread_id for thread_id, data in ACTIVE_QUESTIONS.items()
                   if current_time - data['timestamp'] > QUESTION_TIMEOUT]
        for thread_id in expired:
            del ACTIVE_QUESTIONS[thread_id]

def handle_hoingu_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Clean up expired questions
        cleanup_expired_questions()

        # Check if a question is already active in this thread
        with LOCK:
            if thread_id in ACTIVE_QUESTIONS:
                error_message = Message(text="Đã có một câu hỏi đang chờ trả lời! Vui lòng trả lời trước khi hỏi câu mới.")
                client.replyMessage(error_message, message_object, thread_id, thread_type)
                return

        # Fetch question data
        question_data = fetch_hoingu_question()

        # Store the active question
        with LOCK:
            ACTIVE_QUESTIONS[thread_id] = {
                'question': question_data['question'],
                'trueAnswer': question_data['trueAnswer'],
                'timestamp': time.time()
            }

        # Format the question message
        msg = (
            f"[ HỎI NGỐ ]\n"
            f"❓ Câu hỏi: {question_data['question']}\n"
            f"📝 Đáp án:\n{question_data['listAnswer']}\n"
            f"💬 Reply với đáp án (A, B, C, hoặc D) trong {QUESTION_TIMEOUT} giây!"
        )

        # Apply styling
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=10, length=len(msg), style="italic", auto_format=False)
        ])

        # Send styled message
        styled_message = Message(text=msg, style=style)
        client.replyMessage(styled_message, message_object, thread_id, thread_type,ttl=60000)

    except Exception as e:
        error_message = Message(text=f"Lỗi khi lấy câu hỏi Hỏi Ngố: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def check_answer(thread_id, answer, client, message_object, thread_type, author_id):
    """Check if the user's answer is correct and respond."""
    cleanup_expired_questions()

    with LOCK:
        if thread_id not in ACTIVE_QUESTIONS:
            return False  # No active question

        question_data = ACTIVE_QUESTIONS[thread_id]
        true_answer = question_data['trueAnswer']
        question = question_data['question']

        # Validate answer
        if answer.upper() not in ['A', 'B', 'C', 'D']:
            return False  # Invalid answer format

        # Prepare response
        is_correct = answer.upper() == true_answer
        detail = question_data.get('detail', 'Không có giải thích nào được cung cấp.')
        if is_correct:
            result = f"🎉 Đúng rồi!\n📖 Giải thích: {detail}"
        else:
            result = f"😅 Sai rồi! Đáp án đúng là {true_answer}\n📖 Giải thích: {detail}"

        author_info = client.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
        author_name = author_info.get('zaloName', 'Người dùng')

        msg = (
            f"[ KẾT QUẢ HỎI NGỐ ]\n"
            f"👤 {author_name} trả lời: {answer.upper()}\n"
            f"❓ Câu hỏi: {question}\n"
            f"📌 Kết quả: {result}"
        )

        # Apply styling
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=15, length=len(msg), style="italic", auto_format=False)
        ])

        # Send response
        styled_message = Message(text=msg, style=style)
        client.replyMessage(styled_message, message_object, thread_id, thread_type,ttl=20000)

        # Clear the question
        del ACTIVE_QUESTIONS[thread_id]
        return True

def get_mitaizl():
    return {
        'hoingu': handle_hoingu_command
    }