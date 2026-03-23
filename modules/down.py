import re
import os
import requests
from zlapi.models import Message
from bs4 import BeautifulSoup
import json
import ffmpeg
from config import API_KEY_HUNG, CONNECTION_TIMEOUT
from urllib.parse import quote
from PIL import Image

des = {
    'version': "1.0.8",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tải video hoặc ảnh từ link (capcut, tiktok, youtube, facebook, douyin, pinterest, ig,...)"
}

def get_video_dimensions(video_url):
    """Extract the width and height of a video using ffmpeg."""
    try:
        probe = ffmpeg.probe(video_url)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream:
            return int(video_stream['width']), int(video_stream['height'])
        raise ValueError("Không thể lấy kích thước video")
    except Exception as e:
        raise Exception(f"Lỗi khi lấy kích thước video: {str(e)}")

def get_image_dimensions(image_path):
    """Extract the width and height of an image using PIL."""
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        raise Exception(f"Lỗi khi lấy kích thước ảnh: {str(e)}")

def handle_down_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip()
    video_link = message_object.href if message_object.href else None

    def extract_links(content):
        urls = re.findall(r'(https?://[^\s]+)', content)
        soup = BeautifulSoup(content, 'html.parser')
        href_links = [a['href'] for a in soup.find_all('a', href=True)]
        return urls + href_links

    if not video_link:
        links = extract_links(content)
        if not links:
            error_message = Message(text="Vui lòng nhập một đường link cần down hợp lệ.")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return
        video_link = links[0].strip()

    def downall(video_link):
        try:
            encoded_url = quote(video_link, safe='')
            api_url = f'https://api.hungdev.id.vn/medias/down-aio?url={encoded_url}&apikey={API_KEY_HUNG}'
            response = requests.get(api_url, timeout=CONNECTION_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            if not (data.get('success') and data.get('data')):
                raise ValueError("API không trả về dữ liệu hợp lệ")

            medias = data['data'].get('medias', [])
            title = data['data'].get('title', 'Không có tiêu đề')
            duration = data['data'].get('duration', 0)  # In milliseconds or string (e.g., "6:36")
            thumbnail = data['data'].get('thumbnail', None)

            image_links = []
            video_info = None
            audio_info = None

            # Supported extensions
            video_extensions = ['mp4']
            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
            audio_extensions = ['mp3', 'm4a', 'wav']
            quality_priority = ['hd_no_watermark', 'no_watermark', 'Full HD', 'HD', 'SD', '360p', 'watermark']

            for media in medias:
                media_type = media.get('type')
                quality = media.get('quality')
                extension = media.get('extension', '').lower()

                if media_type == 'image' and extension in image_extensions:
                    image_links.append({
                        'url': media.get('url'),
                        'quality': quality,
                        'extension': extension
                    })
                elif media_type == 'video' and extension in video_extensions:
                    if not video_info or (quality in quality_priority and quality_priority.index(quality) < quality_priority.index(video_info['quality']) if video_info else float('inf')):
                        video_info = {
                            'url': media.get('url'),
                            'quality': quality,
                            'thumbnail': media.get('thumbnail'),
                            'extension': extension
                        }
                elif media_type == 'audio' and extension in audio_extensions:
                    audio_info = {
                        'url': media.get('url'),
                        'quality': quality,
                        'extension': extension
                    }

            return image_links, video_info, audio_info, title, duration, thumbnail

        except requests.exceptions.RequestException as e:
            raise Exception(f"Đã xảy ra lỗi khi gọi API: {str(e)}")
        except ValueError as e:
            raise Exception(f"Lỗi dữ liệu API: {str(e)}")
        except Exception as e:
            raise Exception(f"Đã xảy ra lỗi không xác định: {str(e)}")

    try:
        image_links, video_info, audio_info, title, duration, thumbnail = downall(video_link)
        sendtitle = title  # Only include title
        headers = {'User-Agent': 'Mozilla/5.0'}

        os.makedirs('modules/cache', exist_ok=True)

        # Handle images
        if image_links:
            image_paths = []
            for index, img in enumerate(image_links):
                image_response = requests.get(img['url'], headers=headers, timeout=5)
                image_response.raise_for_status()
                image_path = f'modules/cache/{index + 1}.{img["extension"]}'
                
                with open(image_path, 'wb') as f:
                    f.write(image_response.content)

                # Get dimensions from the downloaded image
                width, height = get_image_dimensions(image_path)
                
                image_paths.append(image_path)

            if all(os.path.exists(image_path) for image_path in image_paths):
                # Use dimensions of the first image for sending
                width, height = get_image_dimensions(image_paths[0])
                
                message_to_send = Message(text=sendtitle)
                client.sendMultiLocalImage(
                    imagePathList=image_paths, 
                    message=message_to_send,
                    thread_id=thread_id,
                    thread_type=thread_type,
                    width=width,
                    height=height,
                    ttl=500000
                )
                for image_path in image_paths:
                    os.remove(image_path)

        # Handle video
        if video_info:
            # Get dimensions from the video URL
            width, height = get_video_dimensions(video_info['url'])
            
            messagesend = Message(text=sendtitle)
            thumbnailUrl = video_info['thumbnail'] or thumbnail or 'https://f59-zpg-r.zdn.vn/jpg/3574552058519415218/d156abc8a66e1f30467f.jpg'
            duration_secs = str(duration // 1000) if isinstance(duration, int) else duration

            client.sendRemoteVideo(
                video_info['url'], 
                thumbnailUrl,
                duration=duration_secs,
                message=messagesend,
                thread_id=thread_id,
                thread_type=thread_type,
                width=width,
                height=height,
                ttl=500000
            )

        # Handle audio
        if audio_info:
            messagesend = Message(text=sendtitle)
            # Convert duration to seconds if it's a string like "6:36"
            if isinstance(duration, str) and ':' in duration:
                minutes, seconds = map(int, duration.split(':'))
                duration_secs = minutes * 60 + seconds
            else:
                duration_secs = duration // 1000 if isinstance(duration, int) else 60

            # Get file size (optional, if required by sendRemoteVoice)
            try:
                audio_response = requests.head(audio_info['url'], headers=headers, timeout=5)
                file_size = int(audio_response.headers.get('content-length', 0))
            except:
                file_size = None

            client.sendRemoteVoice(
                voiceUrl=audio_info['url'],
                thread_id=thread_id,
                thread_type=thread_type,
                fileSize=file_size,
                ttl=500000
            )

        # Handle no media case
        if not image_links and not video_info and not audio_info:
            error_message = Message(text="Không tìm thấy video, ảnh hoặc âm thanh với yêu cầu.")
            client.sendMessage(error_message, thread_id, thread_type)
    
    except Exception as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'down': handle_down_command
    }