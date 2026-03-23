from zlapi.models import Message
import requests
import os

des = {
    'version': "1.0.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Lấy thông tin người dùng tiktok từ id"
}

def handle_tiktokinfo_command(message, message_object, thread_id, thread_type, author_id, client):
    content = message.strip().split()

    if len(content) < 2:
        error_message = Message(text="❌ Vui lòng nhập một ID TikTok cần lấy thông tin.")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
        return

    iduser = content[1].strip()

    try:
        api_url = f'https://www.tikwm.com/api/user/info?unique_id={iduser}'  # FIXED f-string
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        if data.get('code') != 0:
            raise KeyError("API trả về kết quả không thành công.")

        user = data['data'].get('user', {})
        stats = data['data'].get('stats', {})

        if not user:
            raise KeyError("Không tìm thấy thông tin người dùng từ API.")

        uid = user.get('id')
        username = user.get('uniqueId')
        name = user.get('nickname')
        tieusu = user.get('signature', "Không có")
        lkig = user.get('ins_id') or 'Chưa có liên kết nào'
        lkx = user.get('twitter_id') or 'Chưa có liên kết nào'
        lkytb = user.get('youtube_channel_title') or 'Chưa có liên kết nào'
        avt = user.get('avatarMedium')

        tim = stats.get('heart', 0)
        dangfl = stats.get('followingCount', 0)
        sofl = stats.get('followerCount', 0)
        tongvd = stats.get('videoCount', 0)

        gui = (
            f"📌 Thông tin TikTok người dùng:\n"
            f"• Tên: {name}\n"
            f"• ID TikTok: {uid}\n"
            f"• Username: {username}\n"
            f"• Tiểu sử: {tieusu}\n"
            f"• 👥 Số follower: {sofl}\n"
            f"• 👤 Đang follow: {dangfl}\n"
            f"• 🎥 Số video: {tongvd}\n"
            f"• ❤️ Tổng tim: {tim}\n"
            f"• 🔗 Liên kết mạng xã hội:\n"
            f"   - Instagram: {lkig}\n"
            f"   - YouTube: {lkytb}\n"
            f"   - Twitter: {lkx}"
        )

        messagesend = Message(text=gui)

        if avt:
            image_response = requests.get(avt)
            image_path = 'modules/cache/temp_tiktok.jpeg'

            with open(image_path, 'wb') as f:
                f.write(image_response.content)

            client.sendLocalImage(
                image_path,
                message=messagesend,
                thread_id=thread_id,
                thread_type=thread_type,
                width=2500,
                height=2500
            )

            os.remove(image_path)
        else:
            client.sendMessage(messagesend, thread_id, thread_type)

    except requests.exceptions.RequestException as e:
        error_message = Message(text=f"❗ Lỗi khi gọi API: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except KeyError as e:
        error_message = Message(text=f"⚠️ Dữ liệu API sai định dạng: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"❌ Lỗi không xác định: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)

def get_mitaizl():
    return {
        'tiktokinfo': handle_tiktokinfo_command
    }
