"""
Property-based tests for investment persistence functionality.
"""

import tempfile
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st, assume

from buy_the_dip.models import Investment
from buy_the_dip.investment_tracker import InvestmentTracker


class TestInvestmentPersistenceProperties:
    """Property-based tests for investment persistence."""

    @given(
        investments=st.lists(
            st.builds(
                Investment,
                date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)),
                ticker=st.sampled_from(["SPY", "AAPL", "MSFT", "GOOGL", "TSLA"]),
                price=st.floats(min_value=1.0, max_value=1000.0, exclude_min=True),
                amount=st.floats(min_value=100.0, max_value=10000.0, exclude_min=True),
                shares=st.floats(min_value=0.1, max_value=100.0, exclude_min=True),
            ),
            min_size=0,
            max_size=50,
        )
    )
    def test_investment_persistence_round_trip(self, investments: List[Investment]):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For any investment history, saving to file and then loading should produce
        an equivalent investment list, with immediate persistence on investment execution
        and proper constraint checking using persisted data across sessions.

        Validates: Requirements 7.1, 7.2, 7.3
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create tracker with temporary directory
            tracker = InvestmentTracker(data_dir=temp_dir)

            # Add all investments to tracker
            for investment in investments:
                tracker.add_investment(investment)

            # Save investments to file
            save_success = tracker.save_to_file()
            assert save_success, "Save operation should succeed"

            # Create new tracker instance and load from file
            new_tracker = InvestmentTracker(data_dir=temp_dir)
            load_success = new_tracker.load_from_file()

            if investments:
                assert load_success, "Load operation should succeed when investments exist"

            # Get loaded investments
            loaded_investments = new_tracker.get_all_investments()

            # Verify round-trip consistency
            assert len(loaded_investments) == len(investments), "Number of investments should match"

            # Sort both lists by date and ticker for comparison
            original_sorted = sorted(investments, key=lambda x: (x.date, x.ticker, x.price))
            loaded_sorted = sorted(loaded_investments, key=lambda x: (x.date, x.ticker, x.price))

            for original, loaded in zip(original_sorted, loaded_sorted):
                assert (
                    loaded.date == original.date
                ), f"Date mismatch: {loaded.date} != {original.date}"
                assert (
                    loaded.ticker == original.ticker
                ), f"Ticker mismatch: {loaded.ticker} != {original.ticker}"
                assert (
                    abs(loaded.price - original.price) < 0.01
                ), f"Price mismatch: {loaded.price} != {original.price}"
                assert (
                    abs(loaded.amount - original.amount) < 0.01
                ), f"Amount mismatch: {loaded.amount} != {original.amount}"
                assert (
                    abs(loaded.shares - original.shares) < 0.0001
                ), f"Shares mismatch: {loaded.shares} != {original.shares}"

    @given(
        investments=st.lists(
            st.builds(
                Investment,
                date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)),
                ticker=st.sampled_from(["SPY", "AAPL", "MSFT"]),
                price=st.floats(min_value=10.0, max_value=500.0, exclude_min=True),
                amount=st.floats(min_value=500.0, max_value=5000.0, exclude_min=True),
                shares=st.floats(min_value=1.0, max_value=50.0, exclude_min=True),
            ),
            min_size=1,
            max_size=20,
        ),
        check_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31)),
    )
    def test_constraint_checking_with_persisted_data(
        self, investments: List[Investment], check_date: date
    ):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For any persisted investment history, the 28-day constraint checking should work
        correctly across sessions, using the persisted data to enforce constraints.

        Validates: Requirements 7.2, 7.3
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create first tracker and add investments
            tracker1 = InvestmentTracker(data_dir=temp_dir)
            for investment in investments:
                tracker1.add_investment(investment)

            # Save investments
            save_success = tracker1.save_to_file()
            assert save_success, "Save operation should succeed"

            # Create second tracker instance (simulating new session)
            tracker2 = InvestmentTracker(data_dir=temp_dir)
            load_success = tracker2.load_from_file()
            assert load_success, "Load operation should succeed"

            # Check 28-day constraint using both trackers
            result1 = tracker1.has_recent_investment(check_date, days=28)
            result2 = tracker2.has_recent_investment(check_date, days=28)

            # Results should be identical
            assert result1 == result2, "Constraint checking should be consistent across sessions"

            # Verify the result is correct based on actual investment dates
            cutoff_date = check_date - timedelta(days=28)
            expected_result = any(
                cutoff_date < inv.date < check_date  # Exclusive of check_date
                for inv in investments
            )

            assert (
                result1 == expected_result
            ), f"Constraint check result should match expected: {result1} != {expected_result}"

    @given(
        investment=st.builds(
            Investment,
            date=st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
            ticker=st.sampled_from(["SPY", "QQQ", "VTI"]),
            price=st.floats(min_value=50.0, max_value=300.0, exclude_min=True),
            amount=st.floats(min_value=1000.0, max_value=3000.0, exclude_min=True),
            shares=st.floats(min_value=3.0, max_value=20.0, exclude_min=True),
        )
    )
    def test_immediate_persistence_on_investment_execution(self, investment: Investment):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For any investment execution, the investment should be immediately persistable
        and recoverable, ensuring no data loss during system failures.

        Validates: Requirements 7.1
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = InvestmentTracker(data_dir=temp_dir)

            # Add investment (simulating execution)
            tracker.add_investment(investment)

            # Immediately save (simulating immediate persistence)
            save_success = tracker.save_to_file()
            assert save_success, "Immediate save after investment should succeed"

            # Verify file exists
            investment_file = Path(temp_dir) / "investments.json"
            assert investment_file.exists(), "Investment file should exist after save"

            # Create new tracker and load (simulating recovery)
            recovery_tracker = InvestmentTracker(data_dir=temp_dir)
            load_success = recovery_tracker.load_from_file()
            assert load_success, "Recovery load should succeed"

            # Verify investment was recovered
            recovered_investments = recovery_tracker.get_all_investments()
            assert len(recovered_investments) == 1, "Should recover exactly one investment"

            recovered = recovered_investments[0]
            assert recovered.date == investment.date
            assert recovered.ticker == investment.ticker
            assert abs(recovered.price - investment.price) < 0.01
            assert abs(recovered.amount - investment.amount) < 0.01
            assert abs(recovered.shares - investment.shares) < 0.0001

    def test_persistence_handles_empty_investment_list(self):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For an empty investment history, saving and loading should work correctly
        and maintain the empty state.

        Validates: Requirements 7.1, 7.2, 7.3
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = InvestmentTracker(data_dir=temp_dir)

            # Save empty investment list
            save_success = tracker.save_to_file()
            assert save_success, "Save of empty list should succeed"

            # Load in new tracker
            new_tracker = InvestmentTracker(data_dir=temp_dir)
            load_success = new_tracker.load_from_file()
            assert load_success, "Load should succeed even for empty list"

            # Verify empty state is maintained
            loaded_investments = new_tracker.get_all_investments()
            assert len(loaded_investments) == 0, "Should maintain empty investment list"

            # Verify constraint checking works with empty list
            check_date = date(2023, 6, 15)
            has_recent = new_tracker.has_recent_investment(check_date)
            assert not has_recent, "Empty list should have no recent investments"

    def test_persistence_handles_corrupted_file_gracefully(self):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For corrupted investment files, the system should handle the error gracefully
        and initialize with empty history while preserving the corrupted file.

        Validates: Requirements 7.4
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create corrupted investment file
            investment_file = Path(temp_dir) / "investments.json"
            with open(investment_file, "w") as f:
                f.write("invalid json content {")

            # Try to load from corrupted file
            tracker = InvestmentTracker(data_dir=temp_dir)
            load_success = tracker.load_from_file()

            # Should handle gracefully (return False but not crash)
            assert not load_success, "Load should return False for corrupted file"

            # Should initialize with empty history
            investments = tracker.get_all_investments()
            assert len(investments) == 0, "Should initialize with empty history"

            # Verify corrupted file was moved (not deleted)
            corrupted_files = list(Path(temp_dir).glob("*.corrupted.*"))
            assert len(corrupted_files) == 1, "Should create backup of corrupted file"

    def test_persistence_uses_backup_when_main_file_corrupted(self):
        """
        Feature: buy-the-dip-strategy, Property 8: Investment Persistence Round-Trip

        For corrupted main files with valid backup files, the system should recover
        from backup and restore normal operation.

        Validates: Requirements 7.2, 7.3
        """
        # Create temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = InvestmentTracker(data_dir=temp_dir)

            # Add and save an investment (creates backup)
            investment = Investment(
                date=date(2023, 5, 15), ticker="SPY", price=400.0, amount=2000.0, shares=5.0
            )
            tracker.add_investment(investment)
            tracker.save_to_file()

            # Add another investment and save (updates main file, backup has first investment)
            investment2 = Investment(
                date=date(2023, 6, 15), ticker="SPY", price=420.0, amount=2000.0, shares=4.76
            )
            tracker.add_investment(investment2)
            tracker.save_to_file()

            # Corrupt main file
            investment_file = Path(temp_dir) / "investments.json"
            with open(investment_file, "w") as f:
                f.write("corrupted content")

            # Load should recover from backup
            recovery_tracker = InvestmentTracker(data_dir=temp_dir)
            load_success = recovery_tracker.load_from_file()
            assert load_success, "Should successfully recover from backup"

            # Should have the first investment (from backup)
            recovered_investments = recovery_tracker.get_all_investments()
            assert len(recovered_investments) == 1, "Should recover investment from backup"
            assert recovered_investments[0].date == investment.date
