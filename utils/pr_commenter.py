def create_pr_comment(repo, pr_number, comment_body, app_slug):
    pr = repo.get_pull(pr_number)
    comments = pr.get_issue_comments()

    # for comment in comments:
    #     try:
    #         login = comment.user.login.lower()
    #         if (
    #             comment.user.type == "Bot"
    #             and app_slug.lower() in login
    #             and "## 📦 Dependency Scan Report" in comment.body
    #         ):
    #             print(f"🧹 Deleting previous Dependency Scan Report by bot: {login}")
    #             comment.delete()
    #             break  # ✅ Found and deleted. No need to check further!
    #     except Exception as e:
    #         print(f"⚠️ Error while checking/deleting old PR comment: {e}")

    pr.create_issue_comment(comment_body)


