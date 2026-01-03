"""
Property-based tests for investment execution accuracy functionality.
"""

import tempfile
from datetime import date, timedelta
from typing import List

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.strategy_system import StrategySystem
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.investment_tracker import InvestmentTracker
from buy_the_dip.models import Investment


class TestInvestmentExecutionProperties:
    """Property-based tests for investment execution accuracy."""

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=50.0, max_value=500.0, exclude_min=True),
        monthly_dca_amount=st.floats(min_value=1000.0, max_value=5000.0, exclude_min=True),
        ticker=st.sampled_from(["SPY", "AAPL", "MSFT", "GOOGL", "TSLA"])
    )
    def test_investment_execution_and_recording_accuracy(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float,
        ticker: str
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any executed investment, the system should use the current day's closing price, 
        invest exactly the monthly_dca_amount, and accurately record the date, price, amount, 
        and calculated shares (amount/price).
        
        Validates: Requirements 4.4, 4.5, 6.1, 6.2, 6.3, 6.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker=ticker,
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify investment execution accuracy
            # 1. Date should match evaluation date
            assert investment.date == evaluation_date, \
                f"Investment date should match evaluation date: {investment.date} != {evaluation_date}"
            
            # 2. Ticker should match configuration
            assert investment.ticker == ticker, \
                f"Investment ticker should match config: {investment.ticker} != {ticker}"
            
            # 3. Price should match closing price
            assert abs(investment.price - closing_price) < 0.01, \
                f"Investment price should match closing price: {investment.price} != {closing_price}"
            
            # 4. Amount should match monthly DCA amount exactly
            assert abs(investment.amount - monthly_dca_amount) < 0.01, \
                f"Investment amount should match monthly DCA amount: {investment.amount} != {monthly_dca_amount}"
            
            # 5. Shares should be calculated correctly (amount / price)
            expected_shares = monthly_dca_amount / closing_price
            assert abs(investment.shares - expected_shares) < 0.0001, \
                f"Investment shares should be calculated as amount/price: {investment.shares} != {expected_shares}"
            
            # 6. Investment should be recorded in tracker
            all_investments = investment_tracker.get_all_investments()
            assert len(all_investments) == 1, "Investment should be recorded in tracker"
            
            recorded_investment = all_investments[0]
            assert recorded_investment.date == investment.date
            assert recorded_investment.ticker == investment.ticker
            assert abs(recorded_investment.price - investment.price) < 0.01
            assert abs(recorded_investment.amount - investment.amount) < 0.01
            assert abs(recorded_investment.shares - investment.shares) < 0.0001

    @given(
        investments_data=st.lists(
            st.tuples(
                st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
                st.floats(min_value=100.0, max_value=300.0, exclude_min=True),  # closing_price
                st.floats(min_value=1500.0, max_value=3000.0, exclude_min=True)  # amount
            ),
            min_size=1,
            max_size=10
        ),
        ticker=st.sampled_from(["SPY", "QQQ", "VTI"])
    )
    def test_multiple_investment_execution_accuracy(
        self,
        investments_data: List[tuple],
        ticker: str
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any sequence of investment executions, each should be recorded accurately 
        with correct calculations and all investments should be preserved.
        
        Validates: Requirements 4.4, 4.5, 6.1, 6.2, 6.3, 6.4
        """
        # Remove duplicates by date and sort by date (keep first occurrence for each date)
        seen_dates = set()
        unique_investments = []
        for eval_date, price, amount in sorted(investments_data, key=lambda x: x[0]):
            if eval_date not in seen_dates:
                seen_dates.add(eval_date)
                unique_investments.append((eval_date, price, amount))
        
        # Skip NaN and infinite values
        filtered_investments = []
        for eval_date, price, amount in unique_investments:
            if (price == price and price != float('inf') and price != float('-inf') and
                amount == amount and amount != float('inf') and amount != float('-inf')):
                filtered_investments.append((eval_date, price, amount))
        
        assume(len(filtered_investments) >= 1)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker=ticker,
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,  # Default, will be overridden per investment
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            executed_investments = []
            
            # Execute all investments
            for eval_date, closing_price, amount in filtered_investments:
                investment = strategy_system.execute_investment(eval_date, closing_price, amount)
                executed_investments.append(investment)
            
            # Verify all investments were recorded
            all_investments = investment_tracker.get_all_investments()
            assert len(all_investments) == len(executed_investments), \
                f"All investments should be recorded: {len(all_investments)} != {len(executed_investments)}"
            
            # Verify each investment's accuracy
            for i, (eval_date, closing_price, amount) in enumerate(filtered_investments):
                investment = executed_investments[i]
                
                # Verify execution accuracy
                assert investment.date == eval_date
                assert investment.ticker == ticker
                assert abs(investment.price - closing_price) < 0.01
                assert abs(investment.amount - amount) < 0.01
                
                expected_shares = amount / closing_price
                assert abs(investment.shares - expected_shares) < 0.0001
                
                # Verify it's in the recorded investments (should be exactly one since we removed duplicates)
                matching_investments = [
                    inv for inv in all_investments
                    if (inv.date == eval_date and 
                        abs(inv.price - closing_price) < 0.01 and
                        abs(inv.amount - amount) < 0.01)
                ]
                assert len(matching_investments) == 1, \
                    f"Should find exactly one matching recorded investment for {eval_date}"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=1.0, max_value=10.0, exclude_min=True),  # Low price for high share count
        monthly_dca_amount=st.floats(min_value=1000.0, max_value=2000.0, exclude_min=True)
    )
    def test_shares_calculation_precision(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution, the shares calculation should be precise and 
        mathematically correct (amount / price), even with fractional shares.
        
        Validates: Requirements 6.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify shares calculation precision
            expected_shares = monthly_dca_amount / closing_price
            
            # Should be mathematically correct within floating point precision
            assert abs(investment.shares - expected_shares) < 1e-10, \
                f"Shares calculation should be precise: {investment.shares} != {expected_shares}"
            
            # Verify the relationship holds: shares * price ≈ amount
            calculated_amount = investment.shares * investment.price
            assert abs(calculated_amount - investment.amount) < 0.01, \
                f"Shares * price should equal amount: {calculated_amount} != {investment.amount}"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        monthly_dca_amount=st.floats(min_value=2000.0, max_value=3000.0, exclude_min=True)
    )
    def test_investment_uses_current_day_closing_price(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution, the system should use the current day's closing price 
        (not yesterday's price or any other price) for the investment.
        
        Validates: Requirements 4.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment with specific closing price
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify the investment uses exactly the provided closing price
            assert abs(investment.price - closing_price) < 0.001, \
                f"Investment should use current day's closing price: {investment.price} != {closing_price}"
            
            # Verify shares are calculated based on this exact price
            expected_shares = monthly_dca_amount / closing_price
            assert abs(investment.shares - expected_shares) < 0.0001, \
                f"Shares should be calculated using current day's closing price"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
        config_amount=st.floats(min_value=1000.0, max_value=4000.0, exclude_min=True),
        execution_amount=st.floats(min_value=1500.0, max_value=3500.0, exclude_min=True)
    )
    def test_investment_uses_exact_specified_amount(
        self,
        evaluation_date: date,
        closing_price: float,
        config_amount: float,
        execution_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution, the system should invest exactly the specified amount 
        (not the config amount if different amount is provided to execute_investment).
        
        Validates: Requirements 4.5
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(config_amount == config_amount and config_amount != float('inf') and config_amount != float('-inf'))
        assume(execution_amount == execution_amount and execution_amount != float('inf') and execution_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=config_amount,  # Different from execution amount
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment with specific amount (different from config)
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, execution_amount
            )
            
            # Verify the investment uses exactly the specified execution amount
            assert abs(investment.amount - execution_amount) < 0.01, \
                f"Investment should use exact specified amount: {investment.amount} != {execution_amount}"
            
            # Verify it doesn't use the config amount
            if abs(config_amount - execution_amount) > 1.0:  # Only check if amounts are significantly different
                assert abs(investment.amount - config_amount) > 0.1, \
                    f"Investment should not use config amount when different amount specified"
            
            # Verify shares are calculated based on the execution amount
            expected_shares = execution_amount / closing_price
            assert abs(investment.shares - expected_shares) < 0.0001, \
                f"Shares should be calculated using execution amount: {investment.shares} != {expected_shares}"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=100.0, max_value=200.0, exclude_min=True),
        monthly_dca_amount=st.floats(min_value=2000.0, max_value=3000.0, exclude_min=True)
    )
    def test_investment_recording_completeness(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution, all required fields should be recorded completely 
        and accurately in the investment tracker.
        
        Validates: Requirements 6.1, 6.2, 6.3, 6.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="MSFT",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify all required fields are present and valid
            assert investment.date is not None, "Investment date should be recorded"
            assert investment.ticker is not None and investment.ticker != "", "Investment ticker should be recorded"
            assert investment.price > 0, "Investment price should be positive and recorded"
            assert investment.amount > 0, "Investment amount should be positive and recorded"
            assert investment.shares > 0, "Investment shares should be positive and recorded"
            
            # Verify specific values
            assert investment.date == evaluation_date, "Date should be recorded accurately"
            assert investment.ticker == "MSFT", "Ticker should be recorded accurately"
            assert abs(investment.price - closing_price) < 0.01, "Price should be recorded accurately"
            assert abs(investment.amount - monthly_dca_amount) < 0.01, "Amount should be recorded accurately"
            
            expected_shares = monthly_dca_amount / closing_price
            assert abs(investment.shares - expected_shares) < 0.0001, "Shares should be calculated and recorded accurately"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=0.01, max_value=0.1, exclude_min=True),  # Very low price
        monthly_dca_amount=st.floats(min_value=1000.0, max_value=2000.0, exclude_min=True)
    )
    def test_investment_execution_with_fractional_shares(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution that results in fractional shares, the calculation 
        should be accurate and the fractional shares should be recorded correctly.
        
        Validates: Requirements 6.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment (should result in many fractional shares due to low price)
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify fractional shares are calculated correctly
            expected_shares = monthly_dca_amount / closing_price
            assert abs(investment.shares - expected_shares) < 1e-10, \
                f"Fractional shares should be calculated precisely: {investment.shares} != {expected_shares}"
            
            # Verify shares are likely fractional (not whole numbers) given the low price
            assert investment.shares > 1000, "Should have many shares due to low price"
            
            # Verify the mathematical relationship still holds
            calculated_amount = investment.shares * investment.price
            assert abs(calculated_amount - investment.amount) < 0.01, \
                f"Fractional shares * price should equal amount: {calculated_amount} != {investment.amount}"

    @given(
        evaluation_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
        closing_price=st.floats(min_value=1000.0, max_value=5000.0, exclude_min=True),  # Very high price
        monthly_dca_amount=st.floats(min_value=500.0, max_value=1500.0, exclude_min=True)  # Lower amount
    )
    def test_investment_execution_with_small_share_amounts(
        self,
        evaluation_date: date,
        closing_price: float,
        monthly_dca_amount: float
    ):
        """
        Feature: buy-the-dip-strategy, Property 6: Investment Execution and Recording Accuracy
        
        For any investment execution that results in small fractional share amounts 
        (less than 1 share), the calculation should still be accurate.
        
        Validates: Requirements 6.4
        """
        # Skip NaN and infinite values
        assume(closing_price == closing_price and closing_price != float('inf') and closing_price != float('-inf'))
        assume(monthly_dca_amount == monthly_dca_amount and monthly_dca_amount != float('inf') and monthly_dca_amount != float('-inf'))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="BRK.A",  # Expensive stock ticker
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=monthly_dca_amount,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Execute investment (should result in small fractional shares due to high price)
            investment = strategy_system.execute_investment(
                evaluation_date, closing_price, monthly_dca_amount
            )
            
            # Verify small fractional shares are calculated correctly
            expected_shares = monthly_dca_amount / closing_price
            assert abs(investment.shares - expected_shares) < 1e-10, \
                f"Small fractional shares should be calculated precisely: {investment.shares} != {expected_shares}"
            
            # Verify shares are likely less than 1 given the high price and lower amount
            if closing_price > monthly_dca_amount:
                assert investment.shares < 1.0, "Should have less than 1 share due to high price"
            
            # Verify shares are positive
            assert investment.shares > 0, "Shares should be positive even if fractional"
            
            # Verify the mathematical relationship still holds
            calculated_amount = investment.shares * investment.price
            assert abs(calculated_amount - investment.amount) < 0.01, \
                f"Small fractional shares * price should equal amount: {calculated_amount} != {investment.amount}"