import openai
import os

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def is_open_source_governance_question(comment_body: str) -> bool:

    prompt = f"""
    You are an expert AI classifier helping route GitHub pull request comments to the appropriate internal teams.

    Your job is to decide if a comment should be handled by the **Open Source Governance** team.

    The Open Source Governance team is responsible for:
    - All open source license types (e.g. MIT, Apache, BSD, GPL, AGPL, LGPL, SSPL)
    - SPDX license identifiers (e.g. GPL-3.0, AGPL-3.0, SSPL-1.0)
    - Questions about license risk, copyleft, redistribution, or attribution
    - Legal obligations of using specific licenses

    ### Instructions:
    If the comment involves open source licensing, mention of a specific license, or legal risks from open source use — respond with **"Yes"**.

    Otherwise, if it's a general question not related to licenses — respond with **"No"**.

    Comment:
    \"\"\"{comment_body}\"\"\"
    """


    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        print(f"🧠 OpenAI classified as: {response.choices[0].message.content.strip().lower()}")
        return "yes" in response.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"❌ OpenAI classification error: {e}")
        return False
