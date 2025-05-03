import json
def parse_package_json(content: str):
    deps = []
    try:
        data = json.loads(content)
        for dep_set in ["dependencies", "devDependencies"]:
            if dep_set in data:
                for name, version in data[dep_set].items():
                    deps.append((name, version))
    except Exception as e:
        print(f"Error parsing package.json: {e}")
    return deps
