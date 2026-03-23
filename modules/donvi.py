import json
from config import CONNECTION_TIMEOUT
from zlapi.models import Message
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup
import re

des = {
    'version': "1.0.0",
    'credits': "GitHub Copilot",
    'description': "Chuyển đổi đơn vị hành chính cũ sang đơn vị hành chính mới và tra cứu mã số thuế"
}

# Đường dẫn đến file JSON chứa dữ liệu đơn vị hành chính
DATA_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'data.json')

def load_administrative_data():
    """
    Tải dữ liệu đơn vị hành chính từ file JSON
    """
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        return {"error": f"Không thể tải dữ liệu: {str(e)}"}

def convert_administrative_unit(ward_name, district_name, province_name):
    """
    Chuyển đổi đơn vị hành chính cũ sang mới
    
    Args:
        ward_name (str): Tên xã/phường cũ
        district_name (str): Tên quận/huyện cũ
        province_name (str): Tên tỉnh/thành phố cũ
        
    Returns:
        dict: Thông tin đơn vị hành chính mới
    """
    # Tải dữ liệu từ file JSON
    data = load_administrative_data()
    
    if "error" in data:
        return {"error": data["error"]}
    
    # Chuẩn hóa tên đầu vào
    ward_name = ward_name.strip()
    district_name = district_name.strip()
    province_name = province_name.strip()
    
    # Xử lý tiền tố trong tên tỉnh/thành phố
    if not province_name.lower().startswith(("tỉnh ", "thành phố ", "tp ", "t.p ")):
        province_search_terms = [
            f"Tỉnh {province_name}",
            f"Thành phố {province_name}",
            province_name
        ]
    else:
        province_search_terms = [province_name]
    
    # Xử lý tiền tố trong tên quận/huyện
    if not district_name.lower().startswith(("quận ", "huyện ", "thị xã ", "thành phố ")):
        district_search_terms = [
            f"Quận {district_name}",
            f"Huyện {district_name}",
            f"Thị xã {district_name}",
            f"Thành phố {district_name}",
            district_name
        ]
    else:
        district_search_terms = [district_name]
    
    # Xử lý tiền tố trong tên xã/phường
    if not ward_name.lower().startswith(("xã ", "phường ", "thị trấn ")):
        ward_search_terms = [
            f"Xã {ward_name}",
            f"Phường {ward_name}",
            f"Thị trấn {ward_name}",
            ward_name
        ]
    else:
        ward_search_terms = [ward_name]
    
    # Tìm kiếm đơn vị hành chính
    for item in data:
        old_ward_name = item.get("`old_ward_name`", "").strip()
        old_district_name = item.get("`old_district_name`", "").strip()
        old_province_name = item.get("`old_province_name`", "").strip()
        
        # Kiểm tra nếu có kết quả phù hợp
        if any(ward.lower() == old_ward_name.lower() for ward in ward_search_terms) and \
           any(district.lower() == old_district_name.lower() for district in district_search_terms) and \
           any(province.lower() == old_province_name.lower() for province in province_search_terms):
            
            return {
                "success": True,
                "new_ward_name": item.get("`new_ward_name`", ""),
                "new_province_name": item.get("`new_province_name`", ""),
                "new_ward_code": item.get("`new_ward_code`", ""),
                "old_ward_code": item.get("`old_ward_code`", "")
            }
    
    # Nếu không tìm thấy kết quả chính xác, thử tìm kết quả gần đúng
    for item in data:
        old_ward_name = item.get("`old_ward_name`", "").strip()
        old_district_name = item.get("`old_district_name`", "").strip()
        old_province_name = item.get("`old_province_name`", "").strip()
        
        # Kiểm tra nếu có kết quả gần đúng (chỉ cần xã/phường và tỉnh/thành phố phù hợp)
        if any(ward.lower() == old_ward_name.lower() for ward in ward_search_terms) and \
           any(province.lower() == old_province_name.lower() or 
              province.lower() in old_province_name.lower() or 
              old_province_name.lower() in province.lower() for province in province_search_terms):
            
            return {
                "success": True,
                "new_ward_name": item.get("`new_ward_name`", ""),
                "new_province_name": item.get("`new_province_name`", ""),
                "new_ward_code": item.get("`new_ward_code`", ""),
                "old_ward_code": item.get("`old_ward_code`", ""),
                "note": "Kết quả gần đúng"
            }
    
    return {"success": False, "message": "Không tìm thấy thông tin đơn vị hành chính"}

