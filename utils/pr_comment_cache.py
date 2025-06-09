def get_cached_scan_result(repo, pr_number, app_slug) -> str | None:
    """
    Look through PR comments and extract cached scan result from this bot's previous comment.
    Looks for a marker like: <!-- cache:scan_risky_licenses -->
    """
    try:
        pr = repo.get_pull(pr_number)
        comments = pr.get_issue_comments()
        for comment in reversed(list(comments)):
            login = comment.user.login.lower()
            if app_slug.lower() in login:
                body = comment.body
                if "<!-- cache:scan_risky_licenses -->" in body:
                    return body.split("<!-- cache:scan_risky_licenses -->", 1)[-1].strip()
    except Exception as e:
        print(f"⚠️ Error while fetching cache from comments: {e}")
    return None
