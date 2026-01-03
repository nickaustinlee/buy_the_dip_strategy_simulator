"""
Integration tests for complete daily evaluation workflow.

These tests verify the end-to-end functionality of the buy-the-dip strategy
by testing the complete daily evaluation process with real components.
"""

import pytest
import tempfile
import shutil
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.config.config_manager import ConfigurationManager
from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.price_monitor.price_monitor import PriceMonitor
from buy_the_dip.investment_tracker import InvestmentTracker
from buy_the_dip.models import Investment


class TestDailyEvaluationWorkflow:
    """Test complete daily evaluation workflow."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return StrategyConfig(
            ticker="SPY",
            rolling_window_days=30,
            percentage_trigger=0.90,
            monthly_dca_amount=1000.0,
            data_cache_days=7
        )
    
    @pytest.fixture
    def mock_price_data(self):
        """Create mock price data for testing."""
        # Create 60 days of price data with a clear dip pattern
        base_date = date(2024, 1, 1)
        dates = [base_date + timedelta(days=i) for i in range(60)]
        
        # Create price pattern: high prices, then a dip, then recovery
        prices = []
        for i, d in enumerate(dates):
            if i < 20:
                # High prices (around $100)
                price = 100.0 + (i * 0.5)  # Gradual increase
            elif i < 35:
                # Dip period (down to $85)
                price = 110.0 - ((i - 20) * 1.5)  # Sharp decline
            else:
                # Recovery period
                price = 87.5 + ((i - 35) * 0.8)  # Gradual recovery
            prices.append(price)
        
        return pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Open': [p * 0.99 for p in prices],  # Slightly lower opens
            'High': [p * 1.01 for p in prices],  # Slightly higher highs
            'Low': [p * 0.98 for p in prices],   # Slightly lower lows
            'Volume': [1000000] * len(dates)
        })
    
    def test_complete_daily_evaluation_no_investment(self, test_config, mock_price_data, temp_dir):
        """Test daily evaluation when no investment should be made."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Mock price data fetch to return our test data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = mock_price_data.set_index('Date')['Close']
            
            # Evaluate a day when price is high (should not trigger)
            evaluation_date = date(2024, 1, 15)  # Day 14, price should be high
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify no investment was made
            assert not result.investment_executed
            assert result.investment is None
            assert not result.trigger_met  # Price should be above trigger
            assert not result.recent_investment_exists  # No previous investments
            
            # Verify result structure
            assert result.evaluation_date == evaluation_date
            assert result.yesterday_price > 0
            assert result.trigger_price > 0
            assert result.rolling_maximum > 0
            assert result.trigger_price == result.rolling_maximum * test_config.percentage_trigger
    
    def test_complete_daily_evaluation_with_investment(self, test_config, mock_price_data, temp_dir):
        """Test daily evaluation when investment should be made."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Mock price data fetch to return our test data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = mock_price_data.set_index('Date')['Close']
            
            # Evaluate a day during the dip (should trigger investment)
            evaluation_date = date(2024, 1, 30)  # Day 29, price should be low
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify investment was made
            assert result.investment_executed
            assert result.investment is not None
            assert result.trigger_met  # Price should be below trigger
            assert not result.recent_investment_exists  # No previous investments
            
            # Verify investment details
            investment = result.investment
            assert investment.date == evaluation_date
            assert investment.ticker == test_config.ticker
            assert investment.amount == test_config.monthly_dca_amount
            assert investment.price > 0
            assert investment.shares == investment.amount / investment.price
            
            # Verify investment was added to tracker
            all_investments = investment_tracker.get_all_investments()
            assert len(all_investments) == 1
            assert all_investments[0].date == evaluation_date
    
    def test_daily_evaluation_with_28_day_constraint(self, test_config, mock_price_data, temp_dir):
        """Test that 28-day constraint prevents duplicate investments."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Add a recent investment (within 28 days)
        recent_investment = Investment(
            date=date(2024, 1, 15),
            ticker=test_config.ticker,
            price=95.0,
            amount=1000.0,
            shares=10.526
        )
        investment_tracker.add_investment(recent_investment)
        
        # Mock price data fetch to return our test data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = mock_price_data.set_index('Date')['Close']
            
            # Evaluate a day during the dip (would normally trigger, but blocked by constraint)
            evaluation_date = date(2024, 1, 30)  # 15 days after previous investment
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify investment was blocked
            assert not result.investment_executed
            assert result.investment is None
            assert result.trigger_met  # Price condition met
            assert result.recent_investment_exists  # But blocked by constraint
            
            # Verify no new investment was added
            all_investments = investment_tracker.get_all_investments()
            assert len(all_investments) == 1  # Only the original investment
    
    def test_daily_evaluation_after_28_days(self, test_config, mock_price_data, temp_dir):
        """Test that investment is allowed after 28 days."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Add an old investment (more than 28 days ago)
        old_investment = Investment(
            date=date(2023, 12, 1),  # More than 28 days before our test date
            ticker=test_config.ticker,
            price=95.0,
            amount=1000.0,
            shares=10.526
        )
        investment_tracker.add_investment(old_investment)
        
        # Mock price data fetch to return our test data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = mock_price_data.set_index('Date')['Close']
            
            # Evaluate a day during the dip (should trigger investment)
            evaluation_date = date(2024, 1, 30)
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify investment was made
            assert result.investment_executed
            assert result.investment is not None
            assert result.trigger_met
            assert not result.recent_investment_exists  # Old investment doesn't count
            
            # Verify new investment was added
            all_investments = investment_tracker.get_all_investments()
            assert len(all_investments) == 2  # Original + new investment
            
            # Find the new investment
            new_investments = [inv for inv in all_investments if inv.date == evaluation_date]
            assert len(new_investments) == 1
    
    def test_daily_evaluation_insufficient_data(self, test_config, temp_dir):
        """Test daily evaluation with insufficient historical data."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Create minimal price data (less than rolling window)
        minimal_data = pd.DataFrame({
            'Date': [date(2024, 1, 1), date(2024, 1, 2)],
            'Close': [100.0, 95.0]
        })
        
        # Mock price data fetch to return minimal data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = minimal_data.set_index('Date')['Close']
            
            # Should still work with available data (with warning)
            evaluation_date = date(2024, 1, 2)
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify evaluation completed despite insufficient data
            assert result.evaluation_date == evaluation_date
            assert result.yesterday_price > 0
            assert result.trigger_price > 0
            assert result.rolling_maximum > 0
    
    def test_daily_evaluation_no_data_error(self, test_config, temp_dir):
        """Test daily evaluation with no price data."""
        # Set up components
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Mock price data fetch to return empty data
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = pd.Series(dtype=float)
            
            # Should raise ValueError for no data
            evaluation_date = date(2024, 1, 15)
            with pytest.raises(ValueError, match="No price data available"):
                strategy_system.evaluate_trading_day(evaluation_date)
    
    def test_configuration_integration(self, temp_dir):
        """Test integration with configuration management."""
        # Create test config file
        config_file = temp_dir / "test_config.yaml"
        config_content = """
ticker: "AAPL"
rolling_window_days: 45
percentage_trigger: 0.85
monthly_dca_amount: 1500.0
data_cache_days: 14
"""
        config_file.write_text(config_content)
        
        # Load configuration
        config_manager = ConfigurationManager()
        config = config_manager.load_config(str(config_file))
        
        # Verify configuration loaded correctly
        assert config.ticker == "AAPL"
        assert config.rolling_window_days == 45
        assert config.percentage_trigger == 0.85
        assert config.monthly_dca_amount == 1500.0
        assert config.data_cache_days == 14
        
        # Test strategy system with loaded config
        strategy_system = StrategySystem(config)
        assert strategy_system.config.ticker == "AAPL"
        assert strategy_system.config.monthly_dca_amount == 1500.0
    
    def test_investment_persistence_integration(self, test_config, mock_price_data, temp_dir):
        """Test integration with investment persistence."""
        # Set up components with persistent storage
        price_monitor = PriceMonitor()
        investment_tracker = InvestmentTracker(data_dir=str(temp_dir))
        
        strategy_system = StrategySystem(test_config, price_monitor, investment_tracker)
        
        # Mock price data fetch
        with patch.object(price_monitor, 'get_closing_prices') as mock_get_prices:
            mock_get_prices.return_value = mock_price_data.set_index('Date')['Close']
            
            # Make an investment
            evaluation_date = date(2024, 1, 30)
            result = strategy_system.evaluate_trading_day(evaluation_date)
            
            # Verify investment was made
            assert result.investment_executed
            
            # Save investments to file
            success = investment_tracker.save_to_file()
            assert success
            
            # Verify file exists
            persistence_file = temp_dir / "investments.json"
            assert persistence_file.exists()
            
            # Create new tracker and load from file
            new_tracker = InvestmentTracker(data_dir=str(temp_dir))
            success = new_tracker.load_from_file()
            assert success
            
            # Verify investment was loaded
            loaded_investments = new_tracker.get_all_investments()
            assert len(loaded_investments) == 1
            assert loaded_investments[0].date == evaluation_date
            assert loaded_investments[0].amount == test_config.monthly_dca_amount