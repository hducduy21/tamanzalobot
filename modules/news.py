from zlapi.models import Message
import requests
import urllib.parse
from config import API_KEY
des = {
    'version': "1.0.4",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Gửi tin tức ngẫu nhiên hoặc tìm kiếm theo từ khóa"
}

def get_news_help_message():
    """Generate help message for the 'news' command."""
    help_text = (
        "📰 **Hướng dẫn sử dụng lệnh `news`** 📰\n\n"
        "Lệnh: `news [tùy chọn hoặc từ khóa]`\n"
        "- Gửi tất cả các mô tả tin tức mới nhất nếu không cung cấp từ khóa.\n"
        "- Tìm kiếm và gửi tất cả các tin tức theo từ khóa được chỉ định nếu có từ khóa.\n\n"
        "📜 **Các tùy chọn**:\n"
        "- `news help` hoặc `news guide`: Xem hướng dẫn này.\n"
        "- `news [từ khóa]`: Tìm kiếm tin tức theo từ khóa (ví dụ: `news công nghệ`).\n"
        "- `news`: Gửi tất cả các mô tả tin tức mới nhất.\n\n"
        "Ví dụ:\n"
        "- `news công nghệ`: Tìm kiếm tất cả tin tức về công nghệ.\n"
        "- `news bóng đá`: Tìm kiếm tất cả tin tức về bóng đá.\n"
        "- `news`: Gửi tất cả các mô mô tả tin tức mới nhất.\n\n"
        "🎨 Tác giả: Nguyễn Liên Mạnh | Phiên bản: 1.0.4"
    )
    return Message(text=help_text)

def handle_news_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Extract message text and convert to lowercase
        message_text = message.lower().strip().split()

        # Check if user requested help
        if len(message_text) > 1 and message_text[1] in ['help', 'guide']:
            client.sendMessage(get_news_help_message(), thread_id, thread_type)
            return

        # Determine if search query is provided
        query = ' '.join(message_text[1:]) if len(message_text) > 1 else None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        # Use appropriate API based on whether query is provided
        if query:
            # Use search API
            encoded_query = urllib.parse.quote(query)
            api_url = f"https://nguyenmanh.name.vn/api/newSearch?query={encoded_query}&apikey={API_KEY}"
        else:
            # Use general news API
            api_url = "https://nguyenmanh.name.vn/api/news?apikey=GfQGXP86"

        # Make API request
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        json_data = response.json()

        # Validate API response
        if json_data.get('status') != 200:
            raise ValueError("Dữ liệu tin tức không hợp lệ")

        news_text = ""
        if query:
            # Handle search API response
            if 'result' in json_data and len(json_data['result']) > 0:
                news_text += f"📰 **Kết quả tìm kiếm cho '{query}'**:\n\n"
                for idx, result in enumerate(json_data['result'], 1):
                    title = result.get('title', 'Không có tiêu đề')
                    description = result.get('desc', 'Không có mô tả')
                    link = result.get('link', 'Không có liên kết')
                    news_text += (
                        f"**{idx}. {title}**\n"
                        f"📝 Chi tiết: {description}\n"
                        f"🔗 Liên kết: {link}\n\n"
                    )
                news_text += "🎨 Nguồn: Nguyễn Liên Mạnh"
            else:
                raise ValueError("Không tìm thấy tin tức cho từ khóa này")
        else:
            # Handle general news API response
            if 'result' in json_data:
                news_data = json_data['result']
                title = news_data.get('title', 'Không có tiêu đề')
                descriptions = [desc for desc in news_data.get('description', []) if desc.strip()]
                link = news_data.get('link', 'Không có liên kết')
                if not descriptions:
                    raise ValueError("Không có mô tả tin tức hợp lệ")
                news_text += f"📰 **Tin tức**: {title}\n\n"
                for idx, desc in enumerate(descriptions, 1):
                    news_text += f"📝 {idx}. {desc}\n"
                news_text += f"\n🔗 **Liên kết**: {link}\n\n🎨 Nguồn: Nguyễn Liên Mạnh"
            else:
                raise ValueError("Dữ liệu tin tức không hợp lệ")

        # Send the news message
        news_message = Message(text=news_text)
        client.sendMessage(news_message, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Đã xảy ra lỗi khi gọi API tin tức: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Đã xảy ra lỗi: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'news': handle_news_command
    }