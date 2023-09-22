import datetime
import hashlib
import os

import pytz

SECRET_KEY = os.getenv("SECRET_KEY")


class AuthService:
    timezone = "Europe/Kiev"

    def __init__(self, device_id: str, auth_token: str):
        self.device_id = device_id
        self.auth_token = auth_token

    def get_hash_token_hour(self) -> str:
        current_date = datetime.datetime.now(pytz.timezone(self.timezone)).strftime("%Y-%m-%d-%H")
        data = f"{self.device_id}{SECRET_KEY}{current_date}"
        hash_obj = hashlib.sha256(data.encode())
        return hash_obj.hexdigest()

    def get_hash_token_min(self) -> str:
        current_date = datetime.datetime.now(pytz.timezone(self.timezone)).strftime("%Y-%m-%d-%H-%M")
        data = f"{self.device_id}{SECRET_KEY}{current_date}"
        hash_obj = hashlib.sha256(data.encode())
        return hash_obj.hexdigest()

    def is_authenticate(self) -> bool:
        if self.auth_token == self.get_hash_token_min():
            return True
        if self.auth_token == self.get_hash_token_hour():
            return True
        return False
