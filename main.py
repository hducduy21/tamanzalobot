import time
import os
import sys
import shutil
import sqlite3
import subprocess
import json
import random
from config import API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES, ADMIN, CONNECTION_TIMEOUT
from zlapi.models import *
from zlapi.models import Message, MultiMsgStyle, MessageStyle, ThreadType, GroupEventType
import threading
from mitaizl import CommandHandler
from zlapi import ZaloAPI, ZaloAPIException
from colorama import Fore, Style, init
from utils.logging_utils import Logging
from datetime import datetime
import pytz
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from modules.checktt import update_message_count
from modules.hoingu import check_answer
from modules.autosend import load_autosend_data, save_autosend_data
import traceback
import gc
from contextlib import contextmanager
from functools import wraps
from utils.resource_monitor import resource_monitor

temp_thread_storage = {}
uid = "776580269332100397"

init()

colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA, Fore.WHITE]

text = """
████████╗ █████╗ ███╗   ███╗     █████╗ ███╗   ██╗     ███████╗██╗  ██╗ ██████╗ ██████╗ 
╚══██╔══╝██╔══██╗████╗ ████║    ██╔══██╗████╗  ██║     ██╔════╝██║  ██║██╔═══██╗██╔══██╗
   ██║   ███████║██╔████╔██║    ███████║██╔██╗ ██║     ███████╗███████║██║   ██║██████╔╝
   ██║   ██╔══██║██║╚██╔╝██║    ██╔══██║██║╚██╗██║     ╚════██║██╔══██║██║   ██║██╔═
   ██║   ██║  ██║██║ ╚═╝ ██║    ██║  ██║██║ ╚████║     ███████║██║  ██║╚██████╔╝██║ 
   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝    ╚═╝  ╚═╝╚═╝  ╚═══╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝ 
"""
for i, char in enumerate(text):
    color = colors[i % len(colors)]
    print(color + char, end='')

logger = Logging()

colors1 = [
    "FF9900", "FFFF33", "33FFFF", "FF99FF", "FF3366", "FFFF66", "FF00FF", "66FF99", "00CCFF", 
    "FF0099", "FF0066", "0033FF", "FF9999", "00FF66", "00FFFF", "CCFFFF", "8F00FF", "FF00CC", 
    "FF0000", "FF1100", "FF3300", "FF4400", "FF5500", "FF6600", "FF7700", "FF8800", "FF9900", 
    "FFaa00", "FFbb00", "FFcc00", "FFdd00", "FFee00", "FFff00", "FFFFFF", "FFEBCD", "F5F5DC", 
    "F0FFF0", "F5FFFA", "F0FFFF", "F0F8FF", "FFF5EE", "F5F5F5"
]

