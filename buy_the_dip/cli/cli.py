"""
Command-line interface implementation.
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from ..config import ConfigurationManager
from ..strategy_engine import StrategyEngine


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")


def parse_analysis_period(period_str: str) -> int:
    """Parse analysis period string and return number of days."""
    period_str = period_str.lower().strip()
    
    if period_str.endswith('d'):
        # Days: '90d', '30d'
        try:
            return int(period_str[:-1])
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid period format: {period_str}")
    
    elif period_str.endswith('m'):
        # Months: '6m', '12m'
        try:
            months = int(period_str[:-1])
            return months * 30  # Approximate days per month
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid period format: {period_str}")
    
    elif period_str.endswith('y'):
        # Years: '1y', '2y'
        try:
            years = int(period_str[:-1])
            return years * 365  # Days per year
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid period format: {period_str}")
    
    else:
        raise argparse.ArgumentTypeError(
            f"Invalid period format: {period_str}. Use format like '1y', '6m', '90d'"
        )


def resolve_date_range(args) -> Tuple[Optional[date], Optional[date]]:
    """
    Resolve start and end dates from CLI arguments.
    
    Priority:
    1. Explicit --start-date and --end-date
    2. --end-date with --analysis-period
    3. --start-date with --analysis-period (end date = today)
    4. --analysis-period only (end date = today)
    5. Default: 1 year ago to today
    
    Returns:
        Tuple of (start_date, end_date)
    """
    start_date = None
    end_date = None
    
    # Parse explicit dates
    if args.start_date:
        start_date = parse_date(args.start_date)
    
    if args.end_date:
        end_date = parse_date(args.end_date)
    
    # Handle analysis period
    if args.analysis_period:
        period_days = parse_analysis_period(args.analysis_period)
        
        if end_date and not start_date:
            # End date specified, calculate start date
            start_date = end_date - timedelta(days=period_days)
        elif start_date and not end_date:
            # Start date specified, calculate end date
            end_date = start_date + timedelta(days=period_days)
        elif not start_date and not end_date:
            # Only period specified, use today as end date
            end_date = date.today()
            start_date = end_date - timedelta(days=period_days)
        # If both dates specified, ignore analysis period
    
    # Validate date range
    if start_date and end_date:
        if start_date >= end_date:
            raise argparse.ArgumentTypeError("Start date must be before end date")
    
    return start_date, end_date


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Buy the Dip Strategy - Dollar-cost averaging during market downturns"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration YAML file"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check current market status and buy-the-dip recommendation"
    )
    
    parser.add_argument(
        "--quick-status",
        action="store_true",
        help="Get a quick one-line status update"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and display strategy performance report"
    )
    
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration file and exit"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    # Date range options for analysis
    parser.add_argument(
        "--start-date",
        type=str,
        help="Analysis start date (YYYY-MM-DD format, e.g., 2023-01-01)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        help="Analysis end date (YYYY-MM-DD format, e.g., 2024-12-31)"
    )
    
    parser.add_argument(
        "--analysis-period",
        type=str,
        help="Analysis period from end date (e.g., '1y', '6m', '90d', '2y')"
    )
    
    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate config file exists if specified
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {args.config}")
                sys.exit(1)
        
        # Load configuration
        config_manager = ConfigurationManager()
        config = config_manager.load_config(args.config)
        
        if not (args.status or args.quick_status):
            logger.info(f"Loaded configuration for ticker: {config.ticker}")
            logger.info(f"Rolling window: {config.rolling_window_days} days")
            logger.info(f"Trigger percentage: {config.percentage_trigger:.1%}")
            logger.info(f"Monthly DCA amount: ${config.monthly_dca_amount:.2f}")
        
        if args.validate_config:
            logger.info("Configuration validation successful")
            return
        
        # Initialize strategy engine
        engine = StrategyEngine()
        engine.initialize(config)
        
        if args.quick_status:
            # Quick one-line status
            print(engine.get_quick_status())
            return
        
        if args.status:
            # Detailed market status
            status = engine.get_market_status()
            
            print(f"\n🎯 BUY THE DIP STATUS - {status.ticker}")
            print("=" * 50)
            print(f"Current Price:     ${status.current_price:.2f}")
            print(f"Rolling Max ({config.rolling_window_days}d): ${status.rolling_max_price:.2f}")
            print(f"Trigger Price:     ${status.trigger_price:.2f}")
            print(f"From High:         {status.percentage_from_max:+.1f}%")
            print(f"")
            print(f"🎯 RECOMMENDATION: {status.recommendation} ({status.confidence_level} confidence)")
            print(f"💬 {status.message}")
            print(f"")
            print(f"⏰ Last Updated: {status.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if status.is_buy_the_dip_time:
                print(f"\n🚨 ACTION REQUIRED: Consider investing your DCA amount of ${config.monthly_dca_amount:.2f}")
            else:
                distance_to_trigger = ((status.trigger_price - status.current_price) / status.current_price) * 100
                distance_percentage = abs(distance_to_trigger)
                print(f"\n📊 Price needs to drop by {distance_percentage:.1f}% to trigger buy signal")
            
            return
        
        if args.report:
            # Resolve date range from CLI arguments
            try:
                start_date, end_date = resolve_date_range(args)
                
                # Log the analysis period being used
                if start_date and end_date:
                    period_days = (end_date - start_date).days
                    logger.info(f"Analyzing period: {start_date} to {end_date} ({period_days} days)")
                else:
                    logger.info("Using default 1-year analysis period")
                
                report = engine.generate_report(include_cagr=True, cagr_start_date=start_date, cagr_end_date=end_date)
                
                # Use the comprehensive formatted report
                formatted_report = engine.format_comprehensive_report(report)
                print(formatted_report)
                
            except argparse.ArgumentTypeError as e:
                logger.error(f"Date range error: {e}")
                sys.exit(1)
        else:
            # Run the strategy
            engine.run_strategy()
            
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()