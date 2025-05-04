import os
from github import Github
from auth import get_installation_access_token, APP_SLUG
from parsers.maven_parser import parse_pom_xml
from parsers.python_parser import parse_requirements_txt
from parsers.node_parser import parse_package_json
from depsdev.maven import query_maven_license
from depsdev.pypi import query_pypi_license
from depsdev.npm import query_npm_license
from utils.risk_classifier import format_licenses_with_risk, get_risk_sort_weight
from utils.pr_commenter import create_pr_comment
from datetime import datetime
from pytz import timezone  # NEW

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

    comment_lines = []
    comment_lines.append("## 📦 Dependency Scan Report")

    maven_entries = []
    python_entries = []
    node_entries = []
    risky_entries = []

    if not files_to_process:
        comment_lines.append("_No dependency files found in modified folders._")
    else:
        for file in files_to_process:
            try:
                if file.name == "pom.xml":
                    pom_deps = parse_pom_xml(file.decoded_content.decode())
                    for group_artifact, version in pom_deps:
                        licenses, source = query_maven_license(group_artifact, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        maven_entries.append((file.path, group_artifact, version, license_with_risk, source))
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_entries.append((file.path, group_artifact, version, license_with_risk, source))
                elif file.name == "requirements.txt":
                    py_deps = parse_requirements_txt(file.decoded_content.decode())
                    for package, version in py_deps:
                        licenses, source = query_pypi_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        python_entries.append((file.path, package, version, license_with_risk, source))
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_entries.append((file.path, package, version, license_with_risk, source))
                elif file.name == "package.json":
                    node_deps = parse_package_json(file.decoded_content.decode())
                    for package, version in node_deps:
                        licenses, source = query_npm_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        node_entries.append((file.path, package, version, license_with_risk, source))
                        if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                            risky_entries.append((file.path, package, version, license_with_risk, source))
            except Exception as e:
                print(f"Error processing {file.path}: {e}")

        # Sort by risk
        maven_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))
        python_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))
        node_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))
        risky_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))

        # Certification check
        all_risks = [entry[3] for entry in maven_entries + python_entries + node_entries]

        if all(all("✅" in part for part in risk.split(",")) for risk in all_risks):
            comment_lines.insert(1, "\n📜🏆 **Certified by Open Source Governance: No Risky Licenses Found!**\n")

        # Risky Licenses Table (Always Visible if any)
        if risky_entries:
            comment_lines.append("\n### ⚠️ Risky or High-Risk Licenses Detected\n")
            comment_lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
            comment_lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
            for path, dep, ver, license_with_risk, source in risky_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")

        # Expand Note
        comment_lines.append("\n*Expand below to view the full list of all scanned dependencies:*")

        # Collapsed sections for full dependencies
        if maven_entries:
            comment_lines.append("\n<details><summary>### Maven (`pom.xml`)</summary>\n\n")
            comment_lines.append("*_(Expand to view full list of scanned dependencies and their licenses)_*\n")
            comment_lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
            comment_lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
            for path, dep, ver, license_with_risk, source in maven_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")
            comment_lines.append("\n</details>")

        if python_entries:
            comment_lines.append("\n<details><summary>### Python (`requirements.txt`)</summary>\n\n")
            comment_lines.append("*_(Expand to view full list of scanned dependencies and their licenses)_*\n")
            comment_lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
            comment_lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
            for path, dep, ver, license_with_risk, source in python_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")
            comment_lines.append("\n</details>")

        if node_entries:
            comment_lines.append("\n<details><summary>### ReactJS / NodeJS (`package.json`)</summary>\n\n")
            comment_lines.append("*_(Expand to view full list of scanned dependencies and their licenses)_*\n")
            comment_lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
            comment_lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
            for path, dep, ver, license_with_risk, source in node_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")
            comment_lines.append("\n</details>")

    # Legend
    comment_lines.append("\n### Legend:")
    comment_lines.append("- ✅ Safe: Permissive licenses (Apache, MIT, BSD, Zlib)")
    comment_lines.append("- ⚠️ Risky: Weak copyleft or cloud-restricted licenses (LGPL, SSPL, Elastic, etc.)")
    comment_lines.append("- 🔥 High Risk: Strong copyleft licenses requiring open source (GPL, AGPL)")
    comment_lines.append("- ❓ Unknown: License not recognized")

    # Timestamp - Now EST
    timestamp = get_est_timestamp()
    comment_lines.append(f"\n---\n_Last updated: {timestamp}_")

    final_comment = "\n".join(comment_lines)
    create_pr_comment(repo, pr_number, final_comment, APP_SLUG)
    
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
