"""
Unit tests for cache validation functionality.
Tests cached data against actual yfinance closing prices to ensure data integrity.
"""

import pandas as pd
import pytest
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import Mock, patch
from pathlib import Path

from buy_the_dip.price_monitor import PriceMonitor
from buy_the_dip.cli.cli import validate_cached_data


class TestCacheValidation:
    """Test cache validation against real yfinance data."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_cache_validation_with_matching_data(self, temp_cache_dir):
        """Test cache validation when cached data matches API data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create test dates - use recent dates
        test_date = date.today() - timedelta(days=5)  # 5 days ago
        cached_price = 150.25

        # Pre-populate cache with test data
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return matching data
        mock_yf = Mock()
        mock_stock = Mock()
        # Create mock data with the exact same date as cached data
        mock_history_data = pd.DataFrame({"Close": [cached_price]})  # Same price as cached
        # Set the index to match the test_date exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(test_date)])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should pass validation
        assert result["valid"] is True
        assert result["records_checked"] == 1
        assert result["mismatches"] == 0
        assert "error" not in result
        assert "sampling_info" in result

    def test_cache_validation_with_mismatched_data(self, temp_cache_dir):
        """Test cache validation when cached data doesn't match API data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create test dates
        test_date = date.today() - timedelta(days=5)  # 5 days ago
        cached_price = 150.25
        api_price = 152.75  # Different from cached

        # Pre-populate cache with test data
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return different data
        mock_yf = Mock()
        mock_stock = Mock()
        # Create mock data with the exact same date as cached data
        mock_history_data = pd.DataFrame({"Close": [api_price]})  # Different price from cached
        # Set the index to match the test_date exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(test_date)])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should fail validation
        assert result["valid"] is False
        assert result["records_checked"] == 1
        assert result["mismatches"] == 1
        assert len(result["sample_mismatches"]) == 1

        mismatch = result["sample_mismatches"][0]
        assert mismatch["date"] == test_date
        assert mismatch["cached"] == cached_price
        assert mismatch["api"] == api_price
        assert mismatch["difference"] == abs(cached_price - api_price)

    def test_cache_validation_with_no_cached_data(self, temp_cache_dir):
        """Test cache validation when no cached data exists."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Run validation without any cached data
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should indicate no cached data
        assert result["valid"] is False
        assert result["records_checked"] == 0
        assert result["mismatches"] == 0
        assert result["error"] == "No cached data found"

    def test_cache_validation_with_api_failure(self, temp_cache_dir):
        """Test cache validation when API call fails."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Pre-populate cache with test data
        test_date = date.today() - timedelta(days=5)
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [150.25]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to fail
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()  # Empty response
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should indicate API failure
        assert result["valid"] is False
        assert result["records_checked"] == 0
        assert result["mismatches"] == 0
        assert result["error"] == "Could not fetch fresh data from API"

    def test_cache_validation_with_multiple_dates(self, temp_cache_dir):
        """Test cache validation with multiple dates, some matching and some not."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create test data for multiple recent dates
        base_date = date.today() - timedelta(days=7)
        test_dates = [
            base_date,
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
        ]

        cached_prices = [150.25, 151.50, 149.75]
        api_prices = [150.25, 152.00, 149.75]  # Middle price is different

        # Pre-populate cache
        cached_data = pd.DataFrame({"Date": test_dates, "Close": cached_prices})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return mixed matching/non-matching data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": api_prices})
        # Set the index to match the test dates exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(d) for d in test_dates])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should detect one mismatch
        assert result["valid"] is False
        assert result["records_checked"] == 3
        assert result["mismatches"] == 1
        assert len(result["sample_mismatches"]) == 1

        mismatch = result["sample_mismatches"][0]
        assert mismatch["date"] == test_dates[1]  # Middle date
        assert mismatch["cached"] == cached_prices[1]
        assert mismatch["api"] == api_prices[1]

    def test_cache_validation_with_floating_point_tolerance(self, temp_cache_dir):
        """Test that small floating point differences are tolerated."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        test_date = date.today() - timedelta(days=5)
        cached_price = 150.25
        api_price = 150.251  # Very small difference (0.001)

        # Pre-populate cache
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API with tiny difference
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": [api_price]})
        # Set the index to match the test_date exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(test_date)])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should pass validation (difference < 0.01 tolerance)
        assert result["valid"] is True
        assert result["records_checked"] == 1
        assert result["mismatches"] == 0

    def test_cache_validation_with_significant_difference(self, temp_cache_dir):
        """Test that significant price differences are detected."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        test_date = date.today() - timedelta(days=5)
        cached_price = 150.25
        api_price = 150.30  # 5 cent difference (> 0.01 tolerance)

        # Pre-populate cache
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API with significant difference
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": [api_price]})
        # Set the index to match the test_date exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(test_date)])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should fail validation (difference >= 0.01 tolerance)
        assert result["valid"] is False
        assert result["records_checked"] == 1
        assert result["mismatches"] == 1

    def test_cache_validation_small_cache_validates_all(self, temp_cache_dir):
        """Test that small caches (< 30 days) are validated entirely."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create a small cache with only 5 days of data
        base_date = date.today() - timedelta(days=5)
        test_dates = [base_date + timedelta(days=i) for i in range(5)]
        cached_prices = [150.25, 151.50, 149.75, 152.00, 150.80]

        # Pre-populate cache
        cached_data = pd.DataFrame({"Date": test_dates, "Close": cached_prices})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return matching data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": cached_prices})
        # Set the index to match the test dates exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(d) for d in test_dates])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=50)

        # Should validate all records since cache is small
        assert result["valid"] is True
        assert result["records_checked"] == 5  # All 5 records
        assert result["mismatches"] == 0
        assert "sampling_info" in result

        # Check that it used full_cache strategy
        info = result["sampling_info"]
        assert info["validation_strategy"] == "full_cache"
        assert info["total_records_checked"] == 5
        assert info["cache_date_range_days"] == 4  # 5 days = 4 day range

    def test_cache_validation_preserves_original_cache(self, temp_cache_dir):
        """Test that cache validation doesn't permanently modify the cache."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Pre-populate cache and in-memory cache
        test_date = date.today() - timedelta(days=5)
        cached_data = pd.DataFrame({"Date": [test_date], "Close": [150.25]})
        monitor._save_cached_data("SPY", cached_data)
        monitor._cache["SPY"] = cached_data.copy()

        # Mock API
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": [150.25]})
        # Set the index to match the test_date exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(test_date)])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Store original cache state
        original_cache_exists = "SPY" in monitor._cache

        # Run validation
        validate_cached_data(monitor, "SPY", max_records=10)

        # Verify cache state is preserved
        if original_cache_exists:
            assert "SPY" in monitor._cache
            pd.testing.assert_frame_equal(monitor._cache["SPY"], cached_data)
        else:
            assert "SPY" not in monitor._cache


