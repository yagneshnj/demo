import requests

def query_pypi_license(package: str, version: str):
    if version in ["latest", "*", None, "unknown"]:
        # Just query at the package level, don't resolve specific version
        url = f"https://api.deps.dev/v3alpha/systems/pypi/packages/{package}"
        r = requests.get(url)
        if not r.ok:
            print(f"Deps.dev query failed for PyPI package: {package}")
            return []
        data = r.json()
        return data.get("licenses", [])

    # Normal versioned lookup
    url = f"https://api.deps.dev/v3alpha/systems/pypi/packages/{package}/versions/{version}"
    r = requests.get(url)
    if not r.ok:
        print(f"Deps.dev query failed for PyPI package: {package}@{version}")
        return []
    data = r.json()
    return data.get("licenses", [])
