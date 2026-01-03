"""
Core strategy system implementation for daily buy-the-dip evaluation.
"""

import logging
import pandas as pd
from datetime import date, timedelta
from typing import Optional, List

from .config.models import StrategyConfig
from .price_monitor.price_monitor import PriceMonitor
from .investment_tracker import InvestmentTracker
from .models import Investment, PortfolioMetrics

logger = logging.getLogger(__name__)


class EvaluationResult:
    """Result of a daily trading evaluation."""
    
    def __init__(
        self,
        evaluation_date: date,
        yesterday_price: float,
        trigger_price: float,
        rolling_maximum: float,
        trigger_met: bool,
        recent_investment_exists: bool,
        investment_executed: bool,
        investment: Optional[Investment] = None
    ):
        self.evaluation_date = evaluation_date
        self.yesterday_price = yesterday_price
        self.trigger_price = trigger_price
        self.rolling_maximum = rolling_maximum
        self.trigger_met = trigger_met
        self.recent_investment_exists = recent_investment_exists
        self.investment_executed = investment_executed
        self.investment = investment


class BacktestResult:
    """Result of a backtest run."""
    
    def __init__(
        self,
        start_date: date,
        end_date: date,
        total_evaluations: int,
        trigger_conditions_met: int,
        investments_executed: int,
        investments_blocked_by_constraint: int,
        final_portfolio: PortfolioMetrics,
        all_investments: List[Investment]
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.total_evaluations = total_evaluations
        self.trigger_conditions_met = trigger_conditions_met
        self.investments_executed = investments_executed
        self.investments_blocked_by_constraint = investments_blocked_by_constraint
        self.final_portfolio = final_portfolio
        self.all_investments = all_investments


class StrategySystem:
    """Core system that executes the buy-the-dip trading strategy."""
    
    def __init__(self, config: StrategyConfig, price_monitor: Optional[PriceMonitor] = None, 
                 investment_tracker: Optional[InvestmentTracker] = None):
        """
        Initialize the strategy system.
        
        Args:
            config: Strategy configuration
            price_monitor: Price monitor instance (optional, creates default if None)
            investment_tracker: Investment tracker instance (optional, creates default if None)
        """
        self.config = config
        self.price_monitor = price_monitor or PriceMonitor()
        self.investment_tracker = investment_tracker or InvestmentTracker()
        
        logger.info(f"StrategySystem initialized for ticker {config.ticker}")
    
    def calculate_trigger_price(self, prices: pd.Series, window_days: int, trigger_pct: float) -> float:
        """
        Calculate the trigger price based on rolling maximum and percentage trigger.
        
        Args:
            prices: Series of closing prices
            window_days: Number of days for rolling window
            trigger_pct: Percentage trigger (e.g., 0.90 for 90%)
            
        Returns:
            Calculated trigger price
        """
        if prices.empty:
            raise ValueError("Cannot calculate trigger price with empty price data")
        
        # Calculate rolling maximum
        rolling_max = self.price_monitor.calculate_rolling_maximum(prices, window_days)
        
        # Calculate trigger price
        trigger_price = rolling_max * trigger_pct
        
        logger.debug(f"Calculated trigger price: {trigger_price:.2f} (rolling_max: {rolling_max:.2f}, trigger_pct: {trigger_pct:.2%})")
        
        return trigger_price
    
    def should_invest(self, yesterday_price: float, trigger_price: float, evaluation_date: date) -> bool:
        """
        Determine if investment should be made based on trigger conditions and constraints.
        
        Args:
            yesterday_price: Yesterday's closing price
            trigger_price: Calculated trigger price
            evaluation_date: Date being evaluated
            
        Returns:
            True if investment should be made
        """
        # Check if yesterday's price meets trigger condition
        trigger_met = yesterday_price <= trigger_price
        
        if not trigger_met:
            logger.debug(f"Trigger not met: yesterday_price {yesterday_price:.2f} > trigger_price {trigger_price:.2f}")
            return False
        
        # Check 28-day constraint (look back 28 days exclusive to allow investment on day 28)
        recent_investment_exists = self.investment_tracker.has_recent_investment(evaluation_date, days=28)
        
        if recent_investment_exists:
            logger.debug(f"Recent investment exists within 28 days of {evaluation_date}")
            return False
        
        logger.debug(f"Investment conditions met for {evaluation_date}")
        return True
    
    def execute_investment(self, evaluation_date: date, closing_price: float, amount: float) -> Investment:
        """
        Execute an investment at the given price and amount.
        
        Args:
            evaluation_date: Date of the investment
            closing_price: Closing price for the investment
            amount: Dollar amount to invest
            
        Returns:
            Investment record
        """
        shares = amount / closing_price
        
        investment = Investment(
            date=evaluation_date,
            ticker=self.config.ticker,
            price=closing_price,
            amount=amount,
            shares=shares
        )
        
        # Add to tracker
        self.investment_tracker.add_investment(investment)
        
        logger.info(f"Executed investment: {investment.date} - ${investment.amount:.2f} at ${investment.price:.2f} = {investment.shares:.4f} shares")
        
        return investment
    
    def evaluate_trading_day(self, evaluation_date: date) -> EvaluationResult:
        """
        Evaluate a single trading day and execute investment if conditions are met.
        
        Args:
            evaluation_date: Date to evaluate
            
        Returns:
            Evaluation result with details of the decision
        """
        logger.debug(f"Evaluating trading day: {evaluation_date}")
        
        # Get price data for rolling window + 1 day (to get yesterday's price)
        start_date = evaluation_date - timedelta(days=self.config.rolling_window_days + 30)  # Extra buffer
        end_date = evaluation_date
        
        # Fetch price data
        prices = self.price_monitor.get_closing_prices(self.config.ticker, start_date, end_date)
        
        if prices.empty:
            raise ValueError(f"No price data available for {self.config.ticker} from {start_date} to {end_date}")
        
        # Get yesterday's price (last available price before evaluation_date)
        yesterday_date = evaluation_date - timedelta(days=1)
        
        # Find the most recent price before or on yesterday
        available_dates = [d for d in prices.index if d <= yesterday_date]
        if not available_dates:
            raise ValueError(f"No price data available before {evaluation_date}")
        
        yesterday_actual_date = max(available_dates)
        yesterday_price = float(prices[yesterday_actual_date])
        
        # Get current day's closing price for investment execution
        current_day_prices = [p for d, p in prices.items() if d == evaluation_date]
        if not current_day_prices:
            raise ValueError(f"No price data available for evaluation date {evaluation_date}")
        
        current_closing_price = float(current_day_prices[0])
        
        # Calculate trigger price using prices up to yesterday (excluding current day)
        historical_prices = prices[prices.index <= yesterday_actual_date]
        
        if len(historical_prices) < self.config.rolling_window_days:
            logger.warning(f"Insufficient historical data: {len(historical_prices)} days available, {self.config.rolling_window_days} required")
            # Use available data if we have at least some
            if historical_prices.empty:
                raise ValueError("No historical price data available for trigger calculation")
        
        trigger_price = self.calculate_trigger_price(
            historical_prices, 
            self.config.rolling_window_days, 
            self.config.percentage_trigger
        )
        
        # Calculate rolling maximum for result
        rolling_maximum = self.price_monitor.calculate_rolling_maximum(
            historical_prices, 
            self.config.rolling_window_days
        )
        
        # Check if trigger condition is met
        trigger_met = yesterday_price <= trigger_price
        
        # Check 28-day constraint (look back 28 days exclusive to allow investment on day 28)
        recent_investment_exists = self.investment_tracker.has_recent_investment(evaluation_date, days=28)
        
        # Determine if investment should be executed
        should_invest = trigger_met and not recent_investment_exists
        
        investment = None
        if should_invest:
            investment = self.execute_investment(
                evaluation_date, 
                current_closing_price, 
                self.config.monthly_dca_amount
            )
        
        return EvaluationResult(
            evaluation_date=evaluation_date,
            yesterday_price=yesterday_price,
            trigger_price=trigger_price,
            rolling_maximum=rolling_maximum,
            trigger_met=trigger_met,
            recent_investment_exists=recent_investment_exists,
            investment_executed=should_invest,
            investment=investment
        )
    
    def run_backtest(self, start_date: date, end_date: date) -> BacktestResult:
        """
        Run a backtest over the specified date range.
        
        Args:
            start_date: Start date for backtest
            end_date: End date for backtest
            
        Returns:
            Backtest result with performance metrics
        """
        logger.info(f"Running backtest from {start_date} to {end_date}")
        
        # Clear existing investments for clean backtest
        original_investments = self.investment_tracker.get_all_investments()
        self.investment_tracker.clear_all_investments()
        
        total_evaluations = 0
        trigger_conditions_met = 0
        investments_executed = 0
        investments_blocked_by_constraint = 0
        
        try:
            # Fetch all price data upfront for better performance
            logger.info(f"Fetching price data for {self.config.ticker}...")
            data_start_date = start_date - timedelta(days=self.config.rolling_window_days + 30)
            all_prices = self.price_monitor.get_closing_prices(self.config.ticker, data_start_date, end_date)
            
            if all_prices.empty:
                raise ValueError(f"No price data available for {self.config.ticker} from {data_start_date} to {end_date}")
            
            logger.info(f"Fetched {len(all_prices)} price records, running backtest...")
            
            # Generate business days in the range
            current_date = start_date
            while current_date <= end_date:
                # Skip weekends (simplified - real implementation might use trading calendar)
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    try:
                        # Check if we have price data for this date
                        if current_date not in all_prices.index:
                            # Skip silently - likely a holiday
                            current_date += timedelta(days=1)
                            continue
                        
                        # Get yesterday's price (last available price before current_date)
                        yesterday_date = current_date - timedelta(days=1)
                        available_dates = [d for d in all_prices.index if d <= yesterday_date]
                        
                        if not available_dates:
                            current_date += timedelta(days=1)
                            continue
                        
                        yesterday_actual_date = max(available_dates)
                        yesterday_price = float(all_prices[yesterday_actual_date])
                        current_closing_price = float(all_prices[current_date])
                        
                        # Calculate trigger price using historical prices
                        historical_prices = all_prices[all_prices.index <= yesterday_actual_date]
                        
                        if len(historical_prices) < self.config.rolling_window_days:
                            # Not enough data yet
                            current_date += timedelta(days=1)
                            continue
                        
                        trigger_price = self.calculate_trigger_price(
                            historical_prices, 
                            self.config.rolling_window_days, 
                            self.config.percentage_trigger
                        )
                        
                        # Check if trigger condition is met
                        trigger_met = yesterday_price <= trigger_price
                        
                        # Check 28-day constraint
                        recent_investment_exists = self.investment_tracker.has_recent_investment(current_date, days=28)
                        
                        # Count evaluation
                        total_evaluations += 1
                        
                        if trigger_met:
                            trigger_conditions_met += 1
                            
                            if not recent_investment_exists:
                                # Execute investment
                                self.execute_investment(
                                    current_date, 
                                    current_closing_price, 
                                    self.config.monthly_dca_amount
                                )
                                investments_executed += 1
                            else:
                                investments_blocked_by_constraint += 1
                                
                    except Exception as e:
                        # Skip days with errors
                        logger.debug(f"Skipping {current_date}: {e}")
                
                current_date += timedelta(days=1)
            
            # Calculate final portfolio metrics
            all_investments = self.investment_tracker.get_all_investments()
            
            if all_investments:
                # Get final price for portfolio calculation
                if end_date in all_prices.index:
                    current_price = float(all_prices[end_date])
                else:
                    # Use last available price
                    current_price = float(all_prices.iloc[-1])
                
                final_portfolio = self.investment_tracker.calculate_portfolio_metrics(current_price)
            else:
                final_portfolio = PortfolioMetrics(
                    total_invested=0.0,
                    total_shares=0.0,
                    current_value=0.0,
                    total_return=0.0,
                    percentage_return=0.0
                )
            
            logger.info(f"Backtest completed: {total_evaluations} evaluations, {investments_executed} investments executed")
            
            return BacktestResult(
                start_date=start_date,
                end_date=end_date,
                total_evaluations=total_evaluations,
                trigger_conditions_met=trigger_conditions_met,
                investments_executed=investments_executed,
                investments_blocked_by_constraint=investments_blocked_by_constraint,
                final_portfolio=final_portfolio,
                all_investments=all_investments
            )
            
        finally:
            # Restore original investments
            self.investment_tracker.clear_all_investments()
            for investment in original_investments:
                self.investment_tracker.add_investment(investment)