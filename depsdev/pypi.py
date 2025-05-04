import requests
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional for GitHub API auth

def query_pypi_license(package: str, version: str):
    # Try DepsDev first
    depsdev_url = f"https://api.deps.dev/v3alpha/systems/pypi/packages/{package}/versions/{version}"
    depsdev_response = requests.get(depsdev_url)
    if depsdev_response.status_code == 200:
        data = depsdev_response.json()
        licenses = data.get("licenses", [])
        if licenses:
            return licenses, "DepsDev"

    # Fallback to PyPI
    pypi_url = f"https://pypi.org/pypi/{package}/json"
    pypi_response = requests.get(pypi_url)
    if pypi_response.status_code != 200:
        print(f"PyPI API failed: {pypi_response.status_code}")
        return [], "PyPI"
    
    data = pypi_response.json()
    info = data.get("info", {})
    license_name = info.get("license")
    if license_name:
        return [license_name], "PyPI"

    # Fallback to GitHub Repo
    project_urls = info.get("project_urls", {})
    github_url = None
    for name, url in project_urls.items():
        if "github.com" in url.lower():
            github_url = url
            break

    if github_url:
        repo_path = github_url.replace("https://github.com/", "").rstrip("/")
        repo_api_url = f"https://api.github.com/repos/{repo_path}"

        headers = {"Accept": "application/vnd.github+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}" 

        github_response = requests.get(repo_api_url, headers=headers)
        if github_response.status_code == 200:
            github_data = github_response.json()
            license_info = github_data.get("license", {})
            license_spdx = license_info.get("spdx_id")
            if license_spdx and license_spdx != "NOASSERTION":
                return [license_spdx], "GitHub"

    # If everything fails
    return [], "Unknown"

