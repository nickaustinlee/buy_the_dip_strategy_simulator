"""
Strategy engine implementation for orchestrating the buy-the-dip strategy.
"""

import logging
import pandas as pd
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List
from typing import Literal

from ..config import StrategyConfig
from ..price_monitor import PriceMonitor
from ..dca_controller import DCAController
from ..dca_controller.models import DCAState
from ..models import StrategyReport, MarketStatus
from .backtest_engine import BacktestEngine


logger = logging.getLogger(__name__)


class StrategyEngine:
    """Orchestrates the overall buy-the-dip trading strategy."""

    def __init__(self) -> None:
        """Initialize the strategy engine."""
        self.config: Optional[StrategyConfig] = None
        self.price_monitor = PriceMonitor()
        self.dca_controller = DCAController()
        self.backtest_engine = BacktestEngine(self.price_monitor)
        self._initialized = False
        self._last_rolling_max: Optional[float] = None
        self._trigger_conditions_cache: Dict[str, float] = {}

    def initialize(self, config: StrategyConfig) -> None:
        """
        Initialize the strategy engine with configuration.

        Args:
            config: Strategy configuration
        """
        old_config = self.config
        self.config = config
        self._initialized = True

        # Handle configuration changes if this is a reconfiguration
        if old_config is not None:
            self._handle_configuration_change(old_config, config)

        logger.info(f"Strategy engine initialized for ticker {config.ticker}")

    def _handle_configuration_change(
        self, old_config: StrategyConfig, new_config: StrategyConfig
    ) -> None:
        """
        Handle configuration changes and update trigger calculations.

        Args:
            old_config: Previous configuration
            new_config: New configuration
        """
        # Clear cache if ticker changed
        if old_config.ticker != new_config.ticker:
            logger.info(f"Ticker changed from {old_config.ticker} to {new_config.ticker}")
            self._last_rolling_max = None
            self._trigger_conditions_cache.clear()

        # Clear rolling max cache if window size changed
        if old_config.rolling_window_days != new_config.rolling_window_days:
            logger.info(
                f"Rolling window changed from {old_config.rolling_window_days} to {new_config.rolling_window_days} days"
            )
            self._last_rolling_max = None

        # Log percentage trigger changes (affects future sessions only)
        if old_config.percentage_trigger != new_config.percentage_trigger:
            logger.info(
                f"Percentage trigger changed from {old_config.percentage_trigger:.2%} to {new_config.percentage_trigger:.2%}"
            )

        # Log DCA amount changes (affects future investments only)
        if old_config.monthly_dca_amount != new_config.monthly_dca_amount:
            logger.info(
                f"Monthly DCA amount changed from ${old_config.monthly_dca_amount:.2f} to ${new_config.monthly_dca_amount:.2f}"
            )

    def _get_rolling_maximum_price(self) -> float:
        """
        Get the current rolling maximum price, using cache when possible.

        Returns:
            Current rolling maximum price
        """
        if self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        # Get historical data for rolling maximum calculation
        end_date = date.today()
        start_date = end_date - timedelta(days=self.config.rolling_window_days + 30)  # Extra buffer

        price_data = self.price_monitor.fetch_price_data(self.config.ticker, start_date, end_date)

        if price_data.empty:
            raise ValueError(f"No price data available for {self.config.ticker}")

        # Calculate rolling maximum
        prices = price_data["Close"]
        rolling_max_series = self.price_monitor.get_rolling_maximum(
            prices, self.config.rolling_window_days
        )

        # Get the most recent rolling maximum
        rolling_max_price = float(rolling_max_series.iloc[-1])

        # Update cache
        self._last_rolling_max = rolling_max_price

        return rolling_max_price

    def check_trigger_conditions(self, current_price: float) -> bool:
        """
        Check if current price conditions trigger a new DCA session.

        Args:
            current_price: Current stock price

        Returns:
            True if trigger conditions are met
        """
        if not self._initialized or self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        rolling_max_price = self._get_rolling_maximum_price()

        # Use DCA controller's trigger logic
        return bool(
            self.dca_controller.check_trigger_conditions(
                current_price, rolling_max_price, self.config.percentage_trigger
            )
        )

    def process_price_update(self, current_price: float) -> None:
        """
        Process a price update and check for trigger conditions.
        Handles both new session creation and existing session management.

        Args:
            current_price: Current stock price
        """
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")

        assert self.config is not None, "Strategy engine not properly initialized"

        logger.debug(f"Processing price update: ${current_price:.2f}")

        try:
            # Get current rolling maximum
            rolling_max_price = self._get_rolling_maximum_price()

            # Check if we need to start a new DCA session
            if self.check_trigger_conditions(current_price):
                trigger_price = rolling_max_price * self.config.percentage_trigger

                # Check if we already have an active session at this trigger level
                active_sessions = self.dca_controller.get_active_sessions()
                existing_session = any(
                    abs(session.trigger_price - trigger_price) < 0.01 for session in active_sessions
                )

                if not existing_session:
                    session_id = self.dca_controller.start_dca_session(trigger_price)
                    logger.info(
                        f"Started new DCA session {session_id} at trigger price ${trigger_price:.2f}"
                    )

            # Check completion conditions for all active sessions
            active_sessions = self.dca_controller.get_active_sessions()
            for session in active_sessions:
                if self.dca_controller.check_completion_conditions(
                    session.session_id, current_price
                ):
                    logger.info(
                        f"DCA session {session.session_id} completed at price ${current_price:.2f}"
                    )

            # Update trigger calculations for future activations when rolling max increases
            if self._last_rolling_max is not None and rolling_max_price > self._last_rolling_max:
                logger.debug(
                    f"Rolling maximum increased from ${self._last_rolling_max:.2f} to ${rolling_max_price:.2f}"
                )
                self._last_rolling_max = rolling_max_price

        except Exception as e:
            logger.error(f"Error processing price update: {e}")
            raise

    def update_configuration(self, new_config: StrategyConfig) -> None:
        """
        Update the strategy configuration dynamically.

        Args:
            new_config: New strategy configuration
        """
        if not self._initialized:
            raise RuntimeError("Strategy engine not initialized")

        old_config = self.config
        self.config = new_config

        # Handle the configuration change
        if old_config is not None:
            self._handle_configuration_change(old_config, new_config)

        logger.info("Strategy configuration updated successfully")

    def get_market_status(self) -> MarketStatus:
        """
        Get the current market status and buy-the-dip recommendation.

        Returns:
            MarketStatus with current recommendation
        """
        if not self._initialized or self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        try:
            # Get current price
            current_price = self.price_monitor.get_current_price(self.config.ticker)

            # Get rolling maximum price
            rolling_max_price = self._get_rolling_maximum_price()

            # Calculate trigger price and percentage from max
            trigger_price = rolling_max_price * self.config.percentage_trigger
            percentage_from_max = ((current_price - rolling_max_price) / rolling_max_price) * 100

            # Determine if it's buy-the-dip time
            is_buy_the_dip_time = current_price <= trigger_price

            # Generate recommendation and confidence
            recommendation, confidence, message = self._generate_recommendation(
                current_price,
                rolling_max_price,
                trigger_price,
                percentage_from_max,
                is_buy_the_dip_time,
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
                last_updated=datetime.now(),
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
        is_buy_the_dip_time: bool,
    ) -> tuple[Literal["BUY", "HOLD", "MONITOR"], Literal["HIGH", "MEDIUM", "LOW"], str]:
        """
        Generate investment recommendation based on market conditions.

        Returns:
            Tuple of (recommendation, confidence_level, message)
        """
        from typing import Literal

        if is_buy_the_dip_time:
            # Calculate how deep the dip is
            dip_percentage = abs(percentage_from_max)

            if dip_percentage >= 15:  # Very deep dip
                return (
                    "BUY",
                    "HIGH",
                    f"🔥 STRONG BUY SIGNAL! Price is {dip_percentage:.1f}% below recent high. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
                )
            elif dip_percentage >= 10:  # Moderate dip
                return (
                    "BUY",
                    "MEDIUM",
                    f"📈 BUY SIGNAL! Price is {dip_percentage:.1f}% below recent high. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
                )
            else:  # Just crossed trigger
                return (
                    "BUY",
                    "MEDIUM",
                    f"✅ BUY SIGNAL! Price just crossed trigger threshold. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
                )
        else:
            # Not in buy-the-dip territory - current price is above trigger
            # Calculate how far above trigger we are as a percentage
            distance_to_trigger = ((trigger_price - current_price) / current_price) * 100
            # This will be negative when current > trigger, so we need the absolute value for display
            distance_percentage = abs(distance_to_trigger)

            if -2 <= distance_to_trigger < 0:  # Very close to trigger (within 2%)
                return (
                    "MONITOR",
                    "HIGH",
                    f"⚠️  WATCH CLOSELY! Price is {distance_percentage:.1f}% above trigger price. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
                )
            elif -5 <= distance_to_trigger < -2:  # Moderately close (2-5% above trigger)
                return (
                    "MONITOR",
                    "MEDIUM",
                    f"👀 MONITOR! Price is {distance_percentage:.1f}% above trigger price. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
                )
            else:  # Far from trigger (more than 5% above)
                return (
                    "HOLD",
                    "LOW",
                    f"😌 HOLD! Price is {distance_percentage:.1f}% above trigger price. Market looks stable. "
                    f"Current: ${current_price:.2f}, Trigger: ${trigger_price:.2f}",
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
        if not self._initialized or self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        logger.info("Starting buy-the-dip strategy execution")

        try:
            # Get current price and process it
            current_price = self.price_monitor.get_current_price(self.config.ticker)
            self.process_price_update(current_price)

            # Process monthly investments for active sessions
            active_sessions = self.dca_controller.get_active_sessions()
            for session in active_sessions:
                # Check if it's time for monthly investment (simplified for now)
                # In a real implementation, this would check dates and scheduling
                transaction = self.dca_controller.process_monthly_investment(
                    session.session_id, current_price, self.config.monthly_dca_amount
                )

                if transaction:
                    logger.info(
                        f"Processed monthly investment: ${transaction.amount:.2f} "
                        f"at ${transaction.price:.2f} for {transaction.shares:.4f} shares"
                    )

            logger.info("Strategy execution completed successfully")

        except Exception as e:
            logger.error(f"Error during strategy execution: {e}")
            raise

    def generate_report(self) -> StrategyReport:
        """
        Generate a strategy performance report.

        Returns:
            Strategy report with performance metrics
        """
        if not self._initialized or self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        try:
            # Use current DCA controller state for real-time analysis
            current_price = self.price_monitor.get_current_price(self.config.ticker)
            metrics = self.dca_controller.calculate_performance_metrics(current_price)

            # Count active and completed sessions
            active_sessions = self.dca_controller.get_active_sessions()
            all_sessions = list(self.dca_controller._sessions.values())
            completed_sessions = [s for s in all_sessions if s.state == DCAState.COMPLETED]

            current_value = metrics["portfolio_value"]
            total_return = metrics["total_return"]
            percentage_return = metrics["percentage_return"]
            active_sessions_count = len(active_sessions)
            completed_sessions_count = len(completed_sessions)

            return StrategyReport(
                ticker=self.config.ticker,
                total_invested=metrics["total_invested"],
                total_shares=metrics["total_shares"],
                current_value=current_value,
                total_return=total_return,
                percentage_return=percentage_return,
                active_sessions_count=active_sessions_count,
                completed_sessions_count=completed_sessions_count,
            )

        except Exception as e:
            logger.error(f"Error generating strategy report: {e}")
            raise

    def get_analysis_transactions(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List:
        """
        Get the transactions used for analysis in the specified period.

        Args:
            start_date: Analysis period start date
            end_date: Analysis period end date

        Returns:
            List of transactions used in the analysis
        """
        if not self._initialized or self.config is None:
            raise RuntimeError("Strategy engine not initialized")

        # Handle date parameters
        if start_date is not None or end_date is not None:
            # Default end date to today if not specified
            if end_date is None:
                end_date = date.today()

            # Default to 1 year analysis period if start date not specified
            if start_date is None:
                start_date = end_date - timedelta(days=365)

        # Determine if this is historical analysis (end date is in the past)
        is_historical_analysis = end_date is not None and end_date < date.today()

        if is_historical_analysis:
            # Ensure dates are not None for historical analysis
            assert (
                start_date is not None and end_date is not None
            ), "Dates must be set for historical analysis"

            # Run backtest to get transactions for historical period
            transactions = self.backtest_engine.run_backtest(
                config=self.config, start_date=start_date, end_date=end_date
            )
            return transactions
        else:
            # Use current DCA controller transactions
            return self.dca_controller.get_all_transactions()

    def format_comprehensive_report(
        self, report: StrategyReport, transactions: Optional[List] = None
    ) -> str:
        """
        Format a comprehensive report.

        Args:
            report: Strategy report to format
            transactions: List of transactions to include in report (optional)

        Returns:
            Formatted report string
        """
        lines = []
        lines.append(f"📊 Buy-the-Dip Strategy Report for {report.ticker}")
        lines.append("=" * 60)

        # Basic performance metrics
        lines.append("\n💰 Portfolio Summary:")
        lines.append(f"  Total Invested: ${report.total_invested:,.2f}")
        lines.append(f"  Total Shares: {report.total_shares:,.4f}")
        lines.append(f"  Current Value: ${report.current_value:,.2f}")
        lines.append(f"  Total Return: ${report.total_return:,.2f}")
        lines.append(f"  Percentage Return: {report.percentage_return:.2f}%")

        # Session information
        lines.append(f"\n📈 DCA Sessions:")
        lines.append(f"  Active Sessions: {report.active_sessions_count}")
        lines.append(f"  Completed Sessions: {report.completed_sessions_count}")

        # Transaction details if available
        if transactions:
            lines.append(f"\n💳 Investment Transactions:")
            total_invested_check = 0.0
            total_shares_check = 0.0

            # Sort transactions by date
            sorted_transactions = sorted(transactions, key=lambda t: t.date)

            for i, txn in enumerate(sorted_transactions, 1):
                lines.append(
                    f"  {i}. {txn.date} - ${txn.amount:,.2f} at ${txn.price:.2f} = {txn.shares:.4f} shares"
                )
                total_invested_check += txn.amount
                total_shares_check += txn.shares

            lines.append(
                f"  Total: ${total_invested_check:,.2f} invested, {total_shares_check:.4f} shares acquired"
            )

        return "\n".join(lines)
