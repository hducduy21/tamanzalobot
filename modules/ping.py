from zlapi.models import *
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import os

des = {
    'version': "1.0.0",
    'credits': "Nguyen Duc Tai",
    'description': "Xem ping của bot"
}
def handel_ping_command(message, message_object, thread_id, thread_type, author_id, client):
        start_time = time.time()
        reply_message = Message("Pinging Cutii Check Độ trễ >.<...🐰")
        client.replyMessage(reply_message,message_object, thread_id, thread_type,ttl=20000)

        end_time = time.time()
        ping_time = end_time - start_time

        text = f"🎾 Ping Pong! Độ trễ của Bot hiện tại là: {ping_time:.2f}ms"
        client.send(thread_id=thread_id, thread_type=thread_type, ttl=20000, message=Message(text))

def get_mitaizl():
    return {
    'ping': handel_ping_command
    }
