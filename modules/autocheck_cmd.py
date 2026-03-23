import time
from zlapi.models import Message, ThreadType
from utils.logging_utils import Logging

logger = Logging()

# Module metadata for CommandHandler
des = {
    "version": "1.0.0",
    "credits": "AutoCheck Command Module",
    "description": "AutoCheck command handler module"
}

def get_mitaizl():
    """Return empty dict since commands are handled directly in mitaizl.py"""
    return {}

def handle_autocheck_command(client, message, author_id, thread_id, thread_type):
    """Xử lý các lệnh autocheck"""
    try:
        # Kiểm tra quyền admin
        if str(author_id) not in client.admins:
            client.send(Message(text="❌ Bạn không có quyền sử dụng lệnh này!"), thread_id, thread_type)
            return
        
        parts = message.split()
        if len(parts) < 2:
            # Hiển thị trạng thái autocheck
            status = client.autocheck.get_status()
            status_text = f"""
🔍 **TRẠNG THÁI AUTOCHECK**

✅ **Trạng thái:** {'Đang chạy' if status['running'] else 'Đã dừng'}
⏰ **Tần suất kiểm tra:** {status['check_interval']} giây
📊 **Số giao dịch đã thông báo:** {status['sent_count']}
🎯 **Nhóm nhận thông báo:** {status['group_id']}

**Các lệnh có sẵn:**
• `autocheck start` - Bắt đầu autocheck
• `autocheck stop` - Dừng autocheck
• `autocheck restart` - Khởi động lại autocheck
• `autocheck status` - Xem trạng thái
• `autocheck clear` - Xóa lịch sử refNo đã gửi
            """.strip()
            
            client.send(Message(text=status_text), thread_id, thread_type)
            return
        
        command = parts[1].lower()
        
        if command == "start":
            if client.autocheck.running:
                client.send(Message(text="⚠️ AutoCheck đã đang chạy!"), thread_id, thread_type)
            else:
                client.autocheck.start()
                client.send(Message(text="✅ AutoCheck đã được bắt đầu!"), thread_id, thread_type)
                logger.success(f"AutoCheck được bắt đầu bởi {author_id}")
        
        elif command == "stop":
            if not client.autocheck.running:
                client.send(Message(text="⚠️ AutoCheck đã dừng!"), thread_id, thread_type)
            else:
                client.autocheck.stop()
                client.send(Message(text="⏹️ AutoCheck đã được dừng!"), thread_id, thread_type)
                logger.info(f"AutoCheck được dừng bởi {author_id}")
        
        elif command == "restart":
            client.autocheck.stop()
            time.sleep(1)
            client.autocheck.start()
            client.send(Message(text="🔄 AutoCheck đã được khởi động lại!"), thread_id, thread_type)
            logger.info(f"AutoCheck được khởi động lại bởi {author_id}")
        
        elif command == "status":
            status = client.autocheck.get_status()
            status_text = f"""
🔍 **CHI TIẾT TRẠNG THÁI AUTOCHECK**

✅ **Trạng thái:** {'🟢 Đang chạy' if status['running'] else '🔴 Đã dừng'}
⏰ **Tần suất kiểm tra:** {status['check_interval']} giây
📊 **Số giao dịch đã thông báo:** {status['sent_count']}
🎯 **Nhóm nhận thông báo:** {status['group_id']}
🌐 **API URL:** http://160.191.245.27:6868/
            """.strip()
            
            client.send(Message(text=status_text), thread_id, thread_type)
        
        elif command == "clear":
            client.autocheck.sent_refnos = []
            client.autocheck.save_sent_refnos()
            client.send(Message(text="🗑️ Đã xóa lịch sử refNo đã gửi thông báo!"), thread_id, thread_type)
            logger.info(f"Lịch sử refNo được xóa bởi {author_id}")
        
        else:
            client.send(Message(text="❌ Lệnh không hợp lệ! Sử dụng: `autocheck start/stop/restart/status/clear`"), thread_id, thread_type)
    
    except Exception as e:
        logger.error(f"Lỗi khi xử lý lệnh autocheck: {e}")
        client.send(Message(text=f"❌ Lỗi: {str(e)}"), thread_id, thread_type)
