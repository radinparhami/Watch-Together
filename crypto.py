from base64 import b64encode, b64decode
from cryptography.fernet import Fernet
from json import dumps, loads


class Crypto:
    def __init__(self, key: str | bytes | None = None):
        self.key = key

    @property
    def keygen(self):
        self.key = Fernet.generate_key()
        return self.key

    def encrypt(self, data: dict, base_en=True, jsonify=True):
        try:
            if jsonify:
                data = dumps(data)
            if base_en:
                data = b64encode(data.encode())
            if self.key:
                f = Fernet(self.key)
                data = f.encrypt(data)
            return data
        except:
            return False

    def decrypt(self, data, base_en=True, jsonify=True):
        try:
            if self.key:
                f = Fernet(self.key)
                data = f.decrypt(data)
            if base_en:
                data = b64decode(data)
            if jsonify:
                data = loads(data)
            return data
        except:
            return False
