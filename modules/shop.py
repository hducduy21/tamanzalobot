import requests
import json
import time
import random
import string
from datetime import datetime
from utils.logging_utils import Logging
from config import CONNECTION_TIMEOUT

logger = Logging()

# Module metadata for CommandHandler
des = {
    "version": "1.0.0",
    "credits": "Shop Module",
    "description": "Auto shop for selling accounts module"
}

def get_mitaizl():
    """Return empty dict since this is not a command module"""
    return {}

class Shop:
    def __init__(self, client, group_id="8298902621145306978", qr_payment=None):
        self.client = client
        self.group_id = group_id
        self.qr_payment = qr_payment
        self.shop_api_url = "https://script.google.com/macros/s/AKfycbz_URKe8g4NLnRgxB4vehsofCRWR7w6ec6_cEJHTy-xv_or4r1HpVEl6MmD3UqChKV2Rg/exec"
        self.account_api_url = "https://script.google.com/macros/s/AKfycbyGrUznKF-7kyg2InpRip6Ns8GXHZ8EMc5Nk56PFVFgis_v63GVjYoUVtiSsWmCjqVQrg/exec"
        self.orders_file = "modules/cache/shop_orders.json"
        self.products_file = "modules/cache/shop_products.json"
        self.orders = self.load_orders()
        self.products = self.load_products()
        
    def load_orders(self):
        """Load danh sách đơn hàng"""
        try:
            with open(self.orders_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Loi khi load orders: {e}")
            return {}
    
    def save_orders(self):
        """Lưu danh sách đơn hàng"""
        try:
            with open(self.orders_file, 'w', encoding='utf-8') as f:
                json.dump(self.orders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Loi khi save orders: {e}")
    
    def load_products(self):
        """Load danh sách sản phẩm"""
        try:
            with open(self.products_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Loi khi load products: {e}")
            return {}
    
    def save_products(self):
        """Lưu danh sách sản phẩm"""
        try:
            with open(self.products_file, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Loi khi save products: {e}")
    
    def update_products(self):
        """Cập nhật danh sách sản phẩm từ API"""
        try:
            response = requests.get(f"{self.shop_api_url}?get=DanhSach", timeout=CONNECTION_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("ok") == True:
                    products = {}
                    for item in data.get("data", []):
                        if len(item) >= 2:
                            product_name = item[0]
                            price = item[1]
                            products[product_name] = {
                                "name": product_name,
                                "price": price,
                                "last_updated": datetime.now().isoformat()
                            }
                    
                    self.products = products
                    self.save_products()
                    logger.success(f"Da cap nhat {len(products)} san pham")
                    return True
                else:
                    logger.error("API tra ve ok=false")
                    return False
            else:
                logger.error(f"API tra ve status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Loi khi cap nhat products: {e}")
            return False
    
    def get_product_list(self):
        """Lấy danh sách sản phẩm"""
        if not self.products:
            self.update_products()
        return self.products
    
    def create_order(self, product_name, quantity, user_id, thread_id):
        """Tạo đơn hàng mới"""
        try:
            # Kiểm tra sản phẩm có tồn tại không
            if product_name not in self.products:
                return None, f"San pham '{product_name}' khong ton tai"
            
            product = self.products[product_name]
            total_price = product["price"] * quantity
            
            # Tạo order ID
            order_id = f"ORDER_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Tạo addInfo ngẫu nhiên
            addinfo = f"SHOP{random.randint(100000, 999999)}"
            
            # Tạo đơn hàng
            order = {
                "order_id": order_id,
                "product_name": product_name,
                "quantity": quantity,
                "price_per_item": product["price"],
                "total_price": total_price,
                "user_id": user_id,
                "thread_id": thread_id,
                "addinfo": addinfo,
                "status": "pending",  # pending, paid, completed, cancelled
                "created_time": datetime.now().isoformat(),
                "paid_time": None,
                "completed_time": None,
                "transaction_ref": None,
                "accounts_delivered": []
            }
            
            self.orders[order_id] = order
            self.save_orders()
            
            logger.success(f"Tao don hang thanh cong: {order_id}")
            return order, None
            
        except Exception as e:
            logger.error(f"Loi khi tao don hang: {e}")
            return None, f"Loi: {str(e)}"
    
    def get_accounts(self, product_name, quantity):
        """Lấy tài khoản từ API"""
        try:
            response = requests.get(
                f"{self.account_api_url}?get={product_name}&soluong={quantity}&mode=commit",
                timeout=CONNECTION_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("ok") == True:
                    accounts = []
                    for item in data.get("data", []):
                        if len(item) >= 2:
                            accounts.append({
                                "username": item[0],
                                "password": item[1]
                            })
                    
                    logger.success(f"Lay duoc {len(accounts)} tai khoan {product_name}")
                    return accounts, None
                else:
                    return None, "API tra ve ok=false"
            else:
                return None, f"API tra ve status code: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Loi khi lay tai khoan: {e}")
            return None, f"Loi: {str(e)}"
    
    def check_payment_status(self):
        """Kiểm tra trạng thái thanh toán"""
        try:
            if not self.qr_payment:
                return
            
            # Lấy danh sách giao dịch từ QR Payment
            response = requests.get(self.qr_payment.api_url, timeout=CONNECTION_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == "00" and data.get("des") == "success":
                    transactions = data.get("transactions", [])
                    
                    for transaction in transactions:
                        transaction_id = transaction.get("transactionID", "")
                        addinfo = transaction.get("escription", "")
                        amount = transaction.get("amount", "0").replace(",", "")  # Loại bỏ dấu phẩy
                        cd = transaction.get("CD", "")
                        
                        # Chỉ xử lý giao dịch credit (+)
                        if cd != "+":
                            continue
                        
                        # Kiểm tra xem có đơn hàng nào match không
                        for order_id, order in self.orders.items():
                            if (order["status"] == "pending" and 
                                order["addinfo"] in addinfo and 
                                str(order["total_price"]) == amount):
                                
                                # Đánh dấu đã thanh toán
                                order["status"] = "paid"
                                order["transaction_ref"] = transaction_id
                                order["paid_time"] = datetime.now().isoformat()
                                
                                # Lấy tài khoản
                                accounts, error = self.get_accounts(order["product_name"], order["quantity"])
                                
                                if accounts:
                                    order["status"] = "completed"
                                    order["completed_time"] = datetime.now().isoformat()
                                    order["accounts_delivered"] = accounts
                                    
                                    # Gửi tài khoản cho user
                                    self.send_accounts_to_user(order, accounts)
                                    
                                    logger.success(f"Don hang {order_id} da hoan thanh")
                                else:
                                    order["status"] = "error"
                                    logger.error(f"Khong the lay tai khoan cho don hang {order_id}: {error}")
                                
                                self.save_orders()
                                break
                
        except Exception as e:
            logger.error(f"Loi khi check payment status: {e}")
    
    def send_accounts_to_user(self, order, accounts):
        """Gửi tài khoản cho user"""
        try:
            accounts_text = f"""
✅ **DON HANG DA HOAN THANH** ✅

- **Ma don hang:** {order['order_id']}
- **San pham:** {order['product_name']}
- **So luong:** {order['quantity']}
- **Tong tien:** {order['total_price']:,} VND
- **Thoi gian hoan thanh:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

📱 **TAI KHOAN CUA BAN:**
            """.strip()
            
            for i, account in enumerate(accounts, 1):
                accounts_text += f"""

**{i}. {order['product_name'].upper()}**
👤 **Tai khoan:** {account['username']}
🔑 **Mat khau:** {account['password']}
                """.strip()
            
            accounts_text += """

⚠️ **Luu y:** Hay doi mat khau ngay sau khi dang nhap!
Cam on ban da mua hang!
            """.strip()
            
            from zlapi.models import Message, ThreadType
            message = Message(text=accounts_text)
            
            # Gửi riêng cho user
            self.client.send(message, order["user_id"], ThreadType.USER)
            
            # Gửi thông báo chung (không có thông tin tài khoản)
            public_notification = f"""
✅ **DON HANG HOAN THANH** ✅

- **Ma don hang:** {order['order_id']}
- **San pham:** {order['product_name']}
- **So luong:** {order['quantity']}
- **Tong tien:** {order['total_price']:,} VND

Tai khoan da duoc gui rieng cho nguoi mua!
            """.strip()
            
            public_message = Message(text=public_notification)
            self.client.send(public_message, self.group_id, ThreadType.GROUP)
            
        except Exception as e:
            logger.error(f"Loi khi gui tai khoan cho user: {e}")
    
    def get_order_status(self, order_id):
        """Lấy trạng thái đơn hàng"""
        return self.orders.get(order_id)
    
    def get_user_orders(self, user_id):
        """Lấy đơn hàng của user"""
        user_orders = []
        for order_id, order in self.orders.items():
            if order["user_id"] == user_id:
                user_orders.append(order)
        return user_orders
    
    def get_status(self):
        """Lấy trạng thái shop"""
        return {
            "total_products": len(self.products),
            "total_orders": len(self.orders),
            "pending_orders": len([o for o in self.orders.values() if o["status"] == "pending"]),
            "completed_orders": len([o for o in self.orders.values() if o["status"] == "completed"]),
            "group_id": self.group_id
        }
