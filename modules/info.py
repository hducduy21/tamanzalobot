import requests
import os
from zlapi.models import Message, ZaloAPIException
from datetime import datetime

des = {
    'version': "1.4.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Lấy thông tin nhóm"
}

def handle_group_info_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        group_info = client.fetchGroupInfo(thread_id)

        if not isinstance(group_info, dict):
            group_info = group_info.__dict__

        grid_info = group_info.get('gridInfoMap', {}).get(thread_id, {})

        group_id = grid_info.get('groupId', 'N/A')
        group_name = grid_info.get('name', 'N/A')
        description = grid_info.get('desc', 'N/A')
        group_type = grid_info.get('type', 'N/A')
        creator_id = grid_info.get('creatorId', 'N/A')
        version = grid_info.get('version', 'N/A')
        total_member = grid_info.get('totalMember', 'N/A')
        max_member = grid_info.get('maxMember', 'N/A')
        visibility = grid_info.get('visibility', 'N/A')
        global_id = grid_info.get('globalId', 'N/A')
        e2ee = grid_info.get('e2ee', 'N/A')
        has_more_member = grid_info.get('hasMoreMember', 'N/A')
        sub_type = grid_info.get('subType', 'N/A')
        group_avatar = grid_info.get('fullAvt', None)

        created_time_raw = grid_info.get('createdTime', 'N/A')
        created_time = 'N/A'
        days_since_creation = 'N/A'
        if created_time_raw != 'N/A' and isinstance(created_time_raw, (int, float)):
            created_datetime = datetime.fromtimestamp(created_time_raw / 1000)
            created_time = created_datetime.strftime('%d/%m/%Y %H:%M:%S')
            now = datetime.now()
            days_since_creation = (now - created_datetime).days

        setting = grid_info.get('setting', {})
        def format_switch(val):
            return 'Bật' if val == 1 else 'Tắt'

        block_name = format_switch(setting.get('blockName', 0))
        sign_admin_msg = format_switch(setting.get('signAdminMsg', 0))
        add_member_only = format_switch(setting.get('addMemberOnly', 0))
        set_topic_only = format_switch(setting.get('setTopicOnly', 0))
        enable_msg_history = format_switch(setting.get('enableMsgHistory', 0))
        lock_create_post = format_switch(setting.get('lockCreatePost', 0))
        lock_create_poll = format_switch(setting.get('lockCreatePoll', 0))
        join_approval = format_switch(setting.get('joinAppr', 0))
        ban_feature = format_switch(setting.get('bannFeature', 0))
        dirty_media = format_switch(setting.get('dirtyMedia', 0))
        ban_duration = setting.get('banDuration', 'N/A')
        lock_send_msg = format_switch(setting.get('lockSendMsg', 0))
        lock_view_member = format_switch(setting.get('lockViewMember', 0))

        extra_info = grid_info.get('extraInfo', {})
        enable_media_store = format_switch(extra_info.get('enable_media_store', 0))

        group_info_message = (
            f"Group Info:\n"
            f"ID nhóm: {group_id}\n"
            f"Tên nhóm: {group_name}\n"
            f"Mô tả: {description}\n"
            f"Loại nhóm: {group_type}\n"
            f"ID người tạo: {creator_id}\n"
            f"Phiên bản: {version}\n"
            f"Tổng số thành viên: {total_member}\n"
            f"Số thành viên tối đa: {max_member}\n"
            f"Thời gian tạo: {created_time}\n"
            f"Số ngày tồn tại: {days_since_creation} ngày\n"
            f"Chế độ hiển thị: {visibility}\n"
            f"ID toàn cầu: {global_id}\n"
            f"Mã hóa E2EE: {e2ee}\n"
            f"Có thêm thành viên: {has_more_member}\n"
            f"Loại phụ: {sub_type}\n"
            f"\nCài đặt nhóm:\n"
            f"- Chặn đổi tên: {block_name}\n"
            f"- Ký tên tin nhắn admin: {sign_admin_msg}\n"
            f"- Chỉ admin thêm thành viên: {add_member_only}\n"
            f"- Chỉ admin đặt chủ đề: {set_topic_only}\n"
            f"- Lịch sử tin nhắn: {enable_msg_history}\n"
            f"- Khóa tạo bài viết: {lock_create_post}\n"
            f"- Khóa tạo bình chọn: {lock_create_poll}\n"
            f"- Phê duyệt tham gia: {join_approval}\n"
            f"- Tính năng cấm: {ban_feature}\n"
            f"- Nội dung không phù hợp: {dirty_media}\n"
            f"- Thời gian cấm: {ban_duration}\n"
            f"- Khóa gửi tin nhắn: {lock_send_msg}\n"
            f"- Khóa xem thành viên: {lock_view_member}\n"
            f"\nThông tin bổ sung:\n"
            f"- Lưu trữ media: {enable_media_store}\n"
        )

        message_to_send = Message(text=group_info_message)

        if group_avatar:
            image_response = requests.get(group_avatar)
            image_path = 'modules/cache/default_avatar.jpeg'

            with open(image_path, 'wb') as f:
                f.write(image_response.content)

            client.sendLocalImage(
                image_path,
                message=message_to_send,
                thread_id=thread_id,
                thread_type=thread_type
            )
            os.remove(image_path)
        else:
            client.sendMessage(message_to_send, thread_id, thread_type)

        return group_info

    except ZaloAPIException:
        error_message = Message(text="Could not retrieve group info.")
        client.sendMessage(error_message, thread_id, thread_type)
        return None
    except Exception as e:
        error_message = Message(text=f"An unexpected error occurred: {str(e)}")
        client.sendMessage(error_message, thread_id, thread_type)
        return None

def get_mitaizl():
    return {
        'info': handle_group_info_command
    }
