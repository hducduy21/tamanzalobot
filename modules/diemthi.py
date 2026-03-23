import json
import datetime
import requests
from zlapi.models import Message

des = {
    'version': "1.0.0",
    'credits': "basil204",
    'description': "Tra cứu điểm thi THPT Quốc Gia"
}

def config():
    return {
        "name": "diemthi",
        "version": "1.0.0",
        "description": "Tra cứu điểm thi THPT Quốc Gia",
        "credits": "basil204",
        "hasPermssion": 0,
        "usage": "diemthi [SBD] [năm]",
        "cooldowns": 5
    }

def handle_diemthi_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        args = message.split()[1:] if len(message.split()) > 1 else []
        if len(args) < 1:
            return client.send(thread_id=thread_id, thread_type=thread_type, message=Message("Vui lòng nhập số báo danh!"))
        sbd = args[0]
        current_year = datetime.datetime.now().year
        year = args[1] if len(args) > 1 else current_year
        url = f"https://diemthi.itbloginfo.com/newsapi-edu/EducationStudentScore/CheckCandidateNumber/?ComponentId=COMPONENT002297&PageId=95be1729ac2745ba9e873ef1f8f66254&sbd={sbd}&type=2&year={year}"
        response = requests.get(url)
        data = response.json()
        if not data.get("status"):
            return client.send(thread_id=thread_id, thread_type=thread_type, message=Message(f"❌ Không tìm thấy thông tin điểm thi cho SBD: {sbd} năm {year}"))
        student_data = data.get("data", {}).get("data", {})
        if not student_data:
            return client.send(thread_id=thread_id, thread_type=thread_type, message=Message(f"❌ Không tìm thấy thông tin điểm thi cho SBD: {sbd} năm {year}"))
        candidateNumber = student_data.get("candidateNumber", "")
        exam_cluster = student_data.get("examCluster", "")
        cum_thi_code = str(candidateNumber)[:2] if candidateNumber else ""
        subject_scores = student_data.get("subjectScores", {})
        response_msg = f"📝 KẾT QUẢ ĐIỂM THI THPT QUỐC GIA {year}\n"
        response_msg += f"🆔 Số báo danh: {candidateNumber}\n"
        response_msg += f"🏫 Sở GD&ĐT: {exam_cluster}\n"
        response_msg += f"🔢 Mã cụm thi: {cum_thi_code}\n\n"
        response_msg += "📊 ĐIỂM CÁC MÔN THI:\n"
        for subject_code, subject_data in subject_scores.items():
            subject_name = subject_data.get("subjectName", "")
            point = subject_data.get("point", 0)
            response_msg += f"- {subject_name}: {point}\n"
        # Tổng điểm các khối
        toan = subject_scores.get("Toan", {}).get("point", 0)
        van = subject_scores.get("Van", {}).get("point", 0)
        ngoai_ngu = subject_scores.get("NgoaiNgu", {}).get("point", 0)
        ly = subject_scores.get("Ly", {}).get("point", 0)
        hoa = subject_scores.get("Hoa", {}).get("point", 0)
        sinh = subject_scores.get("Sinh", {}).get("point", 0)
        # Khối D
        if toan and van and ngoai_ngu:
            response_msg += f"\n🌐 Tổng điểm khối D (Toán, Văn, Ngoại ngữ): {toan + van + ngoai_ngu:.2f}\n"
        # Khối A
        if toan and ly and hoa:
            response_msg += f"🔬 Tổng điểm khối A (Toán, Lí, Hóa): {toan + ly + hoa:.2f}\n"
        # Khối B
        if toan and hoa and sinh:
            response_msg += f"🌱 Tổng điểm khối B (Toán, Hóa, Sinh): {toan + hoa + sinh:.2f}\n"
        # Khối C
        if van and ly and hoa:
            response_msg += f"📜 Tổng điểm khối C (Văn, Lí, Hóa): {van + ly + hoa:.2f}\n"
        # Tổng điểm các khối phổ biến
        khoi_dict = {
            'A00': ['Toan', 'Ly', 'Hoa'],
            'A01': ['Toan', 'Ly', 'NgoaiNgu'],
            'B00': ['Toan', 'Hoa', 'Sinh'],
            'C00': ['Van', 'Su', 'Dia'],
            'D01': ['Van', 'Toan', 'NgoaiNgu'],
        }
        for khoi, mons in khoi_dict.items():
            if all(subject_scores.get(m, {}).get('point', 0) for m in mons):
                total = sum(subject_scores.get(m, {}).get('point', 0) for m in mons)
                response_msg += f"🔹 Tổng điểm khối {khoi} ({', '.join(mons)}): {total:.2f}\n"
        client.send(thread_id=thread_id, thread_type=thread_type, message=Message(response_msg))
    except Exception as e:
        client.send(thread_id=thread_id, thread_type=thread_type, message=Message(f"❌ Đã xảy ra lỗi: {str(e)}"))

def get_mitaizl():
    return {
        'diemthi': handle_diemthi_command
    }
