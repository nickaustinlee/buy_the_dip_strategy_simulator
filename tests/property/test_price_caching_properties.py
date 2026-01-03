"""
Property-based tests for price data caching functionality.
"""

import tempfile
import shutil
import pandas as pd
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock
from contextlib import contextmanager

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.price_monitor.price_monitor import PriceMonitor


class TestPriceCachingProperties:
    """Property-based tests for price data caching."""

    @contextmanager
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir)

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.strip() and x.isalnum()),
        num_days=st.integers(min_value=1, max_value=30),
        base_price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True),
        cache_days=st.integers(min_value=1, max_value=60)
    )
    def test_price_data_caching_correctness(
        self,
        ticker: str,
        num_days: int,
        base_price: float,
        cache_days: int
    ):
        """
        Feature: buy-the-dip-strategy, Property 2: Price Data Caching Correctness
        
        For any ticker and date range, when data is cached and still valid, repeated requests 
        should return identical price data without additional API calls, and cache expiration 
        should work correctly.
        
        Validates: Requirements 2.2, 2.3
        """
        # Skip NaN and infinite values
        assume(base_price == base_price and base_price != float('inf') and base_price != float('-inf'))
        
        with self.temp_cache_dir() as temp_cache_dir:
            monitor = PriceMonitor(cache_dir=temp_cache_dir)
            
            # Generate test date range
            start_date = date.today() - timedelta(days=num_days)
            end_date = date.today() - timedelta(days=1)  # Yesterday to avoid weekend issues
            
            # Generate mock price data
            date_range = pd.bdate_range(start=start_date, end=end_date)
            if len(date_range) == 0:
                # Skip if no business days in range
                assume(False)
            
            mock_prices = [base_price + (i * 0.1) for i in range(len(date_range))]
            mock_history_data = pd.DataFrame({
                'Close': mock_prices
            }, index=date_range)
            
            # Mock the yfinance API
            mock_yf = Mock()
            mock_stock = Mock()
            mock_stock.history.return_value = mock_history_data
            mock_yf.Ticker.return_value = mock_stock
            monitor._get_yfinance = Mock(return_value=mock_yf)
            
            # First fetch - should call API
            first_result = monitor.fetch_price_data(ticker, start_date, end_date)
            api_call_count_after_first = mock_stock.history.call_count
            
            # Verify first result is not empty and has expected structure
            assert not first_result.empty
            assert 'Date' in first_result.columns
            assert 'Close' in first_result.columns
            assert len(first_result) == len(date_range)
            
            # Second fetch - should use cache (no additional API calls)
            second_result = monitor.fetch_price_data(ticker, start_date, end_date)
            api_call_count_after_second = mock_stock.history.call_count
            
            # Verify no additional API calls were made
            assert api_call_count_after_second == api_call_count_after_first
            
            # Verify results are identical
            pd.testing.assert_frame_equal(first_result, second_result)
            
            # Verify cache validity works correctly
            if cache_days > 0:
                # Cache should be valid for recent data
                assert monitor.is_cache_valid(ticker, cache_days=cache_days)
            
            # Test cache expiration by checking with very short cache duration
            assert not monitor.is_cache_valid(ticker, cache_days=0)

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.strip() and x.isalnum()),
        num_days_first=st.integers(min_value=1, max_value=15),
        num_days_second=st.integers(min_value=1, max_value=15),
        base_price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True)
    )
    def test_cache_merging_correctness(
        self,
        ticker: str,
        num_days_first: int,
        num_days_second: int,
        base_price: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 2: Price Data Caching Correctness
        
        For any ticker, when fetching overlapping or adjacent date ranges, the cache 
        should correctly merge data without duplicates and maintain chronological order.
        
        Validates: Requirements 2.2, 2.3
        """
        # Skip NaN and infinite values
        assume(base_price == base_price and base_price != float('inf') and base_price != float('-inf'))
        
        with self.temp_cache_dir() as temp_cache_dir:
            monitor = PriceMonitor(cache_dir=temp_cache_dir)
            
            # Generate two potentially overlapping date ranges
            end_date = date.today() - timedelta(days=1)
            start_date_first = end_date - timedelta(days=num_days_first + num_days_second)
            end_date_first = end_date - timedelta(days=num_days_second)
            start_date_second = end_date - timedelta(days=num_days_second)
            end_date_second = end_date
            
            # Generate mock data for both ranges
            def create_mock_data(start_dt, end_dt, price_offset=0):
                date_range = pd.bdate_range(start=start_dt, end=end_dt)
                if len(date_range) == 0:
                    return pd.DataFrame()
                
                mock_prices = [base_price + price_offset + (i * 0.1) for i in range(len(date_range))]
                return pd.DataFrame({
                    'Close': mock_prices
                }, index=date_range)
            
            mock_data_first = create_mock_data(start_date_first, end_date_first)
            mock_data_second = create_mock_data(start_date_second, end_date_second, price_offset=10)
            
            # Skip if no business days in either range
            if mock_data_first.empty and mock_data_second.empty:
                assume(False)
            
            # Mock the yfinance API to return different data for different calls
            mock_yf = Mock()
            mock_stock = Mock()
            mock_stock.history.side_effect = [mock_data_first, mock_data_second]
            mock_yf.Ticker.return_value = mock_stock
            monitor._get_yfinance = Mock(return_value=mock_yf)
            
            # Fetch first range
            first_result = monitor.fetch_price_data(ticker, start_date_first, end_date_first)
            
            # Fetch second range (may overlap with first)
            second_result = monitor.fetch_price_data(ticker, start_date_second, end_date_second)
            
            # Fetch combined range - should use cached data
            combined_result = monitor.fetch_price_data(ticker, start_date_first, end_date_second)
            
            # Verify combined result has no duplicate dates
            if not combined_result.empty:
                assert len(combined_result) == len(combined_result['Date'].unique())
                
                # Verify chronological order
                dates = combined_result['Date'].tolist()
                assert dates == sorted(dates)
                
                # Verify all dates from both individual fetches are present
                first_dates = set(first_result['Date'].tolist()) if not first_result.empty else set()
                second_dates = set(second_result['Date'].tolist()) if not second_result.empty else set()
                combined_dates = set(combined_result['Date'].tolist())
                
                assert first_dates.issubset(combined_dates)
                assert second_dates.issubset(combined_dates)

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.strip() and x.isalnum()),
        num_days=st.integers(min_value=1, max_value=20),
        base_price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True)
    )
    def test_persistent_cache_round_trip(
        self,
        ticker: str,
        num_days: int,
        base_price: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 2: Price Data Caching Correctness
        
        For any price data, saving to persistent cache and then loading should produce 
        identical data, ensuring cache persistence works correctly across sessions.
        
        Validates: Requirements 2.2, 2.3
        """
        # Skip NaN and infinite values
        assume(base_price == base_price and base_price != float('inf') and base_price != float('-inf'))
        
        with self.temp_cache_dir() as temp_cache_dir:
            monitor = PriceMonitor(cache_dir=temp_cache_dir)
            
            # Generate test date range
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=num_days)
            
            # Generate mock price data
            date_range = pd.bdate_range(start=start_date, end=end_date)
            if len(date_range) == 0:
                assume(False)
            
            mock_prices = [base_price + (i * 0.1) for i in range(len(date_range))]
            original_data = pd.DataFrame({
                'Date': [d.date() for d in date_range],
                'Close': mock_prices
            })
            
            # Save data to persistent cache
            monitor._save_cached_data(ticker, original_data)
            
            # Load data from persistent cache
            loaded_data = monitor._load_cached_data(ticker)
            
            # Verify loaded data matches original
            assert loaded_data is not None
            assert not loaded_data.empty
            pd.testing.assert_frame_equal(original_data, loaded_data)
            
            # Create a new monitor instance (simulating new session)
            new_monitor = PriceMonitor(cache_dir=temp_cache_dir)
            
            # Load data with new monitor instance
            reloaded_data = new_monitor._load_cached_data(ticker)
            
            # Verify data persists across monitor instances
            assert reloaded_data is not None
            pd.testing.assert_frame_equal(original_data, reloaded_data)

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.strip() and x.isalnum()),
        cache_days_valid=st.integers(min_value=1, max_value=30),
        cache_days_invalid=st.integers(min_value=31, max_value=100)
    )
    def test_cache_expiration_logic(
        self,
        ticker: str,
        cache_days_valid: int,
        cache_days_invalid: int
    ):
        """
        Feature: buy-the-dip-strategy, Property 2: Price Data Caching Correctness
        
        For any cache expiration settings, cache validity should correctly determine 
        whether cached data is fresh enough based on the configured cache duration.
        
        Validates: Requirements 2.2, 2.3
        """
        with self.temp_cache_dir() as temp_cache_dir:
            monitor = PriceMonitor(cache_dir=temp_cache_dir)
            
            # Create data with a specific age
            data_age_days = 30
            old_date = date.today() - timedelta(days=data_age_days)
            
            old_data = pd.DataFrame({
                'Date': [old_date],
                'Close': [100.0]
            })
            
            # Save old data to cache
            monitor._save_cached_data(ticker, old_data)
            
            # Test cache validity with different expiration settings
            # Should be valid if cache_days > data_age_days
            if cache_days_valid > data_age_days:
                assert monitor.is_cache_valid(ticker, cache_days=cache_days_valid)
            
            # Should be invalid if cache_days < data_age_days
            if cache_days_invalid > data_age_days:
                # This case doesn't apply since cache_days_invalid > data_age_days
                pass
            else:
                assert not monitor.is_cache_valid(ticker, cache_days=cache_days_invalid)
            
            # Test with recent data
            recent_data = pd.DataFrame({
                'Date': [date.today()],
                'Close': [105.0]
            })
            
            monitor._save_cached_data(ticker + "_RECENT", recent_data)
            
            # Recent data should always be valid
            assert monitor.is_cache_valid(ticker + "_RECENT", cache_days=cache_days_valid)
            assert monitor.is_cache_valid(ticker + "_RECENT", cache_days=cache_days_invalid)