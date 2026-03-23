import time
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
    "credits": "Shop Command Module",
    "description": "Shop command handler module"
}

def get_mitaizl():
    """Return empty dict since commands are handled directly in mitaizl.py"""
    return {}

def handle_shop_command(client, message, author_id, thread_id, thread_type):
    """Xử lý lệnh shop"""
    try:
        parts = message.split()
        
        if len(parts) < 2:
            # Hiển thị danh sách sản phẩm
            products = client.shop.get_product_list()
            
            if not products:
                client.send(Message(text="❌ Khong co san pham nao trong shop!"), thread_id, thread_type)
                return
            
            shop_text = "🛒 **SHOP TAI KHOAN** 🛒\n\n"
            
            for product_name, product in products.items():
                shop_text += f"📱 **{product_name.upper()}**\n"
                shop_text += f"💰 **Gia:** {product['price']:,} VND\n"
                shop_text += f"📅 **Cap nhat:** {datetime.fromisoformat(product['last_updated']).strftime('%d/%m/%Y %H:%M')}\n\n"
            
            shop_text += """
**Cach su dung:**
• `shop update` - Cap nhat danh sach san pham
• `shop <ten_san_pham> <so_luong>` - Mua san pham
• `shop myorders` - Xem don hang cua ban (10 phut gan nhat)
• `shop status` - Xem trang thai shop

**Vi du:**
• `shop capcut 1` - Mua 1 tai khoan capcut
• `shop chatgpt 2` - Mua 2 tai khoan chatgpt

**Luu y:** Chi hien thi don hang trong 10 phut gan nhat
            """.strip()
            
            client.send(Message(text=shop_text), thread_id, thread_type)
            return
        
        command = parts[1].lower()
        
        if command == "update":
            # Cập nhật danh sách sản phẩm
            if client.shop.update_products():
                client.send(Message(text="✅ Da cap nhat danh sach san pham thanh cong!"), thread_id, thread_type)
            else:
                client.send(Message(text="❌ Khong the cap nhat danh sach san pham!"), thread_id, thread_type)
        
        elif command == "myorders":
            # Xem đơn hàng của user trong 10 phút gần nhất
            user_orders = client.shop.get_user_orders(author_id)
            
            if not user_orders:
                client.send(Message(text="📋 Ban chua co don hang nao!"), thread_id, thread_type)
                return
            
            # Lọc đơn hàng trong 10 phút gần nhất
            current_time = datetime.now()
            recent_orders = []
            
            for order in user_orders:
                order_time = datetime.fromisoformat(order['created_time'])
                time_diff = current_time - order_time
                
                # Chỉ hiển thị đơn hàng trong 10 phút gần nhất
                if time_diff.total_seconds() <= 600:  # 600 giây = 10 phút
                    recent_orders.append(order)
            
            if not recent_orders:
                client.send(Message(text="📋 Ban khong co don hang nao trong 10 phut gan nhat!"), thread_id, thread_type)
                return
            
            orders_text = "📋 **DON HANG CUA BAN (10 PHUT GAN NHAT)** 📋\n\n"
            
            # Sắp xếp theo thời gian tạo (mới nhất trước)
            recent_orders.sort(key=lambda x: x['created_time'], reverse=True)
            
            for order in recent_orders:
                status_emoji = {
                    "pending": "⏳",
                    "paid": "💰",
                    "completed": "✅",
                    "cancelled": "❌",
                    "error": "⚠️"
                }.get(order["status"], "❓")
                
                # Tính thời gian còn lại
                order_time = datetime.fromisoformat(order['created_time'])
                time_diff = current_time - order_time
                minutes_ago = int(time_diff.total_seconds() / 60)
                
                orders_text += f"""
{status_emoji} **{order['order_id']}**
- San pham: {order['product_name']}
- So luong: {order['quantity']}
- Tong tien: {order['total_price']:,} VND
- Trang thai: {order['status'].upper()}
- Thoi gian: {minutes_ago} phut truoc
                """.strip() + "\n\n"
            
            client.send(Message(text=orders_text), thread_id, thread_type)
        
        elif command == "status":
            # Xem trạng thái shop
            status = client.shop.get_status()
            
            status_text = f"""
🛒 **TRANG THAI SHOP** 🛒

📊 **Tong san pham:** {status['total_products']}
📋 **Tong don hang:** {status['total_orders']}
⏳ **Don cho thanh toan:** {status['pending_orders']}
✅ **Don da hoan thanh:** {status['completed_orders']}
🎯 **Nhom:** {status['group_id']}
            """.strip()
            
            client.send(Message(text=status_text), thread_id, thread_type)
        
        else:
            # Mua sản phẩm
            product_name = parts[1]
            quantity = 1
            
            if len(parts) > 2:
                try:
                    quantity = int(parts[2])
                    if quantity <= 0:
                        client.send(Message(text="❌ So luong phai lon hon 0!"), thread_id, thread_type)
                        return
                except ValueError:
                    client.send(Message(text="❌ So luong khong hop le!"), thread_id, thread_type)
                    return
            
            # Tạo đơn hàng
            order, error = client.shop.create_order(product_name, quantity, author_id, thread_id)
            
            if error:
                client.send(Message(text=f"❌ {error}"), thread_id, thread_type)
                return
            
            # Tạo QR thanh toán
            bill_info, qr_error = client.qr_payment.create_qr_payment(
                amount=order["total_price"],
                addinfo=order["addinfo"],
                user_id=author_id,
                thread_id=thread_id
            )
            
            if qr_error:
                client.send(Message(text=f"❌ Loi tao QR thanh toan: {qr_error}"), thread_id, thread_type)
                return
            
            # Tạo thông báo đơn hàng
            order_message = f"""
🛒 **DON HANG DA TAO** 🛒

- **Ma don hang:** {order['order_id']}
- **San pham:** {order['product_name']}
- **So luong:** {order['quantity']}
- **Gia moi cai:** {order['price_per_item']:,} VND
- **Tong tien:** {order['total_price']:,} VND
- **AddInfo:** {order['addinfo']}
- **Thoi gian tao:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

📱 **Quet QR de thanh toan:**
{bill_info['qr_url']}

⏰ QR co han su dung 10 phut
            """.strip()
            
            client.send(Message(text=order_message), thread_id, thread_type,timeout=600000)
            
            # Gửi QR image
            try:
                # Tạo thư mục temp nếu chưa có
                os.makedirs('temp', exist_ok=True)
                
                # Đường dẫn file ảnh
                img_path = f'temp/shop_qr_{order["order_id"]}.png'
                
                # Download ảnh QR từ URL
                print(f'[SHOP] Dang download anh QR: {bill_info["qr_url"]}')
                r = requests.get(bill_info['qr_url'], stream=True, timeout=10)
                
                if r.status_code == 200:
                    # Lưu ảnh vào file
                    with open(img_path, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                    
                    print(f'[SHOP] Dang gui anh QR: {img_path}')
                    
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
                        print(f'[SHOP] Da xoa file anh: {img_path}')
                    except Exception as delete_error:
                        logger.error(f"Loi khi xoa file anh: {delete_error}")
                        
                else:
                    logger.error(f"Khong the download anh QR, status code: {r.status_code}")
                    client.send(Message(text="⚠️ Khong the download anh QR, vui long su dung link tren"), thread_id, thread_type)
                    
            except Exception as e:
                logger.error(f"Loi khi gui QR image: {e}")
                client.send(Message(text="⚠️ Khong the gui anh QR, vui long su dung link tren"), thread_id, thread_type)
            
            logger.success(f"Tao don hang shop thanh cong cho user {author_id}: {order['order_id']}")
    
    except Exception as e:
        logger.error(f"Loi khi xu ly lenh shop: {e}")
        client.send(Message(text=f"❌ Loi: {str(e)}"), thread_id, thread_type)
