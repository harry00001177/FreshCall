"""The L2 judge's reply must be parsed strictly: anything that isn't a clear
yes/no for both questions is recorded as unparseable, never guessed."""

from freshcall.judge import parse_verdict


class TestParseVerdict:
    def test_parses_clean_json(self):
        v = parse_verdict('{"faithful": "yes", "usable": "no", "reason": "too long"}')
        assert v == {"faithful": "yes", "usable": "no", "reason": "too long"}

    def test_tolerates_code_fences_around_json(self):
        v = parse_verdict('```json\n{"faithful": "no", "usable": "yes", "reason": "x"}\n```')
        assert v["faithful"] == "no" and v["usable"] == "yes"

    def test_normalises_case(self):
        assert parse_verdict('{"faithful": "YES", "usable": "No", "reason": ""}')["usable"] == "no"

    def test_unclear_answer_is_marked_unparseable(self):
        v = parse_verdict('{"faithful": "mostly", "usable": "yes", "reason": ""}')
        assert v["faithful"] == "unparseable"

    def test_non_json_is_marked_unparseable(self):
        v = parse_verdict("The sentence looks fine to me.")
        assert v == {"faithful": "unparseable", "usable": "unparseable", "reason": "The sentence looks fine to me."}

    def test_three_question_verdict(self):
        v = parse_verdict('{"faithful": "yes", "usable": "yes", "direction": "no", "reason": "points up"}',
                          keys=("faithful", "usable", "direction"))
        assert v["direction"] == "no" and v["faithful"] == "yes"

    def test_three_question_unparseable_marks_all_three(self):
        v = parse_verdict("no json", keys=("faithful", "usable", "direction"))
        assert v["direction"] == "unparseable"
