"""
Property-based tests for investment constraint enforcement functionality.
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


class TestInvestmentConstraintProperties:
    """Property-based tests for investment constraint enforcement."""

    @given(
        investment_dates=st.lists(
            st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            min_size=2,
            max_size=20
        ),
        check_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31))
    )
    def test_investment_constraint_enforcement(
        self,
        investment_dates: List[date],
        check_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any sequence of investment attempts over time, the system should never allow 
        two investments within 28 calendar days of each other, maintaining this as an 
        invariant across all operations and using calendar days (not trading days).
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
        """
        # Remove duplicates and sort dates
        unique_dates = sorted(set(investment_dates))
        assume(len(unique_dates) >= 2)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Simulate attempting to make investments on all dates
            successful_investments = []
            
            for investment_date in unique_dates:
                # Check if investment should be allowed (no investment within 28 days)
                should_be_allowed = not investment_tracker.has_recent_investment(investment_date, days=28)
                
                if should_be_allowed:
                    # Simulate successful investment
                    investment = Investment(
                        date=investment_date,
                        ticker="SPY",
                        price=150.0,
                        amount=2000.0,
                        shares=13.33
                    )
                    investment_tracker.add_investment(investment)
                    successful_investments.append(investment_date)
            
            # Verify constraint: no two successful investments within 28 days (allow exactly 28 days)
            for i in range(len(successful_investments)):
                for j in range(i + 1, len(successful_investments)):
                    date1 = successful_investments[i]
                    date2 = successful_investments[j]
                    days_apart = abs((date2 - date1).days)
                    
                    assert days_apart >= 28, \
                        f"Constraint violation: investments on {date1} and {date2} are only {days_apart} days apart (should be >= 28)"
            
            # Test the constraint checking function with the check_date
            has_recent = investment_tracker.has_recent_investment(check_date, days=28)
            
            # Manually verify the result (check past 28 days exclusive to allow investment on day 28)
            cutoff_date = check_date - timedelta(days=28)
            expected_has_recent = any(
                cutoff_date < inv_date < check_date
                for inv_date in successful_investments
            )
            
            assert has_recent == expected_has_recent, \
                f"Constraint check result should match expected: {has_recent} != {expected_has_recent}"

    @given(
        base_date=st.dates(min_value=date(2023, 2, 1), max_value=date(2023, 11, 1)),
        days_between=st.integers(min_value=1, max_value=27)  # Within 27 days (should be blocked)
    )
    def test_constraint_prevents_investments_within_28_days(
        self,
        base_date: date,
        days_between: int
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any two investment attempts within 27 calendar days, the second attempt 
        should be prevented by the constraint enforcement.
        
        Validates: Requirements 5.1, 5.2
        """
        second_date = base_date + timedelta(days=days_between)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Make first investment
            first_investment = Investment(
                date=base_date,
                ticker="SPY",
                price=150.0,
                amount=2000.0,
                shares=13.33
            )
            investment_tracker.add_investment(first_investment)
            
            # Check constraint for second investment (look back 28 days exclusive)
            has_recent_investment = investment_tracker.has_recent_investment(second_date, days=28)
            
            # Should have recent investment since days_between <= 27 (within 28 days exclusive)
            assert has_recent_investment, \
                f"Should detect recent investment {days_between} days ago (within 28 days exclusive)"
            
            # Verify the constraint would prevent investment decision
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # Even with trigger met, should not invest due to recent investment
            should_invest = strategy_system.should_invest(
                yesterday_price=100.0,  # Below trigger
                trigger_price=150.0,    # Above yesterday price
                evaluation_date=second_date
            )
            
            assert not should_invest, \
                f"Should not invest when recent investment exists {days_between} days ago (within 28 days exclusive)"

    @given(
        base_date=st.dates(min_value=date(2023, 2, 1), max_value=date(2023, 10, 1)),
        days_between=st.integers(min_value=28, max_value=60)  # Outside 28 days (28+ allowed)
    )
    def test_constraint_allows_investments_after_28_days(
        self,
        base_date: date,
        days_between: int
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any two investment attempts 28 or more calendar days apart, the second 
        attempt should be allowed by the constraint enforcement.
        
        Validates: Requirements 5.3
        """
        second_date = base_date + timedelta(days=days_between)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Make first investment
            first_investment = Investment(
                date=base_date,
                ticker="SPY",
                price=150.0,
                amount=2000.0,
                shares=13.33
            )
            investment_tracker.add_investment(first_investment)
            
            # Check constraint for second investment (look back 28 days exclusive)
            has_recent_investment = investment_tracker.has_recent_investment(second_date, days=28)
            
            # Should not have recent investment since days_between >= 28
            assert not has_recent_investment, \
                f"Should not detect recent investment {days_between} days ago (>= 28 days apart)"
            
            # Verify the constraint would allow investment decision
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # With trigger met and no recent investment, should invest
            should_invest = strategy_system.should_invest(
                yesterday_price=100.0,  # Below trigger
                trigger_price=150.0,    # Above yesterday price
                evaluation_date=second_date
            )
            
            assert should_invest, \
                f"Should invest when no recent investment exists ({days_between} days ago is >= 28 days)"

    @given(
        investment_dates=st.lists(
            st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            min_size=3,
            max_size=15
        )
    )
    def test_constraint_uses_calendar_days_not_trading_days(
        self,
        investment_dates: List[date]
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any investment constraint checking, the system should use calendar days 
        (not trading days) for the 28-day calculation, including weekends and holidays.
        
        Validates: Requirements 5.4
        """
        # Remove duplicates and sort dates
        unique_dates = sorted(set(investment_dates))
        assume(len(unique_dates) >= 3)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Add investments
            for investment_date in unique_dates[:-1]:  # All but last date
                investment = Investment(
                    date=investment_date,
                    ticker="SPY",
                    price=150.0,
                    amount=2000.0,
                    shares=13.33
                )
                investment_tracker.add_investment(investment)
            
            # Check constraint for the last date (look back 28 days exclusive)
            check_date = unique_dates[-1]
            has_recent = investment_tracker.has_recent_investment(check_date, days=28)
            
            # Manually calculate using calendar days (including weekends) - look back 28 days exclusive
            cutoff_date = check_date - timedelta(days=28)
            expected_has_recent = any(
                cutoff_date < inv_date < check_date
                for inv_date in unique_dates[:-1]
            )
            
            assert has_recent == expected_has_recent, \
                f"Constraint should use calendar days, not trading days"
            
            # Verify that weekends are included in the calculation
            # by checking specific weekend dates if they exist in the range
            for inv_date in unique_dates[:-1]:
                days_diff = (check_date - inv_date).days
                if 0 < days_diff < 28:
                    # This investment should be detected as recent (within 28 days exclusive)
                    assert has_recent, \
                        f"Investment on {inv_date} should be detected as recent " \
                        f"({days_diff} calendar days ago, including weekends)"

    @given(
        base_date=st.dates(min_value=date(2023, 2, 1), max_value=date(2023, 11, 1))
    )
    def test_constraint_boundary_conditions(
        self,
        base_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For boundary conditions (exactly 28 days), the constraint should allow 
        investments exactly 28 days apart (same weekday pattern).
        
        Validates: Requirements 5.1, 5.2, 5.3
        """
        # Test dates at various boundaries
        test_cases = [
            (base_date + timedelta(days=27), True),   # 27 days later - should be blocked
            (base_date + timedelta(days=28), False),  # 28 days later - should be allowed (same weekday)
            (base_date + timedelta(days=29), False),  # 29 days later - should be allowed
        ]
        
        for test_date, should_be_blocked in test_cases:
            # Create temporary directory for investment tracker
            with tempfile.TemporaryDirectory() as temp_dir:
                investment_tracker = InvestmentTracker(data_dir=temp_dir)
                
                # Make first investment
                first_investment = Investment(
                    date=base_date,
                    ticker="SPY",
                    price=150.0,
                    amount=2000.0,
                    shares=13.33
                )
                investment_tracker.add_investment(first_investment)
                
                # Check constraint (look back 28 days exclusive)
                has_recent = investment_tracker.has_recent_investment(test_date, days=28)
                
                days_diff = (test_date - base_date).days
                
                if should_be_blocked:
                    assert has_recent, \
                        f"Investment should be blocked at {days_diff} days (within 28 days exclusive)"
                else:
                    assert not has_recent, \
                        f"Investment should be allowed at {days_diff} days (>= 28 days apart)"

    @given(
        investment_sequence=st.lists(
            st.tuples(
                st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
                st.floats(min_value=100.0, max_value=300.0, exclude_min=True),  # price
                st.floats(min_value=1000.0, max_value=5000.0, exclude_min=True)  # amount
            ),
            min_size=5,
            max_size=20
        )
    )
    def test_constraint_maintained_as_invariant(
        self,
        investment_sequence: List[tuple]
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any sequence of operations, the 28-day constraint should be maintained 
        as an invariant across all operations, never allowing violations.
        
        Validates: Requirements 5.5
        """
        # Sort by date to ensure chronological order
        sorted_sequence = sorted(set(investment_sequence), key=lambda x: x[0])
        assume(len(sorted_sequence) >= 5)
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30
            )
            
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            successful_investments = []
            
            # Process each potential investment in chronological order
            for inv_date, price, amount in sorted_sequence:
                # Skip NaN and infinite values
                if price != price or price == float('inf') or price == float('-inf'):
                    continue
                if amount != amount or amount == float('inf') or amount == float('-inf'):
                    continue
                
                # Skip if we already have an investment on this date
                if inv_date in successful_investments:
                    continue
                
                # Check if investment would be allowed (look back 28 days exclusive)
                has_recent = investment_tracker.has_recent_investment(inv_date, days=28)
                
                if not has_recent:
                    # Investment should be allowed - add it
                    investment = Investment(
                        date=inv_date,
                        ticker="SPY",
                        price=price,
                        amount=amount,
                        shares=amount / price
                    )
                    investment_tracker.add_investment(investment)
                    successful_investments.append(inv_date)
                
                # Verify invariant: no two investments within 28 days
                for i in range(len(successful_investments)):
                    for j in range(i + 1, len(successful_investments)):
                        date1 = successful_investments[i]
                        date2 = successful_investments[j]
                        days_apart = abs((date2 - date1).days)
                        
                        assert days_apart >= 28, \
                            f"INVARIANT VIOLATION: investments on {date1} and {date2} " \
                            f"are only {days_apart} days apart (should be >= 28)"

    @given(
        check_date=st.dates(min_value=date(2023, 1, 29), max_value=date(2023, 12, 31))
    )
    def test_constraint_with_no_investment_history(
        self,
        check_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any date with no investment history, the constraint should allow investment 
        (no recent investments exist).
        
        Validates: Requirements 5.3
        """
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Check constraint with empty history (look back 28 days exclusive)
            has_recent = investment_tracker.has_recent_investment(check_date, days=28)
            
            # Should not have recent investment with empty history
            assert not has_recent, \
                f"Should not have recent investment with empty history"
            
            # Verify investment would be allowed (if trigger conditions met)
            config = StrategyConfig(
                ticker="SPY",
                rolling_window_days=90,
                percentage_trigger=0.90,
                monthly_dca_amount=2000.0,
                data_cache_days=30
            )
            
            strategy_system = StrategySystem(config, investment_tracker=investment_tracker)
            
            # With trigger met and no history, should invest
            should_invest = strategy_system.should_invest(
                yesterday_price=100.0,  # Below trigger
                trigger_price=150.0,    # Above yesterday price
                evaluation_date=check_date
            )
            
            assert should_invest, \
                f"Should invest with no investment history and trigger met"

    @given(
        investment_date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 11, 1)),
        check_dates=st.lists(
            st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            min_size=5,
            max_size=15
        )
    )
    def test_constraint_consistency_across_multiple_checks(
        self,
        investment_date: date,
        check_dates: List[date]
    ):
        """
        Feature: buy-the-dip-strategy, Property 5: Investment Constraint Enforcement
        
        For any investment and multiple check dates, the constraint checking should 
        be consistent - dates within 28 days (exclusive) should always be blocked, dates 28+ days 
        apart should always be allowed.
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        """
        # Remove duplicates and sort check dates
        unique_check_dates = sorted(set(check_dates))
        
        # Create temporary directory for investment tracker
        with tempfile.TemporaryDirectory() as temp_dir:
            investment_tracker = InvestmentTracker(data_dir=temp_dir)
            
            # Add single investment
            investment = Investment(
                date=investment_date,
                ticker="SPY",
                price=150.0,
                amount=2000.0,
                shares=13.33
            )
            investment_tracker.add_investment(investment)
            
            # Check constraint for each date (look back 28 days exclusive)
            for check_date in unique_check_dates:
                has_recent = investment_tracker.has_recent_investment(check_date, days=28)
                
                # Calculate expected result
                days_diff = (check_date - investment_date).days
                
                if 0 < days_diff < 28:
                    # Within 28 days exclusive - should be blocked
                    assert has_recent, \
                        f"Check date {check_date} is {days_diff} days after investment " \
                        f"({investment_date}) - should be blocked"
                else:
                    # Outside 28 days or before/same as investment - should be allowed
                    assert not has_recent, \
                        f"Check date {check_date} is {days_diff} days from investment " \
                        f"({investment_date}) - should be allowed"