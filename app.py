from flask import Flask, request
from dotenv import load_dotenv

from utils.pr_processor import process_pull_request

load_dotenv()

from utils.signature_verifier import verify_signature

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def github_webhook():
    verify_signature(request)
    payload = request.json
    print("🚀 Webhook received.")

    if payload.get("action") in ["opened", "reopened", "synchronize"] and "pull_request" in payload:
        process_pull_request(payload)
    else:
        print("Ignoring non-PR webhook event.")
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
