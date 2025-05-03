import hmac, hashlib, os
from flask import abort
GITHUB_WEBHOOK_SECRET = os.getenv('GITHUB_WEBHOOK_SECRET')

def verify_signature(request):
    header_signature = request.headers.get('X-Hub-Signature-256')
    if header_signature is None:
        abort(400, 'Missing signature')
    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha256':
        abort(400, 'Unsupported signature algorithm')
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=request.data, digestmod=hashlib.sha256)
    if not hmac.compare_digest(mac.hexdigest(), signature):
        abort(400, 'Invalid signature')
