import datetime
import hashlib
import os

import pytz

SECRET_KEY = os.getenv("SECRET_KEY")


class AuthService:

    def __init__(self, device_id: str, auth_token: str):
        self.device_id = device_id
        self.auth_token = auth_token

    def get_hash_token(self) -> str:
        timezone = "Europe/Kiev"
        current_date = datetime.datetime.now(pytz.timezone(timezone)).strftime("%Y-%m-%d")
        data = f"{self.device_id}{SECRET_KEY}{current_date}"
        hash_obj = hashlib.sha256(data.encode())
        return hash_obj.hexdigest()

    def is_authenticate(self) -> bool:
        return self.auth_token == self.get_hash_token()
