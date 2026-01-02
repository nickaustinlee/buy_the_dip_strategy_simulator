"""
Strategy engine module for orchestrating the buy-the-dip trading strategy.

This module coordinates between price monitoring, DCA sessions, and configuration
to execute the overall trading strategy.
"""

from .strategy_engine import StrategyEngine
from .backtest_engine import BacktestEngine

__all__ = ["StrategyEngine", "BacktestEngine"]