class TestSpecificDateValidation:
    """Test cache validation with specific known dates to catch real-world issues."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_december_2024_cache_validation(self, temp_cache_dir):
        """
        Test cache validation for recent dates that could cause cache issues.
        This test simulates the type of cache problems that occurred in December 2024.
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Use recent dates instead of specific December 2024 dates
        base_date = date.today() - timedelta(days=10)
        problematic_dates = [
            base_date,
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
            base_date + timedelta(days=3),
            base_date + timedelta(days=4),
        ]

        # Create cached data with potentially incorrect values
        cached_prices = [580.50, 582.25, 579.75, 583.00, 581.50]
        cached_data = pd.DataFrame({"Date": problematic_dates, "Close": cached_prices})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API with "correct" values (simulating what API should return)
        correct_prices = [580.52, 582.27, 579.73, 583.02, 581.48]  # Slightly different
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({"Close": correct_prices})
        # Set the index to match the test dates exactly
        mock_history_data.index = pd.DatetimeIndex([pd.Timestamp(d) for d in problematic_dates])

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=15)

        # Should detect mismatches (differences > 0.01)
        assert result["valid"] is False
        assert result["records_checked"] == 5
        assert result["mismatches"] == 5  # All prices differ by more than tolerance

        # Verify sample mismatches contain expected data
        assert len(result["sample_mismatches"]) == 5

        # The validation function returns most recent dates first, so we need to account for that
        mismatch_dates = [m["date"] for m in result["sample_mismatches"]]
        expected_dates = sorted(problematic_dates, reverse=True)  # Most recent first

        for i, mismatch in enumerate(result["sample_mismatches"]):
            expected_date = expected_dates[i]
            expected_cached_price = cached_prices[problematic_dates.index(expected_date)]
            expected_api_price = correct_prices[problematic_dates.index(expected_date)]

            assert mismatch["date"] == expected_date
            assert mismatch["cached"] == expected_cached_price
            assert mismatch["api"] == expected_api_price

    def test_weekend_holiday_cache_validation(self, temp_cache_dir):
        """Test cache validation handles weekends and holidays correctly."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Use recent weekend dates (should not have trading data)
        # Find the most recent Saturday and Sunday
        today = date.today()
        days_back = 0
        while (today - timedelta(days=days_back)).weekday() != 5:  # Find Saturday
            days_back += 1

        saturday = today - timedelta(days=days_back)
        sunday = saturday + timedelta(days=1)
        weekend_dates = [saturday, sunday]

        # Create cached data for weekend (this shouldn't exist in real cache)
        cached_data = pd.DataFrame({"Date": weekend_dates, "Close": [580.00, 580.00]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return empty data for weekends
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()  # No data for weekends
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should handle gracefully - no API data to compare against
        assert result["valid"] is False
        assert result["error"] == "Could not fetch fresh data from API"

    def test_market_holiday_cache_validation(self, temp_cache_dir):
        """Test cache validation for market holidays."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Use a simulated holiday date (create a date that we'll treat as a holiday)
        # Use a recent Monday that we'll simulate as a holiday
        today = date.today()
        days_back = 0
        while (today - timedelta(days=days_back)).weekday() != 0:  # Find Monday
            days_back += 1

        simulated_holiday = today - timedelta(days=days_back)

        # Create cached data for holiday (this shouldn't exist)
        cached_data = pd.DataFrame({"Date": [simulated_holiday], "Close": [580.00]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return empty data for holidays
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Run validation
        result = validate_cached_data(monitor, "SPY", max_records=10)

        # Should handle gracefully
        assert result["valid"] is False
        assert result["error"] == "Could not fetch fresh data from API"


class TestIgnoreCacheFunctionality:
    """Test the ignore cache functionality."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_fetch_with_ignore_cache_bypasses_cache(self, temp_cache_dir):
        """Test that ignore_cache=True bypasses cached data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Pre-populate cache with old data
        test_date = date(2023, 12, 1)
        cached_price = 150.25
        api_price = 155.75  # Different from cached

        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API to return different data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [api_price]}, index=pd.date_range(test_date, periods=1)
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Fetch with ignore_cache=True
        result = monitor.fetch_price_data("SPY", test_date, test_date, ignore_cache=True)

        # Should return API data, not cached data
        assert not result.empty
        assert len(result) == 1
        assert result["Close"].iloc[0] == api_price  # API price, not cached price

        # Verify API was called
        mock_stock.history.assert_called_once()

    def test_fetch_without_ignore_cache_uses_cache(self, temp_cache_dir):
        """Test that ignore_cache=False (default) uses cached data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Pre-populate cache
        test_date = date(2023, 12, 1)
        cached_price = 150.25

        cached_data = pd.DataFrame({"Date": [test_date], "Close": [cached_price]})
        monitor._save_cached_data("SPY", cached_data)

        # Mock API (should not be called)
        mock_yf = Mock()
        mock_stock = Mock()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Fetch without ignore_cache (default behavior)
        result = monitor.fetch_price_data("SPY", test_date, test_date)

        # Should return cached data
        assert not result.empty
        assert len(result) == 1
        assert result["Close"].iloc[0] == cached_price

        # Verify API was NOT called
        mock_stock.history.assert_not_called()

    def test_fresh_data_fetch_method(self, temp_cache_dir):
        """Test the _fetch_fresh_data method directly."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        test_date = date(2023, 12, 1)
        api_price = 155.75

        # Mock API
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [api_price]}, index=pd.date_range(test_date, periods=1)
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Call _fetch_fresh_data directly
        result = monitor._fetch_fresh_data("SPY", test_date, test_date)

        # Should return fresh API data
        assert not result.empty
        assert len(result) == 1
        assert result["Close"].iloc[0] == api_price
        assert result["Date"].iloc[0] == test_date

        # Verify API was called
        mock_stock.history.assert_called_once()

    def test_fresh_data_fetch_with_api_error(self, temp_cache_dir):
        """Test _fetch_fresh_data handles API errors gracefully."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        test_date = date(2023, 12, 1)

        # Mock API to raise exception
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.side_effect = Exception("API Error")
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Call _fetch_fresh_data
        result = monitor._fetch_fresh_data("SPY", test_date, test_date)

        # Should return empty DataFrame on error
        assert result.empty
