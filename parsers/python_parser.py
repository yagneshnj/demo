import re

def parse_requirements_txt(content: str):
    """
    Parse a requirements.txt content into a list of (package, version) tuples.
    Handles ==, >=, <=, >, <, ~= operators gracefully.
    If no version specified, assigns 'latest'.
    """
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            # Use regex to split package and version
            match = re.match(r'^([a-zA-Z0-9_\-\.]+)(==|>=|<=|>|<|~=)?(.*)$', line)
            if match:
                package = match.group(1)
                operator = match.group(2)
                version = match.group(3)
                if operator in ("==", ">=", "<=", ">", "<", "~=") and version:
                    deps.append((package.strip(), version.strip()))
                else:
                    deps.append((package.strip(), "latest"))
            else:
                print(f"⚠️ Skipping unrecognized line: {line}")
        except Exception as e:
            print(f"⚠️ Error parsing line: {line}, Error: {e}")
            continue
    return deps

