"""
Configuration models using Pydantic for validation.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class StrategyConfig(BaseModel):
    """Configuration model for the buy-the-dip strategy."""
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    ticker: str = Field(default="SPY", description="Stock ticker symbol to monitor")
    rolling_window_days: int = Field(
        default=90, 
        ge=1, 
        le=365, 
        description="Number of days for rolling maximum calculation"
    )
    percentage_trigger: float = Field(
        default=0.90, 
        gt=0.0, 
        le=1.0, 
        description="Percentage of rolling maximum that triggers DCA"
    )
    monthly_dca_amount: float = Field(
        default=2000.0, 
        gt=0.0, 
        description="Monthly dollar amount for DCA investments"
    )
    data_cache_days: int = Field(
        default=30, 
        ge=1, 
        description="Number of days to cache price data"
    )
    use_trading_days: bool = Field(
        default=False,
        description="If True, use trading days for rolling window; if False, use calendar days"
    )