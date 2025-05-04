import requests

def query_npm_license(package: str, version: str):
    package_url = f"https://registry.npmjs.org/{package}"
    response = requests.get(package_url)
    if response.status_code != 200:
        print(f"NPM API failed: {response.status_code}")
        return [], "NPM"
    data = response.json()
    versions = data.get("versions", {})
    if version in versions:
        license_info = versions[version].get("license")
        if license_info:
            if isinstance(license_info, str):
                return [license_info], "NPM"
            if isinstance(license_info, dict):
                return [license_info.get("type", "Unknown")], "NPM"
    return [], "NPM"

