import os
import uuid

from firebase_admin import (
    credentials,
    firestore,
    initialize_app,
)

current_dir = os.path.dirname(os.path.abspath(__file__))
cred = credentials.Certificate(os.path.join(current_dir, "firebase_creds/credentials.json"))
firebase_app = initialize_app(cred)


class FirestoreService:
    def __init__(self):
        self.db = firestore.client()

    def get_device_identifier(self):
        keychain_identifier = "com.example.app.deviceIdentifier"

        device_doc_ref = self.db.collection("devices").document(keychain_identifier)
        device_data = device_doc_ref.get()

        if device_data.exists:
            return device_data.get("identifier")

        new_identifier = str(uuid.uuid4())

        device_doc_ref.set({"identifier": new_identifier})

        return new_identifier

    def get_user(self, device_id: str):
        try:
            snapshot = self.db.collection("Users").where("deviceID", "==", device_id).get()
            if not snapshot:
                return 0

            document = snapshot[0]
            user_data = document.to_dict()
            request_count = user_data.get("requestCount", 0)
            return request_count
        except Exception as e:
            print("Помилка отримання даних:", str(e))
            return 0

    def get_users(self):
        users_collection = self.db.collection("Users")
        users_snapshot = users_collection.get()

        for user_document in users_snapshot:
            user_data = user_document.to_dict()
            user_id = user_document.id
            print("User ID:", user_id)
            print("User Data:", user_data)


if __name__ == '__main__':
    firestore_service = FirestoreService()
    print(firestore_service.get_user(device_id='1EB9B957-C9C1-4624-9558-2EC84958AA30'))
