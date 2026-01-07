"""
Dollar-Cost Averaging (DCA) controller module.

This module manages DCA sessions using a state machine pattern,
handling session lifecycle, investment processing, and completion detection.
"""

from .dca_controller import DCAController
from .models import DCASession, DCAState

__all__ = ["DCAController", "DCASession", "DCAState"]
