def create_pr_check_run(repo, head_sha, markdown, conclusion="neutral"):
    """
    Creates a GitHub Check Run on the PR with the given markdown content.
    """

    icon = {
        "success": "✅",
        "failure": "❌",
        "neutral": "⚠️"
    }.get(conclusion, "ℹ️")

    try:
        repo.create_check_run(
            name="Open Source Governance",
            head_sha=head_sha,
            status="completed",
            conclusion=conclusion,
            output={
                "title": f"{icon} {conclusion.capitalize()}",
                "summary": (
                    "💬 Curious about license details? Comment on this PR.\n"
                    "Ask things like:\n"
                    "• What are the risky licenses?\n"
                    "• Show high risk only\n"
                    "• Any AGPL or SSPL?"
                ),
                "text": markdown + (
                    "\n\n---\n"
                    "**💡 Tip:** Try asking me something like:\n"
                    "- `List risky packages`\n"
                    "- `Explain AGPL`\n"
                    "- `High risk only`\n"
                )
            }
        )
        print("✅ Check run created successfully.")
    except Exception as e:
        print(f"❌ Failed to create check run: {e}")
