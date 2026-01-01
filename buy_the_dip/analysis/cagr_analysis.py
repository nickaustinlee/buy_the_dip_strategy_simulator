"""
CAGR analysis engine for comparing strategy performance vs buy-and-hold.
"""

import logging
import math
from datetime import date, timedelta
from typing import List, Optional

from ..models import Transaction, CAGRAnalysis
from ..price_monitor import PriceMonitor


logger = logging.getLogger(__name__)


class CAGRAnalysisEngine:
    """Engine for calculating and comparing CAGR metrics."""
    
    def __init__(self, price_monitor: Optional[PriceMonitor] = None):
        """
        Initialize the CAGR analysis engine.
        
        Args:
            price_monitor: Price monitor for fetching historical data
        """
        self.price_monitor = price_monitor or PriceMonitor()
    
    def analyze_performance(
        self, 
        transactions: List[Transaction], 
        ticker: str, 
        start_date: date, 
        end_date: date,
        current_price: Optional[float] = None
    ) -> CAGRAnalysis:
        """
        Perform comprehensive CAGR analysis comparing strategy vs buy-and-hold.
        
        Args:
            transactions: List of strategy investment transactions
            ticker: Stock ticker symbol
            start_date: Analysis period start date
            end_date: Analysis period end date
            current_price: Current stock price (if None, fetches from price monitor)
            
        Returns:
            CAGRAnalysis with comprehensive performance metrics
        """
        logger.info(f"Analyzing CAGR performance for {ticker} from {start_date} to {end_date}")
        
        # Get current price if not provided
        if current_price is None:
            current_price = self.price_monitor.get_current_price(ticker)
        
        # Get historical prices for buy-and-hold calculation
        price_data = self.price_monitor.fetch_price_data(ticker, start_date, end_date)
        if price_data.empty:
            raise ValueError(f"No price data available for {ticker} in the specified period")
        
        start_price = float(price_data.iloc[0]['Close'])
        end_price = float(price_data.iloc[-1]['Close'])
        
        # Calculate basic period metrics
        full_period_days = (end_date - start_date).days
        first_investment_date = min(t.date for t in transactions) if transactions else None
        
        # Calculate strategy metrics
        strategy_start_value = 0.0  # Strategy starts with no investment
        strategy_end_value = self._calculate_strategy_portfolio_value(transactions, current_price)
        
        # Calculate buy-and-hold metrics (assuming same total investment)
        total_invested = sum(t.amount for t in transactions)
        buyhold_start_value = total_invested if total_invested > 0 else 1000.0  # Default for comparison
        buyhold_end_value = buyhold_start_value * (end_price / start_price)
        
        # Calculate full period CAGRs
        strategy_full_cagr = self._calculate_cagr(
            strategy_start_value, strategy_end_value, full_period_days
        ) if strategy_end_value > 0 else 0.0
        
        buyhold_full_cagr = self._calculate_cagr(
            buyhold_start_value, buyhold_end_value, full_period_days
        )
        
        # Calculate active period metrics if strategy has investments
        active_period_days = None
        strategy_active_cagr = None
        buyhold_active_cagr = None
        opportunity_cost = None
        
        if first_investment_date:
            active_period_days = (end_date - first_investment_date).days
            
            if active_period_days > 0:
                # Get price at first investment date
                first_investment_price = self._get_price_on_date(price_data, first_investment_date)
                
                # Strategy active period CAGR (from first investment to end)
                strategy_active_start_value = transactions[0].amount  # First investment amount
                strategy_active_cagr = self._calculate_cagr(
                    strategy_active_start_value, strategy_end_value, active_period_days
                )
                
                # Buy-and-hold active period CAGR (same timeframe)
                buyhold_active_start_value = total_invested
                buyhold_active_end_value = buyhold_active_start_value * (end_price / first_investment_price)
                buyhold_active_cagr = self._calculate_cagr(
                    buyhold_active_start_value, buyhold_active_end_value, active_period_days
                )
                
                # Calculate opportunity cost (cost of waiting for dip)
                delay_days = (first_investment_date - start_date).days
                if delay_days > 0:
                    # What would have been earned if invested immediately
                    immediate_buyhold_cagr = self._calculate_cagr(
                        buyhold_start_value, buyhold_end_value, full_period_days
                    )
                    opportunity_cost = immediate_buyhold_cagr - strategy_full_cagr
        
        # Calculate outperformance metrics
        full_period_outperformance = strategy_full_cagr - buyhold_full_cagr
        active_period_outperformance = (
            strategy_active_cagr - buyhold_active_cagr 
            if strategy_active_cagr is not None and buyhold_active_cagr is not None 
            else None
        )
        
        return CAGRAnalysis(
            ticker=ticker,
            analysis_start_date=start_date,
            analysis_end_date=end_date,
            first_investment_date=first_investment_date,
            full_period_days=full_period_days,
            strategy_full_period_cagr=strategy_full_cagr,
            buyhold_full_period_cagr=buyhold_full_cagr,
            active_period_days=active_period_days,
            strategy_active_period_cagr=strategy_active_cagr,
            buyhold_active_period_cagr=buyhold_active_cagr,
            full_period_outperformance=full_period_outperformance,
            active_period_outperformance=active_period_outperformance,
            opportunity_cost=opportunity_cost,
            strategy_start_value=strategy_start_value,
            strategy_end_value=strategy_end_value,
            buyhold_start_value=buyhold_start_value,
            buyhold_end_value=buyhold_end_value
        )
    
    def _calculate_cagr(self, start_value: float, end_value: float, days: int) -> float:
        """
        Calculate Compound Annual Growth Rate.
        
        Args:
            start_value: Starting portfolio value
            end_value: Ending portfolio value
            days: Number of days in the period
            
        Returns:
            CAGR as a decimal (e.g., 0.10 for 10%)
        """
        if start_value <= 0 or days <= 0:
            return 0.0
        
        if end_value <= 0:
            return -1.0  # Total loss
        
        years = days / 365.25  # Account for leap years
        return (end_value / start_value) ** (1 / years) - 1
    
    def _calculate_strategy_portfolio_value(
        self, 
        transactions: List[Transaction], 
        current_price: float
    ) -> float:
        """
        Calculate current portfolio value from strategy transactions.
        
        Args:
            transactions: List of investment transactions
            current_price: Current stock price
            
        Returns:
            Current portfolio value
        """
        total_shares = sum(t.shares for t in transactions)
        return total_shares * current_price
    
    def _get_price_on_date(self, price_data, target_date: date) -> float:
        """
        Get stock price on a specific date from price data.
        
        Args:
            price_data: DataFrame with price data
            target_date: Target date to find price for
            
        Returns:
            Stock price on the target date (or closest available date)
        """
        # Convert target_date to datetime for comparison
        price_data_copy = price_data.copy()
        price_data_copy['Date'] = price_data_copy.index.date
        
        # Find exact match
        exact_match = price_data_copy[price_data_copy['Date'] == target_date]
        if not exact_match.empty:
            return float(exact_match.iloc[0]['Close'])
        
        # Find closest date (within 5 days)
        price_data_copy['DateDiff'] = price_data_copy['Date'].apply(
            lambda x: abs((x - target_date).days)
        )
        closest = price_data_copy[price_data_copy['DateDiff'] <= 5].sort_values('DateDiff')
        
        if not closest.empty:
            return float(closest.iloc[0]['Close'])
        
        # Fallback to first available price
        logger.warning(f"Could not find price data near {target_date}, using first available price")
        return float(price_data.iloc[0]['Close'])
    
    def calculate_buyhold_cagr(self, ticker: str, start_date: date, end_date: date) -> float:
        """
        Calculate buy-and-hold CAGR for a ticker over a period.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            Buy-and-hold CAGR as decimal
        """
        price_data = self.price_monitor.fetch_price_data(ticker, start_date, end_date)
        if price_data.empty:
            raise ValueError(f"No price data available for {ticker}")
        
        start_price = float(price_data.iloc[0]['Close'])
        end_price = float(price_data.iloc[-1]['Close'])
        days = (end_date - start_date).days
        
        return self._calculate_cagr(start_price, end_price, days)
    
    def format_cagr_report(self, analysis: CAGRAnalysis) -> str:
        """
        Format CAGR analysis results into a readable report.
        
        Args:
            analysis: CAGR analysis results
            
        Returns:
            Formatted report string
        """
        report = []
        report.append(f"CAGR Analysis Report for {analysis.ticker}")
        report.append("=" * 50)
        report.append(f"Analysis Period: {analysis.analysis_start_date} to {analysis.analysis_end_date}")
        report.append(f"Total Days: {analysis.full_period_days}")
        
        if analysis.first_investment_date:
            report.append(f"First Investment: {analysis.first_investment_date}")
            delay_days = (analysis.first_investment_date - analysis.analysis_start_date).days
            report.append(f"Days Until First Investment: {delay_days}")
        else:
            report.append("No investments made during period")
        
        report.append("")
        report.append("Full Period Performance:")
        report.append(f"  Strategy CAGR: {analysis.strategy_full_period_cagr:.2%}")
        report.append(f"  Buy-Hold CAGR: {analysis.buyhold_full_period_cagr:.2%}")
        report.append(f"  Outperformance: {analysis.full_period_outperformance:+.2%}")
        
        if analysis.strategy_active_period_cagr is not None:
            report.append("")
            report.append("Active Period Performance (Apples-to-Apples):")
            report.append(f"  Strategy CAGR: {analysis.strategy_active_period_cagr:.2%}")
            report.append(f"  Buy-Hold CAGR: {analysis.buyhold_active_period_cagr:.2%}")
            report.append(f"  Outperformance: {analysis.active_period_outperformance:+.2%}")
            report.append(f"  Active Period Days: {analysis.active_period_days}")
        
        if analysis.opportunity_cost is not None:
            report.append("")
            report.append(f"Opportunity Cost: {analysis.opportunity_cost:+.2%}")
            report.append("  (Cost of waiting for dip vs immediate investment)")
        
        return "\n".join(report)