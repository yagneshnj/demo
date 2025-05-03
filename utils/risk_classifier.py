SAFE_LICENSES = ["Apache-2.0", "MIT", "BSD", "Zlib"]
HIGH_RISK_LICENSES = ["GPL", "AGPL"]
RISKY_LICENSES = ["LGPL", "SSPL", "Elastic", "CDDL", "MPL", "EPL"]

def classify_license(license_name: str) -> str:
    for safe in SAFE_LICENSES:
        if safe in license_name:
            return "✅ Safe"
    for high in HIGH_RISK_LICENSES:
        if high in license_name:
            return "🔥 High Risk"
    for risky in RISKY_LICENSES:
        if risky in license_name:
            return "⚠️ Risky"
    return "❓ Unknown"

def format_licenses_with_risk(licenses: list) -> str:
    return ", ".join(f"{lic} {classify_license(lic)}" for lic in licenses) if licenses else "❓ Unknown"

def get_risk_sort_weight(license_with_risk: str) -> int:
    if "🔥" in license_with_risk:
        return 1
    if "⚠️" in license_with_risk:
        return 2
    if "✅" in license_with_risk:
        return 3
    return 4
