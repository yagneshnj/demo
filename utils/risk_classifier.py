import re

# Define licenses by category
SAFE_LICENSES = [
    "Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "BSD", "Zlib", "LGPL-2.1-or-later", "EPL-2.0"
]
HIGH_RISK_LICENSES = [
    "GPL-2.0", "GPL-3.0", "AGPL-3.0", "AGPL", "Elastic-2.0", "SSPL-1.0"
]
RISKY_LICENSES = [
    "LGPL-2.1", "LGPL-3.0", "SSPL", "Elastic", "CDDL", "MPL", "EPL", "non-standard"
]

def classify_license(license_name: str) -> str:
    """Classify a single license name into a risk category."""
    license_name = license_name.strip()
    if license_name in SAFE_LICENSES:
        return "✅ Safe"
    if license_name in HIGH_RISK_LICENSES:
        return "🔥 High Risk"
    if license_name in RISKY_LICENSES:
        return "⚠️ Risky"
    return "❓ Unknown"

def format_licenses_with_risk(licenses: list) -> str:
    """
    Format a list of license names with risk classification,
    and determine overall combined risk.
    """
    if not licenses:
        return "❓ Unknown"

    risks = []
    formatted = []

    for lic in licenses:
        parts = re.split(r'\s+(?:OR|AND)\s+', lic)
        for part in parts:
            part = part.strip("() ")
            risk = classify_license(part)
            risks.append(risk)
            formatted.append(f"{part} {risk}")

    # Merge logic: Highest risk wins
    if "🔥 High Risk" in risks:
        overall = "🔥 High Risk"
    elif "⚠️ Risky" in risks:
        overall = "⚠️ Risky"
    elif "✅ Safe" in risks:
        overall = "✅ Safe"
    else:
        overall = "❓ Unknown"

    return ", ".join(formatted) + f" ➔ Overall: {overall}"

def get_risk_sort_weight(license_with_risk: str) -> int:
    """Sort helper: High risk first, then risky, then safe, then unknown."""
    if "🔥 High Risk" in license_with_risk:
        return 1
    if "⚠️ Risky" in license_with_risk:
        return 2
    if "✅ Safe" in license_with_risk:
        return 3
    return 4  # ❓ Unknown