def fetch_tax_info(tax_id):
    """
    Lấy thông tin từ mã số thuế
    
    Args:
        tax_id (str): Mã số thuế cần tra cứu
        
    Returns:
        dict: Thông tin về mã số thuế
    """
    url = f"https://thongtin.vn/ma-so-thue-doanh-nghiep/{tax_id}"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=CONNECTION_TIMEOUT)
        
        if response.status_code != 200:
            return {"success": False, "message": f"Không thể kết nối đến trang web. Mã lỗi: {response.status_code}"}
        
        # Phân tích HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tìm thẻ div chứa thông tin
        info_div = soup.find('div', class_='p-6 rounded-xl bg-white dark:bg-white/10 border border-zinc-200 dark:border-white/10 space-y-6')
        
        if not info_div:
            return {"success": False, "message": "Không tìm thấy thông tin mã số thuế"}
        
        # Lấy thông tin cơ bản
        company_name = info_div.find('h1')
        company_name = company_name.text.strip() if company_name else "Không có thông tin"
        
        # Lấy thông tin từ bảng
        table = info_div.find('table')
        result = {"success": True, "company_name": company_name}
        
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].text.strip()
                    value = cells[1].text.strip()
                    
                    # Trích xuất trực tiếp các trường quan trọng
                    if "Mã số thuế" in label:
                        result["ma_so_thue"] = value
                    elif "Địa chỉ" in label:
                        result["dia_chi"] = value
                    elif "Người đại diện" in label:
                        result["nguoi_dai_dien"] = value
                    elif "Số điện thoại" in label:
                        result["so_dien_thoai"] = value
                    elif "Ngày hoạt động" in label:
                        result["ngay_hoat_dong"] = value
                    elif "Quản lý bởi" in label:
                        result["quan_ly_boi"] = value
                    elif "Tình trạng" in label:
                        result["tinh_trang"] = value
                    
                    # Xử lý label để dễ sử dụng (vẫn giữ lại cho tương thích)
                    label = re.sub(r'\s+', '_', label.lower())
                    label = re.sub(r'[^\w]', '', label)
                    
                    result[label] = value
        
        # Thêm URL để người dùng có thể truy cập
        result["url"] = url
        
        return result
    
    except Exception as e:
        return {"success": False, "message": f"Lỗi khi tra cứu: {str(e)}"}

def handle_donvi_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh donvi
    """
    parts = message.strip().split(' ', 1)
    
    if len(parts) < 2:
        response = """❌ Sử dụng: .donvi <xã/phường>,<quận/huyện>,<tỉnh/thành phố>
Ví dụ: .donvi Vạn Yên,Vân Đồn,Quảng Ninh"""
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return
    
    # Lấy nội dung lệnh
    content = parts[1].strip()
    
    # Tách các thành phần
    components = content.split(',')
    
    if len(components) < 3:
        response = """❌ Thiếu thông tin! Sử dụng đúng định dạng:
.donvi <xã/phường>,<quận/huyện>,<tỉnh/thành phố>
Ví dụ: .donvi Vạn Yên,Vân Đồn,Quảng Ninh"""
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return
    
    ward_name = components[0].strip()
    district_name = components[1].strip()
    province_name = components[2].strip()
    
    # Thực hiện chuyển đổi
    result = convert_administrative_unit(ward_name, district_name, province_name)
    
    if "error" in result:
        response = f"❌ Lỗi: {result['error']}"
    elif result["success"]:
        if "note" in result:
            response = f"""✅ Kết quả chuyển đổi (gần đúng):
🔹 Đơn vị hành chính cũ: {ward_name}, {district_name}, {province_name}
🔹 Đơn vị hành chính mới: {result['new_ward_name']}, {result['new_province_name']}
🔹 Mã đơn vị cũ: {result['old_ward_code']}
🔹 Mã đơn vị mới: {result['new_ward_code']}"""
        else:
            response = f"""✅ Kết quả chuyển đổi:
🔹 Đơn vị hành chính cũ: {ward_name}, {district_name}, {province_name}
🔹 Đơn vị hành chính mới: {result['new_ward_name']}, {result['new_province_name']}
🔹 Mã đơn vị cũ: {result['old_ward_code']}
🔹 Mã đơn vị mới: {result['new_ward_code']}"""
    else:
        response = f"""❌ Không tìm thấy thông tin chuyển đổi cho:
🔹 {ward_name}, {district_name}, {province_name}
👉 Vui lòng kiểm tra lại thông tin và cú pháp."""
    
    client.replyMessage(Message(text=response), message_object, thread_id, thread_type)

def handle_mst_command(message, message_object, thread_id, thread_type, author_id, client):
    """
    Xử lý lệnh mst
    """
    parts = message.strip().split(' ', 1)
    
    if len(parts) < 2:
        response = """❌ Sử dụng: .mst <mã số thuế>
Ví dụ: .mst 0111119836"""
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return
    
    # Lấy mã số thuế
    tax_id = parts[1].strip()
    
    # Kiểm tra mã số thuế hợp lệ (chỉ gồm số)
    if not tax_id.isdigit():
        response = "❌ Mã số thuế phải là chuỗi chữ số."
        client.replyMessage(Message(text=response), message_object, thread_id, thread_type)
        return
    
    # Gửi thông báo đang xử lý
    client.replyMessage(Message(text="⏳ Đang tra cứu mã số thuế, vui lòng đợi..."), message_object, thread_id, thread_type)
    
    # Thực hiện tra cứu
    result = fetch_tax_info(tax_id)
    
    if not result["success"]:
        response = f"❌ {result['message']}"
    else:
        # Tạo phản hồi
        response = f"""✅ Thông tin mã số thuế {tax_id}:
🏢 Tên doanh nghiệp: {result.get('company_name', 'Không có thông tin')}
🔢 Mã số thuế: {result.get('ms_thu', 'Không có thông tin')}
📍 Địa chỉ: {result.get('a_ch', 'Không có thông tin')}
👤 Người đại diện: {result.get('ngi_i_din', 'Không có thông tin')}
📱 Số điện thoại: {result.get('s_in_thoi', 'Không có thông tin')}
📅 Ngày hoạt động: {result.get('ngy_hot_ng', 'Không có thông tin')}
👨‍💼 Quản lý bởi: {result.get('qun_l_bi', 'Không có thông tin')}
⚡ Trạng thái: {result.get('tnh_trng', 'Không có thông tin')}

🔗 Xem chi tiết: {result.get('url', '')}"""
    
    client.replyMessage(Message(text=response), message_object, thread_id, thread_type)

def get_mitaizl():
    return {
        'donvi': handle_donvi_command,
        'mst': handle_mst_command
    }
