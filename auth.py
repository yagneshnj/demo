import jwt
import time
import requests
import os
from dotenv import load_dotenv
load_dotenv()

APP_ID = os.getenv('GITHUB_APP_ID')
APP_SLUG = os.getenv('GITHUB_APP_SLUG')
PRIVATE_KEY = os.getenv('GITHUB_PRIVATE_KEY').replace("\\n", "\n")  # Fix for .env format

_cached_jwt = None
_jwt_expiration = 0  # Epoch time

def generate_jwt():
    global _cached_jwt, _jwt_expiration
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (9 * 60),  # 9 minutes lifetime
        "iss": APP_ID
    }
    _cached_jwt = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    _jwt_expiration = now + (8 * 60)  # Refresh 1 min before expiry
    return _cached_jwt

def get_jwt():
    global _cached_jwt, _jwt_expiration
    now = int(time.time())
    if _cached_jwt is None or now >= _jwt_expiration:
        return generate_jwt()
    return _cached_jwt

def get_installation_access_token(installation_id):
    headers = {
        "Authorization": f"Bearer {get_jwt()}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.json()["token"]
