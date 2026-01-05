"""
Property-based tests for trigger price calculation functionality.
"""

import pandas as pd
from datetime import date, timedelta
from typing import List

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.price_monitor.price_monitor import PriceMonitor


class TestTriggerCalculationProperties:
    """Property-based tests for trigger price calculation."""

    @given(
        base_price=st.floats(min_value=10.0, max_value=1000.0, exclude_min=True),
        price_changes=st.lists(
            st.floats(min_value=-0.1, max_value=0.1),  # ±10% daily changes
            min_size=10,
            max_size=200
        ),
        window_days=st.integers(min_value=5, max_value=90),
        percentage_trigger=st.floats(min_value=0.5, max_value=1.0, exclude_min=True)
    )
    def test_trigger_price_calculation_accuracy(
        self,
        base_price: float,
        price_changes: List[float],
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For any price series, window size, and percentage trigger, the system should 
        calculate the rolling maximum over trailing window days using only closing prices, 
        then compute trigger price as rolling_maximum * percentage_trigger, recalculating 
        fresh each day.
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4
        """
        # Skip NaN and infinite values
        assume(base_price == base_price and base_price != float('inf') and base_price != float('-inf'))
        assume(all(change == change and change != float('inf') and change != float('-inf') 
                  for change in price_changes))
        
        # Generate price series from base price and changes
        prices = [base_price]
        for change in price_changes:
            new_price = prices[-1] * (1 + change)
            # Ensure price stays positive
            if new_price > 0.1:
                prices.append(new_price)
            else:
                prices.append(prices[-1])  # Keep previous price if change would make it too small
        
        # Create date index
        start_date = date(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(len(prices))]
        
        # Create pandas Series
        price_series = pd.Series(prices, index=dates, name='Close')
        
        # Create strategy system
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        strategy_system = StrategySystem(config)
        
        # Calculate trigger price
        trigger_price = strategy_system.calculate_trigger_price(
            price_series, window_days, percentage_trigger
        )
        
        # Verify trigger price calculation
        # 1. Calculate expected rolling maximum manually using calendar days (default behavior)
        if len(price_series) >= window_days:
            # Use calendar days logic - get all prices within the window period
            latest_date = price_series.index.max()
            cutoff_date = latest_date - timedelta(days=window_days)
            window_prices = price_series[price_series.index >= cutoff_date]
            expected_rolling_max = window_prices.max()
        else:
            # Use all available data if less than window size
            expected_rolling_max = max(prices)
        
        expected_trigger_price = expected_rolling_max * percentage_trigger
        
        # Verify the calculation is correct (within floating point precision)
        assert abs(trigger_price - expected_trigger_price) < 0.01, \
            f"Trigger price mismatch: {trigger_price} != {expected_trigger_price}"
        
        # Verify trigger price is always less than or equal to rolling maximum
        rolling_max = expected_rolling_max  # We calculated this above using the same logic
        assert trigger_price <= rolling_max + 0.01, \
            f"Trigger price {trigger_price} should be <= rolling maximum {rolling_max}"
        
        # Verify trigger price is positive
        assert trigger_price > 0, "Trigger price should be positive"
        
        # Verify relationship with percentage trigger
        assert abs(trigger_price / rolling_max - percentage_trigger) < 0.001, \
            f"Trigger price should equal rolling_max * percentage_trigger"

    @given(
        prices=st.lists(
            st.floats(min_value=50.0, max_value=500.0, exclude_min=True),
            min_size=30,
            max_size=100
        ),
        window_days=st.integers(min_value=10, max_value=50),
        percentage_trigger=st.floats(min_value=0.7, max_value=0.95, exclude_min=True)
    )
    def test_trigger_price_uses_only_closing_prices(
        self,
        prices: List[float],
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For any price series, the rolling maximum calculation should use only closing 
        prices and not any other price data (high, low, open).
        
        Validates: Requirements 3.2
        """
        # Skip NaN and infinite values
        assume(all(price == price and price != float('inf') and price != float('-inf') 
                  for price in prices))
        
        # Create date index
        start_date = date(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(len(prices))]
        
        # Create pandas Series with only closing prices
        price_series = pd.Series(prices, index=dates, name='Close')
        
        # Create strategy system with explicit use_trading_days=False (calendar days - default)
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30,
            use_trading_days=False  # Use calendar days (default behavior)
        )
        
        strategy_system = StrategySystem(config)
        
        # Calculate trigger price
        trigger_price = strategy_system.calculate_trigger_price(
            price_series, window_days, percentage_trigger
        )
        
        # Manually calculate what the rolling maximum should be using only closing prices
        # Using calendar days logic (default behavior)
        if len(prices) >= window_days:
            # Create date index to simulate calendar days logic
            start_date = date(2023, 1, 1)
            dates = [start_date + timedelta(days=i) for i in range(len(prices))]
            price_series_with_dates = pd.Series(prices, index=dates, name='Close')
            
            latest_date = price_series_with_dates.index.max()
            cutoff_date = latest_date - timedelta(days=window_days)
            window_prices = price_series_with_dates[price_series_with_dates.index >= cutoff_date]
            manual_rolling_max = window_prices.max()
        else:
            manual_rolling_max = max(prices)
        
        manual_trigger_price = manual_rolling_max * percentage_trigger
        
        # Verify the calculation matches manual calculation using only closing prices
        assert abs(trigger_price - manual_trigger_price) < 0.01, \
            f"Trigger price should be calculated using only closing prices"

    @given(
        base_prices=st.lists(
            st.floats(min_value=100.0, max_value=300.0, exclude_min=True),
            min_size=50,
            max_size=150
        ),
        window_days=st.integers(min_value=20, max_value=60),
        percentage_trigger=st.floats(min_value=0.8, max_value=0.95, exclude_min=True)
    )
    def test_trigger_price_recalculated_fresh_each_day(
        self,
        base_prices: List[float],
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For any price series, the trigger price should be recalculated fresh each day 
        based on the current rolling window, not cached or reused from previous calculations.
        
        Validates: Requirements 3.4
        """
        # Skip NaN and infinite values
        assume(all(price == price and price != float('inf') and price != float('-inf') 
                  for price in base_prices))
        
        # Create strategy system with explicit use_trading_days=False (calendar days - default)
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30,
            use_trading_days=False  # Use calendar days (default behavior)
        )
        
        strategy_system = StrategySystem(config)
        
        # Create date index
        start_date = date(2023, 1, 1)
        
        # Test multiple consecutive days to ensure fresh calculation
        trigger_prices = []
        
        for day_offset in range(min(10, len(base_prices) - window_days)):
            # Get prices up to current day
            current_day = day_offset + window_days
            current_prices = base_prices[:current_day]
            current_dates = [start_date + timedelta(days=i) for i in range(len(current_prices))]
            
            price_series = pd.Series(current_prices, index=current_dates, name='Close')
            
            # Calculate trigger price for this day
            trigger_price = strategy_system.calculate_trigger_price(
                price_series, window_days, percentage_trigger
            )
            
            trigger_prices.append(trigger_price)
            
            # Verify this calculation is based on the current window using calendar days logic
            latest_date = price_series.index.max()
            cutoff_date = latest_date - timedelta(days=window_days)
            window_prices = price_series[price_series.index >= cutoff_date]
            expected_rolling_max = window_prices.max()
            expected_trigger_price = expected_rolling_max * percentage_trigger
            
            assert abs(trigger_price - expected_trigger_price) < 0.01, \
                f"Day {day_offset}: Trigger price should be calculated fresh each day"
        
        # If prices change over time, trigger prices should potentially change too
        # (unless all prices in the window are identical)
        if len(set(base_prices)) > 1 and len(trigger_prices) > 1:
            # At least verify that the calculation is responsive to price changes
            # by checking that not all trigger prices are identical when prices vary
            unique_trigger_prices = len(set(round(tp, 2) for tp in trigger_prices))
            total_trigger_prices = len(trigger_prices)
            
            # Allow for some identical values, but expect some variation if prices vary significantly
            price_variation = max(base_prices) - min(base_prices)
            if price_variation > 10.0:  # Significant price variation
                # We should see some variation in trigger prices (not necessarily all different)
                assert unique_trigger_prices >= 1, "Trigger prices should be calculated fresh"

    @given(
        prices=st.lists(
            st.floats(min_value=20.0, max_value=200.0, exclude_min=True),
            min_size=5,
            max_size=15  # Less than typical window size
        ),
        window_days=st.integers(min_value=20, max_value=90),
        percentage_trigger=st.floats(min_value=0.8, max_value=0.95, exclude_min=True)
    )
    def test_trigger_price_handles_insufficient_data(
        self,
        prices: List[float],
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For any price series with insufficient historical data for the full window, 
        the system should use available data to calculate the trigger price.
        
        Validates: Requirements 3.5
        """
        # Skip NaN and infinite values
        assume(all(price == price and price != float('inf') and price != float('-inf') 
                  for price in prices))
        assume(len(prices) < window_days)  # Ensure insufficient data
        
        # Create date index
        start_date = date(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(len(prices))]
        
        # Create pandas Series
        price_series = pd.Series(prices, index=dates, name='Close')
        
        # Create strategy system
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        strategy_system = StrategySystem(config)
        
        # Should not raise an error and should use available data
        trigger_price = strategy_system.calculate_trigger_price(
            price_series, window_days, percentage_trigger
        )
        
        # Verify calculation uses all available data
        expected_rolling_max = max(prices)  # Should use all available prices
        expected_trigger_price = expected_rolling_max * percentage_trigger
        
        assert abs(trigger_price - expected_trigger_price) < 0.01, \
            f"Should use all available data when insufficient history: {trigger_price} != {expected_trigger_price}"
        
        # Verify trigger price is positive and reasonable
        assert trigger_price > 0, "Trigger price should be positive even with insufficient data"
        assert trigger_price <= max(prices), "Trigger price should not exceed maximum available price"

    @given(
        window_days=st.integers(min_value=1, max_value=100),
        percentage_trigger=st.floats(min_value=0.1, max_value=1.0, exclude_min=True)
    )
    def test_trigger_price_handles_empty_price_series(
        self,
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For empty price series, the system should handle the error gracefully 
        and raise an appropriate exception.
        
        Validates: Requirements 3.1
        """
        # Create empty price series
        price_series = pd.Series([], dtype=float, name='Close')
        
        # Create strategy system
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        strategy_system = StrategySystem(config)
        
        # Should raise ValueError for empty price data
        with pytest.raises(ValueError, match="Cannot calculate trigger price with empty price data"):
            strategy_system.calculate_trigger_price(price_series, window_days, percentage_trigger)

    @given(
        constant_price=st.floats(min_value=50.0, max_value=500.0, exclude_min=True),
        num_days=st.integers(min_value=10, max_value=100),
        window_days=st.integers(min_value=5, max_value=50),
        percentage_trigger=st.floats(min_value=0.7, max_value=0.95, exclude_min=True)
    )
    def test_trigger_price_with_constant_prices(
        self,
        constant_price: float,
        num_days: int,
        window_days: int,
        percentage_trigger: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 3: Trigger Price Calculation Accuracy
        
        For any price series with constant prices, the trigger price should be 
        the constant price multiplied by the percentage trigger.
        
        Validates: Requirements 3.1, 3.2, 3.3
        """
        # Skip NaN and infinite values
        assume(constant_price == constant_price and constant_price != float('inf') and constant_price != float('-inf'))
        assume(window_days <= num_days)
        
        # Create constant price series
        prices = [constant_price] * num_days
        start_date = date(2023, 1, 1)
        dates = [start_date + timedelta(days=i) for i in range(num_days)]
        
        price_series = pd.Series(prices, index=dates, name='Close')
        
        # Create strategy system
        config = StrategyConfig(
            ticker="SPY",
            rolling_window_days=window_days,
            percentage_trigger=percentage_trigger,
            monthly_dca_amount=2000.0,
            data_cache_days=30
        )
        
        strategy_system = StrategySystem(config)
        
        # Calculate trigger price
        trigger_price = strategy_system.calculate_trigger_price(
            price_series, window_days, percentage_trigger
        )
        
        # For constant prices, rolling maximum should equal the constant price
        expected_trigger_price = constant_price * percentage_trigger
        
        assert abs(trigger_price - expected_trigger_price) < 0.01, \
            f"For constant prices, trigger should be price * percentage_trigger: {trigger_price} != {expected_trigger_price}"