from zlapi.models import Message
import requests
import random
import os
import urllib.parse
import math
from PIL import Image
from config import API_KEY

des = {
    'version': "1.0.12",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tạo và gửi ảnh banner/avatar (avtWibu2, avtWibu4, hoặc avtWibu5) với kích thước thực hoặc liệt kê danh sách theo trang"
}

def get_all_banners():
    """Fetch all banners from the listAvt API in a single call."""
    try:
        api_url = "https://nguyenmanh.name.vn/api/listAvt"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        banners = response.json()
        return banners if isinstance(banners, list) else []
    except Exception as e:
        print(f"Error fetching banners: {str(e)}")
        return []  # Return empty list on failure

def get_max_banner_id(banners):
    """Get the maximum banner ID from the list of banners."""
    max_id = 0
    for banner in banners:
        banner_id = banner.get('ID', 0)
        if isinstance(banner_id, int) and banner_id > max_id:
            max_id = banner_id
    return max_id if max_id > 0 else 10  # Fallback to 10 if no IDs found

def get_image_dimensions(image_path):
    """Get the width and height of an image file."""
    try:
        with Image.open(image_path) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"Error getting image dimensions: {str(e)}")
        return (1200, 1600)  # Fallback to default dimensions

def get_banner_help_message():
    """Generate help message for the 'banner' command."""
    help_text = (
        "🖼️ **Hướng dẫn sử dụng lệnh `banner`** 🖼️\n\n"
        "Lệnh: `banner [tùy chọn hoặc tham số]`\n"
        "- Tạo và gửi ảnh banner/avatar với loại (avtWibu2, avtWibu4, hoặc avtWibu5), ID, tên chính, tên Facebook (cho avtWibu2), và tên phụ.\n"
        "- Liệt kê danh sách các banner/avatar theo trang (20 mục mỗi trang).\n\n"
        "📜 **Các tùy chọn**:\n"
        "- `banner help` hoặc `banner guide`: Xem hướng dẫn này.\n"
        "- `banner list [page]`: Liệt kê ID, tên và màu của các banner/avatar trên trang được chỉ định (mặc định trang 1).\n"
        "- `banner [type] [id] [tenchinh] [fb] [tenphu]`: Tạo ảnh với loại (`avtWibu2`, `avtWibu4`, `avtWibu5`), ID (1 đến ID lớn nhất), tên chính, tên FB (cho avtWibu2), và tên phụ.\n"
        "- `banner`: Tạo ảnh với loại ngẫu nhiên, ID ngẫu nhiên và tên mặc định (ManhNk, ManhG, ManhICT).\n\n"
        "Ví dụ:\n"
        "- `banner avtWibu2 535 ManhNk ManhG ManhICT`: Tạo avatar avtWibu2 với ID 535, tên chính 'ManhNk', tên FB 'ManhG', tên phụ 'ManhICT'.\n"
        "- `banner avtWibu4 820 ManhNk ManhICT`: Tạo banner avtWibu4 với ID 820, tên chính 'ManhNk', tên phụ 'ManhICT'.\n"
        "- `banner avtWibu5 3 ManhNk ManhICT`: Tạo banner avtWibu5 với ID 3, tên chính 'ManhNk', tên phụ 'ManhICT'.\n"
        "- `banner`: Tạo ảnh với loại ngẫu nhiên và tên mặc định.\n"
        "- `banner list 2`: Xem danh sách trên trang 2.\n\n"
        "🎨 Tác giả: Nguyễn Liên Mạnh | Phiên bản: 1.0.12"
    )
    return Message(text=help_text)

def get_banner_list_message(page=1):
    """Generate message with the list of available banners for a specific page."""
    try:
        banners = get_all_banners()
        if not banners:
            return Message(text="Không thể lấy danh sách banner/avatar từ API.")

        # Paginate banners (20 per page)
        banners_per_page = 20
        total_banners = len(banners)
        total_pages = math.ceil(total_banners / banners_per_page)

        if page < 1 or page > total_pages:
            return Message(text=f"Trang {page} không hợp lệ. Vui lòng chọn trang từ 1 đến {total_pages}.")

        start_idx = (page - 1) * banners_per_page
        end_idx = start_idx + banners_per_page
        page_banners = banners[start_idx:end_idx]

        list_text = f"🖼️ **Danh sách banner/avatar (Trang {page}/{total_pages})** 🖼️\n\n"
        for banner in page_banners:
            banner_id = banner.get('ID', 'N/A')
            name = banner.get('name', 'Không có tên')
            color = banner.get('color', 'Không có màu')
            list_text += f"ID: {banner_id} | Tên: {name} | Màu: {color}\n"
        list_text += f"\n📜 Dùng `banner list [page]` để xem trang khác (tổng {total_pages} trang).\n🎨 Nguồn: Nguyễn Liên Mạnh"

        return Message(text=list_text)
    except Exception as e:
        return Message(text=f"Đã xảy ra lỗi khi lấy danh sách banner/avatar: {str(e)}")

