import json
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from zlapi.models import Message, ThreadType
from utils.logging_utils import Logging

logger = Logging()
_client = None


def set_client(client):
    global _client
    _client = client


def _read_secret():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return json.load(f).get('key', '')
    except Exception:
        return ''


def _read_port():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return int(json.load(f).get('port', 5000))
    except Exception:
        return 5000


def _find_groups_by_prefix(client, prefix):
    """Return list of (group_id, group_name) where name starts with prefix."""
    results = []
    try:
        all_groups = client.fetchAllGroups()
        group_ids = list(all_groups.gridVerMap.keys())
        if not group_ids:
            return results

        id_map = {gid: 0 for gid in group_ids}
        info = client.fetchGroupInfo(id_map)
        grid_map = info.gridInfoMap if hasattr(info, 'gridInfoMap') else {}

        for gid, gdata in grid_map.items():
            name = gdata.get('name', '') if isinstance(gdata, dict) else getattr(gdata, 'name', '')
            if name.startswith(prefix):
                results.append((gid, name))
    except Exception as e:
        logger.error(f"[Webhook] Lỗi khi lấy danh sách nhóm: {e}")
    return results


def _parse_n4(warranty_code):
    """
    Returns (group_prefix, include_ctv) or (None, False).
    N4/n4 at start → ('[INTERNAL]', True)
    N4/n4 elsewhere → ('[<SUFFIX_UPPER>]', False)
    No N4 → (None, False)
    """
    match = re.search(r'n4', warranty_code, re.IGNORECASE)
    if match is None:
        return None, False
    if match.start() == 0:
        return '[INTERNAL]', True
    suffix = warranty_code[match.end():].upper()
    return f'[{suffix}]', False


def _send_password(ctv, warranty_code, password):
    if _client is None:
        logger.warning("[Webhook] Client chưa sẵn sàng, bỏ qua.")
        return

    group_prefix, include_ctv = _parse_n4(warranty_code)
    if group_prefix is None:
        logger.info(f"[Webhook] Mã hàng '{warranty_code}' không chứa N4, bỏ qua.")
        return

    groups = _find_groups_by_prefix(_client, group_prefix)
    if not groups:
        logger.warning(f"[Webhook] Không tìm thấy nhóm nào bắt đầu bằng '{group_prefix}'")
        return

    lines = [
        "Shop gửi lại mật khẩu mới ạ",
        f"Mật khẩu: {password}",
        f"Mã hàng: {warranty_code}",
    ]
    if include_ctv and ctv:
        lines.append(f"CTV: {ctv}")
    msg = Message(text="\n".join(lines))

    for gid, gname in groups:
        try:
            _client.sendMessage(msg, gid, ThreadType.GROUP)
            logger.info(f"[Webhook] Đã gửi tới nhóm '{gname}' ({gid})")
        except Exception as e:
            logger.error(f"[Webhook] Gửi thất bại tới '{gname}': {e}")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default access log

    def _send_json(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != '/warranty':
            self._send_json(404, {"error": "Not found"})
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if data.get('secret', '') != _read_secret():
            self._send_json(401, {"error": "Unauthorized"})
            return

        ctv = data.get('ctv', '').strip()
        warranty_code = data.get('warranty_code', '').strip()
        password = data.get('password', '').strip()

        if not warranty_code:
            self._send_json(400, {"error": "Thiếu warranty_code"})
            return

        threading.Thread(
            target=_send_password,
            args=(ctv, warranty_code, password),
            daemon=True
        ).start()

        self._send_json(200, {"status": "ok"})


def start(client, port=None):
    set_client(client)
    if port is None:
        port = _read_port()

    server = HTTPServer(('0.0.0.0', port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"[Webhook] Server đang lắng nghe tại port {port}")
    return server
