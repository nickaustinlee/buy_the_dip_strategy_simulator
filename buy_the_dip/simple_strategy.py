"""
Simple buy-the-dip strategy implementation.

Core logic:
1. Monthly investment opportunity
2. Invest if price ≤ trigger (90% of rolling max)
3. Skip if price > trigger
4. That's it.
"""

import logging
import pandas as pd
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .config import StrategyConfig
from .price_monitor import PriceMonitor


logger = logging.getLogger(__name__)


@dataclass
class Investment:
    """Simple investment record."""

    date: date
    price: float
    amount: float
    shares: float


@dataclass
class StrategyResult:
    """Simple strategy results."""

    investments: List[Investment]
    total_invested: float
    total_shares: float
    final_value: float
    total_return: float
    return_percentage: float


class SimpleStrategy:
    """Dead simple buy-the-dip strategy."""

    def __init__(self, price_monitor: Optional[PriceMonitor] = None):
        self.price_monitor = price_monitor or PriceMonitor()

    def run_backtest(
        self, config: StrategyConfig, start_date: date, end_date: date
    ) -> StrategyResult:
        """
        Run the simple strategy backtest.

        Args:
            config: Strategy configuration
            start_date: Start date
            end_date: End date

        Returns:
            Strategy results
        """
        logger.info(f"Running simple strategy backtest for {config.ticker}")

        # Get price data
        price_data = self.price_monitor.fetch_price_data(config.ticker, start_date, end_date)
        if price_data.empty:
            raise ValueError(f"No price data for {config.ticker}")

        # Calculate rolling maximum
        price_data = price_data.sort_values("Date").set_index("Date")
        rolling_max = (
            price_data["Close"].rolling(window=config.rolling_window_days, min_periods=1).max()
        )

        investments = []
        current_date = start_date

        # Check monthly (approximately every 30 days)
        while current_date <= end_date:
            try:
                # Find closest trading day
                trading_date = self._find_closest_trading_day(price_data, current_date)
                if trading_date is None:
                    current_date = self._add_month(current_date)
                    continue

                # Get price and rolling max for this date
                # Use iloc for positional access to avoid type issues
                try:
                    current_price = float(price_data.loc[trading_date, "Close"])  # type: ignore[arg-type, index]
                    current_rolling_max = float(rolling_max.loc[trading_date])  # type: ignore[arg-type]
                except (KeyError, TypeError, ValueError):
                    logger.warning(f"Could not get price data for {trading_date}")
                    current_date = self._add_month(current_date)
                    continue
                trigger_price = current_rolling_max * config.percentage_trigger

                # Investment decision: simple comparison
                if current_price <= trigger_price:
                    # Invest!
                    shares = config.monthly_dca_amount / current_price
                    investment = Investment(
                        date=trading_date,
                        price=current_price,
                        amount=config.monthly_dca_amount,
                        shares=shares,
                    )
                    investments.append(investment)

                    logger.info(
                        f"INVEST: {trading_date} - ${config.monthly_dca_amount:,.0f} at ${current_price:.2f} "
                        f"(trigger: ${trigger_price:.2f}, rolling max: ${current_rolling_max:.2f})"
                    )
                else:
                    # Skip
                    logger.info(
                        f"SKIP: {trading_date} - price ${current_price:.2f} > trigger ${trigger_price:.2f} "
                        f"(rolling max: ${current_rolling_max:.2f})"
                    )

            except Exception as e:
                logger.warning(f"Error processing {current_date}: {e}")

            # Move to next month
            current_date = self._add_month(current_date)

        # Calculate results
        total_invested = sum(inv.amount for inv in investments)
        total_shares = sum(inv.shares for inv in investments)

        if investments:
            final_price = float(price_data.iloc[-1]["Close"])
            final_value = total_shares * final_price
            total_return = final_value - total_invested
            return_percentage = (total_return / total_invested) * 100 if total_invested > 0 else 0.0
        else:
            final_value = 0.0
            total_return = 0.0
            return_percentage = 0.0

        return StrategyResult(
            investments=investments,
            total_invested=total_invested,
            total_shares=total_shares,
            final_value=final_value,
            total_return=total_return,
            return_percentage=return_percentage,
        )

    def _find_closest_trading_day(
        self, price_data: pd.DataFrame, target_date: date
    ) -> Optional[date]:
        """Find the closest trading day to target date."""
        # Look for exact match first
        if target_date in price_data.index:
            return target_date

        # Look within ±5 days
        for offset in range(1, 6):
            # Try later dates first (prefer investing later in month)
            for delta in [offset, -offset]:
                candidate = target_date + timedelta(days=delta)
                if candidate in price_data.index:
                    return candidate

        return None

    def _add_month(self, current_date: date) -> date:
        """Add approximately one month to date."""
        # Simple: add 30 days
        return current_date + timedelta(days=30)

    def format_results(
        self, result: StrategyResult, ticker: str, start_date: date, end_date: date
    ) -> str:
        """Format results for display."""
        lines = []
        lines.append(f"📊 Simple Buy-the-Dip Results for {ticker}")
        lines.append("=" * 50)
        lines.append(f"Period: {start_date} to {end_date}")
        lines.append(f"")

        # Summary
        lines.append(f"💰 Results:")
        lines.append(f"  Total Invested: ${result.total_invested:,.2f}")
        lines.append(f"  Total Shares: {result.total_shares:.4f}")
        lines.append(f"  Final Value: ${result.final_value:,.2f}")
        lines.append(f"  Total Return: ${result.total_return:,.2f}")
        lines.append(f"  Return %: {result.return_percentage:.2f}%")
        lines.append(f"")

        # Investments
        if result.investments:
            lines.append(f"💳 Investments ({len(result.investments)} total):")
            for i, inv in enumerate(result.investments, 1):
                lines.append(
                    f"  {i}. {inv.date} - ${inv.amount:,.0f} at ${inv.price:.2f} = {inv.shares:.4f} shares"
                )
        else:
            lines.append(f"💳 No investments made (price never hit trigger)")

        return "\n".join(lines)
