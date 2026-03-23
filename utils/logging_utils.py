import os
import inspect
from datetime import datetime

class Logging:
    def __init__(self, theme="default", text_color="white", log_text_color="black"):
        self.reset = "\x1b[0m"
        
        self.red = None
        self.blue = None
        self.green = None
        self.white = None
        self.black = None
        self.orange = None
        self.yellow = None
        self.magenta = None
        self.light_pink = "\x1b[38;2;255;182;193m"
        self.light_pink_bg = "\x1b[48;2;255;182;193m"
        self.theme = str(theme).lower()
        
        # Setup log directory
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
        self._ensure_log_dir()
        
        self.load_color_scheme()
        
        self.textcolor = (
            "\x1b[30m" if text_color.lower() == "black" else
            "\x1b[37m" if text_color.lower() == "white" else
            text_color
        )
        self.log_text_color = (
            self.black if log_text_color.lower() == "black" else
            self.white if log_text_color.lower() == "white" else
            log_text_color
        )
    
    def _ensure_log_dir(self):
        """Tạo folder log nếu chưa tồn tại"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _get_log_file_path(self):
        """Lấy đường dẫn file log theo ngày hiện tại (format: yyyy-mm-dd.log)"""
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"{today}.log")
    
    def _get_caller_info(self):
        """Lấy thông tin file và line number của nơi gọi log"""
        # Tìm frame gọi log (bỏ qua các frame trong logging_utils.py)
        stack = inspect.stack()
        for frame_info in stack[2:]:  # Bỏ qua _get_caller_info và _write_to_file
            filename = frame_info.filename
            if 'logging_utils.py' not in filename:
                # Lấy tên file relative thay vì full path
                relative_path = os.path.basename(filename)
                # Nếu muốn hiện thêm folder cha
                parent_dir = os.path.basename(os.path.dirname(filename))
                if parent_dir and parent_dir != '.':
                    relative_path = f"{parent_dir}/{relative_path}"
                return relative_path, frame_info.lineno, frame_info.function
        return "unknown", 0, "unknown"
    
    def _write_to_file(self, level: str, message: str):
        """Ghi log vào file với format: [thời gian] [LEVEL] [file:line:function] message"""
        try:
            self._ensure_log_dir()
            log_file = self._get_log_file_path()
            
            # Lấy thông tin caller
            filename, line_no, func_name = self._get_caller_info()
            
            # Format thời gian
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Format log line
            log_line = f"[{timestamp}] [{level:8}] [{filename}:{line_no}:{func_name}] {message}\n"
            
            # Ghi vào file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            print(f"Error writing to log file: {e}")
    
    def load_color_scheme(self):
        if self.theme == "default":
            self.red = "\x1b[41m"
            self.blue = "\x1b[44m"
            self.green = "\x1b[42m"
            self.white = "\x1b[37m"
            self.black = "\x1b[30m"
            self.orange = None
            self.yellow = "\x1b[43m"
            self.magenta = "\x1b[45m"
            
        elif self.theme in ["catppuccin", "catppuccin-mocha"]:
            self.red = "\x1b[48;2;243;139;168m"
            self.blue = "\x1b[48;2;137;180;250m"
            self.green = "\x1b[48;2;166;227;161m"
            self.white = "\x1b[38;2;205;214;244m"
            self.black = "\x1b[38;2;17;17;27m"
            self.orange = "\x1b[48;2;250;179;135m"
            self.yellow = "\x1b[48;2;249;226;175m"
            self.magenta = "\x1b[48;2;203;166;247m"
            
        else:
            self.theme = "default"
            self.load_color_scheme()
            self.info("Theme not supported yet! Switch to default theme.")
    
    def logger(self, text1: str, text: str) -> None:
        text1 = str(text1)
        text = str(text)
        print(f"{self.light_pink_bg}{self.black} {text1} {self.reset} {self.textcolor}{text}{self.reset}")
        self._write_to_file("LOGGER", f"[{text1}] {text}")
    
    def success(self, text: str) -> None:
        text = str(text)
        print(f"{self.green}{self.log_text_color}LOADDER COMMANDS {self.reset}{self.textcolor}{text}")
        self._write_to_file("SUCCESS", text)

    def error(self, text: str) -> None:
        text = str(text)
        print(f"{self.red}{self.log_text_color}ERROR {self.reset}{self.textcolor}{text}")
        self._write_to_file("ERROR", text)

    def prefixcmd(self, text: str) -> None:
        text = str(text)
        print(f"{self.green}{self.log_text_color}PREFIX COMMANDS BOT {self.reset}{self.textcolor}{text}")
        self._write_to_file("PREFIXCMD", text)
    
    def warning(self, text: str) -> None:
        text = str(text)
        print(f"{self.orange or self.yellow}{self.log_text_color}WARN {self.reset}{self.textcolor}{text}")
        self._write_to_file("WARNING", text)

    def restart(self, text: str) -> None:
        text = str(text)
        print(f"{self.green}{self.log_text_color}RESTART BOT {self.reset}{self.textcolor}{text}")
        self._write_to_file("RESTART", text)

    def info(self, text: str) -> None:
        text = str(text)
        print(f"{self.blue}{self.log_text_color}DEBUG {self.reset}{self.textcolor}{text}")
        self._write_to_file("INFO", text)
