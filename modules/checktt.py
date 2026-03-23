import json
import os
from datetime import datetime
import pytz
import re
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType

# Module metadata
des = {
    'version': "1.1.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Xem thống kê tin nhắn cá nhân hoặc top 10 người nhắn nhiều nhất trong nhóm"
}

# Configuration
JSON_FILE = "modules/cache/message_counts.json"
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Initialize JSON file if it doesn't exist
def init_message_counts():
    if not os.path.exists(JSON_FILE):
        os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
        with open(JSON_FILE, 'w') as f:
            json.dump({}, f)

# Load message counts from JSON
def load_message_counts():
    try:
        with open(JSON_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        init_message_counts()
        return {}

# Save message counts to JSON
def save_message_counts(data):
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Get current time periods
def get_time_periods():
    now = datetime.now(VN_TZ)
    day = now.strftime('%Y-%m-%d')
    week = now.isocalendar()[1]
    year = now.year
    month = now.strftime('%Y-%m')
    return day, f"{year}-W{week:02d}", month

# Update message count for a user in a group
def update_message_count(uid, thread_id):
    data = load_message_counts()
    day, week, month = get_time_periods()

    # Initialize user data if not exists
    if thread_id not in data:
        data[thread_id] = {}
    if uid not in data[thread_id]:
        data[thread_id][uid] = {
            'daily': {},
            'weekly': {},
            'monthly': {},
            'total': 0
        }

    # Update counts
    user_data = data[thread_id][uid]
    user_data['daily'][day] = user_data['daily'].get(day, 0) + 1
    user_data['weekly'][week] = user_data['weekly'].get(week, 0) + 1
    user_data['monthly'][month] = user_data['monthly'].get(month, 0) + 1
    user_data['total'] += 1

    save_message_counts(data)

# Get personal message stats
def get_message_stats(uid, thread_id, client):
    data = load_message_counts()
    day, week, month = get_time_periods()

    if thread_id not in data or uid not in data[thread_id]:
        return None, "Người dùng chưa có tin nhắn trong nhóm này!"

    user_data = data[thread_id][uid]
    author_info = client.fetchUserInfo(uid).changed_profiles.get(uid, {})
    author_name = author_info.get('zaloName', 'Không xác định')

    daily_count = user_data['daily'].get(day, 0)
    weekly_count = user_data['weekly'].get(week, 0)
    monthly_count = user_data['monthly'].get(month, 0)
    total_count = user_data['total']

    msg = (
        f"[ Thống kê tin nhắn của {author_name} ]\n"
        f"📅 Hôm nay ({day}): {daily_count} tin nhắn\n"
        f"📆 Tuần này (Tuần {week}): {weekly_count} tin nhắn\n"
        f"🗓 Tháng này ({month}): {monthly_count} tin nhắn\n"
        f"🌟 Tổng cộng: {total_count} tin nhắn"
    )
    return msg, None

# Get top 10 message senders
def get_top_message_stats(thread_id, client):
    data = load_message_counts()

    if thread_id not in data or not data[thread_id]:
        return None, "Chưa có dữ liệu tin nhắn trong nhóm này!"

    user_counts = [(uid, stats.get('total', 0)) for uid, stats in data[thread_id].items()]
    top_users = sorted(user_counts, key=lambda x: x[1], reverse=True)[:10]

    lines = ["[ TOP 10 NGƯỜI GỬI TIN NHẮN ]"]
    for idx, (uid, count) in enumerate(top_users, start=1):
        author_info = client.fetchUserInfo(uid).changed_profiles.get(uid, {})
        name = author_info.get('zaloName', 'Không xác định')
        lines.append(f"{idx}. {name}: {count} tin nhắn")

    return "\n".join(lines), None

# Handle unified `checktt` command
def handle_checktt_command(message, message_object, thread_id, thread_type, author_id, client):
    if thread_type != ThreadType.GROUP:
        client.replyMessage(
            Message(text="Lệnh này chỉ hoạt động trong nhóm!"),
            message_object, thread_id, thread_type
        )
        return

    text = message.strip().lower()
    uid = author_id  # Mặc định là người gọi lệnh

    # Nếu là "checktt all"
    if "all" in text:
        msg, error = get_top_message_stats(thread_id, client)
    else:
        # Nếu có @id thì dùng id đó
        match = re.search(r'@(\d+)', text)
        if match:
            uid = match.group(1)
        msg, error = get_message_stats(uid, thread_id, client)

    if error:
        client.replyMessage(
            Message(text=error),
            message_object, thread_id, thread_type
        )
        return

    style = MultiMsgStyle([
        MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
        MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
        MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
        MessageStyle(offset=35, length=len(msg), style="italic", auto_format=False)
    ])
    styled_message = Message(text=msg, style=style)
    client.replyMessage(styled_message, message_object, thread_id, thread_type)

# Register command
def get_mitaizl():
    init_message_counts()
    return {
        'checktt': handle_checktt_command
    }
