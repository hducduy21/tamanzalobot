from zlapi.models import Message, MultiMsgStyle, MessageStyle
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

des = {
    'version': "1.0.0",
    'credits': "Nguyễn Liên Mạnh",
    'description': "Tính thời gian đã sống từ ngày sinh (năm, tháng, ngày, giờ, phút, giây, tuần)"
}

def calculate_age(birth_date_str):
    try:
        # Validate and parse birth date (format: DD-MM-YYYY)
        if not re.match(r'^\d{2}-\d{2}-\d{4}$', birth_date_str):
            raise ValueError("Định dạng ngày sinh không hợp lệ. Vui lòng nhập theo định dạng DD-MM-YYYY (ví dụ: 15-06-1990)")

        birth_date = datetime.strptime(birth_date_str, '%d-%m-%Y')
        current_date = datetime.now()

        # Check if birth date is in the future
        if birth_date > current_date:
            raise ValueError("Ngày sinh không thể là ngày trong tương lai")

        # Calculate the difference using relativedelta for relative units
        diff = relativedelta(current_date, birth_date)

        # Calculate total time for cumulative units
        total_seconds = (current_date - birth_date).total_seconds()
        total_minutes = total_seconds // 60
        total_hours = total_minutes // 60
        total_days = total_hours // 24
        total_weeks = total_days // 7
        total_months = diff.years * 12 + diff.months  # Approximate total months
        total_years = diff.years

        # Format the result
        result = {
            'relative': {
                'years': diff.years,
                'months': diff.months,
                'days': diff.days,
                'hours': diff.hours,
                'minutes': diff.minutes,
                'seconds': diff.seconds,
                'weeks': total_days // 7  # Weeks based on total days
            },
            'total': {
                'years': total_years,
                'months': total_months,
                'days': int(total_days),
                'weeks': int(total_weeks),
                'hours': int(total_hours),
                'minutes': int(total_minutes),
                'seconds': int(total_seconds)
            }
        }

        return result, birth_date_str

    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError("Định dạng ngày sinh không hợp lệ. Vui lòng nhập theo định dạng DD-MM-YYYY")
        raise e

def handle_age_command(message, message_object, thread_id, thread_type, author_id, client):
    try:
        # Parse command for birth date (e.g., "/age 15-06-1990")
        parts = message.strip().split()

        # Check if no birth date is provided
        if len(parts) < 2:
            usage_msg = (
                "[ HƯỚNG DẪN SỬ DỤNG /age ]\n"
                "📅 Tính thời gian đã sống từ ngày sinh của bạn.\n\n"
                "Cách dùng:\n"
                "- Nhập lệnh: /age DD-MM-YYYY\n"
                "- Ví dụ: /age 15-06-1990\n\n"
                "Kết quả sẽ hiển thị:\n"
                "- Thời gian tương đối (năm, tháng, ngày, ...)\n"
                "- Tổng thời gian đã sống (tổng năm, tháng, ngày, ...)"
            )
            style = MultiMsgStyle([
                MessageStyle(offset=0, length=len(usage_msg), style="color", color="ff6347", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="font", size="13", auto_format=False),
                MessageStyle(offset=0, length=len(usage_msg), style="bold", auto_format=False),
                MessageStyle(offset=20, length=len(usage_msg), style="italic", auto_format=False)
            ])
            styled_message = Message(text=usage_msg, style=style)
            client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=50000)
            return

        birth_date_str = parts[1]

        # Calculate age
        age_result, birth_date = calculate_age(birth_date_str)

        # Format the message
        msg = (
            f"[ THỜI GIAN ĐÃ SỐNG - {birth_date} ]\n"
            f"📅 Ngày sinh: {birth_date}\n\n"
            f"Thời gian tương đối:\n"
            f"- {age_result['relative']['years']} năm\n"
            f"- {age_result['relative']['months']} tháng\n"
            f"- {age_result['relative']['days']} ngày\n"
            f"- {age_result['relative']['weeks']} tuần\n"
            f"- {age_result['relative']['hours']} giờ\n"
            f"- {age_result['relative']['minutes']} phút\n"
            f"- {age_result['relative']['seconds']} giây\n\n"
            f"Tổng thời gian đã sống:\n"
            f"- {age_result['total']['years']} năm\n"
            f"- {age_result['total']['months']} tháng\n"
            f"- {age_result['total']['days']} ngày\n"
            f"- {age_result['total']['weeks']} tuần\n"
            f"- {age_result['total']['hours']} giờ\n"
            f"- {age_result['total']['minutes']} phút\n"
            f"- {age_result['total']['seconds']} giây"
        )

        # Apply styling consistent with the original bot
        style = MultiMsgStyle([
            MessageStyle(offset=0, length=len(msg), style="color", color="ff6347", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="font", size="13", auto_format=False),
            MessageStyle(offset=0, length=len(msg), style="bold", auto_format=False),
            MessageStyle(offset=20, length=len(msg), style="italic", auto_format=False)
        ])

        # Send styled message
        styled_message = Message(text=msg, style=style)
        client.replyMessage(styled_message, message_object, thread_id, thread_type, ttl=50000)

    except ValueError as e:
        error_message = Message(text=f"Lỗi: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)
    except Exception as e:
        error_message = Message(text=f"Lỗi khi tính thời gian: {str(e)}")
        client.replyMessage(error_message, message_object, thread_id, thread_type, ttl=50000)

def get_mitaizl():
    return {
        'age': handle_age_command
    }