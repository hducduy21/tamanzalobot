import json
import queue
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from zlapi.models import Message, ThreadType
from utils.logging_utils import Logging

logger = Logging()
_client = None

_send_queue = queue.Queue()
_worker_lock = threading.Lock()
_worker_started = False

_server_instance = None
_server_lock = threading.Lock()

GROUP_SEND_INTERVAL = 15  # seconds between group messages


def _worker():
    while True:
        msg, gid, gname = _send_queue.get()
        try:
            _client.sendMessage(msg, gid, ThreadType.GROUP)
            logger.info(f"[Webhook] Đã gửi tới nhóm '{gname}' ({gid})")
        except Exception as e:
            logger.error(f"[Webhook] Gửi thất bại tới '{gname}': {e}")
        finally:
            _send_queue.task_done()
        time.sleep(GROUP_SEND_INTERVAL)


def _ensure_worker():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True).start()
            _worker_started = True


def set_client(client):
    global _client
    _client = client


def _read_setting():
    try:
        with open('seting.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _read_secret():
    return _read_setting().get('key', '')


def _read_port():
    try:
        return int(_read_setting().get('port', 5000))
    except Exception:
        return 5000


def _match_category(warranty_code):
    """
    Find the LAST-occurring category ID in warranty_code (case-insensitive).
    At the same start position the longest ID wins (e.g. CH2 > CH1 if both match).
    Returns (start_pos, cat_id, cat_name) or (None, None, None).
    """
    categories = _read_setting().get('category', [])
    code_upper = warranty_code.upper()

    best = None  # (start_pos, id_len, cat_id, cat_name)
    for cat in categories:
        needle = cat['id'].upper()
        pos = 0
        while True:
            idx = code_upper.find(needle, pos)
            if idx == -1:
                break
            if (best is None
                    or idx > best[0]
                    or (idx == best[0] and len(needle) > best[1])):
                best = (idx, len(needle), cat['id'], cat['name'])
            pos = idx + 1

    if best is None:
        return None, None, None
    return best[0], best[2], best[3]


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


def _send_password(ctv, warranty_code, password):
    if _client is None:
        logger.warning("[Webhook] Client chưa sẵn sàng, bỏ qua.")
        return

    start_pos, cat_id, cat_name = _match_category(warranty_code)
    if cat_id is None:
        logger.info(f"[Webhook] Mã hàng '{warranty_code}' không khớp category nào, bỏ qua.")
        return

    cat_end = start_pos + len(cat_id)
    if start_pos == 0:
        group_prefix = '[TAMAN]'
        include_ctv = True
    else:
        suffix = warranty_code[cat_end:].upper()
        group_prefix = f'[{suffix}]'
        include_ctv = False

    logger.info(f"[Webhook] '{warranty_code}' → category '{cat_id}' tại pos {start_pos}, group prefix '{group_prefix}'")

    groups = _find_groups_by_prefix(_client, group_prefix)
    if not groups:
        logger.warning(f"[Webhook] Không tìm thấy nhóm nào bắt đầu bằng '{group_prefix}'")
        return

    lines = [
        "Tâm An, Tài Khoản của Bạn: ",
        f"Mã Hàng: {warranty_code}",
        f"Mật Khẩu/Hạn dùng: {password}",
        f"Dịch vụ: {cat_name}",
    ]

    if include_ctv and ctv:                                                                                                       
        lines.append(f"CTV: {ctv}")  
    msg = Message(text="\n".join(lines))

    for gid, gname in groups:
        _send_queue.put((msg, gid, gname))
        logger.info(f"[Webhook] Đã xếp hàng gửi tới '{gname}' ({gid}), queue size={_send_queue.qsize()}")


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
        client_ip = self.client_address[0]
        logger.info(f"[Webhook] Nhận POST từ {client_ip} → path='{self.path}'")

        if self.path != '/warranty':
            logger.warning(f"[Webhook] Path không hợp lệ: '{self.path}' từ {client_ip}")
            self._send_json(404, {"error": "Not found"})
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except Exception:
            logger.warning(f"[Webhook] JSON không hợp lệ từ {client_ip}")
            self._send_json(400, {"error": "Invalid JSON"})
            return

        if data.get('secret', '') != _read_secret():
            logger.warning(f"[Webhook] Sai secret từ {client_ip}, bị từ chối 401")
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


def _run_server(port):
    global _server_instance
    while True:
        try:
            server = HTTPServer(('0.0.0.0', port), _Handler)
            with _server_lock:
                _server_instance = server
            logger.info(f"[Webhook] Server đang lắng nghe tại port {port}")
            server.serve_forever()
        except Exception as e:
            logger.error(f"[Webhook] Server bị lỗi, tự khởi động lại sau 5s: {e}")
            time.sleep(5)


def start(client, port=None):
    set_client(client)
    _ensure_worker()
    if port is None:
        port = _read_port()

    thread = threading.Thread(target=_run_server, args=(port,), daemon=True)
    thread.start()
    return thread
