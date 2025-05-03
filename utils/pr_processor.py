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

    if not files_to_process:
        comment_lines.append("_No dependency files found in modified folders._")
    else:
        maven_entries = []
        python_entries = []
        node_entries = []

        for file in files_to_process:
            try:
                if file.name == "pom.xml":
                    pom_deps = parse_pom_xml(file.decoded_content.decode())
                    for group_artifact, version in pom_deps:
                        licenses = query_maven_license(group_artifact, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        maven_entries.append((file.path, group_artifact, version, license_with_risk))
                elif file.name == "requirements.txt":
                    py_deps = parse_requirements_txt(file.decoded_content.decode())
                    for package, version in py_deps:
                        licenses = query_pypi_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        python_entries.append((file.path, package, version, license_with_risk))
                elif file.name == "package.json":
                    node_deps = parse_package_json(file.decoded_content.decode())
                    for package, version in node_deps:
                        licenses = query_npm_license(package, version)
                        license_with_risk = format_licenses_with_risk(licenses)
                        node_entries.append((file.path, package, version, license_with_risk))
            except Exception as e:
                print(f"Error processing {file.path}: {e}")

        # Sort by risk
        maven_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))
        python_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))
        node_entries.sort(key=lambda x: get_risk_sort_weight(x[3]))

        # Add to PR comment
        if maven_entries:
            comment_lines.append("\n### Maven (`pom.xml`)\n")
            comment_lines.append("| File Path | Dependency | Version | Licenses (with Risk) |")
            comment_lines.append("|:----------|:-----------|:--------|:---------------------|")
            for path, dep, ver, license_with_risk in maven_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} |")

        if python_entries:
            comment_lines.append("\n### Python (`requirements.txt`)\n")
            comment_lines.append("| File Path | Dependency | Version | Licenses (with Risk) |")
            comment_lines.append("|:----------|:-----------|:--------|:---------------------|")
            for path, dep, ver, license_with_risk in python_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} |")

        if node_entries:
            comment_lines.append("\n### ReactJS / NodeJS (`package.json`)\n")
            comment_lines.append("| File Path | Dependency | Version | Licenses (with Risk) |")
            comment_lines.append("|:----------|:-----------|:--------|:---------------------|")
            for path, dep, ver, license_with_risk in node_entries:
                comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} |")

    comment_lines.append("\n### Legend:")
    comment_lines.append("- ✅ Safe: Permissive licenses (Apache, MIT, BSD, Zlib)")
    comment_lines.append("- ⚠️ Risky: Weak copyleft or cloud-restricted licenses (LGPL, SSPL, Elastic, etc.)")
    comment_lines.append("- 🔥 High Risk: Strong copyleft licenses requiring open source (GPL, AGPL)")
    comment_lines.append("- ❓ Unknown: License not recognized")

    final_comment = "\n".join(comment_lines)
    create_pr_comment(repo, pr_number, final_comment, APP_SLUG)
