from zlapi.models import Message, MultiMsgStyle, MessageStyle
import requests
import urllib.parse
import re

des = {
    'version': "1.0.3",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tạo mã QR ngân hàng để chuyển khoản, hỗ trợ ID giao dịch, mã ngân hàng số, và tên ngân hàng"
}

BANK_IDS = {
    "ICB": ("970415", "VietinBank"), "VCB": ("970436", "Vietcombank"), "BIDV": ("970418", "BIDV"),
    "VBA": ("970405", "Agribank"), "OCB": ("970448", "OCB"), "MB": ("970422", "MBBank"),
    "TCB": ("970407", "Techcombank"), "ACB": ("970416", "ACB"), "VPB": ("970432", "VPBank"),
    "TPB": ("970423", "TPBank"), "STB": ("970403", "Sacombank"), "HDB": ("970437", "HDBank"),
    "VCCB": ("970454", "VietCapitalBank"), "SCB": ("970429", "SCB"), "VIB": ("970441", "VIB"),
    "SHB": ("970443", "SHB"), "EIB": ("970431", "Eximbank"), "MSB": ("970426", "MSB"),
    "CAKE": ("546034", "CAKE"), "Ubank": ("546035", "Ubank"), "TIMO": ("963388", "Timo"),
    "VTLMONEY": ("971005", "ViettelMoney"), "VNPTMONEY": ("971011", "VNPTMoney"),
    "SGICB": ("970400", "SaigonBank"), "BAB": ("970409", "BacABank"), "PVCB": ("970412", "PVcomBank"),
    "Oceanbank": ("970414", "Oceanbank"), "NCB": ("970419", "NCB"), "SHBVN": ("970424", "ShinhanBank"),
    "ABB": ("970425", "ABBANK"), "VAB": ("970427", "VietABank"), "NAB": ("970428", "NamABank"),
    "PGB": ("970430", "PGBank"), "VIETBANK": ("970433", "VietBank"), "BVB": ("970438", "BaoVietBank"),
    "SEAB": ("970440", "SeABank"), "COOPBANK": ("970446", "COOPBANK"), "LPB": ("970449", "LPBank"),
    "KLB": ("970452", "KienLongBank"), "KBank": ("668888", "KBank"), "KBHN": ("970462", "KookminHN"),
    "KEBHANAHCM": ("970466", "KEBHanaHCM"), "KEBHANAHN": ("970467", "KEBHANAHN"), "MAFC": ("977777", "MAFC"),
    "CITIBANK": ("533948", "Citibank"), "KBHCM": ("970463", "KookminHCM"), "VBSP": ("999888", "VBSP"),
    "WVN": ("970457", "Woori"), "VRB": ("970421", "VRB"), "UOB": ("970458", "UnitedOverseas"),
    "SCVN": ("970410", "StandardChartered"), "PBVN": ("970439", "PublicBank"), "NHB HN": ("801011", "Nonghyup"),
    "IVB": ("970434", "IndovinaBank"), "IBK - HCM": ("970456", "IBKHCM"), "IBK - HN": ("970455", "IBKHN"),
    "HSBC": ("458761", "HSBC"), "HLBVN": ("970442", "HongLeong"), "GPB": ("970408", "GPBank"),
    "DOB": ("970406", "DongABank"), "DBS": ("796500", "DBSBank"), "CIMB": ("422589", "CIMB"),
    "CBB": ("970444", "CBBank")
}

VIETQR_BASE_URL = "https://img.vietqr.io/image/"

def get_numeric_bank_id(bank_input):
    # Normalize input
    bank_input = bank_input.strip()
    
    # Check if input is a short code
    if bank_input.upper() in BANK_IDS:
        return BANK_IDS[bank_input.upper()][0], BANK_IDS[bank_input.upper()][1]
    
    # Check if input is a numeric ID
    for short_code, (numeric_id, bank_name) in BANK_IDS.items():
        if bank_input == numeric_id:
            return numeric_id, bank_name
    
    # Check if input is a bank name (case-insensitive, handle spaces)
    bank_input_lower = bank_input.lower().replace(" ", "")
    for short_code, (numeric_id, bank_name) in BANK_IDS.items():
        if bank_name.lower().replace(" ", "") == bank_input_lower:
            return numeric_id, bank_name
    
    raise ValueError(f"Ngân hàng không hợp lệ. Chọn từ: {', '.join(BANK_IDS.keys())} hoặc mã số/tên ngân hàng")

