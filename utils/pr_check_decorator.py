def create_pr_check_run(repo, head_sha, markdown, conclusion="neutral"):
    """
    Creates a GitHub Check Run on the PR with the given markdown content.
    """
    try:
        repo.create_check_run(
            name="Open Source Governance",
            head_sha=head_sha,
            status="completed",
            conclusion=conclusion,
            output={
                "title": "📦 Dependency Risk Report",
                "summary": "Scan completed. Expand for details.",
                "text": markdown
            }
        )
        print("✅ Check run created successfully.")
    except Exception as e:
        print(f"❌ Failed to create check run: {e}")
