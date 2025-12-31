"""
DCA controller implementation for managing dollar-cost averaging sessions.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from .models import DCASession, DCAState, Transaction


logger = logging.getLogger(__name__)


class DCAController:
    """Manages dollar-cost averaging investment sessions."""
    
    def __init__(self):
        """Initialize the DCA controller."""
        self._sessions: Dict[str, DCASession] = {}
        self._transactions: List[Transaction] = []
    
    def check_trigger_conditions(self, current_price: float, max_price: float, percentage_trigger: float) -> bool:
        """
        Check if current conditions trigger a new DCA session.
        
        Args:
            current_price: Current stock price
            max_price: Rolling maximum price
            percentage_trigger: Trigger percentage (e.g., 0.90 for 90%)
            
        Returns:
            True if trigger conditions are met
        """
        trigger_price = max_price * percentage_trigger
        return current_price <= trigger_price
    
    def start_dca_session(self, trigger_price: float, start_date: Optional[date] = None) -> str:
        """
        Start a new DCA session.
        
        Args:
            trigger_price: Price that triggered this session
            start_date: Session start date (defaults to today)
            
        Returns:
            Session ID for the new session
        """
        if start_date is None:
            start_date = date.today()
            
        session = DCASession(
            trigger_price=trigger_price,
            start_date=start_date,
            state=DCAState.ACTIVE
        )
        
        self._sessions[session.session_id] = session
        logger.info(f"Started DCA session {session.session_id} with trigger price ${trigger_price:.2f}")
        
        return session.session_id
    
    def process_monthly_investment(self, session_id: str, current_price: float, investment_amount: float) -> Optional[Transaction]:
        """
        Process a monthly investment for an active DCA session.
        
        Args:
            session_id: ID of the DCA session
            current_price: Current stock price for share calculation
            investment_amount: Dollar amount to invest
            
        Returns:
            Transaction object if investment was processed, None otherwise
        """
        if session_id not in self._sessions:
            raise ValueError(f"DCA session {session_id} not found")
        
        session = self._sessions[session_id]
        
        if session.state != DCAState.ACTIVE:
            logger.warning(f"Cannot invest in session {session_id} - state is {session.state}")
            return None
        
        # Calculate shares purchased
        shares = investment_amount / current_price
        
        # Create transaction record
        transaction = Transaction(
            session_id=session_id,
            date=date.today(),
            price=current_price,
            shares=shares,
            amount=investment_amount
        )
        
        # Update session totals
        session.total_invested += investment_amount
        session.shares_purchased += shares
        session.last_investment_date = date.today()
        
        # Record transaction
        self._transactions.append(transaction)
        
        logger.info(f"Session {session_id}: Invested ${investment_amount:.2f} at ${current_price:.2f}, "
                   f"purchased {shares:.4f} shares")
        
        return transaction
    
    def check_completion_conditions(self, session_id: str, current_price: float) -> bool:
        """
        Check if a DCA session should be completed.
        
        Args:
            session_id: ID of the DCA session
            current_price: Current stock price
            
        Returns:
            True if session should be completed
        """
        if session_id not in self._sessions:
            return False
        
        session = self._sessions[session_id]
        
        if session.state != DCAState.ACTIVE:
            return False
        
        # Complete when price reaches or exceeds original trigger price
        if current_price >= session.trigger_price:
            session.state = DCAState.COMPLETED
            logger.info(f"Completed DCA session {session_id} - price ${current_price:.2f} "
                       f"reached trigger ${session.trigger_price:.2f}")
            return True
        
        return False
    
    def get_active_sessions(self) -> List[DCASession]:
        """Get all active DCA sessions."""
        return [session for session in self._sessions.values() if session.state == DCAState.ACTIVE]
    
    def get_session(self, session_id: str) -> Optional[DCASession]:
        """Get a specific DCA session by ID."""
        return self._sessions.get(session_id)
    
    def get_all_transactions(self) -> List[Transaction]:
        """Get all investment transactions."""
        return self._transactions.copy()
    
    def get_session_transactions(self, session_id: str) -> List[Transaction]:
        """Get all transactions for a specific session."""
        return [t for t in self._transactions if t.session_id == session_id]
    
    def calculate_total_invested(self) -> float:
        """Calculate total amount invested across all sessions."""
        return sum(transaction.amount for transaction in self._transactions)
    
    def calculate_total_shares(self) -> float:
        """Calculate total shares owned across all sessions."""
        return sum(transaction.shares for transaction in self._transactions)
    
    def calculate_portfolio_value(self, current_price: float) -> float:
        """
        Calculate current portfolio value based on latest price.
        
        Args:
            current_price: Current stock price
            
        Returns:
            Current portfolio value in dollars
        """
        total_shares = self.calculate_total_shares()
        return total_shares * current_price
    
    def calculate_performance_metrics(self, current_price: float) -> dict:
        """
        Calculate performance metrics including total return and percentage gain/loss.
        
        Args:
            current_price: Current stock price
            
        Returns:
            Dictionary with performance metrics
        """
        total_invested = self.calculate_total_invested()
        portfolio_value = self.calculate_portfolio_value(current_price)
        
        if total_invested == 0:
            return {
                'total_invested': 0.0,
                'portfolio_value': 0.0,
                'total_return': 0.0,
                'percentage_return': 0.0,
                'total_shares': 0.0
            }
        
        total_return = portfolio_value - total_invested
        percentage_return = (total_return / total_invested) * 100
        
        return {
            'total_invested': total_invested,
            'portfolio_value': portfolio_value,
            'total_return': total_return,
            'percentage_return': percentage_return,
            'total_shares': self.calculate_total_shares()
        }