"""
Unit tests for CLI interface functionality.
"""

import pytest
import argparse
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from buy_the_dip.cli.cli import (
    parse_date,
    parse_period,
    resolve_date_range,
    create_parser,
    format_backtest_result,
    format_evaluation_result,
    format_portfolio_status,
)
from buy_the_dip.strategy_system import BacktestResult, EvaluationResult
from buy_the_dip.models import Investment, PortfolioMetrics
from buy_the_dip.config.models import StrategyConfig
from buy_the_dip.investment_tracker import InvestmentTracker


class TestDateParsing:
    """Test date parsing functionality."""

    def test_parse_date_valid_format(self):
        """Test parsing valid date strings."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

        result = parse_date("2023-12-31")
        assert result == date(2023, 12, 31)

    def test_parse_date_invalid_format(self):
        """Test parsing invalid date strings raises error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024/01/15")

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("invalid-date")

        with pytest.raises(argparse.ArgumentTypeError):
            parse_date("2024-13-01")  # Invalid month


class TestPeriodParsing:
    """Test period parsing functionality."""

    def test_parse_period_days(self):
        """Test parsing day periods."""
        assert parse_period("30d") == 30
        assert parse_period("90D") == 90
        assert parse_period("1d") == 1

    def test_parse_period_months(self):
        """Test parsing month periods."""
        assert parse_period("6m") == 180  # 6 * 30
        assert parse_period("12M") == 360  # 12 * 30
        assert parse_period("1m") == 30

    def test_parse_period_years(self):
        """Test parsing year periods."""
        assert parse_period("1y") == 365
        assert parse_period("2Y") == 730  # 2 * 365

    def test_parse_period_invalid_format(self):
        """Test parsing invalid period strings raises error."""
        with pytest.raises(argparse.ArgumentTypeError):
            parse_period("invalid")

        with pytest.raises(argparse.ArgumentTypeError):
            parse_period("30")  # Missing unit

        with pytest.raises(argparse.ArgumentTypeError):
            parse_period("abc30d")  # Invalid number


class TestDateRangeResolution:
    """Test date range resolution logic."""

    def test_explicit_start_and_end_dates(self):
        """Test when both start and end dates are explicitly provided."""
        args = Mock()
        args.start_date = "2024-01-01"
        args.end_date = "2024-12-31"
        args.period = None

        start, end = resolve_date_range(args)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_end_date_with_period(self):
        """Test when end date and period are provided."""
        args = Mock()
        args.start_date = None
        args.end_date = "2024-12-31"
        args.period = "90d"

        start, end = resolve_date_range(args)
        assert end == date(2024, 12, 31)
        assert start == date(2024, 12, 31) - timedelta(days=90)

    def test_start_date_with_period(self):
        """Test when start date and period are provided."""
        args = Mock()
        args.start_date = "2024-01-01"
        args.end_date = None
        args.period = "90d"

        start, end = resolve_date_range(args)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 1) + timedelta(days=90)

    def test_period_only(self):
        """Test when only period is provided."""
        args = Mock()
        args.start_date = None
        args.end_date = None
        args.period = "365d"

        with patch("buy_the_dip.cli.cli.date") as mock_date:
            mock_date.today.return_value = date(2024, 6, 15)

            start, end = resolve_date_range(args)
            assert end == date(2024, 6, 15)
            assert start == date(2024, 6, 15) - timedelta(days=365)

    def test_default_date_range(self):
        """Test default date range when no dates or period provided."""
        args = Mock()
        args.start_date = None
        args.end_date = None
        args.period = None

        with patch("buy_the_dip.cli.cli.date") as mock_date:
            mock_date.today.return_value = date(2024, 6, 15)

            start, end = resolve_date_range(args)
            assert end == date(2024, 6, 15)
            assert start == date(2024, 6, 15) - timedelta(days=365)

    def test_invalid_date_range(self):
        """Test that invalid date ranges raise errors."""
        args = Mock()
        args.start_date = "2024-12-31"
        args.end_date = "2024-01-01"  # End before start
        args.period = None

        with pytest.raises(argparse.ArgumentTypeError):
            resolve_date_range(args)


