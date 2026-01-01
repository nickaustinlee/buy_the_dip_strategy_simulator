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
    
    # CAGR Analysis metrics
    cagr_analysis: Optional["CAGRAnalysis"] = None
    analysis_period_days: Optional[int] = None


class CAGRAnalysis(BaseModel):
    """Model for CAGR performance analysis comparing strategy vs buy-and-hold."""
    
    model_config = ConfigDict(validate_assignment=True)
    
    ticker: str
    analysis_start_date: date
    analysis_end_date: date
    first_investment_date: Optional[date] = None
    
    # Full period metrics (analysis_start_date to analysis_end_date)
    full_period_days: int = Field(gt=0)
    strategy_full_period_cagr: float
    buyhold_full_period_cagr: float
    
    # Active period metrics (first_investment_date to analysis_end_date)
    active_period_days: Optional[int] = Field(default=None, gt=0)
    strategy_active_period_cagr: Optional[float] = None
    buyhold_active_period_cagr: Optional[float] = None
    
    # Comparison metrics
    full_period_outperformance: float  # strategy - buyhold CAGR
    active_period_outperformance: Optional[float] = None  # strategy - buyhold CAGR (active period)
    opportunity_cost: Optional[float] = None  # cost of waiting for first dip (percentage points)
    
    # Portfolio values for CAGR calculation
    strategy_start_value: float = Field(default=0.0, ge=0.0)
    strategy_end_value: float = Field(ge=0.0)
    buyhold_start_value: float = Field(gt=0.0)
    buyhold_end_value: float = Field(gt=0.0)