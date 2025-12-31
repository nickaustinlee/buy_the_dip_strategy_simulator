"""
Buy the Dip Strategy - A Python-based stock trading strategy simulator.

This package implements a dollar-cost averaging approach during market downturns,
monitoring configurable stock tickers and automatically triggering investment
when prices drop below a threshold relative to recent highs.
"""

__version__ = "0.1.0"
__author__ = "Buy the Dip Strategy Team"

# Lazy imports to avoid dependency issues during package setup
__all__ = [
    "ConfigurationManager",
    "StrategyConfig", 
    "PriceMonitor",
    "PriceData",
    "DCAController",
    "DCASession", 
    "DCAState",
    "StrategyEngine",
    "Transaction",
    "StrategyState",
]

def __getattr__(name):
    """Lazy import for package components."""
    if name == "ConfigurationManager":
        from .config import ConfigurationManager
        return ConfigurationManager
    elif name == "StrategyConfig":
        from .config import StrategyConfig
        return StrategyConfig
    elif name == "PriceMonitor":
        from .price_monitor import PriceMonitor
        return PriceMonitor
    elif name == "PriceData":
        from .price_monitor import PriceData
        return PriceData
    elif name == "DCAController":
        from .dca_controller import DCAController
        return DCAController
    elif name == "DCASession":
        from .dca_controller import DCASession
        return DCASession
    elif name == "DCAState":
        from .dca_controller import DCAState
        return DCAState
    elif name == "StrategyEngine":
        from .strategy_engine import StrategyEngine
        return StrategyEngine
    elif name == "Transaction":
        from .models import Transaction
        return Transaction
    elif name == "StrategyState":
        from .models import StrategyState
        return StrategyState
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")