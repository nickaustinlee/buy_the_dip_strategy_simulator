"""
Strategy engine implementation for orchestrating the buy-the-dip strategy.
"""

import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional

from ..config import StrategyConfig
from ..price_monitor import PriceMonitor
from ..dca_controller import DCAController
from ..models import StrategyReport, MarketStatus


logger = logging.getLogger(__name__)


class StrategyEngine:
    """Orchestrates the overall buy-the-dip trading strategy."""
    
    def __init__(self):
        """Initialize the strategy engine."""
        self.config: Optional[StrategyConfig] = None
        self.price_monitor = PriceMonitor()
        self.dca_controller = DCAController()
        self._initialized = False
    
    def initialize(self, config: StrategyConfig) -> None:
        """
        Initialize the strategy engine with configuration.
        
        Args:
            config: Strategy configuration
        """
        self.config = config
        self._initialized = True
        logger.info(f"Strategy engine initialized for ticker {config.ticker}")
    
    def get_market_status(self) -> MarketStatus:
        """
        Get the current market status and buy-the-dip recommendation.
        
        Returns:
            MarketStatus with current recommendation
        """
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")
        
        try:
            # Get current price
            current_price = self.price_monitor.get_current_price(self.config.ticker)
            
            # Get historical data for rolling maximum calculation
            end_date = date.today()
            start_date = end_date - timedelta(days=self.config.rolling_window_days + 30)  # Extra buffer
            
            price_data = self.price_monitor.fetch_price_data(
                self.config.ticker, 
                start_date, 
                end_date
            )
            
            if price_data.empty:
                raise ValueError(f"No price data available for {self.config.ticker}")
            
            # Calculate rolling maximum
            prices = price_data['Close']
            rolling_max_series = self.price_monitor.get_rolling_maximum(
                prices, 
                self.config.rolling_window_days
            )
            
            # Get the most recent rolling maximum
            rolling_max_price = float(rolling_max_series.iloc[-1])
            
            # Calculate trigger price and percentage from max
            trigger_price = rolling_max_price * self.config.percentage_trigger
            percentage_from_max = ((current_price - rolling_max_price) / rolling_max_price) * 100
            
            # Determine if it's buy-the-dip time
            is_buy_the_dip_time = current_price <= trigger_price
            
            # Generate recommendation and confidence
            recommendation, confidence, message = self._generate_recommendation(
                current_price, rolling_max_price, trigger_price, percentage_from_max, is_buy_the_dip_time
            )
            
            return MarketStatus(
                ticker=self.config.ticker,
                current_price=current_price,
                rolling_max_price=rolling_max_price,
                trigger_price=trigger_price,
                percentage_from_max=percentage_from_max,
                is_buy_the_dip_time=is_buy_the_dip_time,
                recommendation=recommendation,
                confidence_level=confidence,
                message=message,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            raise
    
    def _generate_recommendation(
        self, 
        current_price: float, 
        rolling_max_price: float, 
        trigger_price: float, 
        percentage_from_max: float,
        is_buy_the_dip_time: bool
    ) -> tuple[str, str, str]:
        """
        Generate investment recommendation based on market conditions.
        
        Returns:
            Tuple of (recommendation, confidence_level, message)
        """
        if is_buy_the_dip_time:
            # Calculate how deep the dip is
            dip_percentage = abs(percentage_from_max)
            
            if dip_percentage >= 15:  # Very deep dip
                return (
                    "BUY", 
                    "HIGH", 
                    f"🔥 STRONG BUY SIGNAL! Price is {dip_percentage:.1f}% below recent high. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
            elif dip_percentage >= 10:  # Moderate dip
                return (
                    "BUY", 
                    "MEDIUM", 
                    f"📈 BUY SIGNAL! Price is {dip_percentage:.1f}% below recent high. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
            else:  # Just crossed trigger
                return (
                    "BUY", 
                    "MEDIUM", 
                    f"✅ BUY SIGNAL! Price just crossed trigger threshold. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
        else:
            # Not in buy-the-dip territory
            distance_to_trigger = ((trigger_price - current_price) / current_price) * 100
            
            if distance_to_trigger <= 2:  # Very close to trigger
                return (
                    "MONITOR", 
                    "HIGH", 
                    f"⚠️  WATCH CLOSELY! Price is only {distance_to_trigger:.1f}% above trigger. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
            elif distance_to_trigger <= 5:  # Moderately close
                return (
                    "MONITOR", 
                    "MEDIUM", 
                    f"👀 MONITOR! Price is {distance_to_trigger:.1f}% above trigger threshold. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
            else:  # Far from trigger
                return (
                    "HOLD", 
                    "LOW", 
                    f"😌 HOLD! Price is {distance_to_trigger:.1f}% above trigger. Market looks stable. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}"
                )
    
    def get_quick_status(self) -> str:
        """
        Get a quick one-line status message.
        
        Returns:
            Quick status string
        """
        try:
            status = self.get_market_status()
            if status.is_buy_the_dip_time:
                return f"🚨 BUY THE DIP! {status.ticker} at ${status.current_price:.2f} ({status.percentage_from_max:+.1f}%)"
            else:
                return f"📊 {status.ticker}: ${status.current_price:.2f} ({status.percentage_from_max:+.1f}% from high) - {status.recommendation}"
        except Exception as e:
            return f"❌ Error getting status: {e}"
    
    def run_strategy(self) -> None:
        """Run the main strategy execution loop."""
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")
        
        logger.info("Starting buy-the-dip strategy execution")
        
        # This is a placeholder for the main execution loop
        # Will be implemented in later tasks
        pass
    
    def process_price_update(self, current_price: float) -> None:
        """
        Process a price update and check for trigger conditions.
        
        Args:
            current_price: Current stock price
        """
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")
        
        # This is a placeholder for price update processing
        # Will be implemented in later tasks
        logger.debug(f"Processing price update: ${current_price:.2f}")
    
    def generate_report(self) -> 'StrategyReport':
        """
        Generate a strategy performance report.
        
        Returns:
            Strategy report with performance metrics
        """
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")
        
        # This is a placeholder for report generation
        # Will be implemented in later tasks
        from ..models import StrategyReport
        return StrategyReport(
            ticker=self.config.ticker,
            total_invested=0.0,
            total_shares=0.0,
            current_value=0.0,
            total_return=0.0,
            percentage_return=0.0
        )