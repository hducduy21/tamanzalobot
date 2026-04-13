#!/usr/bin/env python3
"""
Keep-alive wrapper for bot - ensures bot never stays frozen
Detects frozen WebSocket by checking for message processing

Rules:
- 06:00 - 00:00 (6AM - midnight): restart if no message for 60 minutes
- 00:00 - 05:00 (midnight - 5AM): restart if no message for 180 minutes  
- 06:00 daily: auto restart every morning
- Prevent consecutive restarts within MAX_SILENT_TIME
"""
import subprocess
import sys
import time
import os
import re
from datetime import datetime

# Thời gian tối đa không có message theo khung giờ
MAX_SILENT_TIME_DAY = 60 * 60      # 60 phút (6:00 - 00:00)
MAX_SILENT_TIME_NIGHT = 180 * 60   # 180 phút (00:00 - 05:00)
MORNING_RESTART_HOUR = 6           # Restart lúc 6:00 sáng mỗi ngày

CHECK_INTERVAL = 120  # Check mỗi 2 phút (tối ưu performance)
LOG_DIR = "log"

# Track last restart time để tránh restart liên tiếp
last_restart_time = 0
last_morning_restart_date = None


def get_current_max_silent_time():
    """Get MAX_SILENT_TIME based on current hour."""
    current_hour = datetime.now().hour
    
    if 0 <= current_hour < 5:
        # 00:00 - 05:00: ban đêm, ít message
        return MAX_SILENT_TIME_NIGHT
    else:
        # 05:00 - 00:00: ban ngày
        return MAX_SILENT_TIME_DAY


def should_morning_restart():
    """Check if should do daily morning restart at 6:00."""
    global last_morning_restart_date
    
    now = datetime.now()
    today = now.date()
    current_hour = now.hour
    
    # Nếu đúng 6:00 và chưa restart hôm nay
    if current_hour == MORNING_RESTART_HOUR and last_morning_restart_date != today:
        last_morning_restart_date = today
        return True
    
    return False


def can_restart():
    """Check if enough time passed since last restart to prevent consecutive restarts."""
    global last_restart_time
    
    current_max_silent = get_current_max_silent_time()
    time_since_last_restart = time.time() - last_restart_time
    
    # Phải chờ ít nhất MAX_SILENT_TIME giữa 2 lần restart
    if time_since_last_restart < current_max_silent:
        remaining = int(current_max_silent - time_since_last_restart)
        print(f"[KEEP_ALIVE] Skipping restart - only {int(time_since_last_restart)}s since last restart, need {current_max_silent}s (remaining: {remaining}s)")
        return False
    
    return True


def record_restart(reason):
    """Record restart time and log reason to daily log file."""
    global last_restart_time
    last_restart_time = time.time()
    
    # Log to daily log file (same as bot logs)
    today = time.strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.log")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] [KEEP_ALIVE] AUTO-RESTART: {reason}\n")
    
    print(f"[KEEP_ALIVE] [{timestamp}] AUTO-RESTART: {reason}")


def get_latest_log_file():
    """Get today's log file."""
    today = time.strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{today}.log")


def get_last_message_time():
    """Check log file for last message processing time (optimized - only read last 10KB)."""
    log_file = get_latest_log_file()
    if not os.path.exists(log_file):
        return time.time()
    
    try:
        with open(log_file, 'rb') as f:
            # Seek đến cuối file
            f.seek(0, 2)
            file_size = f.tell()
            
            # Chỉ đọc 10KB cuối (đủ cho ~100 dòng log)
            read_size = min(10240, file_size)
            if read_size > 0:
                f.seek(-read_size, 2)
            
            # Đọc và decode
            content = f.read().decode('utf-8', errors='ignore')
            lines = content.split('\n')[-100:]
        
        # Tìm dòng cuối có Processing message hoặc Handling command hoặc Heartbeat
        for line in reversed(lines):
            if '[DEBUG] Processing message' in line or '[DEBUG] Handling command' in line or '[WS] Heartbeat' in line:
                match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    timestamp_str = match.group(1)
                    return time.mktime(time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S"))
        
        return os.path.getmtime(log_file)
    except:
        return time.time()


def is_bot_receiving_messages():
    """
    Check if bot is still receiving messages.
    Returns False if no message processed in current MAX_SILENT_TIME.
    """
    last_msg_time = get_last_message_time()
    elapsed = time.time() - last_msg_time
    current_max_silent = get_current_max_silent_time()
    
    return elapsed < current_max_silent


def main():
    global last_restart_time, last_morning_restart_date
    
    print("[KEEP_ALIVE] Starting bot supervisor...")
    print(f"[KEEP_ALIVE] Rules:")
    print(f"  - 06:00 - 00:00: restart if no message for {MAX_SILENT_TIME_DAY // 60} minutes")
    print(f"  - 00:00 - 05:00: restart if no message for {MAX_SILENT_TIME_NIGHT // 60} minutes")
    print(f"  - 06:00 daily: auto restart every morning")
    print(f"  - Check interval: {CHECK_INTERVAL} seconds")
    
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Initialize last_restart_time để lần đầu không bị block
    last_restart_time = time.time() - MAX_SILENT_TIME_NIGHT
    
    while True:
        print(f"[KEEP_ALIVE] Starting main.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env
        )
        
        last_check = time.time()
        
        try:
            while process.poll() is None:
                # Print output
                try:
                    line = process.stdout.readline()
                    if line:
                        print(line, end='')
                except:
                    pass
                
                # Check every CHECK_INTERVAL seconds
                if time.time() - last_check > CHECK_INTERVAL:
                    last_check = time.time()
                    current_hour = datetime.now().hour
                    current_max_silent = get_current_max_silent_time()
                    
                    # Check 1: Morning auto restart at 6:00
                    if should_morning_restart():
                        if can_restart():
                            record_restart(f"Daily morning restart at {MORNING_RESTART_HOUR}:00")
                            process.kill()
                            break
                    
                    # Check 2: No message timeout
                    if not is_bot_receiving_messages():
                        if can_restart():
                            elapsed = int(time.time() - get_last_message_time())
                            record_restart(f"No messages for {elapsed}s (threshold: {current_max_silent}s, hour: {current_hour})")
                            process.kill()
                            break
                        else:
                            print(f"[KEEP_ALIVE] Bot appears frozen but waiting for cooldown period...")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("[KEEP_ALIVE] Received interrupt, stopping...")
            process.kill()
            sys.exit(0)
        except Exception as e:
            print(f"[KEEP_ALIVE] Error: {e}")
        
        exit_code = process.returncode
        try:
            if process.stdout:
                remaining = process.stdout.read()
                if remaining:
                    print("[KEEP_ALIVE] --- main.py last output ---")
                    print(remaining, end="" if remaining.endswith("\n") else "\n")
                    print("[KEEP_ALIVE] --- end ---")
        except Exception as e:
            print(f"[KEEP_ALIVE] Failed to read remaining output: {e}")

        print(f"[KEEP_ALIVE] Bot ended with code {exit_code}, restarting in 10s...")
        time.sleep(10)


if __name__ == "__main__":
    main()