from zlapi.models import Message, MultiMsgStyle, MessageStyle
import requests
import json
from datetime import datetime
from config import CONNECTION_TIMEOUT

des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Xem kết quả Xổ số miền Bắc (XSMB) gần nhất"
}

XSMB_API_URL = "http://160.30.21.47:9999/v2/tien-ich/check-xsmb.json"

def fetch_xsmb_results():
    try:
        response = requests.get(XSMB_API_URL, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if 'data' not in data or not data['data']:
            raise ValueError("API response missing 'data' field or empty")

        valid_results = []
        current_date = datetime.now().strftime('%d/%m/%Y')

        for result in data['data']:
            date_str = result.get('date')
            if date_str == 'nay':
                # Replace 'nay' with current date
                result['date'] = current_date
                valid_results.append(result)
            else:
                try:
                    # Validate date format
                    datetime.strptime(date_str, '%d/%m/%Y')
                    valid_results.append(result)
                except ValueError:
                    # Skip results with invalid date formats
                    continue

        if not valid_results:
            raise ValueError("No valid XSMB results found")

        # Sort by date in descending order and return the most recent
        sorted_results = sorted(
            valid_results,
            key=lambda x: datetime.strptime(x['date'], '%d/%m/%Y'),
            reverse=True
        )
        return sorted_results[0]

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch XSMB results from API: {str(e)}")
    except (ValueError, KeyError) as e:
        raise Exception(f"Invalid API response: {str(e)}")

def handle_xsmb_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Fetch the most recent XSMB result
        result = fetch_xsmb_results()

        # Format the message
        msg = (
            f"[ KẾT QUẢ XSMB - {result['date']} ]\n"
            f"📅 {result['title'].strip()}\n\n"
            f"{result['message'].strip()}"
        )

        # Apply styling consistent with bot
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=20, length=len(msg), style="italic", auto_format=False)
        ])

        # Send styled message
        styled_message = Message(text=msg, style=style)
        client.replyMessage(styled_message, message_object, thread_id, thread_type,ttl=50000)

    except ValueError as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        # client.replyMessage(error_message, message_object, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Lỗi khi lấy kết quả XSMB: {str(e)}")
        # client.replyMessage(error_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'xsmb': handle_xsmb_command
    }