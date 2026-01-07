"""
Property-based tests for investment decision logic functionality.
"""

import tempfile
from datetime import date, timedelta
from typing import List

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.price_monitor.price_monitor import PriceMonitor
from buy_the_dip.investment_tracker import InvestmentTracker
from buy_the_dip.models import Investment


class TestInvestmentDecisionProperties:
    """Property-based tests for investment decision logic."""

    @given(
        yesterday_price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
        trigger_price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        has_recent_investment=st.booleans(),
    )
    def test_investment_decision_logic_correctness(
        self,
        yesterday_price: float,
        trigger_price: float,
        evaluation_date: date,
        has_recent_investment: bool,
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any trading day evaluation, an investment should be executed if and only if
        yesterday's closing price is <= trigger price AND no investment exists within
        the past 28 calendar days, with each day evaluated independently.

        Validates: Requirements 4.1, 4.2, 4.3, 4.6
        """
        # Skip NaN and infinite values
        assume(
            yesterday_price == yesterday_price
            and yesterday_price != float("inf")
            and yesterday_price != float("-inf")
        )
        assume(
            trigger_price == trigger_price
            and trigger_price != float("inf")
            and trigger_price != float("-inf")
        )

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create strategy system
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            investment_tracker = InvestmentTracker(data_dir=temp_dir)

            # Add recent investment if specified
            if has_recent_investment:
                recent_investment = Investment(
                    date=evaluation_date - timedelta(days=14),  # Within 28 days
                    ticker="SPY",
                    price=200.0,
                    amount=2000.0,
                    shares=10.0,
                )
                investment_tracker.add_investment(recent_investment)

            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Test investment decision logic
            should_invest = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )

            # Determine expected result based on conditions
            trigger_met = yesterday_price <= trigger_price
            expected_should_invest = trigger_met and not has_recent_investment

            assert should_invest == expected_should_invest, (
                f"Investment decision incorrect: should_invest={should_invest}, "
                f"trigger_met={trigger_met}, has_recent_investment={has_recent_investment}"
            )

            # Verify individual conditions
            if yesterday_price > trigger_price:
                # Trigger not met - should not invest regardless of recent investments
                assert (
                    not should_invest
                ), f"Should not invest when yesterday_price ({yesterday_price}) > trigger_price ({trigger_price})"

            if trigger_met and has_recent_investment:
                # Trigger met but recent investment exists - should not invest
                assert (
                    not should_invest
                ), "Should not invest when recent investment exists within 28 days"

            if trigger_met and not has_recent_investment:
                # Both conditions met - should invest
                assert should_invest, "Should invest when trigger met and no recent investment"

    @given(
        yesterday_price=st.floats(min_value=80.0, max_value=120.0, exclude_min=True),
        trigger_price=st.floats(min_value=100.0, max_value=150.0, exclude_min=True),
        evaluation_dates=st.lists(
            st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            min_size=2,
            max_size=10,
        ),
    )
    def test_investment_decision_independence_across_days(
        self, yesterday_price: float, trigger_price: float, evaluation_dates: List[date]
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any sequence of trading days, each day should be evaluated independently,
        with the decision based only on that day's conditions and investment history.

        Validates: Requirements 4.6
        """
        # Skip NaN and infinite values
        assume(
            yesterday_price == yesterday_price
            and yesterday_price != float("inf")
            and yesterday_price != float("-inf")
        )
        assume(
            trigger_price == trigger_price
            and trigger_price != float("inf")
            and trigger_price != float("-inf")
        )

        # Sort dates to ensure chronological order
        evaluation_dates = sorted(set(evaluation_dates))
        assume(len(evaluation_dates) >= 2)

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Evaluate each day independently
            decisions = []
            for eval_date in evaluation_dates:
                should_invest = strategy_system.should_invest(
                    yesterday_price, trigger_price, eval_date
                )
                decisions.append((eval_date, should_invest))

                # If investment decision is positive, simulate adding an investment
                if should_invest:
                    investment = Investment(
                        date=eval_date,
                        ticker="SPY",
                        price=yesterday_price,
                        amount=2000.0,
                        shares=2000.0 / yesterday_price,
                    )
                    investment_tracker.add_investment(investment)

            # Verify that decisions are consistent with independent evaluation
            for i, (eval_date, should_invest) in enumerate(decisions):
                # Check if there was a recent investment before this date
                # Look at previous decisions where investment was actually made
                # Use inclusive 28-day constraint: investment within 27 days blocks new investment
                recent_investment_exists = any(
                    (eval_date - prev_date).days < 28 and prev_date < eval_date
                    for prev_date, prev_decision in decisions[:i]
                    if prev_decision
                )

                trigger_met = yesterday_price <= trigger_price
                expected_decision = trigger_met and not recent_investment_exists

                assert should_invest == expected_decision, (
                    f"Day {eval_date}: Decision should be independent and consistent with conditions. "
                    f"trigger_met={trigger_met}, recent_investment_exists={recent_investment_exists}, "
                    f"should_invest={should_invest}, expected={expected_decision}"
                )

    @given(
        base_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        price_above_trigger=st.floats(min_value=0.01, max_value=0.20),  # 1-20% above trigger
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
    )
    def test_no_investment_when_trigger_not_met(
        self, base_price: float, price_above_trigger: float, evaluation_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any yesterday price that is above the trigger price, no investment should
        be made regardless of other conditions.

        Validates: Requirements 4.1
        """
        # Skip NaN and infinite values
        assume(
            base_price == base_price and base_price != float("inf") and base_price != float("-inf")
        )
        assume(
            price_above_trigger == price_above_trigger
            and price_above_trigger != float("inf")
            and price_above_trigger != float("-inf")
        )

        # Create prices where yesterday_price > trigger_price
        trigger_price = base_price
        yesterday_price = base_price * (1 + price_above_trigger)  # Above trigger

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Test with no recent investments (should still not invest due to trigger)
            should_invest_no_recent = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )
            assert (
                not should_invest_no_recent
            ), f"Should not invest when yesterday_price ({yesterday_price}) > trigger_price ({trigger_price})"

            # Test with recent investments (should still not invest due to trigger)
            recent_investment = Investment(
                date=evaluation_date - timedelta(days=10),
                ticker="SPY",
                price=150.0,
                amount=2000.0,
                shares=13.33,
            )
            investment_tracker.add_investment(recent_investment)

            should_invest_with_recent = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )
            assert (
                not should_invest_with_recent
            ), f"Should not invest when trigger not met, regardless of recent investments"

    @given(
        base_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        price_below_trigger=st.floats(min_value=0.01, max_value=0.20),  # 1-20% below trigger
        evaluation_date=st.dates(min_value=date(2023, 2, 1), max_value=date(2023, 12, 31)),
        days_since_investment=st.integers(min_value=1, max_value=27),  # Within 28 days
    )
    def test_no_investment_when_recent_investment_exists(
        self,
        base_price: float,
        price_below_trigger: float,
        evaluation_date: date,
        days_since_investment: int,
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any evaluation where a recent investment exists within 28 days, no investment
        should be made even if the trigger condition is met.

        Validates: Requirements 4.2, 4.3
        """
        # Skip NaN and infinite values
        assume(
            base_price == base_price and base_price != float("inf") and base_price != float("-inf")
        )
        assume(
            price_below_trigger == price_below_trigger
            and price_below_trigger != float("inf")
            and price_below_trigger != float("-inf")
        )

        # Create prices where yesterday_price <= trigger_price
        trigger_price = base_price
        yesterday_price = base_price * (1 - price_below_trigger)  # Below trigger

        # Ensure we have enough days for the recent investment
        assume((evaluation_date - date(2023, 1, 1)).days > days_since_investment)

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            investment_tracker = InvestmentTracker(data_dir=temp_dir)

            # Add recent investment within 28 days
            recent_investment_date = evaluation_date - timedelta(days=days_since_investment)
            recent_investment = Investment(
                date=recent_investment_date, ticker="SPY", price=150.0, amount=2000.0, shares=13.33
            )
            investment_tracker.add_investment(recent_investment)

            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Should not invest due to recent investment, even though trigger is met
            should_invest = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )
            assert not should_invest, (
                f"Should not invest when recent investment exists {days_since_investment} days ago "
                f"(within 28 days), even though trigger is met"
            )

    @given(
        base_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        price_below_trigger=st.floats(min_value=0.01, max_value=0.20),  # 1-20% below trigger
        evaluation_date=st.dates(min_value=date(2023, 3, 1), max_value=date(2023, 12, 31)),
        days_since_investment=st.integers(min_value=29, max_value=60),  # Outside 28 days
    )
    def test_investment_when_both_conditions_met(
        self,
        base_price: float,
        price_below_trigger: float,
        evaluation_date: date,
        days_since_investment: int,
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any evaluation where the trigger condition is met AND no recent investment
        exists within 28 days, an investment should be made.

        Validates: Requirements 4.1, 4.2, 4.3
        """
        # Skip NaN and infinite values
        assume(
            base_price == base_price and base_price != float("inf") and base_price != float("-inf")
        )
        assume(
            price_below_trigger == price_below_trigger
            and price_below_trigger != float("inf")
            and price_below_trigger != float("-inf")
        )

        # Create prices where yesterday_price <= trigger_price
        trigger_price = base_price
        yesterday_price = base_price * (1 - price_below_trigger)  # Below trigger

        # Ensure we have enough days for the old investment
        assume((evaluation_date - date(2023, 1, 1)).days > days_since_investment)

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            investment_tracker = InvestmentTracker(data_dir=temp_dir)

            # Add old investment outside 28 days
            old_investment_date = evaluation_date - timedelta(days=days_since_investment)
            old_investment = Investment(
                date=old_investment_date, ticker="SPY", price=150.0, amount=2000.0, shares=13.33
            )
            investment_tracker.add_investment(old_investment)

            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Should invest because both conditions are met
            should_invest = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )
            assert should_invest, (
                f"Should invest when trigger is met (yesterday_price {yesterday_price} <= trigger_price {trigger_price}) "
                f"and no recent investment exists (last investment {days_since_investment} days ago)"
            )

    @given(
        yesterday_price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
        trigger_price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
    )
    def test_investment_decision_with_no_investment_history(
        self, yesterday_price: float, trigger_price: float, evaluation_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any evaluation with no investment history, the decision should be based
        solely on whether the trigger condition is met.

        Validates: Requirements 4.1, 4.2
        """
        # Skip NaN and infinite values
        assume(
            yesterday_price == yesterday_price
            and yesterday_price != float("inf")
            and yesterday_price != float("-inf")
        )
        assume(
            trigger_price == trigger_price
            and trigger_price != float("inf")
            and trigger_price != float("-inf")
        )

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            # Empty investment tracker (no history)
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Test investment decision
            should_invest = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )

            # With no investment history, decision should be based only on trigger condition
            trigger_met = yesterday_price <= trigger_price
            assert should_invest == trigger_met, (
                f"With no investment history, should invest if and only if trigger is met: "
                f"should_invest={should_invest}, trigger_met={trigger_met}"
            )

    @given(
        trigger_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
    )
    def test_investment_decision_at_trigger_boundary(
        self, trigger_price: float, evaluation_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 4: Investment Decision Logic Correctness

        For any evaluation where yesterday's price exactly equals the trigger price,
        an investment should be made (if no recent investment exists), since the
        condition is <= trigger price.

        Validates: Requirements 4.1
        """
        # Skip NaN and infinite values
        assume(
            trigger_price == trigger_price
            and trigger_price != float("inf")
            and trigger_price != float("-inf")
        )

        # Set yesterday_price exactly equal to trigger_price
        yesterday_price = trigger_price

        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30,
            )

            # Empty investment tracker (no recent investments)
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)

            # Should invest when yesterday_price == trigger_price
            should_invest = strategy_system.should_invest(
                yesterday_price, trigger_price, evaluation_date
            )
            assert (
                should_invest
            ), f"Should invest when yesterday_price equals trigger_price ({trigger_price})"
