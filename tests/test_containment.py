"""Zero-tolerance check: every number the LLM writes must come from the fact
block. This is the one guardrail standing between 'the LLM described a real
number' and 'the LLM invented a number' — see CONTEXT.md."""

from freshcall.containment import check_numeral_containment


class TestNumeralContainment:
    def test_passes_when_every_number_is_in_the_fact_block(self):
        fact_block = {"recommend_cases": 7, "recent_avg": 82, "last_same_weekday": 79}
        text = "ORDER 7 cases. Recent average 82, similar to last Tuesday's 79."
        assert check_numeral_containment(text, fact_block) is True

    def test_fails_on_a_single_invented_number(self):
        fact_block = {"recommend_cases": 7, "recent_avg": 82, "last_same_weekday": 79}
        # "90" does not appear anywhere in the fact block -> must fail, zero tolerance
        text = "ORDER 7 cases. Predicted demand is 90 units."
        assert check_numeral_containment(text, fact_block) is False

    def test_abstain_string_with_no_digits_always_passes(self):
        fact_block = {"recommend_cases": None, "recent_avg": 82, "last_same_weekday": 79}
        text = "ASK ME - this one is harder to call than usual."
        assert check_numeral_containment(text, fact_block) is True

    def test_decimal_numbers_are_matched_too(self):
        fact_block = {"recent_avg": 82.5}
        text = "Recent average is 82.5 units."
        assert check_numeral_containment(text, fact_block) is True

    def test_ignores_numbers_embedded_in_words_like_ordinals_is_not_required(self):
        # ordinary case: a case count that also happens to match a word boundary
        fact_block = {"recommend_cases": 3}
        text = "ORDER 3 cases."
        assert check_numeral_containment(text, fact_block) is True

    def test_numbers_embedded_in_string_fields_are_allowed(self):
        # Favorita has no product names, only item numbers -- sku_name is a
        # string like "item 502331", and the LLM repeating it is not an
        # invented number, it's the fact block's own SKU identifier
        fact_block = {"sku_name": "item 502331", "recommend_cases": 3}
        text = "ORDER 3 cases of item 502331."
        assert check_numeral_containment(text, fact_block) is True
