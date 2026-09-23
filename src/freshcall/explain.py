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
        return "ASK ME - this one is harder to call than usual. Please set it manually."
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
        "You write a single, plain sentence for a busy restaurant manager, "
        "using ONLY the numbers given in the fact block below. Never write "
        "any number that is not in the fact block. Never mention confidence, "
        "probability, or uncertainty."
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
