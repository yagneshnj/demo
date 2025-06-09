from utils.pr_commenter import create_pr_comment
from utils.scan_wrapper import scan_risky_licenses  # our only implemented tool (currently)
from github import Github
from auth import get_installation_access_token, APP_SLUG
from utils.oss_router import is_open_source_governance_question
from utils.llm_agent import handle_governance_comment

def handle_issue_comment(payload):

    comment_body = payload["comment"]["body"]
    issue = payload["issue"]
    repo_info = payload["repository"]
    installation_id = payload["installation"]["id"]

    repo_full_name = repo_info["full_name"]
    pr_number = issue["number"]  # GitHub treats PRs as issues too

    # Optionally skip bot's own comments
    gh_token = get_installation_access_token(installation_id)
    gh = Github(gh_token)
    repo = gh.get_repo(repo_full_name)

    print(f"🤖 Received comment on PR #{pr_number}: '{comment_body}'")

    if not is_open_source_governance_question(comment_body):
        print("🔕 Comment not related to OSS governance. Ignoring.")
        return

    response = handle_governance_comment(comment_body, repo_full_name, pr_number, installation_id, repo=repo)
    create_pr_comment(repo, pr_number, response, APP_SLUG)
  

