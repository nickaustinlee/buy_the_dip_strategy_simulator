"""
Unit tests for strategy engine functionality.
"""

import pytest
import tempfile
import shutil
from datetime import date, timedelta
from unittest.mock import Mock, patch
import pandas as pd

from buy_the_dip.strategy_engine import StrategyEngine
from buy_the_dip.config import StrategyConfig
from buy_the_dip.price_monitor import PriceMonitor
from buy_the_dip.models import MarketStatus


class TestStrategyEngine:
    """Test StrategyEngine class."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return StrategyConfig(
            ticker="SPY", rolling_window_days=30, percentage_trigger=0.90, monthly_dca_amount=2000.0
        )

    @pytest.fixture
    def engine_with_mock_data(self, config, temp_cache_dir):
        """Create a strategy engine with mock price data."""
        engine = StrategyEngine()
        engine.price_monitor = PriceMonitor(cache_dir=temp_cache_dir)
        engine.initialize(config)

        # Create controlled mock price data - prices around 450 with small variations
        dates = [date.today() - timedelta(days=i) for i in range(35, 0, -1)]
        prices = []
        for i in range(len(dates)):
            # Create prices that stay around 450 with small variations
            base_price = 450.0
            variation = (i % 5) - 2  # -2 to +2 variation
            prices.append(base_price + variation)

        mock_data = pd.DataFrame({"Date": dates, "Close": prices})

        engine.price_monitor.update_cache("SPY", mock_data)
        return engine, prices

    def test_strategy_engine_initialization(self, config):
        """Test strategy engine initialization."""
        engine = StrategyEngine()
        assert not engine._initialized

        engine.initialize(config)
        assert engine._initialized
        assert engine.config == config

    def test_get_market_status_not_initialized(self):
        """Test market status fails when not initialized."""
        engine = StrategyEngine()

        with pytest.raises(RuntimeError, match="Strategy engine not initialized"):
            engine.get_market_status()

    def test_get_market_status_buy_signal(self, engine_with_mock_data):
        """Test market status when in buy-the-dip territory."""
        engine, prices = engine_with_mock_data

        # Mock current price to be below trigger (10% drop from max)
        max_price = max(prices)  # Should be around 452
        trigger_price = max_price * 0.90
        current_price = trigger_price - 5.0  # Below trigger

        def mock_get_current_price(ticker):
            return current_price

        # Mock fetch_price_data to return our controlled data
        def mock_fetch_price_data(ticker, start_date, end_date):
            dates = [date.today() - timedelta(days=i) for i in range(35, 0, -1)]
            mock_prices = []
            for i in range(len(dates)):
                base_price = 450.0
                variation = (i % 5) - 2
                mock_prices.append(base_price + variation)

            return pd.DataFrame({"Date": dates, "Close": mock_prices})

        engine.price_monitor.get_current_price = mock_get_current_price
        engine.price_monitor.fetch_price_data = mock_fetch_price_data

        status = engine.get_market_status()

        assert isinstance(status, MarketStatus)
        assert status.ticker == "SPY"
        assert status.current_price == current_price
        assert status.is_buy_the_dip_time is True
        assert status.recommendation == "BUY"
        assert status.percentage_from_max < -10  # More than 10% drop

    def test_get_market_status_hold_signal(self, engine_with_mock_data):
        """Test market status when not in buy-the-dip territory."""
        engine, prices = engine_with_mock_data

        # Mock current price to be well above trigger
        max_price = max(prices)  # Should be around 452
        current_price = max_price + 10.0  # Above recent high

        def mock_get_current_price(ticker):
            return current_price

        # Mock fetch_price_data to return our controlled data
        def mock_fetch_price_data(ticker, start_date, end_date):
            dates = [date.today() - timedelta(days=i) for i in range(35, 0, -1)]
            mock_prices = []
            for i in range(len(dates)):
                base_price = 450.0
                variation = (i % 5) - 2
                mock_prices.append(base_price + variation)

            return pd.DataFrame({"Date": dates, "Close": mock_prices})

        engine.price_monitor.get_current_price = mock_get_current_price
        engine.price_monitor.fetch_price_data = mock_fetch_price_data

        status = engine.get_market_status()

        assert isinstance(status, MarketStatus)
        assert status.ticker == "SPY"
        assert status.current_price == current_price
        assert status.is_buy_the_dip_time is False
        assert status.recommendation in ["HOLD", "MONITOR"]
        assert status.percentage_from_max > 0  # Above recent high

    def test_get_market_status_monitor_signal(self, engine_with_mock_data):
        """Test market status when close to trigger."""
        engine, prices = engine_with_mock_data

        # Mock current price to be just above trigger
        max_price = max(prices)  # Should be around 452
        trigger_price = max_price * 0.90  # 90% of max
        current_price = trigger_price + 2.0  # Just above trigger

        def mock_get_current_price(ticker):
            return current_price

        # Mock fetch_price_data to return our controlled data
        def mock_fetch_price_data(ticker, start_date, end_date):
            dates = [date.today() - timedelta(days=i) for i in range(35, 0, -1)]
            mock_prices = []
            for i in range(len(dates)):
                base_price = 450.0
                variation = (i % 5) - 2
                mock_prices.append(base_price + variation)

            return pd.DataFrame({"Date": dates, "Close": mock_prices})

        engine.price_monitor.get_current_price = mock_get_current_price
        engine.price_monitor.fetch_price_data = mock_fetch_price_data

        status = engine.get_market_status()

        assert isinstance(status, MarketStatus)
        assert status.ticker == "SPY"
        assert status.current_price == current_price
        assert status.is_buy_the_dip_time is False
        assert status.recommendation == "MONITOR"

    def test_generate_recommendation_deep_dip(self):
        """Test recommendation generation for deep dip scenario."""
        engine = StrategyEngine()

        recommendation, confidence, message = engine._generate_recommendation(
            current_price=400.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-20.0,  # 20% drop
            is_buy_the_dip_time=True,
        )

        assert recommendation == "BUY"
        assert confidence == "HIGH"
        assert "STRONG BUY SIGNAL" in message
        assert "20.0%" in message

    def test_generate_recommendation_moderate_dip(self):
        """Test recommendation generation for moderate dip scenario."""
        engine = StrategyEngine()

        recommendation, confidence, message = engine._generate_recommendation(
            current_price=425.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-15.0,  # 15% drop
            is_buy_the_dip_time=True,
        )

        assert recommendation == "BUY"
        assert confidence == "HIGH"
        assert "STRONG BUY SIGNAL" in message

    def test_generate_recommendation_small_dip(self):
        """Test recommendation generation for small dip scenario."""
        engine = StrategyEngine()

        recommendation, confidence, message = engine._generate_recommendation(
            current_price=445.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-11.0,  # 11% drop
            is_buy_the_dip_time=True,
        )

        assert recommendation == "BUY"
        assert confidence == "MEDIUM"
        assert "BUY SIGNAL" in message

    def test_generate_recommendation_close_to_trigger(self):
        """Test recommendation generation when close to trigger."""
        engine = StrategyEngine()

        recommendation, confidence, message = engine._generate_recommendation(
            current_price=455.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-9.0,  # 9% drop, but above trigger
            is_buy_the_dip_time=False,
        )

        assert recommendation == "MONITOR"
        assert confidence == "HIGH"
        assert "WATCH CLOSELY" in message

    def test_generate_recommendation_far_from_trigger(self):
        """Test recommendation generation when far from trigger."""
        engine = StrategyEngine()

        # Use a price that's definitely far from trigger
        # If trigger is 450 and current is 400, distance = ((450-400)/400)*100 = 12.5% > 5%
        recommendation, confidence, message = engine._generate_recommendation(
            current_price=400.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-20.0,  # 20% below max, but above trigger (not buy time)
            is_buy_the_dip_time=False,  # Key: not in buy territory
        )

        # Distance to trigger is ((450-400)/400)*100 = 12.5% > 5%, so should be HOLD
        assert recommendation == "HOLD"
        assert confidence == "LOW"
        assert "HOLD" in message

    def test_get_quick_status(self, engine_with_mock_data):
        """Test quick status generation."""
        engine, prices = engine_with_mock_data

        # Mock current price
        current_price = 400.0

        def mock_get_current_price(ticker):
            return current_price

        engine.price_monitor.get_current_price = mock_get_current_price

        quick_status = engine.get_quick_status()

        assert isinstance(quick_status, str)
        assert "SPY" in quick_status
        assert "$400.00" in quick_status

    def test_get_quick_status_error_handling(self, config):
        """Test quick status error handling."""
        engine = StrategyEngine()
        engine.initialize(config)

        # Mock an error in get_market_status
        def mock_error():
            raise Exception("Network error")

        engine.get_market_status = mock_error

        quick_status = engine.get_quick_status()

        assert "Error getting status" in quick_status
        assert "Network error" in quick_status

    def test_market_status_model_validation(self):
        """Test MarketStatus model validation."""
        status = MarketStatus(
            ticker="SPY",
            current_price=450.0,
            rolling_max_price=500.0,
            trigger_price=450.0,
            percentage_from_max=-10.0,
            is_buy_the_dip_time=True,
            recommendation="BUY",
            confidence_level="HIGH",
            message="Test message",
        )

        assert status.ticker == "SPY"
        assert status.current_price == 450.0
        assert status.is_buy_the_dip_time is True
        assert status.recommendation == "BUY"
        assert status.confidence_level == "HIGH"

    def test_market_status_model_invalid_price(self):
        """Test MarketStatus model with invalid price."""
        with pytest.raises(ValueError):
            MarketStatus(
                ticker="SPY",
                current_price=-10.0,  # Invalid negative price
                rolling_max_price=500.0,
                trigger_price=450.0,
                percentage_from_max=-10.0,
                is_buy_the_dip_time=True,
                recommendation="BUY",
                confidence_level="HIGH",
                message="Test message",
            )

    def test_format_comprehensive_report(self, engine_with_mock_data):
        """Test comprehensive report formatting."""
        from datetime import date

        engine, prices = engine_with_mock_data

        mock_report = Mock()
        mock_report.ticker = "SPY"
        mock_report.total_invested = 2000.0
        mock_report.total_shares = 16.67
        mock_report.current_value = 2000.4
        mock_report.total_return = 0.4
        mock_report.percentage_return = 0.0002
        mock_report.active_sessions_count = 1
        mock_report.completed_sessions_count = 0

        formatted_report = engine.format_comprehensive_report(mock_report, [])

        # Verify key elements are in the formatted report
        assert "Buy-the-Dip Strategy Report for SPY" in formatted_report
        assert "Total Invested: $2,000.00" in formatted_report
