# GitHub authentication helper
import jwt
import time
import requests
import os
from dotenv import load_dotenv
load_dotenv()

APP_ID = os.getenv('GITHUB_APP_ID')
APP_SLUG = os.getenv('GITHUB_APP_SLUG')
PRIVATE_KEY = os.getenv('GITHUB_PRIVATE_KEY').replace("\\n", "\n")

def get_installation_access_token(installation_id):
    payload = {
        "iat": int(time.time()) - 60,
        "exp": int(time.time()) + (10 * 60),
        "iss": APP_ID
    }
    encoded_jwt = jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    r = requests.post(url, headers=headers)
    r.raise_for_status()
    return r.json()["token"]
