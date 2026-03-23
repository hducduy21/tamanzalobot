from zlapi.models import Message, MultiMsgStyle, MessageStyle
from config import GOOGLE_AI_API_KEY
import requests
import json
import time

des = {
    'version': "1.0.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Hỏi AI bằng Google Generative AI API (Gemini)"
}

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

def ask_gemini(question, retries=3):
    for attempt in range(retries):
        try:
            if not GOOGLE_AI_API_KEY:
                raise ValueError("API key không được cấu hình")

            # Prepare payload
            payload = {
                "contents": [{
                    "parts": [{"text": question}]
                }]
            }

            # Send POST request
            response = requests.post(
                f"{GEMINI_API_URL}?key={GOOGLE_AI_API_KEY}",
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            # Parse response
            data = response.json()
            
            # Check for blocked response due to safety filters
            if 'promptFeedback' in data and data.get('promptFeedback', {}).get('blockReason'):
                raise ValueError("Câu hỏi bị chặn do vi phạm chính sách an toàn của API")

            # Check for candidates
            if 'candidates' not in data or not data['candidates']:
                raise ValueError("Không nhận được phản hồi từ AI")
            
            # Extract answer
            candidate = data['candidates'][0]
            if 'content' not in candidate or 'parts' not in candidate['content'] or not candidate['content']['parts']:
                raise ValueError("Phản hồi từ AI trống hoặc không hợp lệ")
            
            answer = candidate['content']['parts'][0].get('text', '')
            if not answer:
                raise ValueError("Phản hồi từ AI trống")

            return answer.strip()

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1)  # Wait before retrying
                continue
            raise Exception(f"Lỗi khi gọi API AI: {str(e)}")
        except (ValueError, KeyError) as e:
            raise Exception(f"Phản hồi AI không hợp lệ: {str(e)}")

def handle_askai_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Parse command: /askai <question>
        parts = message.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            error_message = Message(text="Vui lòng nhập câu hỏi cho AI. Ví dụ: /askai AI hoạt động như thế nào?")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return

        question = parts[1].strip()

        # Get AI response
        answer = ask_gemini(question)

        # Format message
        msg = (
            f"[ HỎI AI ]\n"
            f"❓ Câu hỏi: {question}\n"
            f"🤖 Trả lời: {answer}"
        )

        # Apply styling consistent with bot
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=10, length=len(msg), style="italic", auto_format=False)
        ])

        # Send styled message
        styled_message = Message(text=msg, style=style)
        client.replyMessage(styled_message, message_object, thread_id, thread_type)

    except Exception as e:
        error_message = Message(text=f"Lỗi khi hỏi AI: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'askai': handle_askai_command
    }