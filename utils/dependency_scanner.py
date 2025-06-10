import os
import io
import uuid
import zipfile
import shutil
import glob
import requests
from datetime import datetime
from pytz import timezone

from utils.risk_classifier import format_licenses_with_risk, get_risk_sort_weight
from parsers.maven_parser import parse_pom_xml_via_maven
from parsers.python_parser import parse_requirements_txt
from parsers.node_parser import parse_package_json
from depsdev.maven import query_maven_license
from depsdev.pypi import query_pypi_license
from depsdev.npm import query_npm_license


def get_est_timestamp():
    est = timezone('America/New_York')
    now_utc = datetime.utcnow()
    now_est = now_utc.astimezone(est)
    return now_est.strftime("%Y-%m-%d %I:%M %p EST")


def scan_dependencies_and_render_markdown(repo, branch_name, access_token):
    maven_entries, python_entries, node_entries, risky_entries = [], [], [], []
    files_to_process, files_to_process_paths = [], set()

    contents = repo.get_contents("", ref=branch_name)
    queue = contents if isinstance(contents, list) else [contents]
    while queue:
        item = queue.pop(0)
        if item.type == "dir":
            queue.extend(repo.get_contents(item.path, ref=branch_name))
        elif item.name in ["pom.xml", "requirements.txt", "package.json"]:
            if item.path not in files_to_process_paths:
                files_to_process.append(item)
                files_to_process_paths.add(item.path)

    for file in files_to_process:
        try:
            if file.name == "pom.xml":
                archive_url = repo.get_archive_link("zipball", ref=branch_name)
                headers = {"Authorization": f"token {access_token}"}
                zip_resp = requests.get(archive_url, headers=headers)
                zip_file = zipfile.ZipFile(io.BytesIO(zip_resp.content))

                tmp_dir = f"/tmp/repo_{uuid.uuid4().hex}"
                os.makedirs(tmp_dir, exist_ok=True)
                zip_file.extractall(tmp_dir)

                extracted_dir = next(os.path.join(tmp_dir, d) for d in os.listdir(tmp_dir))
                relative_path = os.path.dirname(file.path)
                module_dir = os.path.join(extracted_dir, relative_path)

                pom_deps = parse_pom_xml_via_maven(module_dir)
                shutil.rmtree(tmp_dir)

                for group_artifact, version in pom_deps:
                    licenses, source = query_maven_license(group_artifact, version)
                    license_with_risk = format_licenses_with_risk(licenses)
                    maven_entries.append((file.path, group_artifact, version, license_with_risk, source))
                    if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                        risky_entries.append((file.path, group_artifact, version, license_with_risk, source))

            elif file.name == "requirements.txt":
                deps = parse_requirements_txt(file.decoded_content.decode())
                for package, version in deps:
                    licenses, source = query_pypi_license(package, version)
                    license_with_risk = format_licenses_with_risk(licenses)
                    python_entries.append((file.path, package, version, license_with_risk, source))
                    if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                        risky_entries.append((file.path, package, version, license_with_risk, source))

            elif file.name == "package.json":
                deps = parse_package_json(file.decoded_content.decode())
                for package, version in deps:
                    licenses, source = query_npm_license(package, version)
                    license_with_risk = format_licenses_with_risk(licenses)
                    node_entries.append((file.path, package, version, license_with_risk, source))
                    if "⚠️" in license_with_risk or "🔥" in license_with_risk:
                        risky_entries.append((file.path, package, version, license_with_risk, source))

        except Exception as e:
            print(f"⚠️ Error processing {file.path}: {e}")

    for f in glob.glob("/tmp/output*.txt"):
        try:
            os.remove(f)
        except:
            pass

    comment_lines = []
    comment_lines.append("## 📦 Dependency Scan Report")
    all_risks = [entry[3] for entry in maven_entries + python_entries + node_entries]

    if all(all("✅" in part for part in risk.split(",")) for risk in all_risks):
        comment_lines.append("\n📜🏆 **Certified by Open Source Governance: No Risky Licenses Found!**\n")

    if risky_entries:
        comment_lines.append("\n### ⚠️ Risky or High-Risk Licenses Detected\n")
        comment_lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
        comment_lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
        for path, dep, ver, license_with_risk, source in risky_entries:
            comment_lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")

    comment_lines.append("\n*Expand below to view the full list of all scanned dependencies:*")

    def section(title, entries):
        lines = [f"\n<details><summary>{title}</summary>\n\n"]
        lines.append("| File Path | Dependency | Version | License (with Risk) | Source |")
        lines.append("|:----------|:-----------|:--------|:--------------------|:-------|")
        for path, dep, ver, license_with_risk, source in entries:
            lines.append(f"| `{path}` | {dep} | {ver} | {license_with_risk} | {source} |")
        lines.append("\n</details>")
        return lines

    if maven_entries:
        comment_lines.extend(section("### Maven (`pom.xml`)", maven_entries))
    if python_entries:
        comment_lines.extend(section("### Python (`requirements.txt`)", python_entries))
    if node_entries:
        comment_lines.extend(section("### ReactJS / NodeJS (`package.json`)", node_entries))

    comment_lines.append("\n### Legend:")
    comment_lines.append("- ✅ Safe: Permissive licenses (Apache, MIT, BSD, Zlib)")
    comment_lines.append("- ⚠️ Risky: Weak copyleft or cloud-restricted licenses (LGPL, SSPL, Elastic, etc.)")
    comment_lines.append("- 🔥 High Risk: Strong copyleft licenses requiring open source (GPL, AGPL)")
    comment_lines.append("- ❓ Unknown: License not recognized")

    comment_lines.append(f"\n---\n_Last updated: {get_est_timestamp()}_")

    return risky_entries, "\n".join(comment_lines)
