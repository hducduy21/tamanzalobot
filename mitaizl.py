import os
import importlib
import sys
import json
import threading
import time
import random
from datetime import datetime
import pytz
from zlapi.models import Message, ThreadType
from config import PREFIX, ADMIN
from utils.logging_utils import Logging
import traceback
from functools import wraps

logger = Logging()
vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

# Path to autosend data
AUTOSEND_DATA_FILE = 'modules/cache/autosend.json'

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules/auto'))

# Thread-safe decorator
def thread_safe(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
            return None
    return wrapper

def prf():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return json.load(f).get('prefix')
    except Exception as e:
        logger.error(f"Error loading prefix: {e}")
        return "/"

def adm():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return json.load(f).get('adm')
    except Exception as e:
        logger.error(f"Error loading admin: {e}")
        return []

@thread_safe
def load_duyetbox_data():
    try:
        with open('modules/cache/duyetboxdata.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading duyetbox data: {e}")
        return []

@thread_safe
def load_autosend_data():
    """Load auto-send data from JSON file."""
    try:
        if os.path.exists(AUTOSEND_DATA_FILE):
            with open(AUTOSEND_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return {}
    except Exception as e:
        logger.error(f"Lỗi khi tải dữ liệu autosend: {e}")
        return {}

@thread_safe
def save_autosend_data(data):
    """Save auto-send data to JSON file."""
    try:
        os.makedirs(os.path.dirname(AUTOSEND_DATA_FILE), exist_ok=True)
        with open(AUTOSEND_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu autosend: {e}")

class CommandHandler:
    def __init__(self, client):
        self.client = client
        self.mitaizl = self.load_mitaizl()
        self.noprefix_mitaizl = self.load_noprefix_mitaizl()
        self.auto_mitaizl = self.load_auto_mitaizl()
        self.admin_id = ADMIN
        self.adminon = self.load_admin_mode()
        self.command_usage = {}
        self._lock = threading.Lock()
        self._autosend_lock = threading.Lock()
        
        # Start the centralized auto-send thread
        threading.Thread(target=self.auto_send_thread, args=(), daemon=True).start()

    @thread_safe
    def load_admin_mode(self):
        try:
            with open('modules/cache/admindata.json', 'r', encoding='utf-8') as f:
                return json.load(f).get('adminon', False)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error loading admin mode: {e}")
            return False

    @thread_safe
    def save_admin_mode(self):
        try:
            os.makedirs(os.path.dirname('modules/cache/admindata.json'), exist_ok=True)
            with open('modules/cache/admindata.json', 'w', encoding='utf-8') as f:
                json.dump({'adminon': self.adminon}, f)
        except Exception as e:
            logger.error(f"Error saving admin mode: {e}")

    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, rgb_color):
        return '{:02x}{:02x}{:02x}'.format(*rgb_color)

    def generate_random_color(self):
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

    def generate_gradient_colors(self, length, num_colors=5):
        random_colors = [self.generate_random_color() for _ in range(num_colors)]
        rgb_colors = [self.hex_to_rgb(color) for color in random_colors]

        colors = []
        for j in range(num_colors - 1):
            start_rgb = rgb_colors[j]
            end_rgb = rgb_colors[j + 1]
            segment_length = length // (num_colors - 1)
            
            for i in range(segment_length):
                interpolated_color = (
                    int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * i / (segment_length - 1)),
                    int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * i / (segment_length - 1)),
                    int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * i / (segment_length - 1))
                )
                colors.append(self.rgb_to_hex(interpolated_color))
        
        return colors

    def create_rainbow_params(self, text, size=20):
        styles = []
        colors = self.generate_gradient_colors(len(text), num_colors=5)
        
        for i, color in enumerate(colors):
            styles.append({"start": i, "len": 1, "st": f"c_{color}"})
        
        params = {"styles": styles, "ver": 0}
        return json.dumps(params)

    @thread_safe
    def sendMessageColor(self, error_message, thread_id, thread_type):
        try:
            stype = self.create_rainbow_params(error_message)
            mes = Message(
                text=error_message,
                style=stype
            )
            self.client.send(mes, thread_id, thread_type)
        except Exception as e:
            logger.error(f"Error sending colored message: {e}")

    @thread_safe
    def replyMessageColor(self, error_message, message_object, thread_id, thread_type):
        try:
            stype = self.create_rainbow_params(error_message)
            mes = Message(
                text=error_message,
                style=stype
            )
            self.client.replyMessage(mes, message_object, thread_id=thread_id, thread_type=thread_type, ttl=5000)
        except Exception as e:
            logger.error(f"Error replying colored message: {e}")

    @thread_safe
    def load_mitaizl(self):
        mitaizl = {}
        modules_path = 'modules'
        success_count = 0
        failed_count = 0

        try:
            for root, dirs, files in os.walk(modules_path):
                if 'auto' in root.split(os.sep):
                    continue
                for filename in files:
                    if filename.endswith('.py') and filename != '__init__.py':
                        module_name = filename[:-3]
                        relative_path = os.path.relpath(root, modules_path)
                        module_path = (
                            f"{modules_path}.{relative_path.replace(os.sep, '.')}.{module_name}"
                            if relative_path != '.' else
                            f"{modules_path}.{module_name}"
                        )
                        try:
                            module = importlib.import_module(module_path)
                            
                            if hasattr(module, 'get_mitaizl'):
                                if hasattr(module, 'des'):
                                    des = getattr(module, 'des')
                                    if all(key in des for key in ['version', 'credits', 'description']):
                                        mitaizl.update(module.get_mitaizl())
                                        success_count += 1
                                    else:
                                        raise ImportError(f"Module {module_name} lacks required 'des' keys (version, credits, description)")
                                else:
                                    raise ImportError(f"Module {module_name} has no 'des' dictionary")
                            else:
                                raise ImportError(f"Module {module_name} has no 'get_mitaizl' function")
                        except Exception as e:
                            logger.error(f"Failed to load module {module_path}: {e}")
                            failed_count += 1

            if success_count > 0:
                logger.success(f"Loaded {success_count} command modules:done")
            if failed_count > 0:
                logger.warning(f"Failed to load {failed_count} command modules: done")
        except Exception as e:
            logger.error(f"Critical error loading modules: {e}")

        return mitaizl

    @thread_safe
    def load_noprefix_mitaizl(self):
        noprefix_mitaizl = {}
        noprefix_modules_path = 'modules.noprefix'
        success_count = 0
        failed_count = 0

        try:
            for filename in os.listdir('modules/noprefix'):
                if filename.endswith('.py') and filename != '__init__.py':
                    module_name = filename[:-3]
                    try:
                        module = importlib.import_module(f'{noprefix_modules_path}.{module_name}')
                        
                        if hasattr(module, 'get_mitaizl'):
                            if hasattr(module, 'des'):
                                des = getattr(module, 'des')
                                if all(key in des for key in ['version', 'credits', 'description']):
                                    noprefix_mitaizl.update(module.get_mitaizl())
                                    success_count += 1
                                else:
                                    raise ImportError(f"Module {module_name} lacks required 'des' keys")
                            else:
                                raise ImportError(f"Module {module_name} has no 'des' dictionary")
                        else:
                            raise ImportError(f"Module {module_name} has no 'get_mitaizl' function")
                    except Exception as e:
                        logger.error(f"Failed to load noprefix module {module_name}: {e}")
                        failed_count += 1

            if success_count > 0:
                logger.success(f"Loaded {success_count} noprefix command modules")
            if failed_count > 0:
                logger.warning(f"Failed to load {failed_count} noprefix command modules")
        except Exception as e:
            logger.error(f"Critical error loading noprefix modules: {e}")

        return noprefix_mitaizl

    @thread_safe
    def load_auto_mitaizl(self):
        auto_mitaizl = {}
        auto_modules_path = 'modules/auto'
        success_count = 0
        failed_count = 0

        try:
            for filename in os.listdir(auto_modules_path):
                if filename.endswith('.py') and filename != '__init__.py':
                    module_name = filename[:-3]
                    try:
                        module = importlib.import_module(f'modules.auto.{module_name}')
                        
                        if hasattr(module, 'start_auto'):
                            auto_mitaizl[module_name] = module
                            success_count += 1
                            threading.Thread(target=auto_mitaizl[module_name].start_auto, args=(self.client,), daemon=True).start()
                        else:
                            raise ImportError(f"Module {module_name} has no 'start_auto' function")
                    except Exception as e:
                        logger.error(f"Failed to load auto module {module_name}: {e}")
                        failed_count += 1

            if success_count > 0:
                logger.success(f"Loaded {success_count} auto modules")
            if failed_count > 0:
                logger.warning(f"Failed to load {failed_count} auto modules")
        except Exception as e:
            logger.error(f"Critical error loading auto modules: {e}")

        return auto_mitaizl

    def auto_send_thread(self):
        """Centralized thread to check and send scheduled messages from autosend.json."""
        while True:
            try:
                with self._autosend_lock:
                    current_time = datetime.now(vn_tz)
                    current_time_str = current_time.strftime('%H:%M')

                    data = load_autosend_data()
                    if not data:
                        time.sleep(60)
                        continue

                    for thread_id, schedules in data.items():
                        for schedule in schedules:
                            schedule_time = schedule['time']
                            if schedule_time == current_time_str and schedule.get('active', True):
                                last_sent = schedule.get('last_sent')
                                today_str = current_time.strftime('%Y-%m-%d')
                                if last_sent != today_str:
                                    try:
                                        self.client.send(
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
                time.sleep(60)
            except Exception as e:
                logger.error(f"Lỗi trong auto_send_thread: {e}\n{traceback.format_exc()}")
                time.sleep(60)

    @thread_safe
    def toggle_admin_mode(self, message, message_object, thread_id, thread_type, author_id):
        try:
            if author_id == self.admin_id:
                if 'on' in message.lower():
                    self.adminon = True
                    self.save_admin_mode()
                    self.replyMessageColor("Chế độ admin đã được bật.", message_object, thread_id, thread_type)
                elif 'off' in message.lower():
                    self.adminon = False
                    self.save_admin_mode()
                    self.replyMessageColor("Chế độ admin đã được tắt.", message_object, thread_id, thread_type)
                else:
                    self.replyMessageColor("Vui lòng sử dụng lệnh: adminmode on/off.", message_object, thread_id, thread_type)
            else:
                self.replyMessageColor("Bạn không có quyền bật/tắt chế độ admin.", message_object, thread_id, thread_type)
        except Exception as e:
            logger.error(f"Error in toggle_admin_mode: {e}")

    def handle_command(self, message, author_id, message_object, thread_id, thread_type):
        try:
            with self._lock:
                current_time = time.time()
                if author_id not in self.command_usage:
                    self.command_usage[author_id] = []

                self.command_usage[author_id] = [t for t in self.command_usage[author_id] if current_time - t < 2]

                if len(self.command_usage[author_id]) >= 4:
                    def delayed_reaction():
                        try:
                            icon = "⏳"
                            self.client.sendReaction(
                                messageObject=message_object, 
                                reactionIcon=icon, 
                                thread_id=thread_id, 
                                thread_type=thread_type
                            )
                        except Exception as e:
                            logger.error(f"Error sending reaction: {e}")

                    threading.Thread(target=delayed_reaction, daemon=True).start()
                    return

                self.command_usage[author_id].append(current_time)

                if message.startswith(prf()) and thread_id not in load_duyetbox_data() and author_id not in adm():
                    gui = Message(text="> Nhóm của bạn chưa được duyệt!")
                    self.client.replyMessage(gui, message_object, thread_id, thread_type, ttl=120000)
                    return

                if message.startswith(prf() + 'adminmode'):
                    self.toggle_admin_mode(message, message_object, thread_id, thread_type, author_id)
                    return

                # Handle autocheck commands
                if message.startswith(prf() + 'autocheck'):
                    from modules.autocheck_cmd import handle_autocheck_command
                    handle_autocheck_command(self.client, message, author_id, thread_id, thread_type)
                    return

                # Handle QR payment commands
                if message.startswith(prf() + 'qrthanhtoan'):
                    from modules.qrthanhtoan_cmd import handle_qrthanhtoan_command
                    handle_qrthanhtoan_command(self.client, message, author_id, thread_id, thread_type)
                    return

                if message.startswith(prf() + 'qrstatus'):
                    from modules.qrthanhtoan_cmd import handle_qrstatus_command
                    handle_qrstatus_command(self.client, message, author_id, thread_id, thread_type)
                    return

                if message.startswith(prf() + 'qrbills'):
                    from modules.qrthanhtoan_cmd import handle_qrbills_command
                    handle_qrbills_command(self.client, message, author_id, thread_id, thread_type)
                    return

                noprefix_command_handler = self.noprefix_mitaizl.get(message.lower())
                if noprefix_command_handler:
                    try:
                        noprefix_command_handler(message, message_object, thread_id, thread_type, author_id, self.client)
                    except Exception as e:
                        logger.error(f"Error executing noprefix command: {e}")
                    return

                if not message.startswith(prf()):
                    return

                command_name = message[len(prf()):].split(' ')[0].lower()
                command_handler = self.mitaizl.get(command_name)

                if self.adminon and author_id not in adm():
                    error_message = "Chế độ admin đang bật, chỉ có admin mới có thể sử dụng lệnh."
                    self.replyMessageColor(error_message, message_object, thread_id, thread_type)
                    return

                if command_handler:
                    try:
                        command_handler(message, message_object, thread_id, thread_type, author_id, self.client)
                    except Exception as e:
                        logger.error(f"Error executing command {command_name}: {e}\n{traceback.format_exc()}")
                        error_msg = Message(text=f"Lỗi khi thực thi lệnh '{command_name}'. Vui lòng thử lại sau!")
                        self.client.replyMessage(error_msg, message_object, thread_id, thread_type, ttl=20000)
                else:
                    error_message = Message(text=f"Không tìm thấy lệnh: '{command_name}'. Hãy dùng {prf()}menu để biết các lệnh có trên hệ thống.")
                    self.client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=20000)
        except Exception as e:
            logger.error(f"Critical error in handle_command: {e}\n{traceback.format_exc()}")