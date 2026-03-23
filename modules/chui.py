from zlapi.models import Message
import requests
import os
import time
from requests.exceptions import RequestException, HTTPError, JSONDecodeError
from urllib.parse import urlparse
import logging
import re

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

des = {
    'version': "1.0.8",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Gửi ảnh AI từ server"
}

# Cấu hình API
API_URL = os.getenv("IMAGE_API_URL", "http://160.30.21.47:3000/generate-image")
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'modules', 'cache')


def extract_prompt(message):
    """Tách prompt từ tin nhắn, bỏ từ khóa createanh hoặc .createanh nếu có."""
    message = message.strip()
    # Kiểm tra và bỏ tiền tố 'createanh' hoặc '.createanh'
    if message.lower().startswith("createanh"):
        return message[len("createanh"):].strip()
    elif message.lower().startswith(".createanh"):
        return message[len(".createanh"):].strip()
    return message


def fetch_image_url(prompt, max_retries=3, timeout=60):
    headers = {
        'User-Agent': 'CustomImageBot/1.0 (+https://example.com)',
        'Content-Type': 'application/json'
    }
    payload = {
        "prompt": prompt
    }
    logging.info(f"Payload gửi API: {payload}")

    for attempt in range(max_retries):
        try:
            logging.info(f"Gửi yêu cầu tới API: {API_URL}, thử lần {attempt + 1}/{max_retries}")
            response = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()

            try:
                json_data = response.json()
            except JSONDecodeError:
                raise ValueError("Phản hồi từ API không phải JSON hợp lệ")

            if json_data.get("success") and json_data.get("imageUrl"):
                logging.info(f"Nhận được imageUrl: {json_data['imageUrl']}")
                return json_data["imageUrl"]

            raise ValueError(f"Dữ liệu trả về không hợp lệ hoặc thiếu 'imageUrl': {json_data}")

        except HTTPError as e:
            error_detail = e.response.text if e.response else "Không có chi tiết lỗi"
            logging.error(f"Lỗi HTTP {e.response.status_code}: {error_detail}")
            if attempt == max_retries - 1:
                raise RequestException(f"Không thể lấy URL ảnh sau {max_retries} lần thử: {error_detail}")
            time.sleep(5 * (2 ** attempt))

        except (RequestException, ValueError) as e:
            logging.warning(f"Thử lần {attempt + 1}/{max_retries} thất bại: {str(e)}")
            if attempt == max_retries - 1:
                raise RequestException(f"Không thể lấy URL ảnh sau {max_retries} lần thử: {str(e)}")
            time.sleep(5 * (2 ** attempt))


def download_image(image_url, image_path, max_retries=3, timeout=10):
    headers = {
        'User-Agent': 'CustomImageBot/1.0 (+https://example.com)'
    }
    for attempt in range(max_retries):
        try:
            response = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                raise ValueError(f"URL không trả về ảnh: {content_type}")

            with open(image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if os.path.getsize(image_path) == 0:
                raise ValueError("File ảnh tải về rỗng")
            return True

        except (HTTPError, RequestException, ValueError) as e:
            if isinstance(e, HTTPError) and e.response.status_code in (429, 503):
                if attempt == max_retries - 1:
                    raise RequestException(f"Lỗi {e.response.status_code} khi tải ảnh {image_url} sau {max_retries} lần thử")
                time.sleep(5 * (attempt + 1))
            else:
                logging.warning(f"Thử tải ảnh lần {attempt + 1}/{max_retries} thất bại: {str(e)}")
                if attempt == max_retries - 1:
                    raise RequestException(f"Lỗi khi tải ảnh {image_url} sau {max_retries} lần thử: {str(e)}")
            time.sleep(2 ** attempt)


def handle_createanh_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)

        prompt = extract_prompt(message)

        if not prompt:
            client.sendMessage(Message(text="Vui lòng cung cấp mô tả cho ảnh (ví dụ: createanh một thành phố tương lai)!"), thread_id, thread_type)
            return

        if len(prompt) > 500:
            client.sendMessage(Message(text="Mô tả quá dài, vui lòng rút ngắn dưới 500 ký tự!"), thread_id, thread_type)
            return

        client.sendMessage(Message(text="Đang tạo ảnh, vui lòng đợi một chút..."), thread_id, thread_type)

        image_url = fetch_image_url(prompt)

        parsed_url = urlparse(image_url)
        ext = os.path.splitext(parsed_url.path)[1].lower() or '.png'
        if ext not in ('.jpg', '.jpeg', '.png'):
            raise ValueError(f"URL ảnh không hợp lệ: {image_url}")

        image_path = os.path.join(CACHE_DIR, f'temp_ai_image_{int(time.time())}{ext}')
        download_image(image_url, image_path)

        if not os.path.exists(image_path):
            raise FileNotFoundError("Không thể lưu ảnh tải về.")

        client.sendMultiLocalImage(
            imagePathList=[image_path],
            message=Message(text="Ảnh đã tạo xong, mời bạn xem nhé!"),
            thread_id=thread_id,
            thread_type=thread_type,
            width=1200,
            height=1600
        )

    except RequestException as e:
        client.sendMessage(Message(text=f"Đã xảy ra lỗi khi gọi API hoặc tải ảnh: {str(e)}"), thread_id, thread_type)
    except ValueError as e:
        client.sendMessage(Message(text=f"Lỗi: {str(e)}"), thread_id, thread_type)
    except Exception as e:
        client.sendMessage(Message(text=f"Lỗi không xác định: {str(e)}"), thread_id, thread_type)
    finally:
        try:
            if 'image_path' in locals() and os.path.exists(image_path):
                os.remove(image_path)
                logging.info(f"Đã xóa file tạm: {image_path}")
        except Exception as e:
            logging.error(f"Lỗi khi xóa file tạm: {str(e)}")


def get_mitaizl():
    return {
        'createanh': handle_createanh_command
    }
