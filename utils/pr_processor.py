import os
from github import Github
from datetime import datetime
from pytz import timezone  # NEW
import zipfile
import io
import uuid
import requests
import shutil
import glob
from dotenv import load_dotenv
load_dotenv()

from auth import get_installation_access_token, APP_SLUG
from parsers.maven_parser import parse_pom_xml, parse_pom_xml_via_maven
from parsers.python_parser import parse_requirements_txt
from parsers.node_parser import parse_package_json
from depsdev.maven import query_maven_license
from depsdev.pypi import query_pypi_license
from depsdev.npm import query_npm_license
from utils.risk_classifier import format_licenses_with_risk, get_risk_sort_weight
from utils.pr_commenter import create_pr_comment
from utils.pr_check_decorator import create_pr_check_run
from utils.dependency_scanner import scan_dependencies_and_render_markdown


GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def get_est_timestamp():
    est = timezone('America/New_York')
    now_utc = datetime.utcnow()
    now_est = now_utc.astimezone(est)
    return now_est.strftime("%Y-%m-%d %I:%M %p EST")

def process_pull_request(payload):
    pr = payload["pull_request"]
    installation = payload["installation"]
    installation_id = installation["id"]

    access_token = get_installation_access_token(installation_id)
    github_client = Github(access_token)

    repo_full_name = pr["base"]["repo"]["full_name"]
    branch_name = pr["head"]["ref"]
    pr_number = pr["number"]

    repo = github_client.get_repo(repo_full_name)


    risky_entries, final_comment = scan_dependencies_and_render_markdown(repo, branch_name, access_token)
    # create_pr_comment(repo, pr_number, final_comment, APP_SLUG) # Comment out PR Comments

    # Add PR Decoration
    head_sha = pr["head"]["sha"]
    conclusion = "failure" if risky_entries else "success"
    create_pr_check_run(repo, head_sha, final_comment, conclusion)

def scan_risky_packages(repo, pr_number):
    """
    Returns a simplified list of (dependency, license_with_risk) for PR merge-based issue creation.
    """
    pr_obj = repo.get_pull(pr_number)
    branch_name = pr_obj.head.ref

    # Use GitHub App token from environment
    access_token = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_APP_TOKEN')
    if not access_token:
        print("❌ GitHub token not found for scanning.")
        return []

    try:
        risky_entries, _ = scan_dependencies_and_render_markdown(repo, branch_name, access_token)
        return [(dep, license_with_risk) for _, dep, _, license_with_risk, _ in risky_entries]
    except Exception as e:
        print(f"❌ Error scanning risky packages from merged PR: {e}")
        return []

