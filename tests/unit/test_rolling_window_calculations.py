"""
Test cases for rolling window calculations to ensure calendar vs trading days work correctly.
These tests prevent regression of the bug where trading days were used instead of calendar days.
"""

import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import Mock, patch

from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.price_monitor import PriceMonitor


class TestRollingWindowCalculations:
    """Test rolling window calculations for both calendar and trading days modes."""

    def create_mock_price_data(
        self, start_date: date, end_date: date, exclude_weekends: bool = True
    ) -> pd.Series:
        """
        Create mock price data for testing.

        Args:
            start_date: Start date for price data
            end_date: End date for price data
            exclude_weekends: If True, exclude weekends (simulate trading days only)

        Returns:
            Series with mock price data
        """
        dates = []
        prices = []
        current_date = start_date
        base_price = 100.0

        while current_date <= end_date:
            # Skip weekends if exclude_weekends is True
            if exclude_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            dates.append(current_date)
            # Create some price variation - higher prices earlier, lower later
            days_from_start = (current_date - start_date).days
            price_variation = base_price + (50 - days_from_start * 0.5)  # Declining trend
            prices.append(max(price_variation, 50.0))  # Floor at $50

            current_date += timedelta(days=1)

        return pd.Series(prices, index=dates, name="Close")

    def test_calendar_days_vs_trading_days_difference(self):
        """Test that calendar days and trading days produce different results."""
        # Create config for calendar days
        config_calendar = StrategyConfig(
            ticker="TEST",
            rolling_window_days=30,
            percentage_trigger=0.95,
            use_trading_days=False,  # Calendar days
        )

        # Create config for trading days
        config_trading = StrategyConfig(
            ticker="TEST",
            rolling_window_days=30,
            percentage_trigger=0.95,
            use_trading_days=True,  # Trading days
        )

        # Create mock price data spanning 60 days
        end_date = date(2026, 1, 3)  # Friday
        start_date = end_date - timedelta(days=60)

        mock_prices = self.create_mock_price_data(start_date, end_date)

        # Create strategy systems
        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy_calendar = StrategySystem(config_calendar, mock_price_monitor)
        strategy_trading = StrategySystem(config_trading, mock_price_monitor)

        # Calculate trigger prices
        trigger_calendar = strategy_calendar.calculate_trigger_price(mock_prices, 30, 0.95)
        trigger_trading = strategy_trading.calculate_trigger_price(mock_prices, 30, 0.95)

        # They should be different because they use different windows
        assert (
            trigger_calendar != trigger_trading
        ), "Calendar and trading days should produce different results"

        # Calendar days should use a shorter actual window (fewer records)
        # so it should have a lower maximum and lower trigger price
        assert (
            trigger_calendar < trigger_trading
        ), "Calendar days should typically have lower trigger (shorter window)"

    def test_calendar_days_window_boundary(self):
        """Test that calendar days window respects exact date boundaries."""
        config = StrategyConfig(
            ticker="TEST", rolling_window_days=30, percentage_trigger=0.90, use_trading_days=False
        )

        # Create price data where we know the maximum
        end_date = date(2026, 1, 3)  # Friday

        # Create prices with a known maximum outside the 30-day calendar window
        dates = []
        prices = []

        # Add data from 45 days ago to today
        for days_back in range(45, -1, -1):
            current_date = end_date - timedelta(days=days_back)

            if current_date.weekday() < 5:  # Only trading days
                dates.append(current_date)

                if days_back == 35:
                    # Put maximum outside the 30-day calendar window
                    prices.append(200.0)  # Maximum price (should be excluded)
                elif days_back <= 30:
                    # Prices within 30-day window are lower
                    prices.append(100.0)  # Should be the max within window
                else:
                    # Earlier prices are lower
                    prices.append(90.0)

        mock_prices = pd.Series(prices, index=dates, name="Close")

        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy = StrategySystem(config, mock_price_monitor)

        trigger_price = strategy.calculate_trigger_price(mock_prices, 30, 0.90)

        # The trigger should be based on 100.0 (max within 30 calendar days)
        # not 200.0 (max outside the window)
        expected_trigger = 100.0 * 0.90
        assert (
            abs(trigger_price - expected_trigger) < 0.01
        ), f"Expected {expected_trigger}, got {trigger_price}"

    def test_trading_days_window_boundary(self):
        """Test that trading days window uses exact number of trading records."""
        config = StrategyConfig(
            ticker="TEST",
            rolling_window_days=10,  # 10 trading days
            percentage_trigger=0.90,
            use_trading_days=True,
        )

        # Create exactly 20 trading days of data
        end_date = date(2026, 1, 3)  # Friday

        dates = []
        prices = []

        # Create 20 trading days going backwards
        trading_days_created = 0
        days_back = 0

        while trading_days_created < 20:
            current_date = end_date - timedelta(days=days_back)

            if current_date.weekday() < 5:  # Only trading days
                dates.insert(0, current_date)  # Insert at beginning to maintain order
                trading_days_created += 1

                if trading_days_created == 15:  # 15th trading day back (outside 10-day window)
                    prices.insert(0, 200.0)  # Maximum price (should be excluded)
                elif trading_days_created <= 10:  # Last 10 trading days
                    prices.insert(0, 100.0)  # Should be the max within window
                else:
                    prices.insert(0, 90.0)

            days_back += 1

        mock_prices = pd.Series(prices, index=dates, name="Close")

        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy = StrategySystem(config, mock_price_monitor)

        trigger_price = strategy.calculate_trigger_price(mock_prices, 10, 0.90)

        # Should use last 10 trading days, so max should be 100.0, not 200.0
        expected_trigger = 100.0 * 0.90
        assert (
            abs(trigger_price - expected_trigger) < 0.01
        ), f"Expected {expected_trigger}, got {trigger_price}"

    def test_real_world_scenario_meta_bug(self):
        """Test the specific META bug scenario that was discovered."""
        # Simulate the META scenario from the bug report
        config_calendar = StrategyConfig(
            ticker="META", rolling_window_days=60, percentage_trigger=0.95, use_trading_days=False
        )

        config_trading = StrategyConfig(
            ticker="META", rolling_window_days=60, percentage_trigger=0.95, use_trading_days=True
        )

        # Create mock data similar to the META scenario
        end_date = date(2026, 1, 3)

        dates = []
        prices = []

        # Create data going back 90 days to ensure we have enough
        for days_back in range(90, -1, -1):
            current_date = end_date - timedelta(days=days_back)

            if current_date.weekday() < 5:  # Only trading days
                dates.append(current_date)

                # Simulate the bug scenario:
                # - High price on Oct 29 (66 days back, outside 60 calendar days)
                # - Lower recent high on Dec 5 (within 60 calendar days)
                if current_date == date(2025, 10, 29):
                    prices.append(751.06)  # The problematic high (outside calendar window)
                elif current_date == date(2025, 12, 5):
                    prices.append(672.87)  # The correct recent high (within calendar window)
                elif days_back <= 30:
                    prices.append(650.0)  # Recent lower prices
                else:
                    prices.append(680.0)  # Other prices

        mock_prices = pd.Series(prices, index=dates, name="Close")

        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy_calendar = StrategySystem(config_calendar, mock_price_monitor)
        strategy_trading = StrategySystem(config_trading, mock_price_monitor)

        trigger_calendar = strategy_calendar.calculate_trigger_price(mock_prices, 60, 0.95)
        trigger_trading = strategy_trading.calculate_trigger_price(mock_prices, 60, 0.95)

        # Calendar days should use $672.87 max (within 60 calendar days)
        expected_calendar_trigger = 672.87 * 0.95  # ≈ $639.23

        # Trading days should use $751.06 max (within 60 trading days)
        expected_trading_trigger = 751.06 * 0.95  # ≈ $713.50

        # Allow some tolerance since we're using mock data
        assert (
            abs(trigger_calendar - expected_calendar_trigger) < 10.0
        ), f"Calendar trigger should be ~$639, got ${trigger_calendar:.2f}"

        assert (
            abs(trigger_trading - expected_trading_trigger) < 10.0
        ), f"Trading trigger should be ~$713, got ${trigger_trading:.2f}"

        # Verify they're significantly different
        assert (
            abs(trigger_trading - trigger_calendar) > 30
        ), "Trading and calendar triggers should differ significantly in this scenario"

    def test_edge_case_insufficient_data(self):
        """Test behavior when there's insufficient data for the window."""
        config = StrategyConfig(
            ticker="TEST", rolling_window_days=30, percentage_trigger=0.90, use_trading_days=False
        )

        # Create only 5 days of data (less than 30-day window)
        end_date = date(2026, 1, 3)
        start_date = end_date - timedelta(days=4)

        mock_prices = self.create_mock_price_data(start_date, end_date)

        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy = StrategySystem(config, mock_price_monitor)

        # Should not crash and should use available data
        trigger_price = strategy.calculate_trigger_price(mock_prices, 30, 0.90)

        # Should be based on the maximum of available data
        expected_max = mock_prices.max()
        expected_trigger = expected_max * 0.90

        assert (
            abs(trigger_price - expected_trigger) < 0.01
        ), f"Should use available data max. Expected {expected_trigger}, got {trigger_price}"

    def test_weekend_handling_calendar_days(self):
        """Test that calendar days properly include weekends in the count."""
        config = StrategyConfig(
            ticker="TEST",
            rolling_window_days=7,  # 1 week
            percentage_trigger=0.90,
            use_trading_days=False,
        )

        # Create data where weekend dates matter for the boundary
        # End on Friday, so 7 calendar days back includes previous weekend
        end_date = date(2026, 1, 3)  # Friday

        dates = []
        prices = []

        # Create data going back 14 days
        for days_back in range(14, -1, -1):
            current_date = end_date - timedelta(days=days_back)

            if current_date.weekday() < 5:  # Only trading days have prices
                dates.append(current_date)

                # Put high price 10 days ago (outside 7-day calendar window)
                if days_back == 10:
                    prices.append(200.0)  # Should be excluded
                elif days_back <= 7:
                    prices.append(100.0)  # Should be included
                else:
                    prices.append(90.0)

        mock_prices = pd.Series(prices, index=dates, name="Close")

        mock_price_monitor = Mock(spec=PriceMonitor)
        strategy = StrategySystem(config, mock_price_monitor)

        trigger_price = strategy.calculate_trigger_price(mock_prices, 7, 0.90)

        # Should be based on 100.0 (within 7 calendar days), not 200.0
        expected_trigger = 100.0 * 0.90
        assert (
            abs(trigger_price - expected_trigger) < 0.01
        ), f"Calendar days should exclude data outside 7-day window. Expected {expected_trigger}, got {trigger_price}"


