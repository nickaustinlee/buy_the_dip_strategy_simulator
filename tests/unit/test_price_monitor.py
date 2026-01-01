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
        price_data = PriceData(
            date=date(2023, 1, 15),
            close=150.25,
            volume=1000000
        )
        
        assert price_data.date == date(2023, 1, 15)
        assert price_data.close == 150.25
        assert price_data.volume == 1000000
    
    def test_price_data_validation(self):
        """Test PriceData model validation."""
        # Valid data should work
        price_data = PriceData(
            date=date.today(),
            close=100.0,
            volume=500000
        )
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
        data = pd.DataFrame({
            'Date': [date(2023, 1, 1), date(2023, 1, 2)],
            'Close': [100.0, 105.0]
        })
        
        # Update cache
        monitor.update_cache('SPY', data)
        
        # Verify in-memory cache was updated
        assert 'SPY' in monitor._cache
        assert 'SPY' in monitor._cache_timestamps
        assert len(monitor._cache['SPY']) == 2
        pd.testing.assert_frame_equal(monitor._cache['SPY'], data)
        
        # Verify persistent cache was created
        cache_file = monitor._get_cache_file_path('SPY')
        assert cache_file.exists()
    
    def test_persistent_cache_load_save(self, temp_cache_dir):
        """Test loading and saving persistent cache."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Create test data
        data = pd.DataFrame({
            'Date': [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)],
            'Close': [100.0, 105.0, 102.0]
        })
        
        # Save to cache
        monitor._save_cached_data('TEST', data)
        
        # Load from cache
        loaded_data = monitor._load_cached_data('TEST')
        
        # Verify data matches
        assert loaded_data is not None
        assert len(loaded_data) == 3
        pd.testing.assert_frame_equal(loaded_data, data)
    
    def test_cache_info(self, temp_cache_dir):
        """Test cache information retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Test with no cached data
        info = monitor.get_cache_info('SPY')
        assert info['cached'] is False
        assert info['records'] == 0
        
        # Add some cached data
        data = pd.DataFrame({
            'Date': [date(2023, 1, 1), date(2023, 1, 2)],
            'Close': [100.0, 105.0]
        })
        monitor.update_cache('SPY', data)
        
        # Test with cached data
        info = monitor.get_cache_info('SPY')
        assert info['cached'] is True
        assert info['records'] == 2
        assert info['date_range']['start'] == '2023-01-01'
        assert info['date_range']['end'] == '2023-01-02'
    
    def test_clear_cache(self, temp_cache_dir):
        """Test cache clearing functionality."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Add some cached data
        data = pd.DataFrame({
            'Date': [date(2023, 1, 1)],
            'Close': [100.0]
        })
        monitor.update_cache('SPY', data)
        monitor.update_cache('AAPL', data)
        
        # Clear specific ticker
        monitor.clear_cache('SPY')
        assert 'SPY' not in monitor._cache
        assert 'AAPL' in monitor._cache
        
        # Clear all
        monitor.clear_cache()
        assert len(monitor._cache) == 0
    
    def test_fetch_price_data_success(self, temp_cache_dir):
        """Test successful price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Mock the _get_yfinance method to avoid SSL issues
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({
            'Close': [100.0, 105.0, 102.0]
        }, index=pd.date_range('2023-01-01', periods=3))
        
        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)
        
        # Test fetch
        result = monitor.fetch_price_data('SPY', date(2023, 1, 1), date(2023, 1, 3))
        
        # Verify result
        assert len(result) == 3
        assert 'Date' in result.columns
        assert 'Close' in result.columns
        assert result['Close'].tolist() == [100.0, 105.0, 102.0]
        
        # Verify data was cached
        cache_info = monitor.get_cache_info('SPY')
        assert cache_info['cached'] is True
    
    def test_fetch_price_data_with_cache(self, temp_cache_dir):
        """Test fetching price data when some data is already cached."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Pre-populate cache with some data
        cached_data = pd.DataFrame({
            'Date': [date(2023, 1, 1), date(2023, 1, 2)],
            'Close': [100.0, 105.0]
        })
        monitor.update_cache('SPY', cached_data)
        
        # Mock API for additional data
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({
            'Close': [102.0]
        }, index=pd.date_range('2023-01-03', periods=1))
        
        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)
        
        # Fetch data that spans cached and new data
        result = monitor.fetch_price_data('SPY', date(2023, 1, 1), date(2023, 1, 3))
        
        # Should return all three days
        assert len(result) == 3
        assert result['Close'].tolist() == [100.0, 105.0, 102.0]
    
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
        result = monitor.fetch_price_data('INVALID', date(2023, 1, 1), date(2023, 1, 3))
        
        # Should return empty DataFrame
        assert result.empty
    
    def test_fetch_price_data_exception_handling(self, temp_cache_dir):
        """Test exception handling in price data fetching."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Mock exception in _get_yfinance
        monitor._get_yfinance = Mock(side_effect=Exception("Network error"))
        
        # Test fetch
        result = monitor.fetch_price_data('SPY', date(2023, 1, 1), date(2023, 1, 3))
        
        # Should return empty DataFrame on error
        assert result.empty
    
    def test_get_current_price_success(self, temp_cache_dir):
        """Test successful current price retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Mock the _get_yfinance method
        mock_yf = Mock()
        mock_stock = Mock()
        mock_history_data = pd.DataFrame({
            'Close': [150.25]
        }, index=pd.date_range('2023-01-01', periods=1))
        
        mock_stock.history.return_value = mock_history_data
        mock_yf.Ticker.return_value = mock_stock
        monitor._get_yfinance = Mock(return_value=mock_yf)
        
        # Test current price
        current_price = monitor.get_current_price('SPY')
        
        assert current_price == 150.25
    
    def test_get_current_price_from_cache(self, temp_cache_dir):
        """Test current price retrieval from cache when recent data exists."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Add recent data to cache
        recent_data = pd.DataFrame({
            'Date': [date.today()],
            'Close': [145.50]
        })
        monitor.update_cache('SPY', recent_data)
        
        # Should return cached price without API call
        current_price = monitor.get_current_price('SPY')
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
        with pytest.raises(ValueError, match="No current price data for"):
            monitor.get_current_price('INVALID')
    
    def test_get_current_price_exception_handling(self, temp_cache_dir):
        """Test exception handling in current price retrieval."""
        monitor = PriceMonitor(cache_dir=temp_cache_dir)
        
        # Mock exception in _get_yfinance
        monitor._get_yfinance = Mock(side_effect=Exception("Network error"))
        
        # Test current price - should raise exception
        with pytest.raises(Exception):
            monitor.get_current_price('SPY')