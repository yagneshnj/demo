import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()
from github import Github
from utils.pr_processor import process_pull_request
from utils.signature_verifier import verify_signature
from utils.risky_issue_creator import create_risky_issue
from auth import get_installation_access_token

app = Flask(__name__)

def handle_event(payload):
    # this runs in its own thread, so it won’t block the HTTP response
    print("▶️  Background handler starting…")
    pr = payload.get("pull_request", {})
    action = payload.get("action")
    if action in ["opened", "reopened", "synchronize"] and pr:
        print(f"🔄 Processing PR #{pr['number']} ({action})")
        process_pull_request(payload)
        print(f"✅ Finished processing PR #{pr['number']}")
    # … your “closed” logic here …
    else:
        print("ℹ️ Ignoring non‑PR event.")

@app.route("/health", methods=["GET"])
def health_check():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def github_webhook():
    verify_signature(request)
    payload = request.json
    print("🚀 Webhook received.")

    if payload.get("action") in ["opened", "reopened", "synchronize"] and "pull_request" in payload:
        print(f"🚀 Webhook Thread: action={payload.get('action')}, repo={payload['repository']['full_name']}")
        threading.Thread(target=handle_event, args=(payload,)).start()
        return jsonify({"status": "accepted"}), 202
        # process_pull_request(payload)
    elif payload.get("action") == "closed" and "pull_request" in payload:
        pr = payload["pull_request"]
        if pr.get("merged"):
            print(f"PR #{pr['number']} merged. Checking for risky packages...")
            installation = payload["installation"]
            installation_id = installation["id"]

            access_token = get_installation_access_token(installation_id)
            github_client = Github(access_token)

            repo_full_name = pr["base"]["repo"]["full_name"]
            pr_number = pr["number"]

            repo = github_client.get_repo(repo_full_name)

            # WARNING: Here we don't rescan files.
            # Instead, assume risky_entries were scanned during PR and stored.

            # For now, basic scan again: (later optimize caching)
            from utils.pr_processor import scan_risky_packages

            risky_packages = scan_risky_packages(repo, pr_number)
            if risky_packages:
                create_risky_issue(repo, pr_number, risky_packages)
            else:
                print("No risky packages detected. No issue created.")

    else:
        print("Ignoring non-PR webhook event.")
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
