import json
import os
import threading
import time
from datetime import datetime
import pytz
from zlapi.models import Message, ThreadType
from config import PREFIX, ADMIN
from utils.logging_utils import Logging

logger = Logging()
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Path to store auto-send data
DATA_FILE = 'modules/cache/autosend.json'

des = {
    'version': '1.0.3',  # Updated version for new command
    'credits': 'Nguyễn Liên Mạnh',
    'description': 'Quản lý tin nhắn gửi tự động hàng ngày theo nhóm'
}

def load_autosend_data():
    """Load auto-send data from JSON file."""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded autosend data: {json.dumps(data, ensure_ascii=False)}")
                return data
        logger.info("No autosend.json found, returning empty dict")
        return {}
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu autosend: {e}")
        return {}

def save_autosend_data(data):
    """Save auto-send data to JSON file."""
    try:
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Saved autosend data: {json.dumps(data, ensure_ascii=False)}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu autosend: {e}")

def get_current_time_vn():
    """Get current time in Vietnam timezone."""
    current_time = datetime.now(vn_tz)
    logger.info(f"Current time in VN: {current_time.strftime('%H:%M:%S %Y-%m-%d')}")
    return current_time

def parse_time(time_str):
    """Parse time string (HH:MM) to hours and minutes."""
    try:
        parsed_time = datetime.strptime(time_str, '%H:%M').time()
        logger.info(f"Parsed time string '{time_str}' to {parsed_time}")
        return parsed_time
    except ValueError:
        logger.error(f"Invalid time format for '{time_str}', expected HH:MM")
        return None

def auto_send_thread(client):
    """Background thread to check and send scheduled messages."""
    logger.info("Starting auto_send_thread")
    while True:
        try:
            current_time = get_current_time_vn()
            current_time_str = current_time.strftime('%H:%M')
            logger.info(f"Checking schedules at {current_time_str}")

            data = load_autosend_data()
            if not data:
                logger.info("No schedules found in autosend.json")
                time.sleep(60)
                continue

            for thread_id, schedules in data.items():
                logger.info(f"Processing thread_id: {thread_id}, schedules: {len(schedules)}")
                for schedule in schedules:
                    schedule_time = schedule['time']
                    logger.info(f"Checking schedule ID {schedule['id']}: time={schedule_time}, active={schedule.get('active', True)}")
                    if schedule_time == current_time_str and schedule.get('active', True):
                        last_sent = schedule.get('last_sent')
                        today_str = current_time.strftime('%Y-%m-%d')
                        logger.info(f"Schedule matched: last_sent={last_sent}, today={today_str}")
                        if last_sent != today_str:
                            try:
                                client.send(
                                    Message(text=schedule['message']),
                                    thread_id,
                                    ThreadType.GROUP
                                )
                                logger.success(f"Đã gửi tin nhắn tự động cho nhóm {thread_id} lúc {current_time_str}: {schedule['message']}")
                                schedule['last_sent'] = today_str
                                data[thread_id] = schedules
                                save_autosend_data(data)
                            except Exception as send_error:
                                logger.error(f"Failed to send message to thread {thread_id}: {send_error}")
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Lỗi trong auto_send_thread: {e}")
            time.sleep(60)

def handle_autosend_command(message, message_object, thread_id, thread_type, author_id, client):
    """Handle autosend commands."""
    if author_id not in ADMIN:
        client.replyMessage(
            Message(text="Chỉ admin mới có thể sử dụng lệnh này!"),
            message_object, thread_id, thread_type
        )
        return

    data = load_autosend_data()
    if thread_id not in data:
        data[thread_id] = []

    parts = message.split(maxsplit=2)
    if len(parts) < 2:
        client.replyMessage(
            Message(text=f"Sử dụng: {PREFIX}autosend [add|remove|list|clearall]"),
            message_object, thread_id, thread_type
        )
        return

    subcommand = parts[1].lower()

    if subcommand == 'add':
        if len(parts) < 3:
            client.replyMessage(
                Message(text=f"Sử dụng: {PREFIX}autosend add <HH:MM> <tin nhắn>"),
                message_object, thread_id, thread_type
            )
            return

        subparts = parts[2].split(maxsplit=1)
        if len(subparts) < 2:
            client.replyMessage(
                Message(text="Vui lòng cung cấp thời gian và tin nhắn!"),
                message_object, thread_id, thread_type
            )
            return

        time_str, send_message = subparts

        if not parse_time(time_str):
            client.replyMessage(
                Message(text="Định dạng thời gian không hợp lệ! Sử dụng HH:MM (VD: 08:00)"),
                message_object, thread_id, thread_type
            )
            return

        schedule_id = len(data[thread_id]) + 1
        data[thread_id].append({
            'id': schedule_id,
            'time': time_str,
            'message': send_message,
            'last_sent': None,
            'active': True
        })
        save_autosend_data(data)
        client.replyMessage(
            Message(text=f"Đã thêm tin nhắn tự động ID {schedule_id} cho nhóm này, gửi lúc {time_str} hàng ngày."),
            message_object, thread_id, thread_type
        )

    elif subcommand == 'remove':
        if len(parts) < 3:
            client.replyMessage(
                Message(text=f"Sử dụng: {PREFIX}autosend remove <ID> hoặc {PREFIX}autosend remove all"),
                message_object, thread_id, thread_type
            )
            return

        arg = parts[2].lower()
        if arg == 'all':
            data[thread_id] = []
            save_autosend_data(data)
            client.replyMessage(
                Message(text="Đã xóa tất cả tin nhắn tự động của nhóm này."),
                message_object, thread_id, thread_type
            )
            return

        try:
            schedule_id = int(arg)
            schedules = [s for s in data[thread_id] if s['id'] != schedule_id]
            if len(schedules) == len(data[thread_id]):
                client.replyMessage(
                    Message(text=f"Không tìm thấy tin nhắn tự động với ID {schedule_id}!"),
                    message_object, thread_id, thread_type
                )
                return
            data[thread_id] = schedules
            save_autosend_data(data)
            client.replyMessage(
                Message(text=f"Đã xóa tin nhắn tự động ID {schedule_id}."),
                message_object, thread_id, thread_type
            )
        except ValueError:
            client.replyMessage(
                Message(text="ID phải là một số!"),
                message_object, thread_id, thread_type
            )

    elif subcommand == 'list':
        if not data[thread_id]:
            client.replyMessage(
                Message(text="Nhóm này chưa có tin nhắn tự động nào!"),
                message_object, thread_id, thread_type
            )
            return

        msg = "[Danh sách tin nhắn tự động]\n"
        for schedule in data[thread_id]:
            msg += f"ID: {schedule['id']} | Thời gian: {schedule['time']} | Tin nhắn: {schedule['message']}\n"
        client.replyMessage(
            Message(text=msg),
            message_object, thread_id, thread_type
        )

    elif subcommand == 'clearall':
        data = {}
        save_autosend_data(data)
        logger.success(f"Đã xóa tất cả tin nhắn tự động của tất cả các nhóm bởi admin {author_id}")
        client.replyMessage(
            Message(text="Đã xóa tất cả tin nhắn tự động của tất cả các nhóm."),
            message_object, thread_id, thread_type
        )

    else:
        client.replyMessage(
            Message(text=f"Sử dụng: {PREFIX}autosend [add|remove|list|clearall]"),
            message_object, thread_id, thread_type
        )

def start_auto(client):
    """Start the auto-send thread."""
    logger.info("Starting autosend module")
    threading.Thread(target=auto_send_thread, args=(client,), daemon=True).start()

def get_mitaizl():
    return {
        'autosend': handle_autosend_command
    }