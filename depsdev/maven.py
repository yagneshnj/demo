import requests
def query_maven_license(group_artifact: str, version: str):
    if version == "unknown":
        url = f"https://api.deps.dev/v3alpha/systems/maven/packages/{group_artifact}"
        r = requests.get(url)
        if r.ok:
            versions = r.json().get("versions", [])
            if versions:
                version = sorted(versions, key=lambda v: v.get("published", ""), reverse=True)[0]["version"]
    url = f"https://api.deps.dev/v3alpha/systems/maven/packages/{group_artifact}/versions/{version}"
    r = requests.get(url)
    return r.json().get("licenses", []) if r.ok else []
