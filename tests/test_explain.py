"""explain.py never lets an LLM number reach the manager unchecked: every
response is run through numeral containment, and a failure — API error or
an invented number — falls back to a deterministic template. No network
calls in these tests; the LLM call is injected so behaviour is testable
without an API key."""

import re

from freshcall.containment import check_numeral_containment
from freshcall.explain import (
    build_fact_block, build_fact_block_v2, build_fact_block_v3, comparison_word, generate_explanation,
    order_sentence, order_sentence_from, render_template_fallback, system_prompt_for,
)


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


class TestFactBlockV2:
    def _fb(self):
        return build_fact_block_v2(sku_name="item 7", recommend_cases=1, weekday="Tuesday",
                                   weekday_avg=12.5, last_same_weekday=21.0)

    def test_carries_the_weekday_average_not_a_seven_day_mean(self):
        fb = self._fb()
        assert fb["weekday_avg"] == 12.5 and fb["weekday"] == "Tuesday"
        assert "recent_avg" not in fb

    def test_template_uses_only_fact_block_numbers(self):
        fb = self._fb()
        text = render_template_fallback(fb)
        assert text.startswith("ORDER 1 case")
        assert "Tuesday" in text
        assert check_numeral_containment(text, fb)

    def test_v2_blocks_get_the_v2_prompt(self):
        assert "weekday_avg" in system_prompt_for(self._fb())
        assert "recent_avg" in system_prompt_for(build_fact_block("x", False, 3, 30, 28))


class TestComparisonWord:
    def test_within_ten_percent_is_about_the_same(self):
        assert comparison_word(6.5, 7.0) == "about the same as"   # 7% apart (case 13)
        assert comparison_word(39.5, 37.0) == "about the same as"  # 6% apart (case 17)

    def test_beyond_ten_percent_says_higher_or_lower(self):
        assert comparison_word(11, 21) == "lower than"
        assert comparison_word(7.2, 6.0) == "higher than"

    def test_both_zero_is_about_the_same(self):
        assert comparison_word(0, 0) == "about the same as"


class TestOrderSentenceV3:
    def test_states_cases_and_units_and_labels_every_reason_number(self):
        text = order_sentence(cases=4, case_pack=12, weekday="Sunday", weekday_avg=37.5, last_same_weekday=51.0)
        assert text == "ORDER 4 cases (48 units). Sundays have averaged 37.5 units, lower than last Sunday's 51."

    def test_singular_forms(self):
        text = order_sentence(cases=1, case_pack=12, weekday="Monday", weekday_avg=1.0, last_same_weekday=1.0)
        assert text == "ORDER 1 case (12 units). Mondays have averaged 1 unit, about the same as last Monday's 1."

    def test_every_number_is_in_the_fact_block(self):
        fb = build_fact_block_v3("item 7", 2, 12, "Tuesday", 10.2, 0.0)
        assert check_numeral_containment(order_sentence_from(fb), fb)


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
