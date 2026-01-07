"""
Unit tests for price monitoring functionality.
"""

import pandas as pd
import pytest
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from buy_the_dip.price_monitor import PriceMonitor, PriceData


class TestPriceData:
    """Test PriceData model."""

    def test_price_data_creation(self):
        """Test PriceData model creation with valid data."""
        price_data = PriceData(date=date(2023, 1, 15), close=150.25, volume=1000000)

        assert price_data.date == date(2023, 1, 15)
        assert price_data.close == 150.25
        assert price_data.volume == 1000000

    def test_price_data_validation(self):
        """Test PriceData model validation."""
        # Valid data should work
        price_data = PriceData(date=date.today(), close=100.0, volume=500000)
        assert price_data.close == 100.0


class TestPriceMonitor:
    """Test PriceMonitor class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_price_monitor_initialization(self, temp_cache_dir):
        """Test PriceMonitor initialization."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        assert monitor._cache == {}
        assert monitor._cache_timestamps == {}
        assert monitor._yf is None
        assert monitor._cache_dir == Path(temp_cache_dir)

    def test_price_monitor_default_cache_dir(self):
        """Test PriceMonitor initialization with default cache directory."""
        monitor = PriceMonitor()
        expected_path = Path.home() / ".buy_the_dip" / "price_cache"
        assert monitor._cache_dir == expected_path

    def test_rolling_maximum_calculation(self):
        """Test rolling maximum calculation with various scenarios."""
        monitor = PriceMonitor()

        # Test basic rolling maximum
        prices = pd.Series([100, 95, 90, 105, 110, 85, 95])
        rolling_max = monitor.get_rolling_maximum(prices, window=3)

        expected = [100.0, 100.0, 100.0, 105.0, 110.0, 110.0, 110.0]
        assert rolling_max.tolist() == expected

    def test_rolling_maximum_with_single_value(self):
        """Test rolling maximum with single value."""
        monitor = PriceMonitor()

        prices = pd.Series([100])
        rolling_max = monitor.get_rolling_maximum(prices, window=3)

        assert rolling_max.tolist() == [100.0]

    def test_rolling_maximum_with_insufficient_data(self):
        """Test rolling maximum handles insufficient data correctly."""
        monitor = PriceMonitor()

        # Window larger than data
        prices = pd.Series([100, 95])
        rolling_max = monitor.get_rolling_maximum(prices, window=5)

        # Should use min_periods=1, so it calculates with available data
        expected = [100.0, 100.0]
        assert rolling_max.tolist() == expected

    def test_cache_update(self, temp_cache_dir):
        """Test cache update functionality."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create sample data
        data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2)],
                "Close": [100.0, 105.0],
                "Adj Close": [98.0, 103.0],
            }
        )

        # Update cache
        monitor.update_cache("SPY", data)

        # Verify in-memory cache was updated
        assert "SPY" in monitor._cache
        assert "SPY" in monitor._cache_timestamps
        assert len(monitor._cache["SPY"]) == 2
        pd.testing.assert_frame_equal(monitor._cache["SPY"], data)

        # Verify persistent cache was created
        cache_file = monitor._get_cache_file_path("SPY")
        assert cache_file.exists()

    def test_persistent_cache_load_save(self, temp_cache_dir):
        """Test loading and saving persistent cache."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create test data
        data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)],
                "Close": [100.0, 105.0, 102.0],
                "Adj Close": [98.0, 103.0, 100.0],
            }
        )

        # Save to cache
        monitor._save_cached_data("TEST", data)

        # Load from cache
        loaded_data = monitor._load_cached_data("TEST")

        # Verify data matches
        assert loaded_data is not None
        assert len(loaded_data) == 3
        pd.testing.assert_frame_equal(loaded_data, data)

    def test_cache_info(self, temp_cache_dir):
        """Test cache information retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Test with no cached data
        info = monitor.get_cache_info("SPY")
        assert info["cached"] is False
        assert info["records"] == 0

        # Add some cached data
        data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2)],
                "Close": [100.0, 105.0],
                "Adj Close": [98.0, 103.0],
            }
        )
        monitor.update_cache("SPY", data)

        # Test with cached data
        info = monitor.get_cache_info("SPY")
        assert info["cached"] is True
        assert info["records"] == 2
        assert info["date_range"]["start"] == "2023-01-01"
        assert info["date_range"]["end"] == "2023-01-02"

    def test_clear_cache(self, temp_cache_dir):
        """Test cache clearing functionality."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Add some cached data
        data = pd.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0], "Adj Close": [98.0]})
        monitor.update_cache("SPY", data)
        monitor.update_cache("AAPL", data)

        # Clear specific ticker
        monitor.clear_cache("SPY")
        assert "SPY" not in monitor._cache
        assert "AAPL" in monitor._cache

        # Clear all
        monitor.clear_cache()
        assert len(monitor._cache) == 0

    def test_fetch_price_data_success(self, temp_cache_dir):
        """Test successful price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method to avoid SSL issues
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [100.0, 105.0, 102.0], "Adj Close": [98.0, 103.0, 100.0]},
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test fetch
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Verify result
        assert len(result) == 3
        assert "Date" in result.columns
        assert "Close" in result.columns
        assert "Adj Close" in result.columns
        assert result["Close"].tolist() == [100.0, 105.0, 102.0]
        assert result["Adj Close"].tolist() == [98.0, 103.0, 100.0]

        # Verify data was cached
        cache_info = monitor.get_cache_info("SPY")
        assert cache_info["cached"] is True

    def test_dual_price_fetching_basic(self, temp_cache_dir):
        """
        Test that both Close and Adj Close prices are fetched and cached.
        **Validates: Requirements 1.1, 1.2**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance to return dual price data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [150.25, 151.50, 149.75], "Adj Close": [148.50, 149.75, 147.95]},
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test dual price fetching
        result = monitor.fetch_price_data("AAPL", date(2023, 1, 1), date(2023, 1, 3))

        # Verify API was called with auto_adjust=False
        mock_stock.history.assert_called_with(
            start=date(2023, 1, 1), end=date(2023, 1, 4), auto_adjust=False  # end_date + 1 day
        )

        # Verify both price columns are present
        assert "Close" in result.columns, "Close column should be present"
        assert "Adj Close" in result.columns, "Adj Close column should be present"
        assert len(result) == 3, "Should have 3 rows of data"

        # Verify Close prices
        expected_close = [150.25, 151.50, 149.75]
        assert (
            result["Close"].tolist() == expected_close
        ), f"Close prices should match: expected {expected_close}, got {result['Close'].tolist()}"

        # Verify Adj Close prices
        expected_adj_close = [148.50, 149.75, 147.95]
        assert (
            result["Adj Close"].tolist() == expected_adj_close
        ), f"Adj Close prices should match: expected {expected_adj_close}, got {result['Adj Close'].tolist()}"

        # Verify data structure
        assert "Date" in result.columns, "Date column should be present"
        assert len(result.columns) == 3, "Should have exactly 3 columns: Date, Close, Adj Close"

    def test_dual_price_caching_persistence(self, temp_cache_dir):
        """
        Test that both Close and Adj Close prices are properly cached and persist.
        **Validates: Requirements 1.2**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create test data with both price types
        test_data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)],
                "Close": [100.0, 102.5, 101.25],
                "Adj Close": [98.5, 101.0, 99.75],
            }
        )

        # Save to cache
        monitor._save_cached_data("TEST", test_data)

        # Load from cache using the same monitor instance
        cached_data = monitor._load_cached_data("TEST")

        # Verify both price columns are cached
        assert cached_data is not None, "Cached data should not be None"
        assert "Close" in cached_data.columns, "Close column should be cached"
        assert "Adj Close" in cached_data.columns, "Adj Close column should be cached"

        # Verify data integrity
        pd.testing.assert_frame_equal(
            test_data, cached_data, "Cached data should match original data"
        )

        # Test cache persistence across monitor instances (no legacy clearing now)
        new_monitor = PriceMonitor(cache_dir=temp_cache_dir)
        reloaded_data = new_monitor._load_cached_data("TEST")

        assert reloaded_data is not None, "Reloaded data should not be None"
        assert "Close" in reloaded_data.columns, "Close column should persist"
        assert "Adj Close" in reloaded_data.columns, "Adj Close column should persist"
        pd.testing.assert_frame_equal(
            test_data, reloaded_data, "Reloaded data should match original data"
        )

        # Verify cache file format
        cache_file = monitor._get_cache_file_path("TEST")
        assert cache_file.exists(), "Cache file should exist"

        # Read cache file directly to verify dual price format
        import json

        with open(cache_file, "r") as f:
            cache_content = json.load(f)

        assert "format_version" in cache_content, "Cache should have format version"
        assert cache_content["format_version"] == "2.0", "Cache should be dual price format"
        assert "prices" in cache_content, "Cache should have prices data"

        # Verify both price columns are in the cached JSON
        first_price_record = cache_content["prices"][0]
        assert "Close" in first_price_record, "Cache should contain Close prices"
        assert "Adj Close" in first_price_record, "Cache should contain Adj Close prices"

    def test_dual_price_cache_merging(self, temp_cache_dir):
        """
        Test that cache merging works correctly with both price columns.
        **Validates: Requirements 1.4**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create initial cached data
        cached_data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2)],
                "Close": [100.0, 102.0],
                "Adj Close": [98.0, 100.0],
            }
        )

        # Create new data to merge
        new_data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 3), date(2023, 1, 4)],
                "Close": [104.0, 103.5],
                "Adj Close": [102.0, 101.5],
            }
        )

        # Test merging
        merged_data = monitor._merge_cached_and_new_data(cached_data, new_data)

        # Verify merged data has both price columns
        assert "Close" in merged_data.columns, "Merged data should have Close column"
        assert "Adj Close" in merged_data.columns, "Merged data should have Adj Close column"
        assert len(merged_data) == 4, "Merged data should have 4 rows"

        # Verify data integrity
        expected_close = [100.0, 102.0, 104.0, 103.5]
        expected_adj_close = [98.0, 100.0, 102.0, 101.5]
        assert (
            merged_data["Close"].tolist() == expected_close
        ), "Close prices should be merged correctly"
        assert (
            merged_data["Adj Close"].tolist() == expected_adj_close
        ), "Adj Close prices should be merged correctly"

        # Verify chronological order
        dates = merged_data["Date"].tolist()
        assert dates == sorted(dates), "Merged data should be in chronological order"

    def test_dual_price_api_call_structure(self, temp_cache_dir):
        """
        Test that API calls request both Close and Adj Close columns.
        **Validates: Requirements 1.1**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance
        mock_yf = Mock()
        mock_stock = Mock()

        # Create mock data with both columns
        mock_history_data = pd.DataFrame(
            {
                "Open": [99.0, 100.0, 101.0],
                "High": [101.0, 102.0, 103.0],
                "Low": [98.0, 99.0, 100.0],
                "Close": [100.0, 101.0, 102.0],
                "Adj Close": [98.5, 99.5, 100.5],
                "Volume": [1000000, 1100000, 1200000],
            },
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Fetch data
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Verify API was called with auto_adjust=False
        mock_stock.history.assert_called_with(
            start=date(2023, 1, 1), end=date(2023, 1, 4), auto_adjust=False  # end_date + 1 day
        )

        # Verify result contains only the dual price columns we need
        assert set(result.columns) == {
            "Date",
            "Close",
            "Adj Close",
        }, "Result should contain only Date, Close, and Adj Close columns"

        # Verify both price columns have correct data
        assert result["Close"].tolist() == [
            100.0,
            101.0,
            102.0,
        ], "Close prices should be extracted correctly"
        assert result["Adj Close"].tolist() == [
            98.5,
            99.5,
            100.5,
        ], "Adj Close prices should be extracted correctly"

    def test_auto_adjust_false_parameter(self, temp_cache_dir):
        """
        Test that yfinance is called with auto_adjust=False to ensure we get both raw Close and Adj Close.
        **Validates: Requirements 1.1**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance with realistic data showing difference between Close and Adj Close
        mock_yf = Mock()
        mock_stock = Mock()
        # Simulate a stock that had dividends - Adj Close should be lower than Close
        mock_history_data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],  # Raw closing prices
                "Adj Close": [99.5, 100.5],  # Adjusted for dividends (lower)
                "Volume": [1000000, 1100000],
            },
            index=pd.date_range("2023-01-01", periods=2),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Fetch data
        result = monitor.fetch_price_data("DIVIDEND_STOCK", date(2023, 1, 1), date(2023, 1, 2))

        # Verify auto_adjust=False was used
        mock_stock.history.assert_called_with(
            start=date(2023, 1, 1), end=date(2023, 1, 3), auto_adjust=False
        )

        # Verify we get distinct Close and Adj Close values
        assert result["Close"].tolist() == [101.0, 102.0], "Should get raw Close prices"
        assert result["Adj Close"].tolist() == [99.5, 100.5], "Should get dividend-adjusted prices"

        # Verify Close > Adj Close (typical for dividend-paying stocks)
        for i in range(len(result)):
            assert (
                result["Close"].iloc[i] >= result["Adj Close"].iloc[i]
            ), f"Close price should be >= Adj Close price at index {i}"

    def test_fetch_price_data_with_cache(self, temp_cache_dir):
        """Test fetching price data when some data is already cached."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Pre-populate cache with some data
        cached_data = pd.DataFrame(
            {
                "Date": [date(2023, 1, 1), date(2023, 1, 2)],
                "Close": [100.0, 105.0],
                "Adj Close": [98.0, 103.0],
            }
        )
        monitor.update_cache("SPY", cached_data)

        # Mock API for additional data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [102.0], "Adj Close": [100.0]}, index=pd.date_range("2023-01-03", periods=1)
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Fetch data that spans cached and new data
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Should return all three days
        assert len(result) == 3
        assert result["Close"].tolist() == [100.0, 105.0, 102.0]
        assert result["Adj Close"].tolist() == [98.0, 103.0, 100.0]

    def test_fetch_price_data_empty_response(self, temp_cache_dir):
        """Test handling of empty price data response."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test fetch
        result = monitor.fetch_price_data("INVALID", date(2023, 1, 1), date(2023, 1, 3))

        # Should return empty DataFrame
        assert result.empty

    def test_fetch_price_data_exception_handling(self, temp_cache_dir):
        """Test exception handling in price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock exception in _get_yfinance
        monitor._get_yfinance = Mock(side_effect=Exception("Network error"))

        # Test fetch
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Should return empty DataFrame on error
        assert result.empty

    def test_get_current_price_success(self, temp_cache_dir):
        """Test successful current price retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [150.25], "Adj Close": [148.50]}, index=pd.date_range("2023-01-01", periods=1)
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test current price
        current_price = monitor.get_current_price("SPY")

        # Verify auto_adjust=False was used
        mock_stock.history.assert_called_with(period="1d", auto_adjust=False)

        assert current_price == 150.25

    def test_get_current_price_from_cache(self, temp_cache_dir):
        """Test current price retrieval from cache when recent data exists."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Add recent data to cache
        recent_data = pd.DataFrame(
            {"Date": [date.today()], "Close": [145.50], "Adj Close": [143.25]}
        )
        monitor.update_cache("SPY", recent_data)

        # Should return cached price without API call
        current_price = monitor.get_current_price("SPY")
        assert current_price == 145.50

    def test_get_current_price_no_data(self, temp_cache_dir):
        """Test current price retrieval with no data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test current price - should raise exception
        with pytest.raises(ValueError, match="No current price data.*for"):
            monitor.get_current_price("INVALID")

    def test_get_current_price_exception_handling(self, temp_cache_dir):
        """Test exception handling in current price retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock exception in _get_yfinance
        monitor._get_yfinance = Mock(side_effect=Exception("Network error"))

        # Test current price - should raise exception
        with pytest.raises(Exception):
            monitor.get_current_price("SPY")

    def test_get_closing_prices_success(self, temp_cache_dir):
        """Test successful closing prices retrieval as Series."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [100.0, 105.0, 102.0], "Adj Close": [98.0, 103.0, 100.0]},
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test get_closing_prices
        result = monitor.get_closing_prices("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Verify result is a Series
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        assert result.name == "Close"
        assert result.tolist() == [100.0, 105.0, 102.0]

    def test_get_closing_prices_empty(self, temp_cache_dir):
        """Test closing prices retrieval with no data."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock empty response
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test get_closing_prices
        result = monitor.get_closing_prices("INVALID", date(2023, 1, 1), date(2023, 1, 3))

        # Should return empty Series
        assert isinstance(result, pd.Series)
        assert result.empty

    def test_get_adjusted_closing_prices_success(self, temp_cache_dir):
        """
        Test successful adjusted closing prices retrieval as Series.
        **Validates: Requirements 4.1, 4.3**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [100.0, 105.0, 102.0], "Adj Close": [98.0, 103.0, 100.0]},
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test get_adjusted_closing_prices
        result = monitor.get_adjusted_closing_prices("SPY", date(2023, 1, 1), date(2023, 1, 3))

        # Verify result is a Series
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        assert result.name == "Adj Close"
        assert result.tolist() == [98.0, 103.0, 100.0]

        # Verify the method returns Adj Close, not Close prices
        close_result = monitor.get_closing_prices("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert not result.equals(close_result), "Adjusted prices should differ from Close prices"

    def test_get_adjusted_closing_prices_empty(self, temp_cache_dir):
        """
        Test adjusted closing prices retrieval with no data.
        **Validates: Requirements 4.1, 4.3**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock empty response
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test get_adjusted_closing_prices
        result = monitor.get_adjusted_closing_prices("INVALID", date(2023, 1, 1), date(2023, 1, 3))

        # Should return empty Series
        assert isinstance(result, pd.Series)
        assert result.empty

    def test_adjusted_vs_close_prices_distinction(self, temp_cache_dir):
        """
        Test that adjusted closing prices method returns different values than regular closing prices.
        **Validates: Requirements 4.1, 4.3**
        """
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock data where Adj Close differs from Close (typical for dividend-paying stocks)
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {
                "Close": [150.0, 152.0, 151.0],  # Raw closing prices
                "Adj Close": [147.5, 149.5, 148.5],  # Dividend-adjusted prices (lower)
            },
            index=pd.date_range("2023-01-01", periods=3),
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Get both price types
        close_prices = monitor.get_closing_prices(
            "DIVIDEND_STOCK", date(2023, 1, 1), date(2023, 1, 3)
        )
        adj_close_prices = monitor.get_adjusted_closing_prices(
            "DIVIDEND_STOCK", date(2023, 1, 1), date(2023, 1, 3)
        )

        # Verify they are different Series
        assert not close_prices.equals(adj_close_prices), "Close and Adj Close should be different"

        # Verify correct values
        assert close_prices.tolist() == [
            150.0,
            152.0,
            151.0,
        ], "Close prices should match raw closing prices"
        assert adj_close_prices.tolist() == [
            147.5,
            149.5,
            148.5,
        ], "Adj Close prices should match adjusted closing prices"

        # Verify series names
        assert close_prices.name == "Close", "Close prices series should be named 'Close'"
        assert (
            adj_close_prices.name == "Adj Close"
        ), "Adj Close prices series should be named 'Adj Close'"

        # Verify Adj Close <= Close (typical relationship)
        for i in range(len(close_prices)):
            assert (
                adj_close_prices.iloc[i] <= close_prices.iloc[i]
            ), f"Adj Close should be <= Close at index {i}"

    def test_get_latest_closing_price(self, temp_cache_dir):
        """Test latest closing price retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame(
            {"Close": [150.25], "Adj Close": [148.50]}, index=pd.date_range("2023-01-01", periods=1)
        )

        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test latest closing price
        latest_price = monitor.get_latest_closing_price("SPY")

        assert latest_price == 150.25

    def test_calculate_rolling_maximum(self):
        """Test rolling maximum calculation returning single value."""
        monitor = PriceMonitor()

        # Test basic rolling maximum
        prices = pd.Series([100, 95, 90, 105, 110, 85, 95])
        rolling_max = monitor.calculate_rolling_maximum(prices, window_days=3)

        # Should return the latest rolling maximum value
        assert rolling_max == 110.0

    def test_calculate_rolling_maximum_empty(self):
        """Test rolling maximum calculation with empty series."""
        monitor = PriceMonitor()

        prices = pd.Series([], dtype=float)
        rolling_max = monitor.calculate_rolling_maximum(prices, window_days=3)

        assert rolling_max == 0.0

    def test_is_cache_valid(self, temp_cache_dir):
        """Test cache validity checking."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Test with no cached data
        assert not monitor.is_cache_valid("SPY")

        # Add recent data to cache
        recent_data = pd.DataFrame(
            {"Date": [date.today()], "Close": [145.50], "Adj Close": [143.25]}
        )
        monitor.update_cache("SPY", recent_data)

        # Should be valid with default cache days (30)
        assert monitor.is_cache_valid("SPY")
        assert monitor.is_cache_valid("SPY", cache_days=30)

        # Add old data to cache
        old_data = pd.DataFrame(
            {"Date": [date.today() - timedelta(days=35)], "Close": [140.00], "Adj Close": [138.00]}
        )
        monitor.update_cache("OLD", old_data)

        # Should not be valid with default cache days
        assert not monitor.is_cache_valid("OLD")
        assert not monitor.is_cache_valid("OLD", cache_days=30)
        assert monitor.is_cache_valid("OLD", cache_days=40)


class TestPriceMonitorErrorHandling:
    """Test error handling scenarios for PriceMonitor."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_network_failure_during_fetch(self, temp_cache_dir):
        """Test handling of network failures during price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock network failure in yfinance
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.side_effect = ConnectionError("Network connection failed")
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test fetch should return empty DataFrame on network error
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert result.empty

        # Test get_closing_prices should return empty Series on network error
        result_series = monitor.get_closing_prices("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert isinstance(result_series, pd.Series)
        assert result_series.empty

    def test_timeout_during_fetch(self, temp_cache_dir):
        """Test handling of timeout errors during price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock timeout error in yfinance
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.side_effect = TimeoutError("Request timed out")
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test fetch should return empty DataFrame on timeout
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert result.empty

    def test_invalid_ticker_symbol(self, temp_cache_dir):
        """Test handling of invalid ticker symbols."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning empty data for invalid ticker
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()  # Empty response for invalid ticker
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test fetch with invalid ticker
        result = monitor.fetch_price_data("INVALID_TICKER", date(2023, 1, 1), date(2023, 1, 3))
        assert result.empty

        # Test get_closing_prices with invalid ticker
        result_series = monitor.get_closing_prices(
            "INVALID_TICKER", date(2023, 1, 1), date(2023, 1, 3)
        )
        assert isinstance(result_series, pd.Series)
        assert result_series.empty

    def test_invalid_ticker_current_price(self, temp_cache_dir):
        """Test handling of invalid ticker when getting current price."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning empty data for invalid ticker
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Should raise ValueError for invalid ticker
        with pytest.raises(ValueError, match="No current price data.*for.*INVALID"):
            monitor.get_current_price("INVALID_TICKER")

    def test_missing_data_for_date_range(self, temp_cache_dir):
        """Test handling when no data is available for a specific date range."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning empty data for the requested date range
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test with a date range that has no data
        result = monitor.fetch_price_data("SPY", date(1900, 1, 1), date(1900, 1, 3))
        assert result.empty

        # Test get_closing_prices with missing data
        result_series = monitor.get_closing_prices("SPY", date(1900, 1, 1), date(1900, 1, 3))
        assert isinstance(result_series, pd.Series)
        assert result_series.empty

    def test_partial_data_availability(self, temp_cache_dir):
        """Test handling when only partial data is available for a date range."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning partial data (only 1 day out of 3 requested)
        mock_yf = Mock()
        mock_stock = Mock()
        partial_data = pd.DataFrame(
            {"Close": [100.0], "Adj Close": [98.0]}, index=pd.date_range("2023-01-02", periods=1)
        )
        mock_stock.history.return_value = partial_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Should return the available data
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert len(result) == 1
        assert result["Close"].iloc[0] == 100.0
        assert result["Adj Close"].iloc[0] == 98.0
        assert result["Date"].iloc[0] == date(2023, 1, 2)

    def test_yfinance_import_error(self, temp_cache_dir):
        """Test handling of yfinance import errors."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock import error
        def mock_import_error():
            raise ImportError("yfinance module not found")

        monitor._get_yfinance = mock_import_error

        # Should return empty DataFrame when import fails (graceful handling)
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 3))
        assert result.empty

    def test_malformed_api_response(self, temp_cache_dir):
        """Test handling of malformed API responses."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning malformed data (missing Close column)
        mock_yf = Mock()
        mock_stock = Mock()
        malformed_data = pd.DataFrame(
            {
                "Open": [100.0, 105.0],
                "High": [102.0, 107.0]
                # Missing 'Close' column
            },
            index=pd.date_range("2023-01-01", periods=2),
        )
        mock_stock.history.return_value = malformed_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Should handle missing Close column gracefully and return empty DataFrame
        result = monitor.fetch_price_data("SPY", date(2023, 1, 1), date(2023, 1, 2))
        assert result.empty

    def test_cache_file_corruption_handling(self, temp_cache_dir):
        """Test handling of corrupted cache files."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create a corrupted cache file
        cache_file = monitor._get_cache_file_path("SPY")
        with open(cache_file, "w") as f:
            f.write("invalid json content {")

        # Should handle corrupted cache gracefully and return None
        result = monitor._load_cached_data("SPY")
        assert result is None

    def test_cache_permission_error(self, temp_cache_dir):
        """Test handling of cache file permission errors."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Create valid data to save
        data = pd.DataFrame({"Date": [date(2023, 1, 1)], "Close": [100.0]})

        # Mock permission error during save
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            # Should handle permission error gracefully (no exception raised)
            monitor._save_cached_data("SPY", data)
            # The method should log a warning but not raise an exception

    def test_network_error_current_price(self, temp_cache_dir):
        """Test network error handling when getting current price."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock network error in yfinance
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.side_effect = ConnectionError("Network error")
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Should raise the network error
        with pytest.raises(ConnectionError, match="Network error"):
            monitor.get_current_price("SPY")

    def test_weekend_holiday_handling(self, temp_cache_dir):
        """Test handling of weekend and holiday date requests."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)

        # Mock yfinance returning empty data for weekend
        mock_yf = Mock()
        mock_stock = Mock()
        mock_stock.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)

        # Test with a Saturday (weekend)
        saturday = date(2023, 1, 7)  # This was a Saturday
        result = monitor.fetch_price_data("SPY", saturday, saturday)
        assert result.empty

        # Test with Christmas Day (holiday)
        christmas = date(2023, 12, 25)
        result = monitor.fetch_price_data("SPY", christmas, christmas)
        assert result.empty

    def test_empty_cache_directory_creation_failure(self):
        """Test handling when cache directory cannot be created."""
        # Try to create cache in a location that should fail (like root)
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                PriceMonitor(cache_dir="/root/impossible_cache_dir")