# Decorator for error handling
def safe_execute(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                logger.error(f"Timeout in {func.__name__} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error in {func.__name__} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        return None
    return wrapper

# Context manager for resource cleanup
@contextmanager
def managed_resource(resource):
    try:
        yield resource
    finally:
        if hasattr(resource, 'close'):
            try:
                resource.close()
            except:
                pass

class ResetBot:
    def __init__(self, reset_interval=38800):
        self.reset_event = threading.Event()
        self.reset_interval = reset_interval
        self.load_autorestart_setting()
        self._lock = threading.Lock()

    def load_autorestart_setting(self):
        try:
            with open("seting.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
                self.autorestart = settings.get("autorestart", "False") == "True"
            
            if self.autorestart:
                logger.restart("Auto restart mode is enabled")
                threading.Thread(target=self.reset_code_periodically, daemon=True).start()
            else:
                logger.restart("Auto restart mode is disabled")
        except Exception as e:
            logger.error(f"Error loading autorestart config: {e}")
            self.autorestart = False

    def reset_code_periodically(self):
        while not self.reset_event.is_set():
            try:
                time.sleep(self.reset_interval)
                logger.restart("Initiating bot restart...")
                self.restart_bot()
            except Exception as e:
                logger.error(f"Error in reset_code_periodically: {e}")

    def restart_bot(self):
        try:
            with self._lock:
                current_time = datetime.now().strftime("%H:%M:%S")
                gui_message = f"Bot restarted successfully at: {current_time}"
                logger.restart(gui_message)
                
                # Cleanup before restart
                resource_monitor.stop_monitoring()
                gc.collect()
                
                python = sys.executable
                os.execl(python, python, *sys.argv)
        except Exception as e:
            logger.error(f"Error restarting bot: {e}")

init(autoreset=True)

@safe_execute
def create_notification_image(self, event_message, group_name, formatted_time, member_name, count, avatar_url):
    background_path = "modules/cache/banner.png"
    if not os.path.exists(background_path):
        raise FileNotFoundError(f"Background image not found: {background_path}")
    
    background_image = None
    avatar_path = None
    
    try:
        logger.info(f"[DEBUG] Creating notification image for: {member_name}")
        background_image = Image.open(background_path).convert("RGB")
        draw = ImageDraw.Draw(background_image)

        bg_width, bg_height = background_image.size
        logger.info(f"[DEBUG] Background size: {bg_width}x{bg_height}")
        
        font_path = "modules/cache/UTM-AvoBold.ttf"
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"Font not found: {font_path}")
        font_title = ImageFont.truetype(font_path, 40)
        font_info = ImageFont.truetype(font_path, 35)

        info_x = 50
        y = 50
        spacing = 60
        avatar_size = (650, 650)

        try:
            if avatar_url:
                logger.info(f"[DEBUG] Fetching avatar from: {avatar_url}")
                response = self.session.get(avatar_url, timeout=CONNECTION_TIMEOUT)
                if response.status_code == 200:
                    avatar_path = "temp_avatar.png"
                    with open(avatar_path, "wb") as f:
                        f.write(response.content)
                    
                    with managed_resource(Image.open(avatar_path).convert("RGBA")) as avatar_image:
                        avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)

                        mask = Image.new("L", avatar_size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=255)
                        circular_avatar = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
                        circular_avatar.putalpha(mask)

                        avatar_x = (bg_width - avatar_size[0]) // 2 + 490
                        avatar_y = (bg_height - avatar_size[1]) // 2 + 12
                        if avatar_x + avatar_size[0] > bg_width:
                            avatar_x = bg_width - avatar_size[0]
                        background_image.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
                        logger.info(f"[DEBUG] Avatar processed successfully")
                else:
                    logger.warning(f"[DEBUG] Failed to fetch avatar, status: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching or processing avatar: {str(e)}")
            default_avatar_path = "modules/cache/default_avatar.png"
            if os.path.exists(default_avatar_path):
                try:
                    logger.info(f"[DEBUG] Using default avatar")
                    with managed_resource(Image.open(default_avatar_path).convert("RGBA")) as avatar_image:
                        avatar_image = avatar_image.resize(avatar_size, Image.Resampling.LANCZOS)
                        mask = Image.new("L", avatar_size, 0)
                        mask_draw = ImageDraw.Draw(mask)
                        mask_draw.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=255)
                        circular_avatar = ImageOps.fit(avatar_image, mask.size, centering=(0.5, 0.5))
                        circular_avatar.putalpha(mask)
                        avatar_x = (bg_width - avatar_size[0]) // 2 + 80
                        avatar_y = (bg_height - avatar_size[1]) // 2
                        if avatar_x + avatar_size[0] > bg_width:
                            avatar_x = bg_width - avatar_size[0]
                        background_image.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
                except Exception as inner_e:
                    logger.error(f"Error with default avatar: {inner_e}")

        y += spacing
        group_x = min(info_x + 130, 250)
        if len(group_name) > 21:
            group_name = group_name[:18] + "..."
        draw.text((group_x, y + 310), f"{group_name}", font=font_info, fill=(0, 0, 0))

        y += spacing
        random_color = tuple(random.randint(0, 255) for _ in range(3))
        draw.text((info_x, y + 430), event_message, font=font_info, fill=random_color)

        y += spacing
        groups_x = min(info_x + 240, 250)
        draw.text((groups_x, y + 295), f"Thành viên: {count}", font=font_info, fill=(255, 165, 0))

        y += spacing
        draw.text((info_x, 650), f"Thời gian: {formatted_time}", font=font_info, fill=(0, 255, 0))

        canvas_path = "notification_canvas.png"
        background_image.save(canvas_path)
        logger.info(f"[DEBUG] Notification image saved to: {canvas_path}")
        return canvas_path
        
    finally:
        # Cleanup resources
        if avatar_path and os.path.exists(avatar_path):
            try:
                os.remove(avatar_path)
            except:
                pass
        if background_image:
            try:
                background_image.close()
            except:
                pass

