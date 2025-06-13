# utils/risky_issue_creator.py

from uuid import uuid4

def create_risky_issue(repo, pr_number, risky_packages):
    """
    Create a GitHub Issue listing risky packages detected in a merged PR.
    risky_packages: list of (dependency, license_with_risk)
    """
    if not risky_packages:
        return  # No risky packages, no issue needed

    issue_title = f"⚠️ Open Source Governance: Risky Packages Detected"

    body_lines = []
    body_lines.append("## ⚠️ License Risk Alert\n")
    body_lines.append(f"Risky/high-risk licenses were merged in PR #{pr_number}.\n")
    body_lines.append("| Dependency | License (with Risk) |")
    body_lines.append("|:-----------|:--------------------|")

    for dep, license_risk in risky_packages:
        body_lines.append(f"| {dep} | {license_risk} |")

    body_lines.append("\n---")
    body_lines.append("✅ Please review and resolve this licensing risk.")
    # Add hidden Risk Tracking ID for Phase 2
    risk_id = str(uuid4())
    body_lines.append(f"\n<!-- Risk-Tracking-ID: {risk_id} -->")

    repo.create_issue(
        title=issue_title,
        body="\n".join(body_lines)
    )
