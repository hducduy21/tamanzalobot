import requests
import os
import time
from requests.exceptions import RequestException
from zlapi.models import Message
from utils.logging_utils import Logging

# Initialize logger
logger = Logging()

des = {
    'version': "1.0.3",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tạo ảnh AI từ prompt và gửi về chat"
}

def download_image(image_url, image_path, max_retries=3, timeout=10):
    """Tải ảnh từ URL với retry logic."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    for attempt in range(max_retries):
        try:
            response = requests.get(image_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            with open(image_path, 'wb') as f:
                f.write(response.content)
            return True
        except RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to download image {image_url} after {max_retries} retries: {e}")
                return False
            time.sleep(2)
    return False

def handle_taoanh_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        prompt = message.strip()
        if prompt.lower().startswith(('.taoanh', 'taoanh')):
            prompt = prompt.replace('.taoanh', '', 1).replace('taoanh', '', 1).strip()
        if not prompt:
            client.sendMessage(
                Message(text="Vui lòng nhập mô tả hình ảnh (prompt) sau lệnh, ví dụ: .taoanh A cat drinking coffee in space."),
                thread_id,
                thread_type,
                ttl=10000
            )
            return

        # Send waiting message
        waiting_message = Message(text=f"🎨 Đang đợi AI tạo ảnh cho: '{prompt}'\nVui lòng chờ trong giây lát...")
        client.sendMessage(waiting_message, thread_id, thread_type, ttl=1000)

        api_url = "http://160.30.21.47:3000/generate-image"
        headers = {'Content-Type': 'application/json'}
        payload = {"prompt": prompt}

        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        json_data = response.json()

        if not json_data.get('success') or not json_data.get('imageUrl'):
            raise ValueError("API returned error or no image")

        image_url = json_data['imageUrl']
        cache_dir = 'modules/cache'
        os.makedirs(cache_dir, exist_ok=True)
        ext = os.path.splitext(image_url)[1].lower() or '.jpg'
        image_path = os.path.join(cache_dir, f"taoanh_result{ext}")

        if not download_image(image_url, image_path):
            raise ValueError("Failed to download image")

        if os.path.exists(image_path):
            message = Message(text=f"🖼 Hình ảnh cho prompt: '{prompt}'")
            client.sendMultiLocalImage(
                imagePathList=[image_path],
                message=message,
                thread_id=thread_id,
                thread_type=thread_type,
                width=800,
                height=800,
                ttl=5000000
            )
            os.remove(image_path)
        else:
            raise ValueError("Image file not found")

    except RequestException as e:
        logger.error(f"Network error in taoanh command: {e}")
        client.sendMessage(
            Message(text="⚠️ Lỗi kết nối khi tạo ảnh. Vui lòng thử lại sau!"),
            thread_id,
            thread_type,
            ttl=10000
        )
    except ValueError as e:
        logger.error(f"Validation error in taoanh command: {e}")
        client.sendMessage(
            Message(text="⚠️ Không thể tạo ảnh lúc này. Vui lòng kiểm tra mô tả và thử lại!"),
            thread_id,
            thread_type,
            ttl=10000
        )
    except Exception as e:
        logger.error(f"Unexpected error in taoanh command: {e}")
        client.sendMessage(
            Message(text="⚠️ Có lỗi xảy ra khi tạo ảnh. Vui lòng thử lại sau!"),
            thread_id,
            thread_type,
            ttl=10000
        )

def get_mitaizl():
    return {
        'taoanh': handle_taoanh_command
    }