# utils/scan_wrapper.py

import os
from github import Github
from utils.dependency_scanner import scan_dependencies_and_render_markdown

def scan_risky_licenses(repo_full, pr_num, installation_id):

    token = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_APP_TOKEN')
    if not token:
        return "❌ GitHub token not found."

    gh = Github(token)
    repo = gh.get_repo(repo_full)
    pr = repo.get_pull(pr_num)
    branch = pr.head.ref

    risky_entries, markdown = scan_dependencies_and_render_markdown(repo, branch, token)
    if not risky_entries:
        return "✅ No risky licenses found in PR."

    return f"<!-- cache:scan_risky_licenses -->\n{markdown}"
