import requests
from zlapi.models import Message
from config import API_LISTKH, CONNECTION_TIMEOUT
des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Lấy mã xác minh Netflix từ mã và gửi cho người dùng (ai cũng dùng được)"
}

def handle_netflix_otp_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    if len(text) >= 2:
        ma = text[1]
    else:
        client.replyMessage(Message(text="Vui lòng nhập mã cần kiểm tra!"), message_object, thread_id, thread_type)
        return
    url1 = API_LISTKH
    try:
        data1 = requests.get(url1, timeout=CONNECTION_TIMEOUT).json()
    except Exception:
        client.replyMessage(Message(text="Không thể truy cập dữ liệu!"), message_object, thread_id, thread_type)
        return
    for item in data1:
        if item.get("A") == ma:
            url2 = item.get("C")
            if not url2:
                client.replyMessage(Message(text="Không tìm thấy URL dữ liệu tiếp theo!"), message_object, thread_id, thread_type)
                return
            try:
                data2 = requests.get(url2, timeout=CONNECTION_TIMEOUT).json()
            except Exception:
                client.replyMessage(Message(text="Không thể truy cập dữ liệu 2!"), message_object, thread_id, thread_type)
                return
            for row in data2[1:]:
                if "Mã xác minh:" in row[3]:
                    import re
                    match = re.search(r"Mã xác minh:\s*(\d+)", row[3])
                    time_str = row[2] if len(row) > 2 else "Không rõ thời gian"
                    # Convert ISO time to dd/MM/yyyy HH:mm:ss
                    try:
                        from datetime import datetime
                        time_fmt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        time_str_fmt = time_fmt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        time_str_fmt = time_str
                    if match:
                        otp = match.group(1)
                        client.replyMessage(Message(text=f"OTP: {otp}\nThời gian: {time_str_fmt}"), message_object, thread_id, thread_type,ttl=60000)
                        return
            client.replyMessage(Message(text="Không có OTP!"), message_object, thread_id, thread_type,ttl=20000)
            return
    client.replyMessage(Message(text="Không tìm thấy mã trong dữ liệu!"), message_object, thread_id, thread_type,ttl=20000)

def handle_netflix_verify_command(message, message_object, thread_id, thread_type, author_id, client):
    import re
    import html
    from datetime import datetime
    
    text = message.split()
    if len(text) >= 2:
        ma = text[1]
    else:
        client.replyMessage(Message(text="Vui lòng nhập mã cần kiểm tra!"), message_object, thread_id, thread_type)
        return
    
    url1 = API_LISTKH
    try:
        data1 = requests.get(url1, timeout=CONNECTION_TIMEOUT).json()
    except Exception as e:
        client.replyMessage(Message(text=f"Không thể truy cập dữ liệu! Lỗi: {str(e)}"), message_object, thread_id, thread_type)
        return
    
    for item in data1:
        if item.get("A") == ma:
            url2 = item.get("C")
            if not url2:
                client.replyMessage(Message(text="Không tìm thấy URL dữ liệu tiếp theo!"), message_object, thread_id, thread_type)
                return
            
            try:
                data2 = requests.get(url2, timeout=CONNECTION_TIMEOUT).json()
            except Exception as e:
                client.replyMessage(Message(text=f"Không thể truy cập dữ liệu 2! Lỗi: {str(e)}"), message_object, thread_id, thread_type)
                return
            
            # Kiểm tra xem data2 là array of objects hay array of arrays
            if not data2 or len(data2) == 0:
                client.replyMessage(Message(text="Không có dữ liệu email nào!"), message_object, thread_id, thread_type)
                return
            
            # Xử lý format mới: array of objects
            if isinstance(data2[0], dict):
                found_link = None
                found_time = None
                email_count = len(data2)
                email_info = []
                
                for idx, email_item in enumerate(data2):
                    if not isinstance(email_item, dict):
                        continue
                    
                    # Lấy thời gian
                    time_str = email_item.get("Thời gian", "Không rõ thời gian")
                    try:
                        time_fmt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                        time_str_fmt = time_fmt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        time_str_fmt = time_str
                    
                    # Kiểm tra field "Link Netflix Reset" hoặc "Link xác minh Netflix"
                    link_reset = email_item.get("Link Netflix Reset", "")
                    content = email_item.get("Nội dung chính", "")
                    subject = email_item.get("Chủ đề", "")
                    
                    # Tìm link trong "Link Netflix Reset"
                    if link_reset and link_reset.strip() and "netflix.com" in link_reset:
                        found_link = html.unescape(link_reset.strip())
                        found_time = time_str_fmt
                        break
                    
                    # Tìm link trong "Nội dung chính"
                    if content and "Link xác minh Netflix:" in content and "http" in content:
                        match = re.search(r"Link xác minh Netflix:\s*(https?://[^\s>]+)", content)
                        if match:
                            found_link = match.group(1).rstrip('>')
                            found_time = time_str_fmt
                            break
                    
                    # Lưu thông tin email để trả về nếu không tìm thấy link
                    email_info.append({
                        "subject": subject,
                        "time": time_str_fmt,
                        "has_link": bool(link_reset or ("http" in content))
                    })
                
                # Trả về kết quả
                if found_link:
                    client.replyMessage(
                        Message(text=f"Link xác minh Netflix: {found_link}\nThời gian: {found_time}"),
                        message_object, thread_id, thread_type, ttl=60000
                    )
                else:
                    # Trả về thông tin dữ liệu ngay cả khi không tìm thấy link
                    info_text = f"📧 Tổng số email: {email_count}\n"
                    if email_info:
                        info_text += "\n📋 Danh sách email:\n"
                        for i, info in enumerate(email_info[:10], 1):  # Chỉ hiển thị 10 email đầu
                            info_text += f"{i}. {info['subject']} - {info['time']}\n"
                        if len(email_info) > 10:
                            info_text += f"... và {len(email_info) - 10} email khác\n"
                    info_text += "\n❌ Không tìm thấy link xác minh Netflix trong các email này."
                    client.replyMessage(Message(text=info_text), message_object, thread_id, thread_type, ttl=60000)
                return
            
            # Xử lý format cũ: array of arrays (backward compatibility)
            else:
                for row in data2[1:] if len(data2) > 1 else data2:
                    if len(row) > 3 and "Link xác minh Netflix:" in row[3] and "http" in row[3]:
                        match = re.search(r"Link xác minh Netflix:\s*(https?://\S+)", row[3])
                        time_str = row[2] if len(row) > 2 else "Không rõ thời gian"
                        try:
                            time_fmt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                            time_str_fmt = time_fmt.strftime("%d/%m/%Y %H:%M:%S")
                        except Exception:
                            time_str_fmt = time_str
                        if match:
                            verify_link = match.group(1)
                            client.replyMessage(
                                Message(text=f"Link xác minh Netflix: {verify_link}\nThời gian: {time_str_fmt}"),
                                message_object, thread_id, thread_type, ttl=60000
                            )
                            return
                
                # Trả về thông tin dữ liệu nếu không tìm thấy
                info_text = f"📧 Tổng số email: {len(data2)}\n"
                info_text += "❌ Không tìm thấy link xác minh Netflix trong các email này."
                client.replyMessage(Message(text=info_text), message_object, thread_id, thread_type, ttl=60000)
                return
    
    # Không tìm thấy mã
    client.replyMessage(Message(text="Không tìm thấy mã trong dữ liệu!"), message_object, thread_id, thread_type, ttl=20000)

def get_mitaizl():
    return {
        'netflix_otp': handle_netflix_otp_command,
        'netflix_verify': handle_netflix_verify_command
    }
