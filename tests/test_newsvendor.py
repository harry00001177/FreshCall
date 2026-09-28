"""Newsvendor ordering (PRE-REGISTRATION, DECISIONS.md 2026-09-28): order at
quantile r / (1 + r), where r = cost of one unit short / cost of one unit
wasted. The arithmetic here decides every order, so each rule is pinned."""

import math

import numpy as np
import pandas as pd
import pytest

from freshcall.model import fit_quantile_models, predict_all_quantiles
from freshcall.newsvendor import (critical_quantile, floor_applies, nearest_quantile, newsvendor_cases, order_cost,
                                  system_order)

GRID = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


class TestCriticalQuantile:
    def test_equal_costs_mean_the_median(self):
        assert critical_quantile(1) == 0.5

    def test_shortage_four_times_worse_means_p80(self):
        assert critical_quantile(4) == pytest.approx(0.8)

    def test_cheap_shortage_means_a_low_quantile(self):
        assert critical_quantile(0.25) == pytest.approx(0.2)

    def test_non_positive_ratio_is_rejected(self):
        with pytest.raises(ValueError):
            critical_quantile(0)


class TestNearestQuantile:
    @pytest.mark.parametrize("ratio, expected", [
        (0.25, 0.2), (0.5, 0.3), (1, 0.5), (2, 0.7), (4, 0.8), (9, 0.9),
    ])
    def test_pre_registered_mapping(self, ratio, expected):
        # the six scanned ratios and the trained quantile each one uses
        assert nearest_quantile(critical_quantile(ratio), GRID) == expected

    def test_beyond_the_grid_uses_the_end_quantile(self):
        assert nearest_quantile(critical_quantile(99), GRID) == 0.9


class TestOrderCost:
    def test_shortage_weighted_by_ratio_waste_by_one(self):
        # 3 units wasted at cost 1, 2 units short at cost 4
        assert order_cost(over=3, short=2, ratio=4) == 11

    def test_perfect_order_costs_nothing(self):
        assert order_cost(over=0, short=0, ratio=9) == 0


class _FixedModel:
    def __init__(self, value):
        self.value = value

    def predict(self, X):
        return np.array([self.value])


class TestPredictAllQuantiles:
    def test_crossed_predictions_are_sorted_back_into_order(self):
        models = {0.1: _FixedModel(5.0), 0.5: _FixedModel(3.0), 0.9: _FixedModel(9.0)}
        assert predict_all_quantiles(models, X=None) == {0.1: 3.0, 0.5: 5.0, 0.9: 9.0}

    def test_negative_predictions_are_clipped_to_zero(self):
        models = {0.1: _FixedModel(-2.0), 0.5: _FixedModel(1.0), 0.9: _FixedModel(4.0)}
        assert predict_all_quantiles(models, X=None)[0.1] == 0.0

    def test_nine_real_models_are_monotone(self):
        rng = np.random.default_rng(42)
        X = pd.DataFrame({"x": rng.normal(size=80)})
        y = X["x"] * 2 + rng.normal(size=80) + 10
        models = fit_quantile_models(X, y, quantiles=GRID, random_state=42)
        preds = predict_all_quantiles(models, X.iloc[[0]])
        values = [preds[q] for q in GRID]
        assert values == sorted(values)
        assert all(math.isfinite(v) for v in values)


class TestEvaluateSkuFoldQuantiles:
    def test_one_row_per_test_day_with_every_quantile(self):
        from freshcall.backtest import FOLDS, evaluate_sku_fold_quantiles
        rng = np.random.default_rng(0)
        dates = pd.date_range("2017-01-01", FOLDS[0]["test_end"])
        raw = pd.DataFrame({"date": dates, "store_nbr": 1, "item_nbr": 7,
                            "unit_sales": rng.poisson(20, len(dates)).astype(float)})
        cfg = {"case_pack": 12, "model": {"n_estimators": 20, "max_depth": 2,
                                          "learning_rate": 0.1, "random_state": 42}}
        rows = evaluate_sku_fold_quantiles(raw, 1, 7, FOLDS[0], cfg, quantiles=GRID)
        assert len(rows) == 31  # 16 May - 15 Jun
        r = rows[0]
        assert [r[f"q{q}"] for q in GRID] == sorted(r[f"q{q}"] for q in GRID)
        assert r["hindsight"] == math.ceil(r["actual"] / 12)


class TestNewsvendorCases:
    """Amended pre-registration (DECISIONS.md 2026-09-28): the 9 quantile
    forecasts are 9 equally likely demands; order the whole case count
    with the lowest average cost."""

    def test_small_demand_is_not_worth_a_case_when_waste_costs_the_same(self):
        # every scenario ~3 units: 1 case wastes ~9, 0 cases misses ~3
        assert newsvendor_cases([3.0] * 9, ratio=1, case_pack=12) == 0

    def test_same_demand_is_worth_a_case_when_shortage_costs_more(self):
        # at ratio 4 missing 3 units costs 12 > wasting 9
        assert newsvendor_cases([3.0] * 9, ratio=4, case_pack=12) == 1

    def test_can_round_down_below_the_forecast(self):
        # median 13 units: rounding up (2 cases) wastes ~11, 1 case misses ~1
        assert newsvendor_cases([13.0] * 9, ratio=1, case_pack=12) == 1

    def test_ties_go_to_fewer_cases(self):
        # 6 units: 0 cases misses 6, 1 case wastes 6 -- equal at ratio 1
        assert newsvendor_cases([6.0] * 9, ratio=1, case_pack=12) == 0

    def test_spread_of_scenarios_matters_not_just_the_middle(self):
        low = [10.0] * 5 + [30.0] * 4
        # higher ratio -> willing to cover the 30-unit scenarios
        assert newsvendor_cases(low, ratio=9, case_pack=12) > newsvendor_cases(low, ratio=0.25, case_pack=12)

    def test_zero_demand_orders_nothing(self):
        assert newsvendor_cases([0.0] * 9, ratio=9, case_pack=12) == 0


class TestFloor:
    def test_sold_every_one_of_the_last_7_days(self):
        assert floor_applies([1, 2, 5, 1, 1, 3, 1]) is True

    def test_one_zero_day_means_no_floor(self):
        assert floor_applies([1, 2, 0, 1, 1, 3, 1]) is False

    def test_needs_a_full_week_of_history(self):
        assert floor_applies([1, 2, 3]) is False


class TestSystemOrder:
    """What the UI orders (DECISIONS.md 2026-09-28): the newsvendor order,
    lifted to 1 case when the floor applies and the store has it on."""

    def test_floor_lifts_a_zero_order_to_one_case(self):
        assert system_order([3.0] * 9, ratio=1, case_pack=12, floor=True) == 1

    def test_no_floor_leaves_the_zero(self):
        assert system_order([3.0] * 9, ratio=1, case_pack=12, floor=False) == 0

    def test_floor_never_lowers_an_order(self):
        assert system_order([40.0] * 9, ratio=4, case_pack=12, floor=True) == 4
