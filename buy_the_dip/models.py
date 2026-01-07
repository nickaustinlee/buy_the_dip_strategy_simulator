"""
Shared data models for the buy-the-dip strategy.
"""

from datetime import date, datetime
from typing import List, Dict, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
import uuid

from .config.models import StrategyConfig
from .dca_controller.models import DCASession


class Transaction(BaseModel):
    """Model for investment transactions."""

    model_config = ConfigDict(validate_assignment=True)

    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    date: date
    price: float = Field(gt=0.0)
    shares: float = Field(gt=0.0)
    amount: float = Field(gt=0.0)
    transaction_type: Literal["buy"] = "buy"


class MarketStatus(BaseModel):
    """Model for current market status and buy-the-dip recommendation."""

    model_config = ConfigDict(validate_assignment=True)

    ticker: str
    current_price: float = Field(gt=0.0)
    rolling_max_price: float = Field(gt=0.0)
    trigger_price: float = Field(gt=0.0)
    percentage_from_max: float  # Can be negative
    is_buy_the_dip_time: bool
    recommendation: Literal["BUY", "HOLD", "MONITOR"]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    days_since_trigger: Optional[int] = None
    message: str
    last_updated: datetime = Field(default_factory=datetime.now)


class StrategyState(BaseModel):
    """Model for persisting strategy state."""

    model_config = ConfigDict(validate_assignment=True)

    config: StrategyConfig
    active_sessions: List[DCASession] = Field(default_factory=list)
    completed_sessions: List[DCASession] = Field(default_factory=list)
    all_transactions: List[Transaction] = Field(default_factory=list)
    last_update: datetime = Field(default_factory=datetime.now)
    price_cache: Dict[str, List[Dict]] = Field(default_factory=dict)


class StrategyReport(BaseModel):
    """Model for strategy performance reporting."""

    model_config = ConfigDict(validate_assignment=True)

    ticker: str
    total_invested: float = Field(ge=0.0)
    total_shares: float = Field(ge=0.0)
    current_value: float = Field(ge=0.0)
    total_return: float
    percentage_return: float
    active_sessions_count: int = Field(default=0, ge=0)
    completed_sessions_count: int = Field(default=0, ge=0)


class Investment(BaseModel):
    """Model for individual investment records."""

    model_config = ConfigDict(validate_assignment=True)

    date: date
    ticker: str
    price: float = Field(gt=0.0, description="Closing price on investment date")
    amount: float = Field(gt=0.0, description="Dollar amount invested")
    shares: float = Field(gt=0.0, description="Number of shares purchased (amount / price)")


class PortfolioMetrics(BaseModel):
    """Model for portfolio performance metrics."""

    model_config = ConfigDict(validate_assignment=True)

    total_invested: float = Field(ge=0.0, description="Total dollar amount invested")
    total_shares: float = Field(ge=0.0, description="Total shares owned")
    current_value: float = Field(
        ge=0.0, description="Current portfolio value (total_shares * current_price)"
    )
    total_return: float = Field(description="Total return (current_value - total_invested)")
    percentage_return: float = Field(
        description="Percentage return (total_return / total_invested)"
    )
