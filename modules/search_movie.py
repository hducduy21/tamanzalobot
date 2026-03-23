import requests
from config import CONNECTION_TIMEOUT
from zlapi.models import Message
from urllib.parse import quote

# Dictionary mô tả module
des = {
    'version': "1.0.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tìm kiếm phim và lấy hai link_embed đầu tiên từ tập phim sử dụng API phimapi.com"
}

def handle_timphim_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Tìm kiếm phim dựa trên từ khóa và lấy hai link_embed đầu tiên từ API phimapi.com.
    Trả về danh sách phim với thông tin chi tiết, URL phim, và hai link_embed.
    """
    # Tách từ khóa từ tin nhắn
    keyword = message.strip()
    if keyword.startswith('.timphim'):
        keyword = keyword[len('.timphim'):].strip()
    elif keyword.startswith('timphim'):
        keyword = keyword[len('timphim'):].strip()

    # Kiểm tra từ khóa
    if not keyword:
        error_message = Message(text="Vui lòng nhập từ khóa để tìm kiếm phim (ví dụ: .timphim conan).")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return

    try:
        # URL API tìm kiếm phim
        search_api_url = f"https://phimapi.com/v1/api/tim-kiem?keyword={quote(keyword)}"
        
        # Gửi yêu cầu GET đến API tìm kiếm
        response = requests.get(search_api_url, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()

        # Phân tích dữ liệu JSON
        data = response.json()
        if data.get('status') != 'success' or not data.get('data', {}).get('items'):
            error_message = Message(text=f"Không tìm thấy phim nào với từ khóa '{keyword}'.")
            client.sendMessage(error_message, thread_id, thread_type)
            return

        # Lấy danh sách phim
        movies = data['data']['items']
        result_text = f"Kết quả tìm kiếm cho '{keyword}' ({len(movies)} phim):\n\n"

        # Giới hạn số lượng phim hiển thị (5 phim)
        for movie in movies[:5]:
            name = movie.get('name', 'Không rõ')
            slug = movie.get('slug', '')
            origin_name = movie.get('origin_name', 'Không rõ')
            movie_type = movie.get('type', 'Không rõ')
            time = movie.get('time', 'Không rõ')
            episode_current = movie.get('episode_current', 'Không rõ')
            quality = movie.get('quality', 'Không rõ')
            lang = movie.get('lang', 'Không rõ')
            year = movie.get('year', 'Không rõ')
            
            # Tạo URL phim
            movie_url = f"https://kkphim.vip/phim/{slug}" if slug else "Không có URL"

            # Truy cập API chi tiết phim để lấy hai link_embed
            links_text = "📋 Link xem:\n"
            if slug:
                try:
                    detail_api_url = f"https://phimapi.com/phim/{slug}"
                    detail_response = requests.get(detail_api_url, timeout=CONNECTION_TIMEOUT)
                    detail_response.raise_for_status()
                    detail_data = detail_response.json()

                    if detail_data.get('status') and detail_data.get('episodes'):
                        # Thu thập tất cả link_embed từ episodes
                        link_embeds = []
                        for server in detail_data['episodes']:
                            for ep in server.get('server_data', []):
                                if ep.get('link_embed'):
                                    link_embeds.append(ep['link_embed'])
                        
                        # Lấy hai link_embed đầu tiên
                        if link_embeds:
                            links_text += f"  - Link 1: {link_embeds[0]}\n"
                            if len(link_embeds) > 1:
                                links_text += f"  - Link 2: {link_embeds[1]}\n"
                            else:
                                links_text += "  - Link 2: Không có\n"
                        else:
                            links_text += "  - Không có link\n"
                    else:
                        links_text += "  - Không tìm thấy link\n"
                except requests.exceptions.RequestException as e:
                    links_text = f"  - Lỗi khi lấy link: {str(e)}\n"
                except ValueError:
                    links_text = "  - Lỗi dữ liệu chi tiết phim\n"
            else:
                links_text += "  - Không có slug để lấy link\n"

            # Định dạng thông tin phim
            result_text += (
                f"🎬 {name}\n"
                f"📜 Tên gốc: {origin_name}\n"
                f"🎭 Loại: {movie_type}\n"
                f"⏱ Thời lượng: {time}\n"
                f"📺 Tập hiện tại: {episode_current}\n"
                f"📽 Chất lượng: {quality}\n"
                f"🗣 Ngôn ngữ: {lang}\n"
                f"📅 Năm: {year}\n"
                f"🔗 URL: {movie_url}\n"
                f"{links_text}"
                f"{'-'*30}\n"
            )

        # Nếu có nhiều hơn 5 phim, thông báo số lượng còn lại
        if len(movies) > 5:
            result_text += f"...và {len(movies) - 5} phim khác. Vui lòng tìm kiếm cụ thể hơn để xem thêm."

        # Gửi kết quả
        message_to_send = Message(text=result_text)
        client.replyMessage(message_to_send, message_object, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"Lỗi khi gọi API tìm kiếm phim: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except ValueError as e:
        error_message = Message(text=f"Lỗi dữ liệu API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    """
    Đăng ký lệnh timphim cho module timphim.
    """
    return {
        'timphim': handle_timphim_command
    }