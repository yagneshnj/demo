import requests
def query_npm_license(package: str, version: str):
    if version in ["latest", "*"]:
        url = f"https://api.deps.dev/v3alpha/systems/npm/packages/{package}"
        r = requests.get(url)
        if r.ok:
            versions = r.json().get("versions", [])
            if versions:
                version = sorted(versions, key=lambda v: v.get("published", ""), reverse=True)[0]["version"]
    url = f"https://api.deps.dev/v3alpha/systems/npm/packages/{package}/versions/{version}"
    r = requests.get(url)
    return r.json().get("licenses", []) if r.ok else []
