"""
Historical backtesting engine for the buy-the-dip strategy.

This module simulates the strategy execution over historical periods,
generating transactions as if the strategy was running in real-time.
"""

import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from dateutil.relativedelta import relativedelta

from ..config import StrategyConfig
from ..price_monitor import PriceMonitor
from ..dca_controller import DCAController
from ..dca_controller.models import DCAState, Transaction
from ..models import StrategyReport


logger = logging.getLogger(__name__)


class BacktestEngine:
    """Simulates buy-the-dip strategy execution over historical periods."""

    def __init__(self, price_monitor: PriceMonitor):
        """Initialize the backtest engine."""
        self.price_monitor = price_monitor
        self.dca_controller = DCAController()

    def run_backtest(
        self, config: StrategyConfig, start_date: date, end_date: date
    ) -> List[Transaction]:
        """
        Run a historical backtest of the buy-the-dip strategy.

        Args:
            config: Strategy configuration
            start_date: Backtest start date
            end_date: Backtest end date

        Returns:
            List of simulated transactions
        """
        logger.info(f"Starting backtest for {config.ticker} from {start_date} to {end_date}")

        # Reset DCA controller for clean backtest
        self.dca_controller = DCAController()

        # Get historical price data
        price_data = self.price_monitor.fetch_price_data(config.ticker, start_date, end_date)
        if price_data.empty:
            logger.warning(f"No price data available for backtest period")
            return []

        # Convert to daily data and sort by date
        price_data = price_data.sort_values("Date")

        # Set Date as index for proper iteration
        price_data = price_data.set_index("Date")

        # Track rolling maximum
        rolling_max_series = (
            price_data["Close"].rolling(window=config.rolling_window_days, min_periods=1).max()
        )

        transactions = []
        last_investment_dates: Dict[str, date] = {}  # Track last investment per session
        monthly_investments: Dict[
            str, float
        ] = {}  # Track total invested per month (YYYY-MM format)

        # Simulate day by day
        for current_date, row in price_data.iterrows():
            try:
                current_price = float(row["Close"])

                # current_date is now a date object from the index
                if not isinstance(current_date, date):
                    logger.error(
                        f"Unexpected date type: {type(current_date)}, value: {current_date}"
                    )
                    continue

                # Debug logging
                logger.debug(f"Processing date: {current_date} (type: {type(current_date)})")

                # Get rolling maximum for this date
                rolling_max = float(rolling_max_series.loc[current_date])
                trigger_price = rolling_max * config.percentage_trigger

                # Debug logging for trigger conditions
                logger.debug(
                    f"Date: {current_date}, Price: ${current_price:.2f}, "
                    f"Rolling Max: ${rolling_max:.2f}, Trigger: ${trigger_price:.2f}, "
                    f"Should trigger: {current_price <= trigger_price}"
                )
            except Exception as e:
                logger.error(f"Error processing date {current_date}: {e}")
                continue

            # Check if we should start a new DCA session
            if current_price <= trigger_price:
                # Check if we already have an active session for this trigger level
                active_sessions = self.dca_controller.get_active_sessions()

                # Only start new session if no active session exists for this trigger level
                should_start_new_session = True
                for session in active_sessions:
                    if abs(session.trigger_price - trigger_price) < 0.01:  # Same trigger level
                        should_start_new_session = False
                        break

                if should_start_new_session:
                    session_id = self.dca_controller.start_dca_session(
                        trigger_price=trigger_price, start_date=current_date
                    )
                    logger.info(
                        f"Started DCA session {session_id} on {current_date} "
                        f"(price: ${current_price:.2f}, trigger: ${trigger_price:.2f})"
                    )

            # Process monthly investments for active sessions
            active_sessions = self.dca_controller.get_active_sessions()
            for session in active_sessions:
                # Check if it's time for monthly investment
                last_investment = last_investment_dates.get(session.session_id)

                if last_investment is None:
                    # First investment for this session - invest immediately
                    should_invest = True
                else:
                    # Check if we're in the monthly investment window (~30 days ±5 days)
                    target_investment_date = last_investment + relativedelta(months=1)
                    days_since_target = (current_date - target_investment_date).days

                    # Allow investment window: 5 days before to 10 days after target date
                    # This accounts for weekends, holidays, and market closures
                    should_invest = -5 <= days_since_target <= 10

                if should_invest:
                    # Check monthly cash flow constraint
                    month_key = current_date.strftime("%Y-%m")
                    monthly_spent = monthly_investments.get(month_key, 0.0)
                    remaining_budget = config.monthly_dca_amount - monthly_spent

                    if (
                        remaining_budget < config.monthly_dca_amount * 0.01
                    ):  # Less than 1% of budget remaining
                        # No budget left this month - skip investment but update date to avoid daily checks
                        last_investment_dates[session.session_id] = current_date
                        logger.info(
                            f"Skipped investment on {current_date}: monthly budget exhausted "
                            f"(${monthly_spent:.2f} already invested in {month_key})"
                        )
                        continue

                    # Recalculate trigger price based on current rolling maximum
                    current_rolling_max = float(rolling_max_series.loc[current_date])
                    current_trigger_price = current_rolling_max * config.percentage_trigger

                    # Only invest if price is still at or below the current trigger
                    if current_price <= current_trigger_price:
                        # Use remaining budget (could be full amount or partial if multiple sessions)
                        investment_amount = min(remaining_budget, config.monthly_dca_amount)

                        transaction = self.dca_controller.process_monthly_investment(
                            session.session_id,
                            current_price,
                            investment_amount,
                            investment_date=current_date,
                        )

                        if transaction:
                            transactions.append(transaction)
                            last_investment_dates[session.session_id] = current_date
                            monthly_investments[month_key] = monthly_spent + investment_amount

                            days_from_target = (
                                (current_date - (last_investment + relativedelta(months=1))).days
                                if last_investment
                                else 0
                            )
                            logger.info(
                                f"Investment: ${transaction.amount:.2f} at ${current_price:.2f} "
                                f"on {current_date} ({transaction.shares:.4f} shares) "
                                f"[Rolling max: ${current_rolling_max:.2f}, Trigger: ${current_trigger_price:.2f}] "
                                f"({days_from_target:+d} days from target) "
                                f"[Monthly budget: ${monthly_investments[month_key]:.2f}/${config.monthly_dca_amount:.2f}]"
                            )
                    else:
                        # Price recovered above current trigger - skip this month's investment
                        # but update the last investment date to avoid checking every day
                        last_investment_dates[session.session_id] = current_date
                        logger.info(
                            f"Skipped investment on {current_date}: price ${current_price:.2f} "
                            f"above current trigger ${current_trigger_price:.2f} "
                            f"[Rolling max: ${current_rolling_max:.2f}]"
                        )

                # Note: We no longer complete sessions based on price recovery
                # Sessions remain active to continue checking monthly investment opportunities

        logger.info(f"Backtest completed: {len(transactions)} transactions generated")
        return transactions

    def get_backtest_summary(self, transactions: List[Transaction]) -> Dict:
        """Generate a summary of backtest results."""
        if not transactions:
            return {
                "total_invested": 0.0,
                "total_shares": 0.0,
                "transaction_count": 0,
                "first_investment": None,
                "last_investment": None,
                "average_price": 0.0,
            }

        total_invested = sum(t.amount for t in transactions)
        total_shares = sum(t.shares for t in transactions)

        return {
            "total_invested": total_invested,
            "total_shares": total_shares,
            "transaction_count": len(transactions),
            "first_investment": min(t.date for t in transactions),
            "last_investment": max(t.date for t in transactions),
            "average_price": total_invested / total_shares if total_shares > 0 else 0.0,
        }