def handle_banner_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Extract message text and clean it
        message_text = [part.strip() for part in message.strip().split() if part.strip()]

        # Check if user requested help or list
        if len(message_text) > 1 and message_text[1].lower() in ['help', 'guide']:
            client.sendMessage(get_banner_help_message(), thread_id, thread_type)
            return
        if len(message_text) > 1 and message_text[1].lower() == 'list':
            page = 1
            if len(message_text) > 2 and message_text[2].isdigit():
                page = int(message_text[2])
                if page < 1:
                    raise ValueError("Số trang phải lớn hơn 0")
            client.sendMessage(get_banner_list_message(page), thread_id, thread_type)
            return

        # Get all banners and max ID
        banners = get_all_banners()
        max_id = get_max_banner_id(banners)

        # Default values
        banner_type = random.choice(['avtWibu2', 'avtWibu4', 'avtWibu5'])
        banner_id = str(random.randint(1, max_id))  # Random ID from 1 to max_id
        tenchinh = "ManhNk"
        fb = "ManhG"
        tenphu = "ManhICT"

        # Parse user-provided parameters
        if len(message_text) > 1:
            banner_type_input = message_text[1].strip().lower()
            # Map lowercase input to correct API name
            type_mapping = {
                'avtwibu2': 'avtWibu2',
                'avtwibu4': 'avtWibu4',
                'avtwibu5': 'avtWibu5'
            }
            if banner_type_input not in type_mapping:
                raise ValueError(f"Loại phải là 'avtWibu2', 'avtWibu4', hoặc 'avtWibu5', nhận được '{banner_type_input}'")
            banner_type = type_mapping[banner_type_input]

        if len(message_text) > 2:
            try:
                banner_id = message_text[2].strip()
                # Validate ID (must be 1 to max_id)
                if not banner_id.isdigit() or int(banner_id) < 1 or int(banner_id) > max_id:
                    raise ValueError(f"ID phải là số từ 1 đến {max_id}")
            except ValueError:
                raise ValueError(f"ID phải là số từ 1 đến {max_id}")

        # Handle parameters based on banner_type
        if banner_type == 'avtWibu2':
            # For avtWibu2: tenchinh, fb, tenphu
            if len(message_text) < 6:
                tenchinh = message_text[3] if len(message_text) > 3 else tenchinh
                fb = message_text[4] if len(message_text) > 4 else fb
                tenphu = message_text[5] if len(message_text) > 5 else tenphu
            else:
                tenchinh = ' '.join(message_text[3:-2])
                fb = message_text[-2]
                tenphu = message_text[-1]
            # Validate parameters for avtWibu2
            if not tenchinh or not fb or not tenphu:
                raise ValueError("avtWibu2 yêu cầu tên chính, tên Facebook, và tên phụ không được rỗng")
        else:
            # For avtWibu4 and avtWibu5: tenchinh, tenphu
            if len(message_text) < 5:
                tenchinh = message_text[3] if len(message_text) > 3 else tenchinh
                tenphu = message_text[4] if len(message_text) > 4 else tenphu
            else:
                tenchinh = ' '.join(message_text[3:-1])
                tenphu = message_text[-1]

        # Validate parameter lengths (arbitrary max length to prevent API errors)
        max_length = 50  # Adjust based on API requirements if known
        for param, name in [(tenchinh, "tên chính"), (fb, "tên Facebook"), (tenphu, "tên phụ")]:
            if len(param) > max_length:
                raise ValueError(f"{name.capitalize()} không được dài quá {max_length} ký tự")

        # Encode parameters for URL
        encoded_tenchinh = urllib.parse.quote(tenchinh)
        encoded_tenphu = urllib.parse.quote(tenphu)
        encoded_fb = urllib.parse.quote(fb) if banner_type == 'avtWibu2' else ""

        # API endpoint for banner/avatar creation
        api_url = f"https://nguyenmanh.name.vn/api/{banner_type}?id={banner_id}&tenchinh={encoded_tenchinh}"
        if banner_type == 'avtWibu2':
            api_url += f"&fb={encoded_fb}"
        api_url += f"&tenphu={encoded_tenphu}&apikey={API_KEY}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        # Make API request
        response = requests.get(api_url, headers=headers, stream=True)
        response.raise_for_status()

        # Check if response is an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            raise ValueError(f"API trả về dữ liệu không phải hình ảnh: {content_type} (URL: {api_url})")

        # Save the image
        image_path = 'modules/cache/temp_banner.jpeg'
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Send the image if it exists
        if os.path.exists(image_path):
            # Get image dimensions
            width, height = get_image_dimensions(image_path)
            if banner_type == 'avtWibu2':
                t = Message(text=f"Đã tạo avatar {banner_type} (ID: {banner_id}, Tên chính: {tenchinh}, Tên FB: {fb}, Tên phụ: {tenphu})")
            else:
                t = Message(text=f"Đã tạo banner {banner_type} (ID: {banner_id}, Tên chính: {tenchinh}, Tên phụ: {tenphu})")
            client.sendMultiLocalImage(
                imagePathList=[image_path],
                message=t,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height
            )
            os.remove(image_path)
        else:
            raise FileNotFoundError("Không thể lưu ảnh")

    except requests.exceptions.HTTPError as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API")
        client.sendMessage(error_message, thread_id, thread_type,ttl=5000)
    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API")
        client.sendMessage(error_message, thread_id, thread_type,ttl=5000)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi")
        client.sendMessage(error_message, thread_id, thread_type,ttl=5000)

def get_mitaizl():
    return {
        'banner': handle_banner_command
    }