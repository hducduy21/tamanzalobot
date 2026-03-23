import requests
from zlapi.models import Message
import time
import re  # Regular expression module to clean the license plate input
des = {
    'version': "1.9.2",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tìm Phạt Nguồi"
}
# Define API URL for traffic fine checking
phatnguoi_api_url = "https://api.checkphatnguoi.vn/phatnguoi"

# Function to clean the license plate (remove any non-alphanumeric characters)
def clean_license_plate(bienso):
    # Remove anything that is not a number or letter (like "-", ".")
    return re.sub(r'[^a-zA-Z0-9]', '', bienso)

# Function to fetch traffic fine information
def fetch_traffic_fines(bienso, retries=3):
    try:
        # Clean the license plate
        cleaned_bienso = clean_license_plate(bienso)

        # Make a POST request to the API with the cleaned license plate
        response = requests.post(
            phatnguoi_api_url,
            json={"bienso": cleaned_bienso}
        )
        response.raise_for_status()
        data = response.json()

        # Check if the API returned any fines
        if data.get('status') != 1 or not data.get('data'):
            return "Không tìm thấy thông tin phạt nguội cho biển số này!"

        # Parse the fine details
        fine_data = data['data'][0]
        license_plate = fine_data.get('Biển kiểm soát', 'Không có thông tin')
        violation_time = fine_data.get('Thời gian vi phạm', 'Không có thông tin')
        violation_location = fine_data.get('Địa điểm vi phạm', 'Không có thông tin')
        violation_type = fine_data.get('Hành vi vi phạm', 'Không có thông tin')
        status = fine_data.get('Trạng thái', 'Không có thông tin')
        unit = fine_data.get('Đơn vị phát hiện vi phạm', 'Không có thông tin')

        # Create a response message
        msg = (
            f"[ Thông tin phạt nguội ]\n"
        f"🚗 Biển số xe: {license_plate}\n"
    f"🕒 Thời gian vi phạm: {violation_time}\n"
    f"📍 Địa điểm vi phạm: {violation_location}\n"
    f"🔴 Hành vi vi phạm: {violation_type}\n"
    f"⚖ Trạng thái: {status}\n"
    f"👮‍♂️ Đơn vị phát hiện: {unit}\n"
    f"📞 Liên hệ: Cục Cảnh sát giao thông - 0886889666\n"
    f"🤖 Kiểm tra bởi bot: Nguyễn Liên Mạnh"
)

        return msg

    except requests.exceptions.RequestException:
        if retries > 0:
            time.sleep(1)
            return fetch_traffic_fines(bienso, retries - 1)
        return "Đã có lỗi xảy ra khi kiểm tra phạt nguội!"

# Function to handle traffic fine check command (now called phatnguoi)
def handle_phatnguoi_command(message, message_object, thread_id, thread_type, author_id, client):
    text = message.split()
    if len(text) < 2:
        error_message = Message(text="Vui lòng nhập biển số xe để kiểm tra phạt nguội.")
        client.sendMessage(error_message, thread_id, thread_type)
        return

    bienso = text[1]
    fine_info = fetch_traffic_fines(bienso)
    client.replyMessage(Message(text=f"{fine_info}"), message_object, thread_id, thread_type)

# Add the new command to your modules
def get_mitaizl():
    return {
        'phatnguoi': handle_phatnguoi_command  # Renamed the command to 'phatnguoi'
    }
