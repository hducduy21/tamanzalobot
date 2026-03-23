import random
import datetime
import pytz
from zlapi.models import Message, Mention

des = {
    'version': "1.0.5",
    'credits': "Nguyễn Liên Mạnh",
    'description': "chào"
}

GREETINGS = [
    "Tốt Lành 🥳", "Vui Vẻ 😄", "Hạnh Phúc ❤", "Yêu Đời 😘", 
    "May Mắn 🍀", "Full Năng Lượng ⚡", "Tuyệt Vời 😁", 
    "Tỉnh Táo 🤓", "Đầy Sức Sống 😽", "Nhiệt Huyết 🔥"
]

def chao(message, message_object, thread_id, thread_type, author_id, client):
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    current_time = datetime.datetime.now(tz).strftime('%H%M')
    hours = int(current_time)

    if 301 <= hours <= 400:
        session = "Sáng Tinh Mơ"
    elif 401 <= hours <= 700:
        session = "Sáng Sớm"
    elif 701 <= hours <= 1000:
        session = "Sáng"
    elif 1001 <= hours <= 1200:
        session = "Trưa"
    elif 1201 <= hours <= 1700:
        session = "Chiều"
    elif 1701 <= hours <= 1800:
        session = "Chiều Tà"
    elif 1801 <= hours <= 2100:
        session = "Tối"
    elif 2101 <= hours or hours <= 300:
        session = "Đêm"
    else:
        session = "Lỗi"

    greeting_text = random.choice(GREETINGS)
    response_text = f"Xin chào! Chúc Bạn Một Buổi {session} {greeting_text}"
    mention = Mention(author_id, length=7, offset=3)

    client.replyMessage(
        Message(
            text=response_text
        ),
        message_object,
        thread_id,
        thread_type
    )

    client.sendSticker(
        stickerType=7,
        stickerId=29557,
        cateId=10882,
        thread_id=thread_id,
        thread_type=thread_type
    )

def get_mitaizl():
    return dict.fromkeys(
        ['hello', 'hi', 'hai', 'chào', 'xin chào', 'chao', 'hí', 'lô', 
         'hú', 'hú hú', 'hê nhô', 'alo', 'a lô', 'a nhô'],
        chao
    )
