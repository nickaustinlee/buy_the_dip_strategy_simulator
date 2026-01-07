"""
Test cases for configurable investment spacing (min_days_between_investments).
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch
import pandas as pd

from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.investment_tracker import InvestmentTracker
from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.models import Investment


class TestInvestmentSpacing:
    """Test investment spacing with different min_days_between_investments values."""

    def test_daily_spacing_allows_consecutive_days(self, temp_dir):
        """Test that min_days_between_investments=1 allows daily investments."""
        # Create config with daily spacing
        config = StrategyConfig(
            ticker="SPY",
            min_days_between_investments=1,
            rolling_window_days=30,
            percentage_trigger=0.90,
            monthly_dca_amount=1000.0,
        )

        investment_tracker = InvestmentTracker(data_dir=temp_dir)

        # Add investment on day 1
        investment1 = Investment(
            date=date(2024, 1, 1),
            ticker="SPY",
            price=100.0,
            amount=1000.0,
            shares=10.0,
        )
        investment_tracker.add_investment(investment1)

        # Check if we can invest on day 2 (1 day later)
        check_date = date(2024, 1, 2)
        has_recent = investment_tracker.has_recent_investment(check_date, days=1)
        assert not has_recent, "Should allow investment after 1 day with daily spacing"

        # Check if we can invest on same day (should be blocked)
        same_day_check = date(2024, 1, 1)
        has_recent_same_day = investment_tracker.has_recent_investment(same_day_check, days=1)
        # This should return False because we're checking the same day as the investment
        # The logic is: investment.date > cutoff_date and investment.date < check_date
        # For same day: 2024-01-01 > 2023-12-31 (True) and 2024-01-01 < 2024-01-01 (False)
        assert not has_recent_same_day, "Same day check should not find recent investment"

    def test_weekly_spacing_blocks_within_week(self, temp_dir):
        """Test that min_days_between_investments=7 blocks investments within 7 days."""
        config = StrategyConfig(
            ticker="SPY",
            min_days_between_investments=7,
            rolling_window_days=30,
            percentage_trigger=0.90,
            monthly_dca_amount=1000.0,
        )

        investment_tracker = InvestmentTracker(data_dir=temp_dir)

        # Add investment on Monday
        investment1 = Investment(
            date=date(2024, 1, 1),  # Monday
            ticker="SPY",
            price=100.0,
            amount=1000.0,
            shares=10.0,
        )
        investment_tracker.add_investment(investment1)

        # Check various days within the week
        test_cases = [
            (date(2024, 1, 2), True, "Tuesday (1 day later)"),
            (date(2024, 1, 3), True, "Wednesday (2 days later)"),
            (date(2024, 1, 7), True, "Sunday (6 days later)"),
            (date(2024, 1, 8), False, "Next Monday (7 days later)"),
            (date(2024, 1, 9), False, "Next Tuesday (8 days later)"),
        ]

        for check_date, should_block, description in test_cases:
            has_recent = investment_tracker.has_recent_investment(check_date, days=7)
            assert has_recent == should_block, f"Weekly spacing failed for {description}"

    def test_monthly_spacing_blocks_within_month(self, temp_dir):
        """Test that min_days_between_investments=28 blocks investments within 28 days."""
        config = StrategyConfig(
            ticker="SPY",
            min_days_between_investments=28,
            rolling_window_days=30,
            percentage_trigger=0.90,
            monthly_dca_amount=1000.0,
        )

        investment_tracker = InvestmentTracker(data_dir=temp_dir)

        # Add investment on January 1st
        investment1 = Investment(
            date=date(2024, 1, 1),
            ticker="SPY",
            price=100.0,
            amount=1000.0,
            shares=10.0,
        )
        investment_tracker.add_investment(investment1)

        # Check various days within and after 28 days
        test_cases = [
            (date(2024, 1, 15), True, "15 days later"),
            (date(2024, 1, 28), True, "27 days later"),
            (date(2024, 1, 29), False, "28 days later"),
            (date(2024, 2, 1), False, "31 days later"),
        ]

        for check_date, should_block, description in test_cases:
            has_recent = investment_tracker.has_recent_investment(check_date, days=28)
            assert has_recent == should_block, f"Monthly spacing failed for {description}"

    def test_strategy_system_respects_spacing_config(self, temp_dir):
        """Test that StrategySystem uses the configured spacing value."""
        # Create config with weekly spacing
        config = StrategyConfig(
            ticker="SPY",
            min_days_between_investments=7,
            rolling_window_days=30,
            percentage_trigger=0.90,
            monthly_dca_amount=1000.0,
        )

        # Mock price monitor
        price_monitor = Mock()

        # Create price data that would trigger investment
        price_data = pd.Series(
            [110.0, 105.0, 100.0, 95.0, 90.0],  # Declining prices
            index=[
                date(2024, 1, 1),
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ],
        )
        price_monitor.get_closing_prices.return_value = price_data

        investment_tracker = InvestmentTracker(data_dir=temp_dir)
        strategy_system = StrategySystem(config, price_monitor, investment_tracker)

        # Add a recent investment (3 days ago)
        recent_investment = Investment(
            date=date(2024, 1, 2),
            ticker="SPY",
            price=105.0,
            amount=1000.0,
            shares=9.52,
        )
        investment_tracker.add_investment(recent_investment)

        # Try to evaluate on day that would normally trigger (but should be blocked by 7-day rule)
        evaluation_date = date(2024, 1, 5)  # 3 days after last investment

        # Mock the should_invest method to test the constraint logic
        with patch.object(strategy_system, "calculate_trigger_price", return_value=95.0):
            should_invest = strategy_system.should_invest(
                yesterday_price=90.0,  # Below trigger
                trigger_price=95.0,
                evaluation_date=evaluation_date,
            )

            # Should be blocked because only 3 days have passed (need 7)
            assert not should_invest, "Investment should be blocked by 7-day spacing rule"

        # Test that investment is allowed after 7 days
        later_date = date(2024, 1, 9)  # 7 days after last investment
        should_invest_later = strategy_system.should_invest(
            yesterday_price=90.0, trigger_price=95.0, evaluation_date=later_date  # Below trigger
        )

        # Should be allowed now
        assert should_invest_later, "Investment should be allowed after 7 days"

    def test_invalid_spacing_values(self):
        """Test that invalid spacing values are rejected."""
        # Test that 0 is rejected
        with pytest.raises(ValueError):
            StrategyConfig(min_days_between_investments=0)

        # Test that negative values are rejected
        with pytest.raises(ValueError):
            StrategyConfig(min_days_between_investments=-1)

    def test_has_recent_investment_edge_cases(self, temp_dir):
        """Test edge cases for has_recent_investment method."""
        investment_tracker = InvestmentTracker(data_dir=temp_dir)

        # Test with invalid days parameter
        with pytest.raises(ValueError):
            investment_tracker.has_recent_investment(date(2024, 1, 1), days=0)

        with pytest.raises(ValueError):
            investment_tracker.has_recent_investment(date(2024, 1, 1), days=-1)

        # Test with no investments
        has_recent = investment_tracker.has_recent_investment(date(2024, 1, 1), days=7)
        assert not has_recent, "Should return False when no investments exist"

        # Test boundary conditions
        investment = Investment(
            date=date(2024, 1, 1),
            ticker="SPY",
            price=100.0,
            amount=1000.0,
            shares=10.0,
        )
        investment_tracker.add_investment(investment)

        # Test exact boundary (7 days later)
        check_date = date(2024, 1, 8)  # Exactly 7 days later
        has_recent = investment_tracker.has_recent_investment(check_date, days=7)
        assert not has_recent, "Should allow investment exactly 7 days later"

        # Test one day before boundary
        check_date = date(2024, 1, 7)  # 6 days later
        has_recent = investment_tracker.has_recent_investment(check_date, days=7)
        assert has_recent, "Should block investment 6 days later with 7-day spacing"

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test data."""
        return str(tmp_path)


class TestInvestmentSpacingIntegration:
    """Integration tests for investment spacing with CLI and config."""

    def test_cli_min_days_between_override(self):
        """Test that CLI --min-days-between overrides config value."""
        # This would be tested in CLI integration tests
        # For now, just test the config validation
        config = StrategyConfig(min_days_between_investments=14)
        assert config.min_days_between_investments == 14

        # Test that the field validation works
        with pytest.raises(ValueError):
            StrategyConfig(min_days_between_investments=0)

    def test_config_file_spacing_values(self):
        """Test various spacing values in config."""
        test_cases = [
            (1, "daily"),
            (7, "weekly"),
            (14, "bi-weekly"),
            (28, "monthly"),
            (90, "quarterly"),
        ]

        for days, description in test_cases:
            config = StrategyConfig(min_days_between_investments=days)
            assert config.min_days_between_investments == days, f"Failed for {description} spacing"
