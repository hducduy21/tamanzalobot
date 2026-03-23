__version__ = "4.8.0"
__author__ = "mitai-zlbot"
__description__ = "Bot Zalo hỗ trợ các chức năng như quản lý nhóm, nhắc nhở, và các lệnh tự động."

import os
import json

def init():
    config_path = "seting/seting.json"
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump({"PREFIX": "!", "ADMIN": []}, f, indent=4)
    print("Initialization completed.")

init()
