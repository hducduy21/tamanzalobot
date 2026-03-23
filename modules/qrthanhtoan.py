import requests
from config import CONNECTION_TIMEOUT
import json
import time
import threading
import random
import string
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from utils.logging_utils import Logging

logger = Logging()

# Module metadata for CommandHandler
des = {
    "version": "1.0.0",
    "credits": "QR Payment Module",
    "description": "QR payment generator and transaction checker module"
}

def get_mitaizl():
    """Return empty dict since this is not a command module"""
    return {}

class QRPayment:
    def __init__(self, client, group_id="5366422691182401170", shop=None):
        self.client = client
        self.group_id = group_id
        self.api_url = "http://160.191.245.27/api-vietcombank-11062024/api-vietcombank-11062024/to9xvn.php?type=3"
        self.vietqr_template = "https://img.vietqr.io/image/vcb-1061233835-compact.png?amount={amount}&addInfo={addInfo}"
        self.account_no = "1061233835"
        self.pending_bills_file = "modules/cache/pending_bills.json"
        self.pending_bills = self.load_pending_bills()
        self.running = False
        self.thread = None
        self.shop = shop  # Reference to Shop instance
        
    def load_pending_bills(self):
        """Load danh sách hóa đơn chờ thanh toán"""
        try:
            with open(self.pending_bills_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Loi khi load pending bills: {e}")
            return {}
    
    def save_pending_bills(self):
        """Lưu danh sách hóa đơn chờ thanh toán"""
        try:
            with open(self.pending_bills_file, 'w', encoding='utf-8') as f:
                json.dump(self.pending_bills, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Loi khi save pending bills: {e}")
    
    def generate_addinfo(self, custom_addinfo=None):
        """Tạo addInfo cho QR"""
        if custom_addinfo and custom_addinfo.strip():
            return custom_addinfo.strip()
        
        # Tạo addInfo ngẫu nhiên tự động
        timestamp = int(time.time())
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        auto_addinfo = f"QR{timestamp}{random_str}"
        
        logger.info(f"Tao addInfo tu dong: {auto_addinfo}")
        return auto_addinfo
    
    def create_qr_payment(self, amount, addinfo=None, user_id=None, thread_id=None, app_name=None, months=None, warranty_code=None):
        """Tạo QR thanh toán"""
        try:
            # Validate amount
            try:
                amount_int = int(amount)
                if amount_int <= 0:
                    return None, "So tien phai lon hon 0"
            except ValueError:
                return None, "So tien khong hop le"
            
            # Tạo addInfo
            addinfo = self.generate_addinfo(addinfo)
            
            # Tạo QR URL
            qr_url = self.vietqr_template.format(amount=amount_int, addInfo=addinfo)
            
            # Tạo bill ID
            bill_id = f"BILL_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Lưu thông tin hóa đơn
            bill_info = {
                "bill_id": bill_id,
                "amount": amount_int,
                "addinfo": addinfo,
                "qr_url": qr_url,
                "user_id": user_id,
                "thread_id": thread_id,
                "app_name": app_name,
                "months": months,
                "warranty_code": warranty_code,
                "created_time": datetime.now().isoformat(),
                "expire_time": (datetime.now() + timedelta(minutes=10)).isoformat(),
                "status": "pending",  # pending, paid, expired
                "transaction_ref": None
            }
            
            self.pending_bills[bill_id] = bill_info
            self.save_pending_bills()
            
            logger.success(f"Tao QR thanh toan thanh cong: {bill_id}")
            return bill_info, None
            
        except Exception as e:
            logger.error(f"Loi khi tao QR thanh toan: {e}")
            return None, f"Loi: {str(e)}"
    
    def check_payment_status(self):
        """Kiểm tra trạng thái thanh toán"""

        try:
            # Load lại pending bills để đảm bảo có dữ liệu mới nhất
            self.pending_bills = self.load_pending_bills()
            
            # Lấy danh sách bills pending
            pending_bills = {k: v for k, v in self.pending_bills.items() if v.get("status") == "pending"}
            
            if not pending_bills:
                logger.info("Khong co bill pending nao de kiem tra")
                return
            
            logger.info(f"Kiem tra {len(pending_bills)} bills pending")
            
            response = requests.get(self.api_url, timeout=CONNECTION_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == "00" and data.get("des") == "success":
                    transactions = data.get("transactions", [])
                    logger.info(f"Lay duoc {len(transactions)} giao dich tu API")
                    
                    for transaction in transactions:
                        transaction_id = transaction.get("transactionID", "")
                        addinfo = transaction.get("escription", "").strip()
                        amount = transaction.get("amount", "0").replace(",", "")  # Loại bỏ dấu phẩy
                        cd = transaction.get("CD", "")  # + hoặc -
                        
                        # Chỉ xử lý giao dịch credit (+)
                        if cd != "+":
                            continue
                            
                        logger.info(f"Kiem tra giao dich: {transaction_id}, AddInfo: '{addinfo}', Amount: {amount}")
                        
                        # Kiểm tra xem có hóa đơn nào match không
                        for bill_id, bill_info in pending_bills.items():
                            bill_addinfo = bill_info.get("addinfo", "").strip()
                            bill_amount = str(bill_info.get("amount", 0))
                            
                            logger.info(f"  So sanh voi bill {bill_id}: AddInfo='{bill_addinfo}', Amount={bill_amount}")
                            
                            # Kiểm tra match: AddInfo có trong transaction và amount trùng
                            # Loại bỏ khoảng trắng để so sánh chính xác hơn
                            bill_addinfo_clean = bill_addinfo.replace(" ", "")
                            addinfo_clean = addinfo.replace(" ", "")
                            
                            if (bill_addinfo and bill_addinfo_clean in addinfo_clean and 
                                bill_amount == amount):
                                
                                logger.success(f"*** MATCH FOUND! Bill {bill_id} ***")
                                
                                # Đánh dấu đã thanh toán
                                bill_info["status"] = "paid"
                                bill_info["transaction_ref"] = transaction_id
                                bill_info["paid_time"] = datetime.now().isoformat()
                                
                                # Lưu lại thay đổi
                                self.pending_bills[bill_id] = bill_info
                                self.save_pending_bills()
                                
                                # Gửi thông báo thanh toán thành công
                                self.send_payment_success_notification(bill_info, transaction)
                                
                                # Thông báo cho Shop về giao dịch mới
                                if self.shop:
                                    self.shop.check_payment_status()
                                    logger.success(f"Da thong bao cho Shop ve giao dich: {transaction_id}")
                                
                                logger.success(f"Hoa don {bill_id} da thanh toan thanh cong")
                                break  # Chỉ xử lý 1 bill match đầu tiên
                            else:
                                logger.info(f"  Khong match")
                else:
                    logger.warning(f"API tra ve code: {data.get('code')}, des: {data.get('des')}")
            else:
                logger.error(f"API tra ve status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Loi ket noi API: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Loi parse JSON: {e}")
        except Exception as e:
            logger.error(f"Loi khi check payment status: {e}")
    
    def check_expired_bills(self):
        """Kiểm tra và xóa hóa đơn hết hạn"""
        current_time = datetime.now()
        expired_bills = []
        
        for bill_id, bill_info in self.pending_bills.items():
            if bill_info["status"] == "pending":
                expire_time = datetime.fromisoformat(bill_info["expire_time"])
                if current_time > expire_time:
                    bill_info["status"] = "expired"
                    expired_bills.append(bill_id)
                    logger.info(f"Hoa don {bill_id} da het han")
        
        if expired_bills:
            self.save_pending_bills()
    
    def send_payment_success_notification(self, bill_info, transaction):
        """Gửi thông báo thanh toán thành công"""
        try:
            notification = f"""
[+] **THANH TOAN THANH CONG** [+]

[$] **Ma hoa don:** {bill_info['bill_id']}
[$] **So tien:** {bill_info['amount']:,} VND
[#] **AddInfo:** {bill_info['addinfo']}
[&] **Ma giao dich:** {transaction.get('transactionID', 'N/A')}
[@] **Thoi gian thanh toan:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
[$] **Ngay giao dich:** {transaction.get('tranDate', 'N/A')}

[!] Cam on ban da su dung dich vu!
            """.strip()
            
            from zlapi.models import Message, ThreadType
            message = Message(text=notification)
            self.client.send(message, self.group_id, ThreadType.GROUP)
            
            # Gửi thông báo bảo hành vào box riêng
            self.send_warranty_notification(bill_info, transaction)
            
        except Exception as e:
            logger.error(f"Loi khi gui thong bao thanh toan: {e}")
    
    def send_warranty_notification(self, bill_info, transaction):
        """Gửi thông báo bảo hành vào box đã tạo hóa đơn"""
        try:
            # Lấy thread_id từ bill_info (box đã tạo hóa đơn)
            thread_id = bill_info.get('thread_id')
            if not thread_id:
                logger.warning("Khong co thread_id de gui thong bao bao hanh")
                return
            
            # Tạo mã bảo hành từ warranty_code tùy chỉnh hoặc addInfo (random)
            warranty_code = bill_info.get('warranty_code') or bill_info.get('addinfo', 'N/A')
            
            # Lấy tên app từ bill_info
            app_name = bill_info.get('app_name', 'Dich vu')
            
            # Lấy số tháng từ bill_info
            months = bill_info.get('months', 1)
            try:
                months = int(months)
            except (ValueError, TypeError):
                months = 1
            
            # Tính toán hạn sử dụng (thời gian hiện tại + số tháng)
            current_date = datetime.now()
            
            # Thêm số tháng vào ngày hiện tại
            expiry_date = current_date + relativedelta(months=months)
            
            warranty_message = f"""
[!] TAM AN KINH CHAO!!! [!]
Dich vu {app_name}
[+] MA BAO HANH: {warranty_code}
[+] Nhom bao hanh 1: ( Full thi join nhom 2 nhe )
[>] Nhom bao hanh 2:

[+] Han: {current_date.strftime('%d/%m/%Y')} - {expiry_date.strftime('%d/%m/%Y')}

[!] LUU Y THAM GIA:
[+] Luu y doc tin nhan gui kem ma bao hanh nay de ro cach su dung hieu qua nhat.
[+] Cac ban tham gia nhom bao hanh, khi co van de nhan ma bao hanh vao nhom, se duoc cac Nhan Vien ho tro.
Tranh nhan rieng 1 mot nguoi viec ho tro se keo dai.
            """.strip()
            
            from zlapi.models import Message, ThreadType
            message = Message(text=warranty_message)
            
            # Gửi vào box đã tạo hóa đơn
            self.client.send(message, thread_id, ThreadType.GROUP)
            
            logger.success(f"Da gui thong bao bao hanh vao box {thread_id} voi ma {warranty_code}")
            
        except Exception as e:
            logger.error(f"Loi khi gui thong bao bao hanh: {e}")
    
    def start(self):
        """Bắt đầu kiểm tra thanh toán"""
        if self.running:
            logger.warning("QR Payment checker da dang chay")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.success("QR Payment checker da bat dau chay")
    
    def stop(self):
        """Dừng kiểm tra thanh toán"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("QR Payment checker da dung")
    
    def _run(self):
        """Chạy kiểm tra thanh toán trong thread riêng"""
        logger.info("QR Payment checker bat dau kiem tra moi 30 giay")
        
        while self.running:
            try:
                self.check_payment_status()
                self.check_expired_bills()
                time.sleep(30)  # Kiểm tra mỗi 30 giây
            except Exception as e:
                logger.error(f"Loi trong QR Payment checker: {e}")
                time.sleep(30)
    
    def get_bill_status(self, bill_id):
        """Lấy trạng thái hóa đơn"""
        return self.pending_bills.get(bill_id)
    
    def get_pending_bills_count(self):
        """Lấy số lượng hóa đơn chờ thanh toán"""
        return len([bill for bill in self.pending_bills.values() if bill["status"] == "pending"])
    
    def get_status(self):
        """Lấy trạng thái QR Payment checker"""
        return {
            "running": self.running,
            "pending_bills": self.get_pending_bills_count(),
            "total_bills": len(self.pending_bills),
            "group_id": self.group_id
        }
