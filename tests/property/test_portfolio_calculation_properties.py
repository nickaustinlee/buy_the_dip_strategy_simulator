"""
Property-based tests for portfolio calculation functionality.
"""

from datetime import date
from typing import List

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.models import Investment, PortfolioMetrics
from buy_the_dip.investment_tracker import InvestmentTracker


class TestPortfolioCalculationProperties:
    """Property-based tests for portfolio calculations."""

    @given(
        investments=st.lists(
            st.builds(
                Investment,
                date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)),
                ticker=st.sampled_from(["SPY", "AAPL", "MSFT", "GOOGL", "TSLA"]),
                price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True),
                amount=st.floats(min_value=100.0, max_value=10000.0, exclude_min=True),
                shares=st.floats(min_value=0.1, max_value=100.0, exclude_min=True),
            ).map(
                lambda inv: Investment(
                    date=inv.date,
                    ticker=inv.ticker,
                    price=inv.price,
                    amount=inv.amount,
                    shares=inv.amount / inv.price,  # Ensure consistent shares calculation
                )
            ),
            min_size=0,
            max_size=50,
        ),
        current_price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True),
    )
    def test_portfolio_calculation_correctness(
        self, investments: List[Investment], current_price: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any set of investments and current price, the calculated metrics should
        accurately reflect total invested (sum of amounts), total shares (sum of shares),
        current value (total_shares * current_price), total return (current_value - total_invested),
        and percentage return (total_return / total_invested).

        Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
        """
        # Create tracker and add investments
        tracker = InvestmentTracker()
        for investment in investments:
            tracker.add_investment(investment)

        # Calculate portfolio metrics
        metrics = tracker.calculate_portfolio_metrics(current_price)

        # Verify calculations are correct
        if not investments:
            # Empty portfolio case
            assert metrics.total_invested == 0.0, "Empty portfolio should have zero total invested"
            assert metrics.total_shares == 0.0, "Empty portfolio should have zero total shares"
            assert metrics.current_value == 0.0, "Empty portfolio should have zero current value"
            assert metrics.total_return == 0.0, "Empty portfolio should have zero total return"
            assert (
                metrics.percentage_return == 0.0
            ), "Empty portfolio should have zero percentage return"
        else:
            # Non-empty portfolio case
            expected_total_invested = sum(inv.amount for inv in investments)
            expected_total_shares = sum(inv.shares for inv in investments)
            expected_current_value = expected_total_shares * current_price
            expected_total_return = expected_current_value - expected_total_invested
            expected_percentage_return = expected_total_return / expected_total_invested

            # Verify total invested (sum of amounts)
            assert (
                abs(metrics.total_invested - expected_total_invested) < 0.01
            ), f"Total invested mismatch: {metrics.total_invested} != {expected_total_invested}"

            # Verify total shares (sum of shares)
            assert (
                abs(metrics.total_shares - expected_total_shares) < 0.0001
            ), f"Total shares mismatch: {metrics.total_shares} != {expected_total_shares}"

            # Verify current value (total_shares * current_price)
            assert (
                abs(metrics.current_value - expected_current_value) < 0.01
            ), f"Current value mismatch: {metrics.current_value} != {expected_current_value}"

            # Verify total return (current_value - total_invested)
            assert (
                abs(metrics.total_return - expected_total_return) < 0.01
            ), f"Total return mismatch: {metrics.total_return} != {expected_total_return}"

            # Verify percentage return (total_return / total_invested * 100)
            assert (
                abs(metrics.percentage_return - expected_percentage_return) < 0.01
            ), f"Percentage return mismatch: {metrics.percentage_return} != {expected_percentage_return}"

    @given(
        investment_data=st.lists(
            st.tuples(
                st.floats(min_value=100.0, max_value=5000.0, exclude_min=True),  # amount
                st.floats(min_value=10.0, max_value=500.0, exclude_min=True),  # price
            ),
            min_size=1,
            max_size=20,
        ),
        current_price=st.floats(min_value=10.0, max_value=500.0, exclude_min=True),
    )
    def test_portfolio_calculation_with_consistent_shares(
        self, investment_data: List[tuple], current_price: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any set of investments where shares are calculated consistently (amount/price),
        the portfolio calculations should be mathematically correct.

        Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
        """
        # Create investments with consistent shares calculation
        investments = []
        for i, (amount, price) in enumerate(investment_data):
            shares = amount / price  # Ensure consistent calculation
            investment = Investment(
                date=date(2023, 1, 1 + i), ticker="SPY", price=price, amount=amount, shares=shares
            )
            investments.append(investment)

        # Create tracker and add investments
        tracker = InvestmentTracker()
        for investment in investments:
            tracker.add_investment(investment)

        # Calculate metrics
        metrics = tracker.calculate_portfolio_metrics(current_price)

        # Verify mathematical relationships
        expected_total_invested = sum(amount for amount, _ in investment_data)
        expected_total_shares = sum(amount / price for amount, price in investment_data)
        expected_current_value = expected_total_shares * current_price
        expected_total_return = expected_current_value - expected_total_invested
        expected_percentage_return = expected_total_return / expected_total_invested

        # All calculations should be mathematically consistent
        assert abs(metrics.total_invested - expected_total_invested) < 0.01
        assert abs(metrics.total_shares - expected_total_shares) < 0.0001
        assert abs(metrics.current_value - expected_current_value) < 0.01
        assert abs(metrics.total_return - expected_total_return) < 0.01
        assert abs(metrics.percentage_return - expected_percentage_return) < 0.01

        # Verify internal consistency of calculated metrics
        calculated_current_value = metrics.total_shares * current_price
        assert (
            abs(metrics.current_value - calculated_current_value) < 0.01
        ), "Current value should equal total_shares * current_price"

        calculated_total_return = metrics.current_value - metrics.total_invested
        assert (
            abs(metrics.total_return - calculated_total_return) < 0.01
        ), "Total return should equal current_value - total_invested"

        if metrics.total_invested > 0:
            calculated_percentage_return = metrics.total_return / metrics.total_invested
            assert (
                abs(metrics.percentage_return - calculated_percentage_return) < 0.01
            ), "Percentage return should equal (total_return / total_invested)"

    @given(
        base_investment=st.builds(
            Investment,
            date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            ticker=st.just("SPY"),
            price=st.floats(min_value=100.0, max_value=300.0, exclude_min=True),
            amount=st.floats(min_value=1000.0, max_value=3000.0, exclude_min=True),
            shares=st.floats(min_value=3.0, max_value=30.0, exclude_min=True),
        ).map(
            lambda inv: Investment(
                date=inv.date,
                ticker=inv.ticker,
                price=inv.price,
                amount=inv.amount,
                shares=inv.amount / inv.price,  # Ensure consistent shares calculation
            )
        ),
        price_multiplier=st.floats(min_value=0.5, max_value=2.0, exclude_min=True),
    )
    def test_portfolio_value_scales_with_price(
        self, base_investment: Investment, price_multiplier: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any portfolio, when the current price changes by a factor, the current value
        should change by the same factor, while total invested remains constant.

        Validates: Requirements 8.2, 8.3
        """
        tracker = InvestmentTracker()
        tracker.add_investment(base_investment)

        # Calculate metrics at base price
        base_price = 200.0
        base_metrics = tracker.calculate_portfolio_metrics(base_price)

        # Calculate metrics at scaled price
        scaled_price = base_price * price_multiplier
        scaled_metrics = tracker.calculate_portfolio_metrics(scaled_price)

        # Total invested should remain constant
        assert (
            abs(scaled_metrics.total_invested - base_metrics.total_invested) < 0.01
        ), "Total invested should not change with price changes"

        # Total shares should remain constant
        assert (
            abs(scaled_metrics.total_shares - base_metrics.total_shares) < 0.0001
        ), "Total shares should not change with price changes"

        # Current value should scale with price
        expected_scaled_value = base_metrics.current_value * price_multiplier
        assert (
            abs(scaled_metrics.current_value - expected_scaled_value) < 0.01
        ), f"Current value should scale with price: {scaled_metrics.current_value} != {expected_scaled_value}"

        # Total return should scale accordingly
        expected_scaled_return = scaled_metrics.current_value - scaled_metrics.total_invested
        assert (
            abs(scaled_metrics.total_return - expected_scaled_return) < 0.01
        ), "Total return should be calculated correctly with scaled price"

    @given(
        investments=st.lists(
            st.builds(
                Investment,
                date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
                ticker=st.just("SPY"),
                price=st.floats(min_value=50.0, max_value=200.0, exclude_min=True),
                amount=st.floats(min_value=500.0, max_value=2000.0, exclude_min=True),
                shares=st.floats(min_value=2.5, max_value=40.0, exclude_min=True),
            ).map(
                lambda inv: Investment(
                    date=inv.date,
                    ticker=inv.ticker,
                    price=inv.price,
                    amount=inv.amount,
                    shares=inv.amount / inv.price,  # Ensure consistent shares calculation
                )
            ),
            min_size=2,
            max_size=10,
        ),
        current_price=st.floats(min_value=50.0, max_value=200.0, exclude_min=True),
    )
    def test_portfolio_metrics_are_additive(
        self, investments: List[Investment], current_price: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any set of investments, the portfolio metrics should be additive -
        calculating metrics for the full set should equal the sum of metrics
        for individual investments.

        Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
        """
        # Calculate metrics for full portfolio
        full_tracker = InvestmentTracker()
        for investment in investments:
            full_tracker.add_investment(investment)
        full_metrics = full_tracker.calculate_portfolio_metrics(current_price)

        # Calculate metrics for individual investments and sum them
        total_invested_sum = 0.0
        total_shares_sum = 0.0
        current_value_sum = 0.0

        for investment in investments:
            individual_tracker = InvestmentTracker()
            individual_tracker.add_investment(investment)
            individual_metrics = individual_tracker.calculate_portfolio_metrics(current_price)

            total_invested_sum += individual_metrics.total_invested
            total_shares_sum += individual_metrics.total_shares
            current_value_sum += individual_metrics.current_value

        # Verify additivity
        assert (
            abs(full_metrics.total_invested - total_invested_sum) < 0.01
        ), "Total invested should be additive across investments"

        assert (
            abs(full_metrics.total_shares - total_shares_sum) < 0.0001
        ), "Total shares should be additive across investments"

        assert (
            abs(full_metrics.current_value - current_value_sum) < 0.01
        ), "Current value should be additive across investments"

        # Total return should also be additive
        expected_total_return = current_value_sum - total_invested_sum
        assert (
            abs(full_metrics.total_return - expected_total_return) < 0.01
        ), "Total return should be additive across investments"

    def test_portfolio_calculation_handles_zero_investment_correctly(self):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For a portfolio with no investments, all metrics should be zero and
        calculations should not raise errors.

        Validates: Requirements 8.6
        """
        tracker = InvestmentTracker()

        # Test with various current prices
        for current_price in [1.0, 100.0, 1000.0]:
            metrics = tracker.calculate_portfolio_metrics(current_price)

            assert metrics.total_invested == 0.0, "Empty portfolio should have zero total invested"
            assert metrics.total_shares == 0.0, "Empty portfolio should have zero total shares"
            assert metrics.current_value == 0.0, "Empty portfolio should have zero current value"
            assert metrics.total_return == 0.0, "Empty portfolio should have zero total return"
            assert (
                metrics.percentage_return == 0.0
            ), "Empty portfolio should have zero percentage return"

    @given(
        investment=st.builds(
            Investment,
            date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            ticker=st.just("SPY"),
            price=st.floats(min_value=100.0, max_value=300.0, exclude_min=True),
            amount=st.floats(min_value=1000.0, max_value=3000.0, exclude_min=True),
            shares=st.floats(min_value=3.0, max_value=30.0, exclude_min=True),
        ).map(
            lambda inv: Investment(
                date=inv.date,
                ticker=inv.ticker,
                price=inv.price,
                amount=inv.amount,
                shares=inv.amount / inv.price,  # Ensure consistent shares calculation
            )
        )
    )
    def test_portfolio_break_even_point(self, investment: Investment):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any investment, when the current price equals the average cost basis,
        the total return should be zero and percentage return should be zero.

        Validates: Requirements 8.4, 8.5
        """
        tracker = InvestmentTracker()
        tracker.add_investment(investment)

        # Calculate average cost basis (total invested / total shares)
        average_cost_basis = investment.amount / investment.shares

        # Calculate metrics at break-even price
        metrics = tracker.calculate_portfolio_metrics(average_cost_basis)

        # At break-even, total return should be zero (within floating point precision)
        assert (
            abs(metrics.total_return) < 0.01
        ), f"Total return should be zero at break-even price: {metrics.total_return}"

        # Percentage return should also be zero
        assert (
            abs(metrics.percentage_return) < 0.01
        ), f"Percentage return should be zero at break-even price: {metrics.percentage_return}"

        # Current value should equal total invested
        assert (
            abs(metrics.current_value - metrics.total_invested) < 0.01
        ), "Current value should equal total invested at break-even price"

    @given(
        investments=st.lists(
            st.builds(
                Investment,
                date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
                ticker=st.just("SPY"),
                price=st.floats(min_value=50.0, max_value=200.0, exclude_min=True),
                amount=st.floats(min_value=500.0, max_value=2000.0, exclude_min=True),
                shares=st.floats(min_value=2.5, max_value=40.0, exclude_min=True),
            ).map(
                lambda inv: Investment(
                    date=inv.date,
                    ticker=inv.ticker,
                    price=inv.price,
                    amount=inv.amount,
                    shares=inv.amount / inv.price,  # Ensure consistent shares calculation
                )
            ),
            min_size=1,
            max_size=15,
        )
    )
    def test_portfolio_average_cost_basis_calculation(self, investments: List[Investment]):
        """
        Feature: buy-the-dip-strategy, Property 7: Portfolio Calculation Correctness

        For any portfolio, the average cost basis (total_invested / total_shares)
        should be a weighted average of individual investment prices.

        Validates: Requirements 8.1, 8.2
        """
        tracker = InvestmentTracker()
        for investment in investments:
            tracker.add_investment(investment)

        # Calculate portfolio metrics (using arbitrary current price)
        metrics = tracker.calculate_portfolio_metrics(100.0)

        if metrics.total_shares > 0:
            # Calculate average cost basis
            average_cost_basis = metrics.total_invested / metrics.total_shares

            # Verify it's a reasonable weighted average
            min_price = min(inv.price for inv in investments)
            max_price = max(inv.price for inv in investments)

            # Average cost basis should be within the range of individual prices
            # (allowing for small floating point errors)
            assert (
                average_cost_basis >= min_price - 0.01
            ), f"Average cost basis {average_cost_basis} should be >= min price {min_price}"
            assert (
                average_cost_basis <= max_price + 0.01
            ), f"Average cost basis {average_cost_basis} should be <= max price {max_price}"

            # Verify the calculation is mathematically correct
            expected_weighted_average = sum(inv.amount for inv in investments) / sum(
                inv.shares for inv in investments
            )
            assert (
                abs(average_cost_basis - expected_weighted_average) < 0.01
            ), f"Average cost basis should equal total_invested / total_shares"
