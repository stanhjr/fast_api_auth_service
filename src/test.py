import datetime
import hashlib

import pytz


def generate_hash(secret: str):
    timezone = "Europe/Kiev"
    current_date = datetime.datetime.now(pytz.timezone(timezone)).strftime("%Y-%m-%d")
    data = secret.encode() + current_date.encode()
    hash_obj = hashlib.sha256(data)
    return hash_obj.hexdigest()


# Пример использования
secret_token = "your_secret_tokensrgsrgsrgsrgsrg"
desired_timezone = "America/New_York"
hashed_token = generate_hash(secret_token)
print("Generated Hash:", hashed_token)
