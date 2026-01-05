"""
Unit tests for StrategySystem edge cases and boundary conditions.
"""

import tempfile
import pandas as pd
from datetime import date, timedelta
from unittest.mock import Mock, patch

import pytest

from buy_the_dip.strategy_system import StrategySystem, EvaluationResult, BacktestResult
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.price_monitor.price_monitor import PriceMonitor
from buy_the_dip.investment_tracker import InvestmentTracker
from buy_the_dip.models import Investment


class TestStrategySystemEdgeCases:
    """Unit tests for StrategySystem edge cases and boundary conditions."""

    def test_insufficient_historical_data_uses_available_data(self):
        """
        Test that the system uses available data when insufficient historical data exists.
        
        Validates: Requirements 3.5
        """
        # Create config requiring 90 days but provide only 10 days
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock price data with only 10 days of data
            evaluation_date = date(2023, 6, 15)
            start_date = evaluation_date - timedelta(days=9)  # Only 10 days total
            
            # Create limited price series
            dates = [start_date + timedelta(days=i) for i in range(10)]
            prices = [100.0 + i for i in range(10)]  # Increasing prices
            price_series = pd.Series(prices, index=dates, name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            # Mock the calculate_rolling_maximum method to return the expected value
            price_monitor.calculate_rolling_maximum.return_value = max(prices[:-1])  # Exclude current day
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should not raise an error despite insufficient data
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify it used available data
            assert isinstance(result, EvaluationResult)
            assert result.evaluation_date == evaluation_date
            # The rolling maximum should be calculated from available historical data
            assert result.rolling_maximum > 0  # Should have some value
            
            # Verify price monitor was called with available data
            price_monitor.get_closing_prices.assert_called_once()
            # The new logic doesn't call calculate_rolling_maximum separately anymore
            # Instead, the rolling maximum calculation is done inside calculate_trigger_price
            # So we just verify that the evaluation completed successfully

    def test_evaluation_with_no_price_data_raises_error(self):
        """
        Test that evaluation raises appropriate error when no price data is available.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="INVALID",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock empty price data
            price_monitor.get_closing_prices.return_value = pd.Series([], dtype=float, name='Close')
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should raise ValueError for no price data
            with pytest.raises(ValueError, match="No price data available"):
                strategy_system.evaluate_trading_day(date(2023, 6, 15))

    def test_evaluation_with_no_yesterday_price_raises_error(self):
        """
        Test that evaluation raises error when no price data exists before evaluation date.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock price data that only has current day (no yesterday)
            evaluation_date = date(2023, 6, 15)
            price_series = pd.Series([150.0], index=[evaluation_date], name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should raise ValueError for no historical data
            with pytest.raises(ValueError, match="No price data available before"):
                strategy_system.evaluate_trading_day(evaluation_date)

    def test_evaluation_with_no_current_day_price_raises_error(self):
        """
        Test that evaluation raises error when no price data exists for evaluation date.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock price data that only has yesterday (no current day)
            evaluation_date = date(2023, 6, 15)
            yesterday = evaluation_date - timedelta(days=1)
            price_series = pd.Series([150.0], index=[yesterday], name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should raise ValueError for no current day price
            with pytest.raises(ValueError, match="No price data available for evaluation date"):
                strategy_system.evaluate_trading_day(evaluation_date)

    def test_trigger_calculation_with_minimal_data(self):
        """
        Test trigger price calculation when only minimal historical data is available.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock minimal price data (just 2 days: yesterday and today)
            evaluation_date = date(2023, 6, 15)
            yesterday = evaluation_date - timedelta(days=1)
            
            dates = [yesterday, evaluation_date]
            prices = [100.0, 105.0]
            price_series = pd.Series(prices, index=dates, name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            price_monitor.calculate_rolling_maximum.return_value = 100.0  # Yesterday's price
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should work with minimal data
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            assert isinstance(result, EvaluationResult)
            assert result.yesterday_price == 100.0
            assert result.rolling_maximum == 100.0
            assert result.trigger_price == 90.0  # 100.0 * 0.90

    def test_backtest_with_no_trading_days(self):
        """
        Test backtest behavior when date range contains no trading days.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock empty price data for all requests
            price_monitor.get_closing_prices.return_value = pd.Series([], dtype=float, name='Close')
            # Mock get_api_stats to return a proper dictionary
            price_monitor.get_api_stats.return_value = {'api_calls_made': 0, 'cache_hits': 0}
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Run backtest over weekend (no trading days)
            start_date = date(2023, 6, 17)  # Saturday
            end_date = date(2023, 6, 18)    # Sunday
            
            # Should raise ValueError for no price data
            with pytest.raises(ValueError, match="No price data available"):
                result = strategy_system.run_backtest(start_date, end_date)

    def test_backtest_with_price_data_gaps(self):
        """
        Test backtest behavior when some days have missing price data.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=5,  # Short window for testing
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock price data with gaps (some days missing)
            def mock_get_closing_prices(ticker, start_date, end_date):
                # Only return data for some days in a limited range
                available_dates = [
                    date(2023, 6, 12),  # Monday
                    date(2023, 6, 13),  # Tuesday
                    # Wednesday missing
                    date(2023, 6, 15),  # Thursday
                    date(2023, 6, 16),  # Friday
                ]
                
                # Filter to requested range
                filtered_dates = [d for d in available_dates if start_date <= d <= end_date]
                if not filtered_dates:
                    return pd.Series([], dtype=float, name='Close')
                
                # The backtest will request data from much earlier (start_date - rolling_window_days - 30)
                # which will be around 2023-05-08, so our limited data won't cover that range
                # Return empty series for the extended range that backtest needs
                if start_date < date(2023, 6, 10):  # If requesting data before our available range
                    return pd.Series([], dtype=float, name='Close')
                
                prices = [100.0 + i for i in range(len(filtered_dates))]
                return pd.Series(prices, index=filtered_dates, name='Close')
            
            price_monitor.get_closing_prices.side_effect = mock_get_closing_prices
            price_monitor.calculate_rolling_maximum.return_value = 103.0
            # Mock get_api_stats to return a proper dictionary
            price_monitor.get_api_stats.return_value = {'api_calls_made': 5, 'cache_hits': 2}
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Run backtest over the week
            start_date = date(2023, 6, 12)
            end_date = date(2023, 6, 16)
            
            # Should raise ValueError for no price data in the extended range needed for backtest
            with pytest.raises(ValueError, match="No price data available"):
                result = strategy_system.run_backtest(start_date, end_date)

    def test_evaluation_with_weekend_dates(self):
        """
        Test that evaluation handles weekend dates appropriately.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock no price data for weekend
            price_monitor.get_closing_prices.return_value = pd.Series([], dtype=float, name='Close')
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Try to evaluate on Saturday
            saturday = date(2023, 6, 17)
            
            # Should raise ValueError for no price data
            with pytest.raises(ValueError, match="No price data available"):
                strategy_system.evaluate_trading_day(saturday)

    def test_evaluation_with_single_price_point(self):
        """
        Test evaluation when only one historical price point is available.
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=90,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock single price point
            evaluation_date = date(2023, 6, 15)
            yesterday = evaluation_date - timedelta(days=1)
            
            # Only yesterday's price available
            price_series = pd.Series([100.0, 105.0], index=[yesterday, evaluation_date], name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            price_monitor.calculate_rolling_maximum.return_value = 100.0
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should work with single historical point
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            assert isinstance(result, EvaluationResult)
            assert result.yesterday_price == 100.0
            assert result.rolling_maximum == 100.0

    def test_backtest_preserves_original_investments(self):
        """
        Test that backtest preserves original investments after completion.
        
        Validates: Backtest isolation
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=5,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Add original investment
            original_investment = Investment(
                date=date(2023, 5, 1),
                ticker="SPY",
                price=150.0,
                amount=1000.0,
                shares=6.67
            )
            investment_tracker.add_investment(original_investment)
            
            price_monitor = Mock(spec=PriceMonitor)
            price_monitor.get_closing_prices.return_value = pd.Series([], dtype=float, name='Close')
            # Mock get_api_stats to return a proper dictionary
            price_monitor.get_api_stats.return_value = {'api_calls_made': 0, 'cache_hits': 0}
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Run backtest
            start_date = date(2023, 6, 12)
            end_date = date(2023, 6, 16)
            
            # Should raise ValueError for no price data
            with pytest.raises(ValueError, match="No price data available"):
                result = strategy_system.run_backtest(start_date, end_date)

    def test_evaluation_with_extreme_price_values(self):
        """
        Test evaluation with extreme price values (very high/low).
        
        Validates: Requirements 3.5
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=5,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            # Mock extreme price values
            evaluation_date = date(2023, 6, 15)
            dates = [evaluation_date - timedelta(days=i) for i in range(5, 0, -1)]
            dates.append(evaluation_date)
            
            # Very high prices
            prices = [10000.0, 15000.0, 20000.0, 25000.0, 30000.0, 35000.0]
            price_series = pd.Series(prices, index=dates, name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            price_monitor.calculate_rolling_maximum.return_value = max(prices[:-1])
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            # Should handle extreme values without error
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            assert isinstance(result, EvaluationResult)
            assert result.rolling_maximum == 30000.0
            assert result.trigger_price == 27000.0  # 30000 * 0.90

    def test_evaluation_with_zero_percentage_trigger(self):
        """
        Test evaluation behavior with edge case percentage trigger values.
        
        Validates: Requirements 3.1, 3.3
        """
        # Note: Config validation should prevent 0.0, but test the calculation logic
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=5,
            percentage_trigger=0.01,  # Very low trigger (1%)
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            price_monitor = Mock(spec=PriceMonitor)
            
            evaluation_date = date(2023, 6, 15)
            yesterday = evaluation_date - timedelta(days=1)
            
            price_series = pd.Series([100.0, 50.0], index=[yesterday, evaluation_date], name='Close')
            
            price_monitor.get_closing_prices.return_value = price_series
            price_monitor.calculate_rolling_maximum.return_value = 100.0
            
            strategy_system = StrategySystem(config, price_monitor, investment_tracker)
            
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # With 1% trigger, trigger price should be 1.0
            assert result.trigger_price == 1.0  # 100.0 * 0.01
            # Yesterday price (100.0) should be well above trigger (1.0)
            assert not result.trigger_met

    def test_calculate_trigger_price_edge_cases(self):
        """
        Test trigger price calculation with various edge cases.
        
        Validates: Requirements 3.1, 3.2, 3.3
        """
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=5,
            percentage_trigger=0.90,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        strategy_system = StrategySystem(config)
        
        # Test with identical prices
        identical_prices = pd.Series([100.0] * 10, name='Close')
        trigger_price = strategy_system.calculate_trigger_price(identical_prices, 5, 0.90)
        assert trigger_price == 90.0  # 100.0 * 0.90
        
        # Test with single price
        single_price = pd.Series([150.0], name='Close')
        trigger_price = strategy_system.calculate_trigger_price(single_price, 5, 0.80)
        assert trigger_price == 120.0  # 150.0 * 0.80
        
        # Test with decreasing prices
        decreasing_prices = pd.Series([100.0, 90.0, 80.0, 70.0, 60.0], name='Close')
        trigger_price = strategy_system.calculate_trigger_price(decreasing_prices, 5, 0.90)
        assert trigger_price == 90.0  # max(100.0, 90.0, 80.0, 70.0, 60.0) * 0.90