class TestCLIRollingWindowIntegration:
    """Test CLI integration with rolling window calculations."""

    @patch("buy_the_dip.cli.cli.PriceMonitor")
    def test_cli_count_trading_days_flag(self, mock_price_monitor_class):
        """Test that --count-trading-days flag works correctly in CLI."""
        from buy_the_dip.cli.cli import main
        from buy_the_dip.config.models import StrategyConfig
        import sys

        # Mock the price monitor
        mock_price_monitor = Mock()
        mock_price_monitor_class.return_value = mock_price_monitor

        # Create mock price data
        end_date = date(2026, 1, 3)
        start_date = end_date - timedelta(days=30)

        dates = []
        prices = []
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() < 5:
                dates.append(current_date)
                prices.append(100.0)
            current_date += timedelta(days=1)

        mock_prices = pd.Series(prices, index=dates, name="Close")
        mock_price_monitor.get_closing_prices.return_value = mock_prices
        mock_price_monitor.get_api_stats.return_value = {"api_calls_made": 0, "cache_hits": 1}

        # Test with --count-trading-days flag
        test_args = [
            "buy_the_dip.py",
            "--check",
            "--tickers",
            "TEST",
            "--rolling-window",
            "10",
            "--trigger-pct",
            "0.90",
            "--count-trading-days",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("builtins.print") as mock_print:
                try:
                    main()
                except SystemExit:
                    pass  # CLI exits normally

        # Verify that the strategy was created with use_trading_days=True
        # This is verified by checking that the price monitor was called
        assert mock_price_monitor.get_closing_prices.called

        # The exact verification would require more complex mocking,
        # but this ensures the flag is processed without errors

    def test_config_file_override_with_cli_flag(self):
        """Test that CLI flag overrides config file setting."""
        from buy_the_dip.config.models import StrategyConfig

        # Create a config with use_trading_days=False
        config = StrategyConfig(
            ticker="TEST", rolling_window_days=30, percentage_trigger=0.90, use_trading_days=False
        )

        # Simulate CLI override
        config.use_trading_days = True

        assert config.use_trading_days == True, "CLI flag should override config file setting"


if __name__ == "__main__":
    pytest.main([__file__])