def generate_qr_url(bank_id, account_no, amount, description, account_name, transaction_id=None):
    try:
        # Get numeric bank ID and bank name
        numeric_bank_id, bank_name = get_numeric_bank_id(bank_id)

        # Validate inputs
        if not account_no.isdigit():
            raise ValueError("Số tài khoản chỉ được chứa chữ số")
        if not amount.isdigit() or int(amount) <= 0:
            raise ValueError("Số tiền phải là số dương")
        if not account_name.strip():
            raise ValueError("Tên tài khoản không được để trống")
        if transaction_id and (not re.match(r'^[a-zA-Z0-9]+$', transaction_id) or len(transaction_id) > 50):
            raise ValueError("ID giao dịch phải là chữ cái hoặc số, tối đa 50 ký tự")

        # Combine description and transaction ID
        add_info = description.strip()
        if transaction_id:
            add_info = f"{add_info} - {transaction_id}"

        # Encode parameters
        encoded_add_info = urllib.parse.quote(add_info)
        encoded_account_name = urllib.parse.quote(account_name.strip())

        # Generate QR code URL
        qr_url = (
            f"{VIETQR_BASE_URL}{numeric_bank_id}-{account_no}-compact.png"
            f"?amount={amount}&addInfo={encoded_add_info}&accountName={encoded_account_name}"
        )

        # Verify URL accessibility
        response = requests.head(qr_url, timeout=5)
        if response.status_code != 200:
            raise Exception(f"Không thể tạo mã QR: HTTP {response.status_code}")

        return qr_url, add_info, bank_name
    except requests.exceptions.RequestException as e:
        raise Exception(f"Lỗi khi kiểm tra URL QR: {str(e)}")

def handle_bankqr_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Parse command: /bankqr <BANK_ID> <ACCOUNT_NO> <AMOUNT> <DESCRIPTION> <ACCOUNT_NAME> [ID]
        parts = message.strip().split(maxsplit=5)
        if len(parts) < 5:
            error_message = Message(text="Vui lòng nhập đầy đủ: /bankqr <BANK_ID> <ACCOUNT_NO> <AMOUNT> <DESCRIPTION> <ACCOUNT_NAME> [ID]\nVí dụ: /bankqr VCB 123456789 1000000 Thanh toan Nguyen Van A ID123")
            client.replyMessage(error_message, message_object, thread_id, thread_type)
            return

        _, bank_id, account_no, amount, description_and_name = parts[:5]
        transaction_id = parts[5] if len(parts) > 5 else None

        # Split description_and_name to separate description and account_name
        desc_parts = description_and_name.rsplit(maxsplit=1)
        if len(desc_parts) < 2:
            description = description_and_name
            account_name = "Unknown"
        else:
            description, account_name = desc_parts

        # Generate QR code URL
        qr_url, add_info, bank_name = generate_qr_url(bank_id, account_no, amount, description, account_name, transaction_id)

        # Format message
        msg = (
            f"[ MÃ QR CHUYỂN KHOẢN ]\n"
            f"🏦 Ngân hàng: {bank_name}\n"
            f"💳 Số tài khoản: {account_no}\n"
            f"👤 Tên tài khoản: {account_name}\n"
            f"💰 Số tiền: {int(amount):,} VND\n"
            f"📝 Nội dung: {add_info}\n"
            f"📷 Quét mã QR dưới để chuyển khoản!"
        )

        # Apply styling
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=20, length=len(msg), style="italic", auto_format=False)
        ])

        # Send QR code image and message
        client.sendRemoteImage(
            qr_url,
            message=Message(text=msg, style=style),
            thread_id=thread_id,
            thread_type=thread_type,
            width=300,
            height=300
        )

    except ValueError as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type)
    except Exception as e:
        error_message = Message(text=f"Lỗi khi tạo mã QR: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'bankqr': handle_bankqr_command
    }