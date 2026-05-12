import json
from zlapi.models import Message
from utils.feature_flags import get_all_flags, set_flag, DESCRIPTIONS

des = {
    'version': "1.0.0",
    'credits': "Hoàng Đức Duy",
    'description': "Quản lý feature flag của bot"
}


def _is_admin(author_id):
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return author_id == data.get('admin') or author_id in data.get('adm', [])
    except Exception:
        return False


def handle_flag_command(message, message_object, thread_id, thread_type, author_id, client):
    if not _is_admin(author_id):
        client.replyMessage(
            Message(text="• Bạn không đủ quyền hạn để sử dụng lệnh này."),
            message_object, thread_id, thread_type
        )
        return

    parts = message.split()
    sub = parts[1].lower() if len(parts) >= 2 else 'list'

    if sub == 'list':
        flags = get_all_flags()
        lines = ["[ FEATURE FLAGS ]", ""]
        for name, value in flags.items():
            status = "✅ BẬT" if value else "❌ TẮT"
            desc = DESCRIPTIONS.get(name, '')
            lines.append(f"• {name}: {status}")
            if desc:
                lines.append(f"  {desc}")
        client.replyMessage(
            Message(text="\n".join(lines)),
            message_object, thread_id, thread_type
        )
        return

    if sub in ('on', 'off') and len(parts) >= 3:
        flag_name = parts[2]
        value = sub == 'on'
        if not set_flag(flag_name, value):
            client.replyMessage(
                Message(text=f"• Flag '{flag_name}' không tồn tại."),
                message_object, thread_id, thread_type
            )
            return
        status = "✅ BẬT" if value else "❌ TẮT"
        client.replyMessage(
            Message(text=f"• Flag '{flag_name}' đã được {status}."),
            message_object, thread_id, thread_type
        )
        return

    client.replyMessage(
        Message(text=(
            "• Cách dùng:\n"
            "  flag list\n"
            "  flag on <tên_flag>\n"
            "  flag off <tên_flag>\n\n"
            "• Các flag hiện có:\n"
            "  notify_batch_sync\n"
            "  notify_warranty_edit"
        )),
        message_object, thread_id, thread_type
    )


def get_mitaizl():
    return {
        'flag': handle_flag_command
    }
