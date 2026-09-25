"""explain.py never lets an LLM number reach the manager unchecked: every
response is run through numeral containment, and a failure — API error or
an invented number — falls back to a deterministic template. No network
calls in these tests; the LLM call is injected so behaviour is testable
without an API key."""

import re

from freshcall.containment import check_numeral_containment
from freshcall.explain import build_fact_block, generate_explanation, render_template_fallback


class TestBuildFactBlock:
    def test_order_fact_block_has_no_none_for_a_normal_recommendation(self):
        fb = build_fact_block(
            sku_name="Tomato slices", abstain=False, recommend_cases=3,
            recent_avg=30, last_same_weekday=28,
        )
        assert fb["recommend_cases"] == 3
        assert fb["abstain"] is False

    def test_abstain_fact_block_has_no_recommend_cases(self):
        fb = build_fact_block(
            sku_name="Lettuce", abstain=True, recommend_cases=None,
            recent_avg=15, last_same_weekday=12,
        )
        assert fb["recommend_cases"] is None
        assert fb["abstain"] is True


class TestRenderTemplateFallback:
    def test_order_template_contains_only_fact_block_numbers(self):
        fb = build_fact_block(
            sku_name="Tomato slices", abstain=False, recommend_cases=3,
            recent_avg=30, last_same_weekday=28,
        )
        text = render_template_fallback(fb)
        assert "3" in text
        assert "ORDER" in text

    def test_abstain_template_shows_only_the_reference_anchor(self):
        # the one number allowed on abstain: last same-weekday actual sales,
        # a historical fact -- no recommended quantity, no confidence figure
        fb = build_fact_block(
            sku_name="Lettuce", abstain=True, recommend_cases=None,
            recent_avg=15, last_same_weekday=12,
        )
        text = render_template_fallback(fb)
        assert "ASK ME" in text
        assert re.findall(r"\d+(?:\.\d+)?", text) == ["12"]

    def test_abstain_anchor_of_one_is_singular(self):
        fb = build_fact_block(
            sku_name="Lettuce", abstain=True, recommend_cases=None,
            recent_avg=15, last_same_weekday=1.0,
        )
        assert render_template_fallback(fb).endswith("Same day last week: 1 unit.")

    def test_abstain_template_without_an_anchor_has_no_digits(self):
        fb = build_fact_block(
            sku_name="Lettuce", abstain=True, recommend_cases=None,
            recent_avg=15, last_same_weekday=None,
        )
        assert not any(c.isdigit() for c in render_template_fallback(fb))


class TestGenerateExplanation:
    def test_uses_llm_output_when_it_passes_containment(self):
        fb = build_fact_block(
            sku_name="Tomato slices", abstain=False, recommend_cases=3,
            recent_avg=30, last_same_weekday=28,
        )
        fake_llm = lambda fact_block: "ORDER 3 cases. Recent average 30, similar to last week's 28."
        text = generate_explanation(fb, call_llm=fake_llm)
        assert text == "ORDER 3 cases. Recent average 30, similar to last week's 28."

    def test_falls_back_to_template_when_llm_invents_a_number(self):
        fb = build_fact_block(
            sku_name="Tomato slices", abstain=False, recommend_cases=3,
            recent_avg=30, last_same_weekday=28,
        )
        fake_llm = lambda fact_block: "ORDER 3 cases. Predicted demand is 99 units."
        text = generate_explanation(fb, call_llm=fake_llm)
        assert "99" not in text
        assert "ORDER" in text  # template fallback still gives a usable answer

    def test_falls_back_to_template_when_the_llm_call_raises(self):
        fb = build_fact_block(
            sku_name="Tomato slices", abstain=False, recommend_cases=3,
            recent_avg=30, last_same_weekday=28,
        )

        def broken_llm(fact_block):
            raise RuntimeError("API is down")

        text = generate_explanation(fb, call_llm=broken_llm)
        assert "ORDER" in text
        assert "3" in text

    def test_abstain_case_never_reaches_the_llm(self):
        fb = build_fact_block(
            sku_name="Lettuce", abstain=True, recommend_cases=None,
            recent_avg=15, last_same_weekday=12,
        )
        calls = []

        def tracking_llm(fact_block):
            calls.append(fact_block)
            return "should never get here"

        text = generate_explanation(fb, call_llm=tracking_llm)
        assert calls == []  # the LLM was never invoked
        assert "ASK ME" in text
        assert check_numeral_containment(text, fb)
