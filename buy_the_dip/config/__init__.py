"""
Configuration management module for the buy-the-dip strategy.

This module handles loading, validating, and managing YAML configuration files
using Pydantic for robust validation and type safety.
"""

from .config_manager import ConfigurationManager
from .models import StrategyConfig

__all__ = ["ConfigurationManager", "StrategyConfig"]