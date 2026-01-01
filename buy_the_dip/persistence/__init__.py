"""
Data persistence module for the buy-the-dip strategy.

This module handles saving and loading strategy state to/from persistent storage,
including error handling for corrupted files and recovery mechanisms.
"""

from .state_manager import StateManager

__all__ = ['StateManager']