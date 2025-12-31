"""
Basic test to verify the testing framework is working.
"""

from buy_the_dip.config.models import StrategyConfig


def test_strategy_config_creation():
    """Test that StrategyConfig can be created with defaults."""
    config = StrategyConfig()
    
    assert config.ticker == "SPY"
    assert config.rolling_window_days == 90
    assert config.percentage_trigger == 0.90
    assert config.monthly_dca_amount == 2000.0
    assert config.data_cache_days == 30


def test_strategy_config_validation():
    """Test that StrategyConfig validates input parameters."""
    # Valid configuration
    config = StrategyConfig(
        ticker="AAPL",
        rolling_window_days=60,
        percentage_trigger=0.85,
        monthly_dca_amount=1500.0,
        data_cache_days=15
    )
    
    assert config.ticker == "AAPL"
    assert config.rolling_window_days == 60
    assert config.percentage_trigger == 0.85
    assert config.monthly_dca_amount == 1500.0
    assert config.data_cache_days == 15