@safe_execute
def noti(self, event_data, event_type):
    if event_type == GroupEventType.UNKNOWN:
        logger.info(f"[DEBUG] Skipping UNKNOWN event type")
        return
    
    try:
        current_time = datetime.now()
        formatted_time = current_time.strftime("%d/%m/%Y [%H:%M:%S]")
        thread_id = event_data['groupId']
        
        logger.info(f"[DEBUG] Processing event type: {event_type} for group: {thread_id}")
        
        group_info = self.fetchGroupInfo(thread_id)
        if group_info and thread_id in group_info.gridInfoMap:
            tt = group_info.gridInfoMap[thread_id]['totalMember']
        else:
            tt = 0
            logger.warning(f"[DEBUG] Could not fetch group info for: {thread_id}")

        logger.info(f"[DEBUG] updateMembers data: {event_data.get('updateMembers', [])}")

        if event_type == GroupEventType.JOIN:
            name_gr = event_data.groupName
            for i, member in enumerate(event_data.updateMembers, start=0):
                member_id = member['id']
                name = member['dName']
                avatar = member.get('avatar', None)
                count = tt + i
                logger.info(f"[DEBUG] Processing JOIN member {i}: ID={member_id}, Name={name}, Count={count}, Avatar={avatar}")
                event_message = f"Chào mừng {name} tham gia nhóm!"
                welcome_message = f"[ MITAI PROJECT NOTIFICATION GROUP ]\n> Chào mừng: {name}\n> Bạn là thành viên thứ: {count}\n> Đã tham gia nhóm: {name_gr}."

                canvas_path = create_notification_image(self, event_message, name_gr, formatted_time, name, count, avatar)
                if canvas_path and os.path.exists(canvas_path):
                    try:
                        self.sendLocalImage(
                            canvas_path,
                            message=None,
                            thread_id=thread_id,
                            thread_type=ThreadType.GROUP,
                            width=2323,
                            height=1039,
                            ttl=60000
                        )
                        logger.info(f"[DEBUG] Sent welcome image for: {name}")
                    finally:
                        try:
                            os.remove(canvas_path)
                        except:
                            pass

                style = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(welcome_message), style="color", color="ff6347", auto_format=False),
                    MessageStyle(offset=0, length=len(welcome_message), style="font", size="13", auto_format=False),
                    MessageStyle(offset=0, length=len(welcome_message), style="bold", auto_format=False),
                    MessageStyle(offset=39, length=len(welcome_message), style="italic", auto_format=False)
                ])
                styled_message = Message(text=welcome_message, style=style)

        elif event_type == GroupEventType.LEAVE or event_type == GroupEventType.REMOVE_MEMBER:
            name_gr = event_data.groupName
            for i, member in enumerate(event_data.updateMembers, start=0):
                member_id = member['id']
                name = member['dName']
                avatar = member.get('avatar', None)
                count = tt - i
                event_action = 'REMOVE' if event_type == GroupEventType.REMOVE_MEMBER else 'LEAVE'
                logger.info(f"[DEBUG] Processing {event_action} member {i}: ID={member_id}, Name={name}, Count={count}, Avatar={avatar}")
                if event_type == GroupEventType.REMOVE_MEMBER:
                    event_message = f"{name} đã bị xóa khỏi nhóm."
                    farewell_message = f"[ MITAI PROJECT NOTIFICATION GROUP ]\n> {name} bị xoá khỏi nhóm\n> Nhóm: {name_gr}.\n> Vào lúc: {formatted_time}\n> Tổng thành viên còn lại: {count}."
                else:
                    event_message = f"{name} đã rời nhóm."
                    farewell_message = f"[ MITAI PROJECT NOTIFICATION GROUP ]\n> {name} đã out nhóm\n> Nhóm: {name_gr}.\n> Vào lúc: {formatted_time}\n> Tổng thành viên còn lại: {count}."

                canvas_path = create_notification_image(self, event_message, name_gr, formatted_time, name, count, avatar)
                if canvas_path and os.path.exists(canvas_path):
                    try:
                        self.sendLocalImage(
                            canvas_path,
                            message=None,
                            thread_id=thread_id,
                            thread_type=ThreadType.GROUP,
                            width=2323,
                            height=1039,
                            ttl=60000
                        )
                        logger.info(f"[DEBUG] Sent farewell image for: {name}")
                    finally:
                        try:
                            os.remove(canvas_path)
                        except:
                            pass

                style = MultiMsgStyle([
                    MessageStyle(offset=0, length=len(farewell_message), style="color", color="ff6347", auto_format=False),
                    MessageStyle(offset=0, length=len(farewell_message), style="font", size="13", auto_format=False),
                    MessageStyle(offset=0, length=len(farewell_message), style="bold", auto_format=False),
                    MessageStyle(offset=39, length=len(farewell_message), style="italic", auto_format=False)
                ])
                styled_message = Message(text=farewell_message, style=style)

    except FileNotFoundError as e:
        logger.error(f"FileNotFoundError: {str(e)}")
    except Exception as e:
        logger.error(f"General error in noti: {str(e)}\n{traceback.format_exc()}")

