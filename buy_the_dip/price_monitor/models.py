"""
Data models for price monitoring.
"""

from datetime import date
from pydantic import BaseModel, ConfigDict


class PriceData(BaseModel):
    """Model for stock price data."""

    model_config = ConfigDict(validate_assignment=True)

    date: date
    close: float
    volume: int