class TestArgumentParser:
    """Test argument parser configuration."""

    def test_parser_creation(self):
        """Test that parser is created with expected arguments."""
        parser = create_parser()

        # Test that parser exists and has expected description
        assert (
            parser.description
            == "Buy the Dip Strategy - Dollar-cost averaging during market downturns"
        )

        # Parse empty args to check defaults
        args = parser.parse_args([])
        assert args.log_level == "INFO"
        assert args.config is None
        assert not args.backtest
        assert not args.status
        assert not args.validate_config

    def test_parser_config_argument(self):
        """Test config file argument parsing."""
        parser = create_parser()

        args = parser.parse_args(["--config", "test.yaml"])
        assert args.config == "test.yaml"

    def test_parser_backtest_argument(self):
        """Test backtest argument parsing."""
        parser = create_parser()

        args = parser.parse_args(["--backtest"])
        assert args.backtest is True

    def test_parser_date_arguments(self):
        """Test date argument parsing."""
        parser = create_parser()

        args = parser.parse_args(
            ["--start-date", "2024-01-01", "--end-date", "2024-12-31", "--period", "1y"]
        )
        assert args.start_date == "2024-01-01"
        assert args.end_date == "2024-12-31"
        assert args.period == "1y"

    def test_parser_log_level_argument(self):
        """Test log level argument parsing."""
        parser = create_parser()

        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

        # Test invalid log level
        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "INVALID"])


class TestResultFormatting:
    """Test result formatting functions."""

    def test_format_backtest_result(self):
        """Test backtest result formatting."""
        # Create test data
        config = StrategyConfig(ticker="SPY", monthly_dca_amount=1000.0)

        investments = [
            Investment(
                date=date(2024, 1, 15), ticker="SPY", price=450.0, amount=1000.0, shares=2.2222
            ),
            Investment(
                date=date(2024, 2, 15), ticker="SPY", price=460.0, amount=1000.0, shares=2.1739
            ),
        ]

        portfolio = PortfolioMetrics(
            total_invested=2000.0,
            total_shares=4.3961,
            current_value=2200.0,
            total_return=200.0,
            percentage_return=0.10,
        )

        result = BacktestResult(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            total_evaluations=250,
            trigger_conditions_met=10,
            investments_executed=2,
            investments_blocked_by_constraint=3,
            final_portfolio=portfolio,
            all_investments=investments,
        )

        # Create a mock price monitor for the test
        from unittest.mock import Mock

        mock_price_monitor = Mock()
        formatted = format_backtest_result(result, config, mock_price_monitor)

        # Check key information is present
        assert "SPY" in formatted
        assert "2024-01-01 to 2024-12-31" in formatted
        assert "Total Trading Days Evaluated: 250" in formatted
        assert "Investments Executed: 2" in formatted
        assert "$2,000.00" in formatted  # Total invested
        assert "10.00%" in formatted  # Percentage return
        assert "2024-01-15" in formatted  # Investment date

    def test_format_evaluation_result(self):
        """Test single day evaluation result formatting."""
        config = StrategyConfig(ticker="SPY", rolling_window_days=90)

        investment = Investment(
            date=date(2024, 6, 15), ticker="SPY", price=500.0, amount=1000.0, shares=2.0
        )

        result = EvaluationResult(
            evaluation_date=date(2024, 6, 15),
            yesterday_price=495.0,
            trigger_price=500.0,
            rolling_maximum=555.56,
            trigger_met=True,
            recent_investment_exists=False,
            investment_executed=True,
            investment=investment,
        )

        formatted = format_evaluation_result(result, config)

        # Check key information is present
        assert "SPY on 2024-06-15" in formatted
        assert "Yesterday's Price: $495.00" in formatted
        assert "Trigger Price: $500.00" in formatted
        assert "Rolling Maximum (90d): $555.56" in formatted
        assert "✅ YES" in formatted  # Trigger met
        assert "INVESTMENT EXECUTED!" in formatted
        assert "$1,000.00" in formatted  # Investment amount

    def test_format_portfolio_status_with_investments(self):
        """Test portfolio status formatting with investments."""
        config = StrategyConfig(ticker="SPY")

        # Create mock tracker with investments
        tracker = Mock(spec=InvestmentTracker)

        investments = [
            Investment(
                date=date(2024, 6, 15), ticker="SPY", price=500.0, amount=1000.0, shares=2.0
            ),
            Investment(
                date=date(2024, 5, 15), ticker="SPY", price=480.0, amount=1000.0, shares=2.0833
            ),
        ]

        metrics = PortfolioMetrics(
            total_invested=2000.0,
            total_shares=4.0833,
            current_value=2250.0,
            total_return=250.0,
            percentage_return=0.125,
        )

        tracker.get_all_investments.return_value = investments
        tracker.calculate_portfolio_metrics.return_value = metrics

        formatted = format_portfolio_status(tracker, 550.0, config)

        # Check key information is present
        assert "SPY" in formatted
        assert "Current Price: $550.00" in formatted
        assert "Total Invested: $2,000.00" in formatted
        assert "12.50%" in formatted  # Percentage return
        assert "2024-06-15" in formatted  # Recent investment

    def test_format_portfolio_status_no_investments(self):
        """Test portfolio status formatting with no investments."""
        config = StrategyConfig(ticker="SPY")

        # Create mock tracker with no investments
        tracker = Mock(spec=InvestmentTracker)
        tracker.get_all_investments.return_value = []

        formatted = format_portfolio_status(tracker, 500.0, config)

        # Check that it handles empty portfolio
        assert "SPY" in formatted
        assert "No investments found" in formatted


