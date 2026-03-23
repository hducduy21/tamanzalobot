import time
from config import CONNECTION_TIMEOUT
import os
import shutil
import requests
from datetime import datetime
from zlapi.models import Message, ThreadType
from utils.logging_utils import Logging

logger = Logging()

# Module metadata for CommandHandler
des = {
    "version": "1.0.0",
    "credits": "QR Payment Command Module",
    "description": "QR Payment command handler module"
}

def get_mitaizl():
    """Return empty dict since commands are handled directly in mitaizl.py"""
    return {}

def handle_qrthanhtoan_command(client, message, author_id, thread_id, thread_type):
    """Xử lý lệnh tạo QR thanh toán"""
    try:
        parts = message.split()
        
        if len(parts) < 2:
            # Hiển thị hướng dẫn sử dụng
            help_text = f"""
💳 **HUONG DAN SU DUNG QR THANH TOAN**

**Cach su dung:**
• `qrthanhtoan <so_tien>, <noi_dung>, <thang>` - Format co ban
• `qrthanhtoan <so_tien>, <noi_dung>, <thang>, <ma_bao_hanh>` - Format day du

**Vi du:**
• `qrthanhtoan 50000, capcut, 10` - Tao QR 50,000 VND voi noi dung "capcut" va thang "10"
• `qrthanhtoan 75000, chatgpt, 11` - Tao QR 75,000 VND voi noi dung "chatgpt" va thang "11"
• `qrthanhtoan 100000, netflix, 12, ABC123` - Tao QR 100,000 VND voi ma bao hanh "ABC123"

**Luu y:**
- QR co han su dung 10 phut
- Tu dong kiem tra thanh toan moi 30 giay
- Hoa don se tu dong huy sau 10 phut neu chua thanh toan
- AddInfo se tu dong tao random
- Ma bao hanh tuy chon (tham so thu 4)
            """.strip()
            
            client.send(Message(text=help_text), thread_id, thread_type)
            return
        
        # Lấy số tiền (có thể có dấu phẩy)
        try:
            amount_str = parts[1].replace(",", "")
            amount = int(amount_str)
            if amount <= 0:
                client.send(Message(text="❌ So tien phai lon hon 0!"), thread_id, thread_type)
                return
        except ValueError:
            client.send(Message(text="❌ So tien khong hop le!"), thread_id, thread_type)
            return
        
        # Lấy addInfo, tháng và mã bảo hành (format: số_tiền, nội_dung, tháng, mã_bảo_hành)
        addinfo = None
        month_info = None
        warranty_code = None
        
        if len(parts) > 2:
            full_text = " ".join(parts[2:])
            # Format: số_tiền, nội_dung, tháng, mã_bảo_hành
            if "," in full_text:
                # Tách theo dấu phẩy và xử lý từng phần
                parts_with_comma = full_text.split(",")
                
                if len(parts_with_comma) >= 1:
                    # Phần đầu là nội dung (chatgpt)
                    content = parts_with_comma[0].strip()
                    if content and content != "":
                        addinfo = content
                
                if len(parts_with_comma) >= 2:
                    # Phần thứ hai là tháng (11)
                    month_info = parts_with_comma[1].strip()
                
                if len(parts_with_comma) >= 3:
                    # Phần thứ ba là mã bảo hành (abc)
                    warranty_code = parts_with_comma[2].strip()
            else:
                # Nếu không có dấu phẩy, coi như toàn bộ là nội dung
                addinfo = full_text
        
        # Tạo QR thanh toán (nội dung luôn được tạo random, app_name là nội dung được nhập)
        bill_info, error = client.qr_payment.create_qr_payment(
            amount=amount,
            addinfo=None,  # Luôn tạo random
            user_id=author_id,
            thread_id=thread_id,
            app_name=addinfo,  # Tên app là nội dung được nhập (chatgpt)
            months=month_info,  # Số tháng từ tham số
            warranty_code=warranty_code  # Mã bảo hành tùy chỉnh
        )
        
        if error:
            client.send(Message(text=f"❌ {error}"), thread_id, thread_type)
            return
        
        # Tạo thông báo QR
        qr_message = f"""
[QR] **QR THANH TOAN DA TAO** [QR]

[$] **Ma hoa don:** {bill_info['bill_id']}
[$] **So tien:** {bill_info['amount']:,} VND
[#] **AddInfo:** {bill_info['addinfo']}
[@] **Thoi gian tao:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
[@] **Het han:** {datetime.fromisoformat(bill_info['expire_time']).strftime('%d/%m/%Y %H:%M:%S')}"""

        # Thêm thông tin tháng nếu có
        if month_info:
            qr_message += f"""
[@] **Thang:** {month_info}"""

        # Thêm thông tin mã bảo hành nếu có
        if warranty_code:
            qr_message += f"""
[#] **Ma bao hanh:** {warranty_code}"""

        qr_message += f"""

[!] QR co han su dung 10 phut
        """.strip()
        
        client.send(Message(text=qr_message), thread_id, thread_type)
        
        # Gửi QR image
        try:
            # Tạo thư mục temp nếu chưa có
            os.makedirs('temp', exist_ok=True)
            
            # Đường dẫn file ảnh
            img_path = f'temp/qr_{bill_info["bill_id"]}.png'
            
            # Download ảnh QR từ URL
            print(f'[QR] Dang download anh QR: {bill_info["qr_url"]}')
            r = requests.get(bill_info['qr_url'], stream=True, timeout=CONNECTION_TIMEOUT)
            
            if r.status_code == 200:
                # Lưu ảnh vào file
                with open(img_path, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
                
                print(f'[QR] Dang gui anh QR: {img_path}')
                
                # Gửi ảnh QR
                client.sendLocalImage(
                    img_path,
                    message=None,
                    thread_id=thread_id,
                    thread_type=ThreadType.GROUP,
                    width=300,
                    height=300,
                    ttl=600000  # 10 phút
                )
                
                # Xóa file ảnh sau khi gửi
                try:
                    os.remove(img_path)
                    print(f'[QR] Da xoa file anh: {img_path}')
                except Exception as delete_error:
                    logger.error(f"Loi khi xoa file anh: {delete_error}")
                    
            else:
                logger.error(f"Khong the download anh QR, status code: {r.status_code}")
                client.send(Message(text="⚠️ Khong the download anh QR, vui long su dung link tren"), thread_id, thread_type)
                
        except Exception as e:
            logger.error(f"Loi khi gui QR image: {e}")
            client.send(Message(text="⚠️ Khong the gui anh QR, vui long su dung link tren"), thread_id, thread_type)
        
        logger.success(f"Tao QR thanh toan thanh cong cho user {author_id}: {bill_info['bill_id']}")
    
    except Exception as e:
        logger.error(f"Loi khi xu ly lenh qrthanhtoan: {e}")
        client.send(Message(text=f"❌ Loi: {str(e)}"), thread_id, thread_type)

def handle_qrstatus_command(client, message, author_id, thread_id, thread_type):
    """Xử lý lệnh xem trạng thái QR Payment"""
    try:
        status = client.qr_payment.get_status()
        
        status_text = f"""
💳 **TRANG THAI QR PAYMENT**

✅ **Trang thai:** {'Dang chay' if status['running'] else 'Da dung'}
📊 **Hoa don cho thanh toan:** {status['pending_bills']}
📋 **Tong hoa don:** {status['total_bills']}
🎯 **Nhom nhan thong bao:** {status['group_id']}

**Cac lenh co san:**
• `qrthanhtoan <so_tien>` - Tao QR thanh toan
• `qrstatus` - Xem trang thai
• `qrbills` - Xem danh sach hoa don
        """.strip()
        
        client.send(Message(text=status_text), thread_id, thread_type)
    
    except Exception as e:
        logger.error(f"Loi khi xu ly lenh qrstatus: {e}")
        client.send(Message(text=f"❌ Loi: {str(e)}"), thread_id, thread_type)

def handle_qrbills_command(client, message, author_id, thread_id, thread_type):
    """Xử lý lệnh xem danh sách hóa đơn"""
    try:
        pending_bills = [bill for bill in client.qr_payment.pending_bills.values() if bill["status"] == "pending"]
        
        if not pending_bills:
            client.send(Message(text="📋 Khong co hoa don nao dang cho thanh toan"), thread_id, thread_type)
            return
        
        bills_text = "📋 **DANH SACH HOA DON CHO THANH TOAN**\n\n"
        
        for i, bill in enumerate(pending_bills[:10], 1):  # Chỉ hiển thị 10 hóa đơn đầu
            expire_time = datetime.fromisoformat(bill['expire_time'])
            time_left = expire_time - datetime.now()
            minutes_left = max(0, int(time_left.total_seconds() / 60))
            
            bills_text += f"""
**{i}. {bill['bill_id']}**
- So tien: {bill['amount']:,} VND
- AddInfo: {bill['addinfo']}
- Con lai: {minutes_left} phut
- Tao luc: {datetime.fromisoformat(bill['created_time']).strftime('%H:%M:%S')}
            """.strip() + "\n\n"
        
        if len(pending_bills) > 10:
            bills_text += f"... va {len(pending_bills) - 10} hoa don khac"
        
        client.send(Message(text=bills_text), thread_id, thread_type)
    
    except Exception as e:
        logger.error(f"Loi khi xu ly lenh qrbills: {e}")
        client.send(Message(text=f"❌ Loi: {str(e)}"), thread_id, thread_type)
