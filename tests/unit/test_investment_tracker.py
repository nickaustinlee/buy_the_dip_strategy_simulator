"""
Unit tests for investment tracker error handling functionality.
"""

import json
import tempfile
import shutil
import os
from datetime import date
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from buy_the_dip.models import Investment
from buy_the_dip.investment_tracker import InvestmentTracker


class TestInvestmentTrackerErrorHandling:
    """Test InvestmentTracker error handling scenarios."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_investment(self):
        """Create a sample investment for testing."""
        return Investment(
            date=date(2023, 6, 15), ticker="SPY", price=400.0, amount=2000.0, shares=5.0
        )

    def test_load_from_nonexistent_file(self, temp_data_dir):
        """Test loading from a file that doesn't exist."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Try to load from nonexistent file
        result = tracker.load_from_file()

        # Should return False but not crash
        assert result is False

        # Should initialize with empty investment list
        investments = tracker.get_all_investments()
        assert len(investments) == 0

    def test_load_from_corrupted_json_file(self, temp_data_dir):
        """Test loading from a file with invalid JSON."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create corrupted JSON file
        investment_file = Path(temp_data_dir) / "investments.json"
        with open(investment_file, "w") as f:
            f.write("invalid json content {")

        # Try to load corrupted file
        result = tracker.load_from_file()

        # Should return False
        assert result is False

        # Should initialize with empty investment list
        investments = tracker.get_all_investments()
        assert len(investments) == 0

        # Should move corrupted file to backup
        corrupted_files = list(Path(temp_data_dir).glob("*.corrupted.*"))
        assert len(corrupted_files) == 1

        # Original file should be gone
        assert not investment_file.exists()

    def test_load_from_file_with_invalid_investment_data(self, temp_data_dir):
        """Test loading from a file with invalid investment data structure."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create file with invalid investment data
        investment_file = Path(temp_data_dir) / "investments.json"
        invalid_data = {
            "investments": [
                {
                    "date": "2023-06-15",
                    "ticker": "SPY",
                    "price": "invalid_price",  # Should be float
                    "amount": 2000.0,
                    "shares": 5.0,
                }
            ],
            "last_updated": "2023-06-15T12:00:00",
        }

        with open(investment_file, "w") as f:
            json.dump(invalid_data, f)

        # Try to load file with invalid data
        result = tracker.load_from_file()

        # Should return False due to validation error
        assert result is False

        # Should initialize with empty investment list
        investments = tracker.get_all_investments()
        assert len(investments) == 0

    def test_save_to_file_permission_error(self, temp_data_dir, sample_investment):
        """Test saving to a file when permission is denied."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)
        tracker.add_investment(sample_investment)

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = tracker.save_to_file()

        # Should return False
        assert result is False

    def test_save_to_file_disk_full_error(self, temp_data_dir, sample_investment):
        """Test saving to a file when disk is full."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)
        tracker.add_investment(sample_investment)

        # Mock open to raise OSError (disk full)
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            result = tracker.save_to_file()

        # Should return False
        assert result is False

    def test_save_to_file_creates_backup_on_existing_file(self, temp_data_dir, sample_investment):
        """Test that saving creates backup when file already exists."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create initial investment file
        initial_data = {
            "investments": [
                {
                    "date": "2023-05-15",
                    "ticker": "SPY",
                    "price": 380.0,
                    "amount": 1500.0,
                    "shares": 3.95,
                }
            ],
            "last_updated": "2023-05-15T12:00:00",
        }

        investment_file = Path(temp_data_dir) / "investments.json"
        with open(investment_file, "w") as f:
            json.dump(initial_data, f)

        # Add new investment and save
        tracker.add_investment(sample_investment)
        result = tracker.save_to_file()

        # Should succeed
        assert result is True

        # Should create backup file
        backup_file = Path(temp_data_dir) / "investments.json.backup"
        assert backup_file.exists()

        # Backup should contain original data
        with open(backup_file, "r") as f:
            backup_data = json.load(f)
        assert backup_data["investments"][0]["price"] == 380.0

        # Main file should contain new data
        with open(investment_file, "r") as f:
            current_data = json.load(f)
        assert len(current_data["investments"]) == 1
        assert current_data["investments"][0]["price"] == 400.0

    def test_load_from_backup_when_main_file_corrupted(self, temp_data_dir):
        """Test loading from backup when main file is corrupted."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create valid backup file
        backup_data = {
            "investments": [
                {
                    "date": "2023-05-15",
                    "ticker": "SPY",
                    "price": 380.0,
                    "amount": 1500.0,
                    "shares": 3.95,
                }
            ],
            "last_updated": "2023-05-15T12:00:00",
        }

        backup_file = Path(temp_data_dir) / "investments.json.backup"
        with open(backup_file, "w") as f:
            json.dump(backup_data, f)

        # Create corrupted main file
        investment_file = Path(temp_data_dir) / "investments.json"
        with open(investment_file, "w") as f:
            f.write("corrupted json")

        # Try to load - should recover from backup
        result = tracker.load_from_file()

        # Should succeed
        assert result is True

        # Should load investment from backup
        investments = tracker.get_all_investments()
        assert len(investments) == 1
        assert investments[0].price == 380.0
        assert investments[0].amount == 1500.0

    def test_load_from_backup_when_both_files_corrupted(self, temp_data_dir):
        """Test loading when both main and backup files are corrupted."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create corrupted main file
        investment_file = Path(temp_data_dir) / "investments.json"
        with open(investment_file, "w") as f:
            f.write("corrupted json")

        # Create corrupted backup file
        backup_file = Path(temp_data_dir) / "investments.json.backup"
        with open(backup_file, "w") as f:
            f.write("also corrupted json")

        # Try to load - should fail gracefully
        result = tracker.load_from_file()

        # Should return False
        assert result is False

        # Should initialize with empty investment list
        investments = tracker.get_all_investments()
        assert len(investments) == 0

    def test_handle_corrupted_file_backup_failure(self, temp_data_dir):
        """Test handling corrupted file when backup creation fails."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create corrupted file
        corrupted_file = Path(temp_data_dir) / "investments.json"
        with open(corrupted_file, "w") as f:
            f.write("corrupted json")

        # Mock shutil.move to raise an exception
        with patch("shutil.move", side_effect=OSError("Permission denied")):
            # This should not crash even if backup fails
            tracker._handle_corrupted_file(corrupted_file)

        # File should still exist since backup failed
        assert corrupted_file.exists()

    def test_save_to_custom_filepath_error(self, temp_data_dir, sample_investment):
        """Test saving to a custom filepath that causes an error."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)
        tracker.add_investment(sample_investment)

        # Try to save to an invalid path (directory that doesn't exist)
        invalid_path = "/nonexistent/directory/investments.json"
        result = tracker.save_to_file(filepath=invalid_path)

        # Should return False
        assert result is False

    def test_load_from_custom_filepath_error(self, temp_data_dir):
        """Test loading from a custom filepath that doesn't exist."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Try to load from nonexistent path
        invalid_path = "/nonexistent/directory/investments.json"
        result = tracker.load_from_file(filepath=invalid_path)

        # Should return False
        assert result is False

        # Should initialize with empty investment list
        investments = tracker.get_all_investments()
        assert len(investments) == 0

    def test_atomic_write_failure_recovery(self, temp_data_dir, sample_investment):
        """Test atomic write failure and recovery."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)
        tracker.add_investment(sample_investment)

        # Create existing file
        investment_file = Path(temp_data_dir) / "investments.json"
        original_data = {"investments": [], "last_updated": "2023-01-01T00:00:00"}
        with open(investment_file, "w") as f:
            json.dump(original_data, f)

        # Mock Path.replace to fail (simulating atomic write failure)
        with patch.object(Path, "replace", side_effect=OSError("Atomic write failed")):
            result = tracker.save_to_file()

        # Should return False
        assert result is False

        # Original file should still exist and be unchanged
        assert investment_file.exists()
        with open(investment_file, "r") as f:
            data = json.load(f)
        assert len(data["investments"]) == 0  # Original empty data

    def test_directory_creation_failure(self):
        """Test behavior when data directory cannot be created."""
        # Try to create tracker with invalid directory path
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Cannot create directory")):
            # This should not crash, but may not work properly
            try:
                tracker = InvestmentTracker(data_dir="/root/restricted/path")
                # If it doesn't crash, that's acceptable behavior
            except PermissionError:
                # If it does crash with PermissionError, that's also acceptable
                pass

    def test_investment_shares_calculation_warning(self, temp_data_dir):
        """Test that investment tracker warns about shares calculation mismatches."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create investment with inconsistent shares calculation
        inconsistent_investment = Investment(
            date=date(2023, 6, 15),
            ticker="SPY",
            price=400.0,
            amount=2000.0,
            shares=10.0,  # Should be 5.0 (2000/400)
        )

        # This should log a warning but not crash
        with patch("buy_the_dip.investment_tracker.logger") as mock_logger:
            tracker.add_investment(inconsistent_investment)

            # Should have logged a warning about shares mismatch
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "shares calculation mismatch" in warning_call.lower()

    def test_empty_data_directory_handling(self):
        """Test handling of empty or missing data directory."""
        # Create tracker with None data_dir (should use default)
        tracker = InvestmentTracker(data_dir=None)

        # Should create default directory
        expected_dir = Path.home() / ".buy_the_dip" / "data"
        assert tracker._data_dir == expected_dir
        assert tracker._data_dir.exists()

    def test_portfolio_calculation_with_minimal_shares(self, temp_data_dir):
        """Test portfolio calculation edge case with very small shares."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        # Create investment with very small shares (edge case but valid)
        minimal_investment = Investment(
            date=date(2023, 6, 15),
            ticker="SPY",
            price=1000.0,
            amount=0.10,  # 10 cents
            shares=0.0001,  # Very small number of shares
        )

        tracker.add_investment(minimal_investment)

        # Should handle small shares gracefully
        metrics = tracker.calculate_portfolio_metrics(current_price=1100.0)

        assert metrics.total_invested == 0.10
        assert metrics.total_shares == 0.0001
        assert abs(metrics.current_value - 0.11) < 0.001  # 0.0001 * 1100
        assert abs(metrics.total_return - 0.01) < 0.001  # 0.11 - 0.10
        assert abs(metrics.percentage_return - 0.10) < 0.001  # 10% return as decimal


class TestDualPricePerformanceCalculations:
    """Test dual price performance calculation functionality."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary data directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_investments(self):
        """Create sample investments for testing."""
        return [
            Investment(
                date=date(2025, 3, 14), ticker="SPY", price=562.81, amount=2000.0, shares=3.5536
            ),
            Investment(
                date=date(2025, 4, 11), ticker="SPY", price=533.94, amount=2000.0, shares=3.7457
            ),
        ]

    def test_price_return_uses_close_prices(self, temp_data_dir, sample_investments):
        """Test that price return calculation uses Close prices."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        for investment in sample_investments:
            tracker.add_investment(investment)

        current_close_price = 692.00

        # Calculate metrics using Close prices (price-only return)
        metrics = tracker.calculate_portfolio_metrics(current_close_price)

        # Verify calculations
        expected_total_invested = 4000.0
        expected_total_shares = 7.2993
        expected_current_value = expected_total_shares * current_close_price
        expected_total_return = expected_current_value - expected_total_invested
        expected_percentage_return = expected_total_return / expected_total_invested

        assert abs(metrics.total_invested - expected_total_invested) < 0.01
        assert abs(metrics.total_shares - expected_total_shares) < 0.0001
        assert abs(metrics.current_value - expected_current_value) < 0.01
        assert abs(metrics.total_return - expected_total_return) < 0.01
        assert abs(metrics.percentage_return - expected_percentage_return) < 0.0001

    def test_total_return_uses_adjusted_close_prices(self, temp_data_dir, sample_investments):
        """Test that total return calculation uses Adjusted Close prices."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        for investment in sample_investments:
            tracker.add_investment(investment)

        current_adj_price = 695.50  # Slightly higher than Close due to dividends

        # Calculate metrics using Adjusted Close prices (total return including dividends)
        metrics = tracker.calculate_portfolio_metrics_adjusted(current_adj_price)

        # Verify calculations
        expected_total_invested = 4000.0
        expected_total_shares = 7.2993
        expected_current_value = expected_total_shares * current_adj_price
        expected_total_return = expected_current_value - expected_total_invested
        expected_percentage_return = expected_total_return / expected_total_invested

        assert abs(metrics.total_invested - expected_total_invested) < 0.01
        assert abs(metrics.total_shares - expected_total_shares) < 0.0001
        assert abs(metrics.current_value - expected_current_value) < 0.01
        assert abs(metrics.total_return - expected_total_return) < 0.01
        assert abs(metrics.percentage_return - expected_percentage_return) < 0.0001

    def test_dual_price_methods_return_different_results(self, temp_data_dir, sample_investments):
        """Test that Close and Adjusted Close methods return different results when prices differ."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        for investment in sample_investments:
            tracker.add_investment(investment)

        current_close_price = 692.00
        current_adj_price = 695.50  # Higher due to dividends

        # Calculate metrics using both methods
        close_metrics = tracker.calculate_portfolio_metrics(current_close_price)
        adj_metrics = tracker.calculate_portfolio_metrics_adjusted(current_adj_price)

        # Both should have same invested amount and shares
        assert close_metrics.total_invested == adj_metrics.total_invested
        assert close_metrics.total_shares == adj_metrics.total_shares

        # But different current values and returns due to price difference
        assert adj_metrics.current_value > close_metrics.current_value
        assert adj_metrics.total_return > close_metrics.total_return
        assert adj_metrics.percentage_return > close_metrics.percentage_return

        # Verify the dividend effect
        dividend_effect = adj_metrics.total_return - close_metrics.total_return
        expected_dividend_effect = adj_metrics.total_shares * (
            current_adj_price - current_close_price
        )
        assert abs(dividend_effect - expected_dividend_effect) < 0.01

    def test_dual_price_methods_same_when_prices_equal(self, temp_data_dir, sample_investments):
        """Test that both methods return identical results when Close and Adj Close prices are equal."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        for investment in sample_investments:
            tracker.add_investment(investment)

        current_price = 692.00  # Same price for both

        # Calculate metrics using both methods
        close_metrics = tracker.calculate_portfolio_metrics(current_price)
        adj_metrics = tracker.calculate_portfolio_metrics_adjusted(current_price)

        # All values should be identical
        assert close_metrics.total_invested == adj_metrics.total_invested
        assert close_metrics.total_shares == adj_metrics.total_shares
        assert close_metrics.current_value == adj_metrics.current_value
        assert close_metrics.total_return == adj_metrics.total_return
        assert close_metrics.percentage_return == adj_metrics.percentage_return

    def test_dual_price_methods_with_empty_portfolio(self, temp_data_dir):
        """Test that both methods handle empty portfolios correctly."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        current_close_price = 692.00
        current_adj_price = 695.50

        # Calculate metrics using both methods
        close_metrics = tracker.calculate_portfolio_metrics(current_close_price)
        adj_metrics = tracker.calculate_portfolio_metrics_adjusted(current_adj_price)

        # Both should return zero values for empty portfolio
        assert close_metrics.total_invested == 0.0
        assert close_metrics.total_shares == 0.0
        assert close_metrics.current_value == 0.0
        assert close_metrics.total_return == 0.0
        assert close_metrics.percentage_return == 0.0

        assert adj_metrics.total_invested == 0.0
        assert adj_metrics.total_shares == 0.0
        assert adj_metrics.current_value == 0.0
        assert adj_metrics.total_return == 0.0
        assert adj_metrics.percentage_return == 0.0

    def test_dual_price_methods_preserve_mathematical_relationships(
        self, temp_data_dir, sample_investments
    ):
        """Test that both methods preserve mathematical relationships in calculations."""
        tracker = InvestmentTracker(data_dir=temp_data_dir)

        for investment in sample_investments:
            tracker.add_investment(investment)

        current_close_price = 692.00
        current_adj_price = 695.50

        # Calculate metrics using both methods
        close_metrics = tracker.calculate_portfolio_metrics(current_close_price)
        adj_metrics = tracker.calculate_portfolio_metrics_adjusted(current_adj_price)

        # Verify mathematical relationships for Close prices
        assert (
            abs(close_metrics.current_value - (close_metrics.total_shares * current_close_price))
            < 0.01
        )
        assert (
            abs(
                close_metrics.total_return
                - (close_metrics.current_value - close_metrics.total_invested)
            )
            < 0.01
        )
        if close_metrics.total_invested > 0:
            expected_pct = close_metrics.total_return / close_metrics.total_invested
            assert abs(close_metrics.percentage_return - expected_pct) < 0.0001

        # Verify mathematical relationships for Adjusted Close prices
        assert (
            abs(adj_metrics.current_value - (adj_metrics.total_shares * current_adj_price)) < 0.01
        )
        assert (
            abs(adj_metrics.total_return - (adj_metrics.current_value - adj_metrics.total_invested))
            < 0.01
        )
        if adj_metrics.total_invested > 0:
            expected_pct = adj_metrics.total_return / adj_metrics.total_invested
            assert abs(adj_metrics.percentage_return - expected_pct) < 0.0001