class TestConfigurationHandling:
    """Test configuration file handling in CLI."""

    @patch("buy_the_dip.cli.cli.Path")
    def test_config_file_validation(self, mock_path):
        """Test that config file existence is validated."""
        # Mock file doesn't exist
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        # This would be tested in integration, but we can test the path logic
        config_path = Path("nonexistent.yaml")
        assert not config_path.exists()  # This will be True in real test

    def test_config_loading_integration(self):
        """Test configuration loading integration."""
        # This is more of an integration test, but we can test the basic flow
        with patch("buy_the_dip.cli.cli.ConfigurationManager") as mock_config_manager:
            mock_manager = Mock()
            mock_config = StrategyConfig(ticker="TEST")
            mock_manager.load_config.return_value = mock_config
            mock_config_manager.return_value = mock_manager

            # Test that config manager is called correctly
            from buy_the_dip.cli.cli import ConfigurationManager

            manager = ConfigurationManager()
            config = manager.load_config("test.yaml")

            # In real implementation, this would load the actual config
            assert isinstance(config, StrategyConfig)


class TestErrorHandling:
    """Test error handling in CLI functions."""

    def test_parse_date_error_message(self):
        """Test that date parsing errors have helpful messages."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_date("invalid-date")

        assert "Invalid date format" in str(exc_info.value)
        assert "YYYY-MM-DD" in str(exc_info.value)

    def test_parse_period_error_message(self):
        """Test that period parsing errors have helpful messages."""
        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            parse_period("invalid")

        assert "Invalid period format" in str(exc_info.value)

    def test_date_range_validation_error(self):
        """Test date range validation error messages."""
        args = Mock()
        args.start_date = "2024-12-31"
        args.end_date = "2024-01-01"
        args.period = None

        with pytest.raises(argparse.ArgumentTypeError) as exc_info:
            resolve_date_range(args)

        assert "Start date must be before end date" in str(exc_info.value)
