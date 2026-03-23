import requests
import os
from datetime import datetime
from zlapi.models import Message, ZaloAPIException
from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO

des = {
    'version': "1.0.3",
    'credits': "Nguyễn Liên Mạnh",
    'description': "info người dùng(tag)"
}

def create_canvas(user_data):
    background_path = "modules/cache/nen.jpeg"
    if not os.path.exists(background_path):
        raise FileNotFoundError(f"Ảnh nền không tìm thấy: {background_path}")
    background_image = Image.open(background_path).convert("RGB")
    draw = ImageDraw.Draw(background_image)

    bg_width, bg_height = background_image.size

    avatar_url = user_data.get('avatar')
    if avatar_url:
        response = requests.get(avatar_url)
        avatar_image = Image.open(BytesIO(response.content)).convert("RGB")
    else:
        avatar_default_path = "modules/cache/default_avatar.jpg"
        if not os.path.exists(avatar_default_path):
            raise FileNotFoundError(f"Ảnh avatar mặc định không tìm thấy: {avatar_default_path}")
        avatar_image = Image.open(avatar_default_path).convert("RGB")

    avatar_size = (400, 400)
    avatar_image = ImageOps.fit(avatar_image, avatar_size, centering=(0.5, 0.5))

    mask = Image.new("L", avatar_size, 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0) + avatar_size, fill=255)
    avatar_image.putalpha(mask)

    avatar_x = bg_width - avatar_size[0] - 50
    avatar_y = 80
    background_image.paste(avatar_image, (avatar_x, avatar_y), avatar_image)

    font_path = "modules/cache/UTM-AvoBold.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font không tìm thấy: {font_path}")

    font_title = ImageFont.truetype(font_path, 40)
    font_info = ImageFont.truetype(font_path, 35)
    font_bio = ImageFont.truetype(font_path, 28)

    info_x = 50
    y = 50
    spacing = 60

    # Tên
    draw.text((info_x, y), "Tên:", font=font_title, fill=(255, 0, 0))
    draw.text((info_x + 200, y + 8), user_data.get('displayName', 'N/A'), font=font_info, fill=(255, 255, 255))

    # ID
    y += spacing
    draw.text((info_x, y), "ID:", font=font_title, fill=(0, 255, 255))
    draw.text((info_x + 200, y + 8), user_data.get('userId', 'N/A'), font=font_info, fill=(255, 255, 255))

    # Username
    y += spacing
    draw.text((info_x, y), "Username:", font=font_title, fill=(255, 255, 255))
    draw.text((info_x + 200, y + 8), user_data.get('username', 'N/A'), font=font_info, fill=(255, 255, 255))

    # Số điện thoại
    y += spacing
    draw.text((info_x, y), "Số điện thoại:", font=font_title, fill=(255, 0, 255))
    draw.text((info_x + 250, y + 8), user_data.get('phoneNumber', 'Chưa có'), font=font_info, fill=(255, 255, 255))

    # Giới tính
    y += spacing
    gender = {0: "Nam", 1: "Nữ"}.get(user_data.get('gender'), "Khác")
    draw.text((info_x, y), "Giới tính:", font=font_title, fill=(255, 255, 0))
    draw.text((info_x + 220, y + 8), gender, font=font_info, fill=(255, 255, 255))

    # Ngày sinh
    y += spacing
    dob = user_data.get('dob')
    dob_str = datetime.fromtimestamp(dob).strftime('%d/%m/%Y') if dob else "N/A"
    draw.text((info_x, y), "Sinh nhật:", font=font_title, fill=(0, 255, 0))
    draw.text((info_x + 220, y + 8), dob_str, font=font_info, fill=(255, 255, 255))

    # Ngày tạo tài khoản
    y += spacing
    created_ts = user_data.get('createdTs')
    created_str = datetime.fromtimestamp(created_ts).strftime('%d/%m/%Y %H:%M:%S') if created_ts else "Không rõ"
    draw.text((info_x, y), "Tạo tài khoản:", font=font_title, fill=(255, 165, 0))
    draw.text((info_x + 320, y + 8), created_str, font=font_info, fill=(255, 255, 255))

    # Bio / Status
    y += spacing
    draw.text((info_x, y), "Tiểu sử:", font=font_title, fill=(255, 192, 203))
    bio_text = user_data.get('status', 'Không có')
    bio_lines = bio_text.split("\n")
    bio_start_y = y + 50
    for line in bio_lines:
        draw.text((info_x + 50, bio_start_y), line, font=font_bio, fill=(255, 255, 255))
        bio_start_y += 40

    canvas_path = "output_canvas.png"
    background_image.save(canvas_path)
    return canvas_path

def handle_user_info(message, message_object, thread_id, thread_type, author_id, client):
    try:
        input_value = message.split()[1].lower() if len(message.split()) > 1 else author_id
        if message_object.mentions:
            input_value = message_object.mentions[0]['uid']

        user_id_data = client.fetchPhoneNumber(input_value, language="vi") or {}
        user_id_to_fetch = user_id_data.get('uid', input_value)
        user_info = client.fetchUserInfo(user_id_to_fetch) or {}
        user_data = user_info.get('changed_profiles', {}).get(user_id_to_fetch, {})

        canvas_path = create_canvas(user_data)

        if os.path.exists(canvas_path):
            client.sendLocalImage(
                canvas_path,
                message=None,
                thread_id=thread_id,
                thread_type=thread_type,
                width=2323,
                height=1039
            )
            os.remove(canvas_path)

    except (ValueError, ZaloAPIException) as e:
        client.replyMessage(Message(text=f"Error: {str(e)}"), message_object, thread_id, thread_type)
    except FileNotFoundError as e:
        client.replyMessage(Message(text=f"Lỗi file: {str(e)}"), message_object, thread_id, thread_type)
    except Exception as e:
        client.replyMessage(Message(text=f"Đã xảy ra lỗi không mong muốn: {str(e)}"), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'userinfo': handle_user_info
    }
