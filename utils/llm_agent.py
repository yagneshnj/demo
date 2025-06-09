import openai
import os
from utils.scan_wrapper import scan_risky_licenses
from auth import APP_SLUG
from utils.pr_comment_cache import get_cached_scan_result

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Tool 1: license scanner
def run_scan_risky_licenses(repo, pr, install, **kwargs):
    return scan_risky_licenses(repo, pr, install)

# Tool 2: license summarizer
def summarize_license(license_id: str) -> str:
    prompt = f"""
    You are a legal-aware assistant that explains open source licenses in simple, accurate terms.

    Summarize the license: {license_id}

    Include:
    - Whether it's permissive or copyleft
    - Redistribution obligations
    - Notable risks or restrictions

    Keep the response under 100 words and markdown-formatted.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Could not summarize {license_id}: {e}"

# Tool registry
TOOLS = {
    "scan_risky_licenses": {
        "description": "Scans the pull request for risky open source licenses.",
        "function": run_scan_risky_licenses
    },
    "summarize_license": {
        "description": "Provides a plain-English explanation of an open source license like AGPL-3.0.",
        "function": lambda repo, pr, install, license_id=None: summarize_license(license_id)
    }
}

def parse_tool_action(action: str):
    if not action.startswith("TOOL:"):
        return None, None
    try:
        content = action[5:].strip()
        if ":" in content:
            tool_name, arg = content.split(":", 1)
            return tool_name.strip(), arg.strip()
        return content.strip(), None
    except:
        return None, None

def handle_governance_comment(comment_body: str, repo_full_name: str, pr_number: int, installation_id: int, repo) -> str:

    tool_list = "\n".join(f"- {name}: {tool['description']}" for name, tool in TOOLS.items())

    cached_result = get_cached_scan_result(repo, pr_number, APP_SLUG)

    context = [
        {
            "role": "system",
            "content": "You are an AI assistant that helps respond to GitHub PR comments related to open source governance. "
                       "You can use tools, reason step-by-step, and write helpful markdown responses. "
                       f"Available tools:\n{tool_list}"
        },
        {
            "role": "user",
            "content": f"A user commented:\n\"\"\"{comment_body}\"\"\"\n\n"
                       "Think step-by-step and respond with TOOL: <tool_name> or TOOL: <tool_name>:<arg> to run a tool, "
                       "or FINAL: <your markdown reply> to respond to the user."
        }
    ]

    if cached_result:
        context.append({
            "role": "user",
            "content": f"TOOL_RESULT: {cached_result}"
        })
        print("🧠 Injected cached scan result from prior comment.")

    for _ in range(3):  # max 3 reasoning steps
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=context,
                temperature=0
            )
            action = response.choices[0].message.content.strip()
            print(f"🧠 LLM action: {action}")
            if action.startswith("FINAL:"):
                return action[len("FINAL:"):].strip()

            tool_name, arg = parse_tool_action(action)
            if tool_name in TOOLS:
                tool_fn = TOOLS[tool_name]["function"]
                if tool_name == "summarize_license":
                    result = tool_fn(repo_full_name, pr_number, installation_id, license_id=arg)
                else:
                    result = tool_fn(repo_full_name, pr_number, installation_id)

                context.append({"role": "assistant", "content": action})
                context.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
            else:
                context.append({"role": "assistant", "content": action})
                context.append({"role": "user", "content": "TOOL_RESULT: Invalid tool or unknown action."})

        except Exception as e:
            print(f"❌ LLM error: {e}")
            return "⚠️ I encountered an error while trying to reason with this comment."

    return "⚠️ I could not complete reasoning within the allowed steps."
