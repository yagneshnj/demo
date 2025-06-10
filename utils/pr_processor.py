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

    changed_files = []
    try:
        pr_obj = repo.get_pull(pr_number)
        files = pr_obj.get_files()
        for f in files:
            changed_files.append(f.filename)
    except Exception as e:
        print(f"Error fetching changed files: {e}")

    folders_to_check = {""}
    for file_path in changed_files:
        folder = os.path.dirname(file_path)
        if folder:
            folders_to_check.add(folder.split('/')[0])

    files_to_process_paths = set()
    files_to_process = []

    for folder in folders_to_check:
        try:
            contents = repo.get_contents(folder, ref=branch_name)
            queue = contents if isinstance(contents, list) else [contents]
            while queue:
                file_content = queue.pop(0)
                if file_content.type == "dir":
                    queue.extend(repo.get_contents(file_content.path, ref=branch_name))
                elif file_content.name in ["pom.xml", "requirements.txt", "package.json"]:
                    if file_content.path not in files_to_process_paths:
                        files_to_process.append(file_content)
                        files_to_process_paths.add(file_content.path)
        except Exception as e:
            print(f"Error reading folder {folder}: {e}")

    risky_entries, final_comment = scan_dependencies_and_render_markdown(repo, branch_name, access_token)
    # create_pr_comment(repo, pr_number, final_comment, APP_SLUG) # Comment out PR Comments

    # Add PR Decoration
    head_sha = pr["head"]["sha"]
    conclusion = "failure" if risky_entries else "success"
    create_pr_check_run(repo, head_sha, final_comment, conclusion)

    
def scan_risky_packages(repo, pr_number):
    risky_packages = []
    try:
        pr_obj = repo.get_pull(pr_number)
        files = pr_obj.get_files()
        for file in files:
            if file.filename.endswith(("pom.xml", "requirements.txt", "package.json")):
                content = repo.get_contents(file.filename, ref=pr_obj.head.ref)
                if file.filename.endswith("pom.xml"):
                    deps = parse_pom_xml(content.decoded_content.decode())
                    for group_artifact, version in deps:
                        licenses, _ = query_maven_license(group_artifact, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_packages.append((group_artifact, license_with_risk))
                elif file.filename.endswith("requirements.txt"):
                    deps = parse_requirements_txt(content.decoded_content.decode())
                    for package, version in deps:
                        licenses, _ = query_pypi_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_packages.append((package, license_with_risk))
                elif file.filename.endswith("package.json"):
                    deps = parse_package_json(content.decoded_content.decode())
                    for package, version in deps:
                        licenses, _ = query_npm_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_packages.append((package, license_with_risk))
    except Exception as e:
        print(f"Error scanning risky packages in merged PR: {e}")

    return risky_packages
