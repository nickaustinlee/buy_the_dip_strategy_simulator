"""
Data models for DCA controller.
"""

from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
import uuid


class DCAState(Enum):
    """States for DCA session lifecycle."""

    MONITORING = "monitoring"
    ACTIVE = "active"
    COMPLETED = "completed"


class DCASession(BaseModel):
    """Model for a DCA investment session."""

    model_config = ConfigDict(validate_assignment=True)

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_price: float = Field(gt=0.0)
    start_date: date
    state: DCAState = DCAState.MONITORING
    total_invested: float = Field(default=0.0, ge=0.0)
    shares_purchased: float = Field(default=0.0, ge=0.0)
    last_investment_date: Optional[date] = None


class Transaction(BaseModel):
    """Model for an investment transaction."""

    model_config = ConfigDict(validate_assignment=True)

    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    date: date
    price: float = Field(gt=0.0)
    shares: float = Field(gt=0.0)
    amount: float = Field(gt=0.0)
    transaction_type: Literal["buy"] = "buy"
