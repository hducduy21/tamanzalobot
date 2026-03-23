import requests
from config import CONNECTION_TIMEOUT
import json
import time
import threading
from datetime import datetime
from utils.logging_utils import Logging

logger = Logging()

# Module metadata for CommandHandler
des = {
    "version": "1.0.0",
    "credits": "AutoCheck Module",
    "description": "Auto transaction checker module"
}

def get_mitaizl():
    """Return empty dict since this is not a command module"""
    return {}

class AutoCheck:
    def __init__(self, client, group_id="5366422691182401170"):
        self.client = client
        self.group_id = group_id
        self.api_url = "http://160.191.245.27/api-vietcombank-11062024/api-vietcombank-11062024/to9xvn.php?type=3"
        self.check_interval = 2  # 20 giây
        self.sent_refnos_file = "modules/cache/sent_refnos.json"
        self.sent_refnos = self.load_sent_refnos()
        self.running = False
        self.thread = None
        
    def load_sent_refnos(self):
        """Load danh sách refNo đã gửi thông báo"""
        try:
            with open(self.sent_refnos_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Lỗi khi load sent_refnos: {e}")
            return []
    
    def save_sent_refnos(self):
        """Lưu danh sách refNo đã gửi thông báo"""
        try:
            with open(self.sent_refnos_file, 'w', encoding='utf-8') as f:
                json.dump(self.sent_refnos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Lỗi khi save sent_refnos: {e}")
    
    def check_transactions(self):
        """Kiểm tra giao dịch mới từ API"""
        try:
            response = requests.get(self.api_url, timeout=CONNECTION_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == "00" and data.get("des") == "success":
                    transactions = data.get("transactions", [])
                    
                    for transaction in transactions:
                        transaction_id = transaction.get("transactionID", "")
                        cd = transaction.get("CD", "")
                        
                        # Chỉ xử lý giao dịch credit (+)
                        if cd != "+":
                            continue
                        
                        # Kiểm tra xem transactionID đã được gửi thông báo chưa
                        if transaction_id and transaction_id not in self.sent_refnos:
                            # Kiểm tra xem có phải giao dịch từ QR Payment không
                            if not self.is_qr_payment_transaction(transaction):
                                self.send_transaction_notification(transaction)
                                self.sent_refnos.append(transaction_id)
                                self.save_sent_refnos()
                                logger.success(f"Da gui thong bao giao dich moi: {transaction_id}")
                            else:
                                # Vẫn lưu transactionID để tránh spam nhưng không gửi thông báo
                                self.sent_refnos.append(transaction_id)
                                self.save_sent_refnos()
                                logger.info(f"Giao dich tu QR Payment, khong gui thong bao: {transaction_id}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Loi ket noi API: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Loi parse JSON: {e}")
        except Exception as e:
            logger.error(f"Loi khi check transactions: {e}")
    
    def is_qr_payment_transaction(self, transaction):
        """Kiểm tra xem giao dịch có phải từ QR Payment không"""
        try:
            # Import QRPayment để kiểm tra pending bills
            from modules.qrthanhtoan import QRPayment
            
            # Tạo instance tạm để kiểm tra
            temp_qr = QRPayment(None)
            pending_bills = temp_qr.load_pending_bills()
            
            addinfo = transaction.get("escription", "")
            amount = transaction.get("amount", "0").replace(",", "")  # Loại bỏ dấu phẩy
            
            # Kiểm tra xem có hóa đơn nào match không
            for bill_id, bill_info in pending_bills.items():
                if (bill_info["status"] == "pending" and 
                    bill_info["addinfo"] in addinfo and 
                    str(bill_info["amount"]) == amount):
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Loi khi kiem tra QR payment transaction: {e}")
            return False
    
    def send_transaction_notification(self, transaction):
        """Gửi thông báo giao dịch mới đến nhóm"""
        try:
            # Lấy thông tin giao dịch
            transaction_id = transaction.get("transactionID", "N/A")
            tran_date = transaction.get("tranDate", "N/A")
            transaction_date = transaction.get("TransactionDate", "N/A")
            cur_code = transaction.get("curCode", "VND")
            amount_str = transaction.get("amount", "0").replace(",", "")
            cd = transaction.get("CD", "")
            description = transaction.get("escription", "N/A")
            posting_date = transaction.get("PostingDate", "N/A")
            posting_time = transaction.get("PostingTime", "N/A")
            tnx_code = transaction.get("TnxCode", "N/A")
            
            # Xác định loại giao dịch
            if cd == "+":
                amount = f"+{int(amount_str):,} {cur_code}"
                transaction_kind = "NHAN TIEN"
                emoji = "[+]"
            elif cd == "-":
                amount = f"-{int(amount_str):,} {cur_code}"
                transaction_kind = "CHUYEN TIEN"
                emoji = "[-]"
            else:
                amount = f"{int(amount_str):,} {cur_code}"
                transaction_kind = "GIAO DICH KHAC"
                emoji = "[*]"
            
            # Tạo thông báo
            notification = f"""
{emoji} **THONG BAO GIAO DICH MOI** {emoji}

- **Loai giao dich:** {transaction_kind}
- **So tien:** {amount}
- **Ma giao dich:** {transaction_id}
- **Thoi gian:** {tran_date}
- **Ngay ghi so:** {posting_date} {posting_time}
- **Mo ta:** {description[:100]}{'...' if len(description) > 100 else ''}

- **Thoi gian thong bao:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            """.strip()
            
            # Gửi thông báo đến nhóm
            from zlapi.models import Message, ThreadType
            
            message = Message(text=notification)
            self.client.send(message, self.group_id, ThreadType.GROUP)
            
        except Exception as e:
            logger.error(f"Loi khi gui thong bao giao dich: {e}")
    
    def start(self):
        """Bắt đầu autocheck"""
        if self.running:
            logger.warning("AutoCheck da dang chay")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.success("AutoCheck da bat dau chay")
    
    def stop(self):
        """Dừng autocheck"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("AutoCheck da dung")
    
    def _run(self):
        """Chạy autocheck trong thread riêng"""
        logger.info(f"AutoCheck bat dau kiem tra moi {self.check_interval} giay")
        
        while self.running:
            try:
                self.check_transactions()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Loi trong AutoCheck: {e}")
                time.sleep(self.check_interval)
    
    def get_status(self):
        """Lấy trạng thái autocheck"""
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "sent_count": len(self.sent_refnos),
            "group_id": self.group_id
        }