def hex_to_ansi(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'\033[38;2;{r};{g};{b}m'

@safe_execute
def check_autosend_messages(self):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    data = load_autosend_data()
    current_time = datetime.now(vn_tz)
    current_time_str = current_time.strftime('%H:%M')

    try:
        for thread_id, schedules in data.items():
            for schedule in schedules:
                if schedule['time'] == current_time_str and schedule.get('active', True):
                    last_sent = schedule.get('last_sent')
                    today_str = current_time.strftime('%Y-%m-%d')
                    if last_sent != today_str:
                        self.send(
                            Message(text=schedule['message']),
                            thread_id,
                            ThreadType.GROUP
                        )
                        logger.success(f"Sent auto message to group {thread_id} at {current_time_str}")
                        schedule['last_sent'] = today_str
                        data[thread_id] = schedules
                        save_autosend_data(data)
    except Exception as e:
        logger.error(f"Error sending auto message: {e}")

class Client(ZaloAPI):
    subprocess.Popen(['python3', 'utils/clearCPU.py'])

    def __init__(self, api_key, secret_key, imei, session_cookies, *args, reset_interval=7200, **kwargs):
        super().__init__(api_key, secret_key, imei=imei, session_cookies=session_cookies)
        self.command_handler = CommandHandler(self)
        self.reset_bot = ResetBot(reset_interval)
        self.group_info_cache = {}
        self.last_sms_times = {}
        self.session = requests.Session()
        self.restricted_keywords = self.load_restricted_keywords()
        self._message_lock = threading.Lock()
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set timeouts
        self.session.request = lambda *args, **kwargs: requests.Session.request(
            self.session, *args, timeout=kwargs.get('timeout', CONNECTION_TIMEOUT), **kwargs
        )

        logger.logger('EVENT GROUP', 'Starting to receive group events...')
        
        # Start resource monitoring
        resource_monitor.start_monitoring()
        logger.info("[DEBUG] Resource monitor started")

    def load_restricted_keywords(self):
        """Load group-specific and global restricted keywords from tukhoa.json."""        
        try:
            keyword_file = "modules/cache/tukhoa.json"
            if not os.path.exists(keyword_file):
                logger.error(f"Keyword file not found: {keyword_file}")
                return {"group_keywords": {}, "global_keywords": []}
            with open(keyword_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            group_keywords = {
                group_id: [keyword.lower() for keyword in keywords]
                for group_id, keywords in data.get("group_keywords", {}).items()
            }
            global_keywords = [keyword.lower() for keyword in data.get("global_keywords", [])]
            logger.info(f"[DEBUG] Loaded {len(global_keywords)} global keywords and {len(group_keywords)} group keyword sets")
            return {
                "group_keywords": group_keywords,
                "global_keywords": global_keywords
            }
        except Exception as e:
            logger.error(f"Error loading restricted keywords: {e}")
            return {"group_keywords": {}, "global_keywords": []}

    def contains_restricted_keyword(self, message_text, thread_id):
        """Check if the message contains restricted keywords for the group or globally."""        
        if not isinstance(message_text, str):
            return False
        message_text = message_text.lower()
        
        # Check group-specific keywords
        group_keywords = self.restricted_keywords["group_keywords"].get(thread_id, [])
        if any(keyword in message_text for keyword in group_keywords):
            logger.info(f"[DEBUG] Found group-specific restricted keyword in message")
            return True
        
        # Check global keywords
        if any(keyword in message_text for keyword in self.restricted_keywords["global_keywords"]):
            logger.info(f"[DEBUG] Found global restricted keyword in message")
            return True
            
        return False

    def run_autosend_check(self):
        while True:
            try:
                self.check_autosend_messages()
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in autosend check: {e}")
                time.sleep(60)

    def onEvent(self, event_data, event_type):
        try:
            logger.info(f"[DEBUG] Received event: {event_type}")
            thread = threading.Thread(target=noti, args=(self, event_data, event_type), daemon=True)
            thread.start()
        except Exception as e:
            logger.error(f"Error in onEvent: {e}")

    @safe_execute
    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        try:
            with self._message_lock:
                logger.info(f"[DEBUG] Processing message ID: {mid} from author: {author_id}")
                update_message_count(author_id, thread_id)

                # Check restricted keywords and delete message if found, but not for bot
                try:
                    message_text = message.text if isinstance(message, Message) else str(message)
                    if author_id != uid and self.contains_restricted_keyword(message_text, thread_id) and thread_type == ThreadType.GROUP:
                        logger.info(f"Detected restricted keyword in message '{message_text}' from {author_id} in group {thread_id}")
                        try:
                            if not hasattr(message_object, 'cliMsgId'):
                                logger.error(f"cliMsgId not found in message_object: {message_object.__dict__}")
                                self.send(Message(text="Error: Missing cliMsgId to delete message."), thread_id, ThreadType.GROUP)
                                return
                            deleted_msg = self.deleteGroupMsg(
                                mid,
                                str(author_id),
                                message_object.cliMsgId,
                                thread_id
                            )
                            if deleted_msg.status == 0:
                                logger.success(f"Deleted message {mid} containing restricted keyword in group {thread_id}")
                            else:
                                logger.error(f"Failed to delete message {mid}: Status {deleted_msg.status}")
                        except ZaloAPIException as e:
                            logger.error(f"Cannot delete message {mid}: {e}")
                        return
                except Exception as e:
                    logger.error(f"Error checking restricted keywords: {e}")

                if isinstance(message, str) and message.strip().upper() in ['A', 'B', 'C', 'D']:
                    if check_answer(thread_id, message.strip(), self, message_object, thread_type, author_id):
                        logger.info(f"[DEBUG] Answer check handled for message: {message}")
                        return

                if isinstance(message, str):
                    logger.info(f"[DEBUG] Handling command: {message[:50]}...")
                    self.command_handler.handle_command(message, author_id, message_object, thread_id, thread_type)
                        
                try:
                    author_info = self.fetchUserInfo(author_id).changed_profiles.get(author_id, {})
                    author_name = author_info.get('zaloName', 'Unknown')

                    group_info = self.fetchGroupInfo(thread_id)
                    group_name = group_info.gridInfoMap.get(thread_id, {}).get('name', 'None')
                    if group_name == 'None':
                        group_name = 'Private Chat'

                    current_time = time.strftime("%H:%M:%S - %d/%m/%Y", time.localtime())

                    colors_selected = random.sample(colors1, 9)
                    output = (
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}------------------------------{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}• Message: {message_text}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[1])}{Style.BRIGHT}• Message ID: {mid}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[2])}{Style.BRIGHT}• USER ID: {author_id}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[6])}{Style.BRIGHT}• USER NAME: {author_name}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[3])}{Style.BRIGHT}• GROUP ID: {thread_id}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[4])}{Style.BRIGHT}• GROUP NAME: {group_name}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[5])}{Style.BRIGHT}• TYPE: {thread_type}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[7])}{Style.BRIGHT}• RECEIVED AT: {current_time}{Style.RESET_ALL}\n"
                        f"{hex_to_ansi(colors_selected[0])}{Style.BRIGHT}------------------------------{Style.RESET_ALL}"
                    )
                    print(output)

                    if author_id == uid:
                        logger.info(f"[DEBUG] Skipping bot's own message")
                        return

                    if thread_type == ThreadType.USER:
                        now = time.time()
                        if author_id in temp_thread_storage:
                            last_message_time = temp_thread_storage[author_id]
                            if now - last_message_time < 7200:
                                logger.info(f"[DEBUG] Skipping auto-reply, last reply was {now - last_message_time:.0f}s ago")
                                return
                        msg = f"Chào {author_name} đây là bot zalo"
                        styles = MultiMsgStyle([
                            MessageStyle(offset=0, length=2, style="color", color="#a24ffb", auto_format=False),
                            MessageStyle(offset=2, length=len(msg) - 2, style="color", color="#ffaf00", auto_format=False),
                            MessageStyle(offset=0, length=40, style="color", color="#a24ffb", auto_format=False),
                            MessageStyle(offset=45, length=len(msg) - 2, style="color", color="#ffaf00", auto_format=False),
                            MessageStyle(offset=0, length=len(msg), style="font", size="3", auto_format=False),
                            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
                            MessageStyle(offset=0, length=len(msg), style="italic", auto_format=False)
                        ])
                        self.replyMessage(Message(text=msg, style=styles), message_object, thread_id, thread_type)
                        temp_thread_storage[author_id] = now
                        logger.info(f"[DEBUG] Sent auto-reply to user: {author_id}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
        except Exception as e:
            logger.error(f"Critical error in onMessage: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    max_restart_attempts = 5
    restart_count = 0
    
    logger.info("[DEBUG] Starting bot initialization...")
    logger.info(f"[DEBUG] Max restart attempts: {max_restart_attempts}")
    
    while restart_count < max_restart_attempts:
        try:
            logger.info(f"[DEBUG] Attempting to create client (attempt {restart_count + 1}/{max_restart_attempts})")
            logger.info(f"[DEBUG] API_KEY: {API_KEY[:10]}... IMEI: {IMEI[:10]}...")
            
            client = Client(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
            
            # Log resource stats on startup
            stats = resource_monitor.get_resource_stats()
            if stats:
                logger.info(f"Resource stats - Memory: {stats['memory_percent']:.1f}%, CPU: {stats['cpu_percent']:.1f}%, Disk: {stats['disk_percent']:.1f}%, Process Memory: {stats['process_memory_mb']:.1f}MB")
            
            logger.info("[DEBUG] Client created successfully, starting listener...")
            client.listen(thread=True, delay=0)
            logger.info("[DEBUG] Listener started successfully")
            break  # Exit loop if successful
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (KeyboardInterrupt)")
            resource_monitor.stop_monitoring()
            sys.exit(0)
        except Exception as e:
            restart_count += 1
            logger.error(f"Login failed (attempt {restart_count}/{max_restart_attempts}): {e}")
            logger.error(f"[DEBUG] Full traceback:\n{traceback.format_exc()}")
            
            if restart_count < max_restart_attempts:
                wait_time = min(60, 10 * restart_count)  # Max 60 seconds
                logger.info(f"Retrying connection in {wait_time} seconds...")
                time.sleep(wait_time)
                
                # Cleanup
                logger.info("[DEBUG] Running garbage collection...")
                gc.collect()
            else:
                logger.error("Exceeded maximum retry attempts. Exiting program.")
                resource_monitor.stop_monitoring()
                sys.exit(1)