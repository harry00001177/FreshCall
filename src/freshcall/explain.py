"""Wording layer. The LLM only ever paraphrases a fixed fact block into one
sentence — it never sees raw data, never does arithmetic, and never runs at
all on an abstain SKU-day (there's nothing for it to safely say). Every
LLM response is checked with numeral containment before it's allowed to
reach the manager; a failure falls back to a deterministic template, never
to a retry or a guess."""

import os

from freshcall.containment import check_numeral_containment


def build_fact_block(sku_name, abstain, recommend_cases, recent_avg, last_same_weekday) -> dict:
    return {
        "sku_name": sku_name,
        "abstain": abstain,
        "recommend_cases": recommend_cases,
        "recent_avg": recent_avg,
        "last_same_weekday": last_same_weekday,
    }


def render_template_fallback(fact_block: dict) -> str:
    """Deterministic, LLM-free wording. Used directly for every abstain
    SKU-day, and as the fallback for any order SKU-day whose LLM output
    fails containment or the API call itself fails."""
    if fact_block["abstain"]:
        text = "ASK ME - this one is harder to call than usual. Please set it manually."
        anchor = fact_block.get("last_same_weekday")
        # reference anchor (DECISIONS.md 2026-09-22): a historical fact, not a
        # recommendation or a confidence figure, so it's the one number allowed here
        return text if anchor is None else f"{text} Same day last week: {anchor:g} unit{'' if anchor == 1 else 's'}."
    return (
        f"ORDER {fact_block['recommend_cases']} cases. "
        f"Recent average {fact_block['recent_avg']}, "
        f"last same weekday {fact_block['last_same_weekday']}."
    )


def _default_call_llm(fact_block: dict) -> str:
    """Real OpenRouter call, used only when no `call_llm` is injected (i.e.
    outside tests). Imported lazily so tests never require the `openai`
    package to hit the network or even have a key configured."""
    from openai import OpenAI

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    system_prompt = (
        "You write a one-line order recommendation for a restaurant manager "
        "who has 5 seconds to read it, not a data summary. Always start with "
        "'ORDER {recommend_cases} cases.' exactly, then one short clause "
        "giving the reason, using ONLY the numbers in the fact block below. "
        "Compare recent_avg with last_same_weekday using exactly one of "
        "'higher than', 'lower than', or 'about the same as' (the last only "
        "when the two are within 10% of each other). Never add intensity "
        "words such as 'significantly', 'sharply', 'slightly' or 'much'. "
        "Never write a number that is not in the fact block. Never mention "
        "confidence, probability, or uncertainty.\n\n"
        "Example — fact block {'recommend_cases': 3, 'recent_avg': 30, "
        "'last_same_weekday': 28}\n"
        "Good: \"ORDER 3 cases. Recent average 30, about the same as last week's 28.\"\n"
        "Bad: \"The recommended order is 3 cases based on a recent average "
        "of 30 units and a similar figure of 28 units last week.\" "
        "(too long, reads like a report, not an instruction)"
    )
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        temperature=0,
        max_tokens=80,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": str(fact_block)},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_explanation(fact_block: dict, call_llm=None) -> str:
    """Abstain SKU-days never reach the LLM — there's no safe sentence for
    it to write about a number that doesn't exist. Everything else tries
    the LLM once, and falls back to the template on any failure: a raised
    exception (network, auth) or a containment failure (an invented
    number)."""
    if fact_block["abstain"]:
        return render_template_fallback(fact_block)

    llm = call_llm or _default_call_llm
    try:
        text = llm(fact_block)
    except Exception:
        return render_template_fallback(fact_block)

    if not check_numeral_containment(text, fact_block):
        return render_template_fallback(fact_block)

    return text
