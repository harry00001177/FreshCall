"""L2 judge for the explanation harness (pre-registered, DECISIONS.md
2026-09-24). Asks a different model family than the generator the same two
yes/no questions Harry answered. The judge is a component under test, not
ground truth — its value is measured by how often it disagrees with Harry."""

import json
import os
import re

JUDGE_MODEL = "anthropic/claude-haiku-4.5"

JUDGE_PROMPT = """You are checking one sentence shown to a restaurant manager who is placing tomorrow's fresh-food order.

Fact block the sentence was written from:
{fact_block}

Sentence shown to the manager:
{sentence}

Answer two questions:
1. faithful: does the sentence say ONLY things the fact block supports? Any number not in the fact block, or any wrong or unsupported comparison word (e.g. "higher", "lower", "significantly"), makes it "no".
2. usable: does it open with the order (or a clear hand-back to the manager), is it readable in about 5 seconds, and does it avoid talking about confidence or probability?

Reply with JSON only: {{"faithful": "yes" or "no", "usable": "yes" or "no", "reason": "one short sentence"}}"""


def parse_verdict(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict):
        return {"faithful": "unparseable", "usable": "unparseable", "reason": text.strip()}

    def yes_no(value) -> str:
        v = str(value).strip().lower()
        return v if v in ("yes", "no") else "unparseable"

    return {
        "faithful": yes_no(data.get("faithful")),
        "usable": yes_no(data.get("usable")),
        "reason": str(data.get("reason", "")).strip(),
    }


def call_judge(fact_block_json: str, sentence: str) -> dict:
    from openai import OpenAI

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        max_tokens=150,
        messages=[{"role": "user", "content": JUDGE_PROMPT.format(fact_block=fact_block_json, sentence=sentence)}],
    )
    return parse_verdict(response.choices[0].message.content)
