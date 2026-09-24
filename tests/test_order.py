"""Order arithmetic must be pure, deterministic Python — no model, no LLM.
An error here is a direct cash error, so every branch gets a test."""

from freshcall.order import hindsight_demand_order, naive_seasonal_order, recommended_cases


class TestRecommendedCases:
    def test_rounds_up_to_next_case(self):
        # 37 units needed, case_pack=12 -> 3 cases (36) is not enough, need 4
        assert recommended_cases(demand=37, safety=0, on_hand=0, case_pack=12) == 4

    def test_exact_multiple_needs_no_rounding(self):
        assert recommended_cases(demand=36, safety=0, on_hand=0, case_pack=12) == 3

    def test_on_hand_reduces_the_order(self):
        # need 37, already have 12 on hand -> only 25 more needed -> 3 cases
        assert recommended_cases(demand=37, safety=0, on_hand=12, case_pack=12) == 3

    def test_on_hand_can_cover_demand_entirely(self):
        assert recommended_cases(demand=10, safety=0, on_hand=50, case_pack=12) == 0

    def test_safety_stock_is_added_before_rounding(self):
        # demand 20 + safety 10 = 30 -> ceil(30/12) = 3
        assert recommended_cases(demand=20, safety=10, on_hand=0, case_pack=12) == 3

    def test_never_returns_negative_cases(self):
        assert recommended_cases(demand=0, safety=0, on_hand=100, case_pack=12) == 0

    def test_near_zero_forecast_orders_nothing(self):
        # SKUs are integer-sold, so 0.001 units means 0 units -- not a full case
        assert recommended_cases(demand=0.001, safety=0, on_hand=0, case_pack=12) == 0

    def test_forecast_below_half_a_unit_rounds_to_zero(self):
        assert recommended_cases(demand=0.49, safety=0, on_hand=0, case_pack=12) == 0

    def test_half_a_unit_rounds_up_to_one_unit_then_one_case(self):
        assert recommended_cases(demand=0.5, safety=0, on_hand=0, case_pack=12) == 1

    def test_forecast_just_over_a_case_rounds_to_nearest_unit_first(self):
        # 12.4 units -> 12 units -> exactly 1 case, not 2
        assert recommended_cases(demand=12.4, safety=0, on_hand=0, case_pack=12) == 1
        # 12.5 units -> 13 units -> 2 cases
        assert recommended_cases(demand=12.5, safety=0, on_hand=0, case_pack=12) == 2

    def test_units_are_always_a_whole_multiple_of_case_pack(self):
        for demand in range(0, 100, 7):
            cases = recommended_cases(demand=demand, safety=0, on_hand=0, case_pack=12)
            assert (cases * 12) % 12 == 0


class TestHindsightDemandOrder:
    def test_rounds_actual_sales_up_to_a_case(self):
        assert hindsight_demand_order(actual_units=37, case_pack=12) == 4

    def test_zero_sales_is_zero_cases(self):
        assert hindsight_demand_order(actual_units=0, case_pack=12) == 0

    def test_negative_actual_units_floors_at_zero_cases(self):
        # a net-negative sales day (returns exceeded sales) is not a demand signal
        assert hindsight_demand_order(actual_units=-3, case_pack=12) == 0


class TestNaiveSeasonalOrder:
    def test_matches_same_weekday_last_week_rounded_up(self):
        assert naive_seasonal_order(same_weekday_last_week_units=25, case_pack=12) == 3
