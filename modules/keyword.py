from zlapi.models import *
from zlapi.models import Message, ThreadType
from config import PREFIX, ADMIN
import json
import os
from utils.logging_utils import Logging

logger = Logging()

des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Quản lý danh sách từ khóa theo nhóm"
}

# File to store keywords
KEYWORD_FILE = "modules/cache/tukhoa.json"

def load_keywords():
    """Tải từ khóa từ tệp JSON."""
    try:
        if os.path.exists(KEYWORD_FILE):
            with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"group_keywords": {}, "global_keywords": []}
    except Exception as e:
        logger.error(f"Lỗi khi tải danh sách từ khóa: {e}")
        return {"group_keywords": {}, "global_keywords": []}

def save_keywords(data):
    """Lưu từ khóa vào tệp JSON."""
    try:
        with open(KEYWORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi khi lưu danh sách từ khóa: {e}")

def handle_keyword(message, message_object, thread_id, thread_type, author_id, client):
    """Xử lý lệnh keyword với các tham số add, remove, list cho nhóm cụ thể."""
    if author_id not in ADMIN:
        client.replyMessage(Message(text="Bạn không có quyền để thực hiện điều này!"), message_object, thread_id, thread_type, ttl=10000)
        return

    if thread_type != ThreadType.GROUP:
        client.replyMessage(Message(text="Lệnh này chỉ hoạt động trong nhóm!"), message_object, thread_id, thread_type, ttl=10000)
        return

    command_parts = message.split()
    if len(command_parts) < 2:
        client.replyMessage(Message(text=f"Vui lòng cung cấp hành động! Cách dùng: {PREFIX}keyword [add|remove|list] [từ khóa]"), message_object, thread_id, thread_type, ttl=10000)
        return

    action = command_parts[1].lower()
    data = load_keywords()

    # Initialize group keywords if not exist
    if thread_id not in data["group_keywords"]:
        data["group_keywords"][thread_id] = []

    keywords = data["group_keywords"][thread_id]

    if action == "add":
        if len(command_parts) < 3:
            client.replyMessage(Message(text="Vui lòng cung cấp từ khóa để thêm!"), message_object, thread_id, thread_type, ttl=10000)
            return
        keyword = " ".join(command_parts[2:]).lower()
        if keyword in keywords:
            client.replyMessage(Message(text=f"Từ khóa '{keyword}' đã tồn tại trong nhóm này!"), message_object, thread_id, thread_type, ttl=10000)
            return
        keywords.append(keyword)
        data["group_keywords"][thread_id] = keywords
        save_keywords(data)
        logger.info(f"Đã thêm từ khóa '{keyword}' cho nhóm {thread_id} bởi admin {author_id}")
        client.replyMessage(Message(text=f"Đã thêm từ khóa '{keyword}' cho nhóm này thành công!"), message_object, thread_id, thread_type, ttl=10000)

    elif action == "remove":
        if len(command_parts) < 3:
            client.replyMessage(Message(text="Vui lòng cung cấp từ khóa để xóa!"), message_object, thread_id, thread_type, ttl=10000)
            return
        keyword = " ".join(command_parts[2:]).lower()
        if keyword not in keywords:
            client.replyMessage(Message(text=f"Từ khóa '{keyword}' không tồn tại trong nhóm này!"), message_object, thread_id, thread_type, ttl=10000)
            return
        keywords.remove(keyword)
        data["group_keywords"][thread_id] = keywords
        save_keywords(data)
        logger.info(f"Đã xóa từ khóa '{keyword}' khỏi nhóm {thread_id} bởi admin {author_id}")
        client.replyMessage(Message(text=f"Đã xóa từ khóa '{keyword}' khỏi nhóm này thành công!"), message_object, thread_id, thread_type, ttl=10000)

    elif action == "list":
        if not keywords:
            client.replyMessage(Message(text="Danh sách từ khóa của nhóm này trống!"), message_object, thread_id, thread_type, ttl=10000)
            return
        keyword_list = "\n".join([f"- {kw}" for kw in keywords])
        client.replyMessage(Message(text=f"📋 Danh sách từ khóa của nhóm:\n{keyword_list}"), message_object, thread_id, thread_type, ttl=10000)
        logger.info(f"Đã liệt kê danh sách từ khóa của nhóm {thread_id} bởi admin {author_id}")

    else:
        client.replyMessage(Message(text=f"Hành động không hợp lệ! Cách dùng: {PREFIX}keyword [add|remove|list] [từ khóa]"), message_object, thread_id, thread_type, ttl=10000)

def get_mitaizl():
    return {
        'keyword': handle_keyword
    }