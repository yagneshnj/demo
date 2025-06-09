# utils/scan_wrapper.py

import os
from github import Github
from utils.pr_processor import scan_risky_packages

def scan_risky_licenses(repo_full, pr_num, installation_id):
    """
    Wrapper for scanning risky licenses using scan_risky_packages.
    """
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_APP_TOKEN')
    if not token:
        return "❌ GitHub token not found."

    gh = Github(token)
    repo = gh.get_repo(repo_full)

    risky = scan_risky_packages(repo, pr_num)
    if not risky:
        return "✅ No risky licenses found in PR."

    out = []
    for pkg, risk in risky:
        out.append(f"- **{pkg}**: {risk}")
    return "\n".join(out)
