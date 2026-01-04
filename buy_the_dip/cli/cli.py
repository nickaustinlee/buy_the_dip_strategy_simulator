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
from ..strategy_system import StrategySystem, BacktestResult
from ..price_monitor import PriceMonitor
from ..investment_tracker import InvestmentTracker


def validate_cached_data(price_monitor: PriceMonitor, ticker: str, max_records: int = 50) -> dict:
    """
    Validate cached data against live API data for a specific ticker.
    Uses a hybrid sampling strategy:
    - 20% most recent data (critical for current operations)
    - 10% random sample from remaining data (broader coverage)
    
    Args:
        price_monitor: PriceMonitor instance
        ticker: Stock ticker to validate
        max_records: Maximum number of records to validate (default: 50)
        
    Returns:
        Dictionary with validation results
    """
    from datetime import date, timedelta
    import pandas as pd
    import random
    
    # Get cached data
    cached_data = price_monitor._load_cached_data(ticker)
    if cached_data is None or cached_data.empty:
        return {
            'valid': False,
            'records_checked': 0,
            'mismatches': 0,
            'error': 'No cached data found'
        }
    
    # Sort by date (newest first)
    cached_data_sorted = cached_data.sort_values('Date', ascending=False)
    total_records = len(cached_data_sorted)
    
    if total_records == 0:
        return {
            'valid': False,
            'records_checked': 0,
            'mismatches': 0,
            'error': 'No cached data available'
        }
    
    # Check if cache has less than 30 days of data - if so, validate entire cache
    date_range_days = (cached_data_sorted['Date'].max() - cached_data_sorted['Date'].min()).days
    
    if date_range_days < 30 or total_records <= max_records:
        # Small cache or fits within max_records - validate everything
        validation_data = cached_data_sorted
        recent_count = total_records
        random_count = 0
    else:
        # Calculate sampling strategy for larger caches
        recent_count = max(1, int(total_records * 0.20))  # 20% most recent
        remaining_records = total_records - recent_count
        random_count = max(0, int(remaining_records * 0.10))  # 10% of remaining
        
        # Cap total records to max_records
        total_to_check = recent_count + random_count
        if total_to_check > max_records:
            # Prioritize recent data, adjust random sample
            recent_count = min(recent_count, int(max_records * 0.7))  # At least 70% recent
            random_count = max_records - recent_count
        
        # Get recent data (most important)
        recent_cached = cached_data_sorted.head(recent_count)
        
        # Get random sample from remaining data
        if random_count > 0 and remaining_records > 0:
            remaining_data = cached_data_sorted.iloc[recent_count:]
            if len(remaining_data) <= random_count:
                # If remaining data is small, take all of it
                random_cached = remaining_data
            else:
                # Random sample from remaining data
                random_indices = random.sample(range(len(remaining_data)), random_count)
                random_cached = remaining_data.iloc[random_indices]
            
            # Combine recent and random samples
            validation_data = pd.concat([recent_cached, random_cached], ignore_index=True)
        else:
            validation_data = recent_cached
    
    if validation_data.empty:
        return {
            'valid': False,
            'records_checked': 0,
            'mismatches': 0,
            'error': 'No data selected for validation'
        }
    
    # Get date range from the validation data
    start_date = validation_data['Date'].min()
    end_date = validation_data['Date'].max()
    
    # Temporarily clear cache to force fresh API fetch
    original_cache = price_monitor._cache.get(ticker)
    original_cached_data = price_monitor._load_cached_data(ticker)
    
    # Clear both in-memory and persistent cache temporarily
    price_monitor._cache.pop(ticker, None)
    cache_file = price_monitor._get_cache_file_path(ticker)
    cache_file_existed = cache_file.exists()
    if cache_file_existed:
        cache_file.rename(cache_file.with_suffix('.backup'))
    
    try:
        # Fetch fresh data from API for the date range
        fresh_data = price_monitor.fetch_price_data(ticker, start_date, end_date)
        
        if fresh_data.empty:
            return {
                'valid': False,
                'records_checked': 0,
                'mismatches': 0,
                'error': 'Could not fetch fresh data from API',
                'sampling_info': {
                    'total_cached_records': total_records,
                    'recent_records_checked': recent_count,
                    'random_records_checked': random_count,
                    'total_records_checked': len(validation_data),
                    'validation_strategy': 'full_cache' if date_range_days < 30 or total_records <= max_records else 'hybrid_sampling',
                    'cache_date_range_days': date_range_days
                }
            }
        
        # Compare cached vs fresh data
        mismatches = []
        records_checked = 0
        
        for _, cached_row in validation_data.iterrows():
            cached_date = cached_row['Date']
            cached_price = cached_row['Close']
            
            # Find matching date in fresh data
            fresh_match = fresh_data[fresh_data['Date'] == cached_date]
            if not fresh_match.empty:
                fresh_price = fresh_match['Close'].iloc[0]
                records_checked += 1
                
                # Check if prices match (allow small floating point differences)
                if abs(cached_price - fresh_price) > 0.01:  # 1 cent tolerance
                    mismatches.append({
                        'date': cached_date,
                        'cached': cached_price,
                        'api': fresh_price,
                        'difference': abs(cached_price - fresh_price)
                    })
        
        return {
            'valid': len(mismatches) == 0,
            'records_checked': records_checked,
            'mismatches': len(mismatches),
            'sample_mismatches': mismatches[:5],  # First 5 mismatches
            'sampling_info': {
                'total_cached_records': total_records,
                'recent_records_checked': recent_count,
                'random_records_checked': random_count if random_count > 0 else 0,
                'total_records_checked': len(validation_data),
                'recent_percentage': round((recent_count / total_records) * 100, 1),
                'random_percentage': round((random_count / max(1, total_records - recent_count)) * 100, 1) if random_count > 0 else 0,
                'validation_strategy': 'full_cache' if date_range_days < 30 or total_records <= max_records else 'hybrid_sampling',
                'cache_date_range_days': date_range_days
            }
        }
        
    finally:
        # Restore original cache
        if original_cache is not None:
            price_monitor._cache[ticker] = original_cache
        
        # Restore persistent cache
        if cache_file_existed:
            backup_file = cache_file.with_suffix('.backup')
            if backup_file.exists():
                backup_file.rename(cache_file)


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


def parse_period(period_str: str) -> int:
    """Parse period string and return number of days."""
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
    2. --end-date with --period
    3. --start-date with --period (end date = today)
    4. --period only (end date = today)
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
    
    # Handle period
    if args.period:
        period_days = parse_period(args.period)
        
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
        # If both dates specified, ignore period
    
    # Default to 1 year if no dates specified
    if not start_date and not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
    
    # Validate date range
    if start_date and end_date:
        if start_date >= end_date:
            raise argparse.ArgumentTypeError("Start date must be before end date")
    
    return start_date, end_date


def format_backtest_result(result: BacktestResult, config, price_monitor: PriceMonitor) -> str:
    """Format backtest result for display."""
    lines = []
    lines.append(f"\n🎯 BACKTEST RESULTS - {config.ticker}")
    lines.append("=" * 60)
    lines.append(f"Period: {result.start_date} to {result.end_date}")
    lines.append(f"Total Trading Days Evaluated: {result.total_evaluations}")
    lines.append(f"Trigger Conditions Met: {result.trigger_conditions_met}")
    lines.append(f"Investments Executed: {result.investments_executed}")
    lines.append(f"Investments Blocked (28-day rule): {result.investments_blocked_by_constraint}")
    lines.append("")
    
    # Portfolio metrics
    portfolio = result.final_portfolio
    lines.append("📊 PORTFOLIO PERFORMANCE")
    lines.append("-" * 30)
    lines.append(f"Total Invested: ${portfolio.total_invested:,.2f}")
    lines.append(f"Total Shares: {portfolio.total_shares:.4f}")
    lines.append(f"Current Value: ${portfolio.current_value:,.2f}")
    lines.append(f"Total Return: ${portfolio.total_return:,.2f}")
    
    if portfolio.total_invested > 0:
        lines.append(f"Strategy Return: {portfolio.percentage_return:.2%}")
    else:
        lines.append("Strategy Return: N/A (no investments)")
    
    # Buy-and-hold comparison
    if result.all_investments:
        try:
            # Get start and end prices for buy-and-hold comparison
            # Data should already be cached from backtest, so this should be fast
            price_monitor_logger = logging.getLogger('buy_the_dip.price_monitor.price_monitor')
            original_level = price_monitor_logger.level
            price_monitor_logger.setLevel(logging.ERROR)
            
            price_data = price_monitor.fetch_price_data(config.ticker, result.start_date, result.end_date)
            
            price_monitor_logger.setLevel(original_level)
            
            # Log API stats after buy-and-hold fetch
            api_stats_after_bh = price_monitor.get_api_stats()
            logging.getLogger(__name__).debug(f"After buy-and-hold fetch - API calls: {api_stats_after_bh['api_calls_made']}, Cache hits: {api_stats_after_bh['cache_hits']}")
            
            if not price_data.empty:
                start_price = float(price_data.iloc[0]['Close'])
                end_price = float(price_data.iloc[-1]['Close'])
                buyhold_return = (end_price - start_price) / start_price
                
                lines.append("")
                lines.append("📈 COMPARISON - Strategy vs Buy-and-Hold")
                lines.append("-" * 30)
                lines.append(f"Strategy Return: {portfolio.percentage_return:.2%}")
                lines.append(f"Buy-and-Hold Return: {buyhold_return:.2%}")
                lines.append(f"Outperformance: {(portfolio.percentage_return - buyhold_return):+.2%}")
                
        except Exception as e:
            price_monitor_logger.setLevel(original_level)
            logging.getLogger(__name__).warning(f"Could not calculate buy-and-hold comparison: {e}")
    
    lines.append("")
    
    # Investment history
    if result.all_investments:
        lines.append("💰 INVESTMENT HISTORY")
        lines.append("-" * 30)
        for inv in result.all_investments:
            lines.append(f"{inv.date}: ${inv.amount:,.2f} at ${inv.price:.2f} = {inv.shares:.4f} shares")
    else:
        lines.append("💰 No investments were executed during this period")
    
    return "\n".join(lines)


def format_evaluation_result(result, config) -> str:
    """Format single day evaluation result for display."""
    lines = []
    lines.append(f"\n🎯 EVALUATION RESULT - {config.ticker} on {result.evaluation_date}")
    lines.append("=" * 60)
    lines.append(f"Yesterday's Price: ${result.yesterday_price:.2f}")
    lines.append(f"Trigger Price: ${result.trigger_price:.2f}")
    lines.append(f"Rolling Maximum ({config.rolling_window_days}d): ${result.rolling_maximum:.2f}")
    lines.append(f"Trigger Met: {'✅ YES' if result.trigger_met else '❌ NO'}")
    lines.append(f"Recent Investment Exists: {'✅ YES' if result.recent_investment_exists else '❌ NO'}")
    lines.append("")
    
    if result.investment_executed:
        lines.append("🚀 INVESTMENT EXECUTED!")
        lines.append(f"Amount: ${result.investment.amount:,.2f}")
        lines.append(f"Price: ${result.investment.price:.2f}")
        lines.append(f"Shares: {result.investment.shares:.4f}")
    elif result.trigger_met and result.recent_investment_exists:
        lines.append("⏸️  Investment blocked by 28-day constraint")
    elif not result.trigger_met:
        lines.append("⏸️  Trigger condition not met")
    else:
        lines.append("⏸️  No investment executed")
    
    return "\n".join(lines)


def format_portfolio_status(tracker: InvestmentTracker, current_price: float, config) -> str:
    """Format current portfolio status for display."""
    investments = tracker.get_all_investments()
    
    if not investments:
        return f"\n📊 PORTFOLIO STATUS - {config.ticker}\n" + "=" * 50 + "\nNo investments found."
    
    metrics = tracker.calculate_portfolio_metrics(current_price)
    
    lines = []
    lines.append(f"\n📊 PORTFOLIO STATUS - {config.ticker}")
    lines.append("=" * 50)
    lines.append(f"Current Price: ${current_price:.2f}")
    lines.append(f"Total Invested: ${metrics.total_invested:,.2f}")
    lines.append(f"Total Shares: {metrics.total_shares:.4f}")
    lines.append(f"Current Value: ${metrics.current_value:,.2f}")
    lines.append(f"Total Return: ${metrics.total_return:,.2f}")
    lines.append(f"Percentage Return: {metrics.percentage_return:.2%}")
    lines.append("")
    
    # Recent investments
    recent_investments = sorted(investments, key=lambda x: x.date, reverse=True)[:5]
    lines.append("💰 RECENT INVESTMENTS (Last 5)")
    lines.append("-" * 30)
    for inv in recent_investments:
        lines.append(f"{inv.date}: ${inv.amount:,.2f} at ${inv.price:.2f} = {inv.shares:.4f} shares")
    
    if len(investments) > 5:
        lines.append(f"... and {len(investments) - 5} more investments")
    
    return "\n".join(lines)


def format_multi_ticker_check(results: list, check_date: date) -> str:
    """Format multi-ticker check results as a table."""
    lines = []
    lines.append(f"\n🔍 MULTI-TICKER BUY SIGNAL CHECK ({check_date})")
    lines.append("=" * 80)
    lines.append("")
    
    # Table header
    lines.append(f"{'Ticker':<8} {'Yesterday':<12} {'Trigger':<12} {'Signal':<8} {'% from Trigger':<15}")
    lines.append("-" * 80)
    
    # Table rows
    buy_signals = 0
    for result in results:
        ticker = result['ticker']
        yesterday_price = result['yesterday_price']
        trigger_price = result['trigger_price']
        signal = "✅ BUY" if result['trigger_met'] else "❌ NO"
        
        # Calculate percentage from trigger
        pct_from_trigger = ((yesterday_price - trigger_price) / trigger_price) * 100
        pct_str = f"{pct_from_trigger:+.1f}%"
        
        lines.append(f"{ticker:<8} ${yesterday_price:<11.2f} ${trigger_price:<11.2f} {signal:<8} {pct_str:<15}")
        
        if result['trigger_met']:
            buy_signals += 1
    
    lines.append("")
    lines.append(f"Summary: {'✅' if buy_signals > 0 else '❌'} {buy_signals} of {len(results)} tickers have buy signals")
    lines.append("")
    lines.append("Note: This check ignores the 28-day constraint.")
    lines.append("      Use --evaluate with --config to see if an investment would actually execute.")
    
    return "\n".join(lines)


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
        "--tickers",
        type=str,
        nargs="+",
        help="List of ticker symbols to check (e.g., QQQ SPY AAPL). Use with --check and strategy parameters."
    )
    
    parser.add_argument(
        "--rolling-window",
        type=int,
        help="Number of days for rolling maximum calculation (required with --tickers)"
    )
    
    parser.add_argument(
        "--trigger-pct",
        type=float,
        help="Percentage trigger (e.g., 0.95 for 95%%) (required with --tickers)"
    )
    
    parser.add_argument(
        "--amount",
        type=float,
        help="Investment amount in dollars (optional, not used with --check)"
    )
    
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest for historical evaluation"
    )
    
    parser.add_argument(
        "--evaluate",
        type=str,
        help="Evaluate a specific date (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current portfolio status and metrics"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if today is a buying day according to the strategy (ignores 28-day constraint)"
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
    
    # Date range options for backtest
    parser.add_argument(
        "--start-date",
        type=str,
        help="Backtest start date (YYYY-MM-DD format, e.g., 2023-01-01)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        help="Backtest end date (YYYY-MM-DD format, e.g., 2024-12-31)"
    )
    
    parser.add_argument(
        "--period",
        type=str,
        help="Backtest period from end date (e.g., '1y', '6m', '90d', '2y')"
    )
    
    # Cache management options
    parser.add_argument(
        "--clear-cache",
        type=str,
        nargs="?",
        const="all",
        help="Clear price data cache (specify ticker or 'all' for everything)"
    )
    
    parser.add_argument(
        "--cache-info",
        type=str,
        help="Show cache information for a specific ticker"
    )
    
    parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Ignore cached data and fetch fresh data from API"
    )
    
    parser.add_argument(
        "--validate-cache",
        type=str,
        help="Validate cached data against live API data for a ticker"
    )
    
    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Handle multi-ticker mode
        if args.tickers:
            # Validate required parameters for multi-ticker mode
            if not args.check:
                logger.error("--tickers can only be used with --check")
                sys.exit(1)
            
            if not args.rolling_window or not args.trigger_pct:
                logger.error("--tickers requires --rolling-window and --trigger-pct")
                sys.exit(1)
            
            # Validate parameter ranges
            if args.rolling_window < 1 or args.rolling_window > 365:
                logger.error("--rolling-window must be between 1 and 365")
                sys.exit(1)
            
            if args.trigger_pct <= 0.0 or args.trigger_pct > 1.0:
                logger.error("--trigger-pct must be between 0.0 and 1.0")
                sys.exit(1)
            
            # Create shared price monitor for cache efficiency
            price_monitor = PriceMonitor()
            
            # Process each ticker
            results = []
            today = date.today()
            
            for ticker in args.tickers:
                ticker = ticker.upper()
                
                try:
                    # Create config for this ticker
                    from ..config.models import StrategyConfig
                    config = StrategyConfig(
                        ticker=ticker,
                        rolling_window_days=args.rolling_window,
                        percentage_trigger=args.trigger_pct,
                        monthly_dca_amount=1000.0  # Dummy value, not used for checking
                    )
                    
                    # Create strategy system
                    strategy_system = StrategySystem(config, price_monitor)
                    
                    # Get price data for rolling window
                    start_date = today - timedelta(days=config.rolling_window_days + 30)
                    prices = price_monitor.get_closing_prices(ticker, start_date, today)
                    
                    if prices.empty:
                        logger.warning(f"No price data available for {ticker}")
                        continue
                    
                    # Get yesterday's price
                    yesterday = today - timedelta(days=1)
                    available_dates = [d for d in prices.index if d <= yesterday]
                    
                    if not available_dates:
                        logger.warning(f"No price data available before {today} for {ticker}")
                        continue
                    
                    yesterday_actual = max(available_dates)
                    yesterday_price = float(prices[yesterday_actual])
                    
                    # Calculate trigger price
                    historical_prices = prices[prices.index <= yesterday_actual]
                    trigger_price = strategy_system.calculate_trigger_price(
                        historical_prices,
                        config.rolling_window_days,
                        config.percentage_trigger
                    )
                    
                    rolling_max = price_monitor.calculate_rolling_maximum(
                        historical_prices,
                        config.rolling_window_days
                    )
                    
                    # Check if trigger is met
                    trigger_met = yesterday_price <= trigger_price
                    
                    results.append({
                        'ticker': ticker,
                        'yesterday_price': yesterday_price,
                        'trigger_price': trigger_price,
                        'rolling_max': rolling_max,
                        'trigger_met': trigger_met
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to check {ticker}: {e}")
                    continue
            
            if not results:
                logger.error("No tickers could be checked successfully")
                sys.exit(1)
            
            # Log API stats before displaying results
            api_stats = price_monitor.get_api_stats()
            logger.info(f"Session total - API calls: {api_stats['api_calls_made']}, Cache hits: {api_stats['cache_hits']}")
            
            # Display results
            formatted_result = format_multi_ticker_check(results, today)
            print(formatted_result)
            
            return
        
        # Validate config file exists if specified
        if args.config:
            config_path = Path(args.config)
            if not config_path.exists():
                logger.error(f"Configuration file not found: {args.config}")
                sys.exit(1)
        
        # Load configuration
        config_manager = ConfigurationManager()
        config = config_manager.load_config(args.config)
        
        logger.info(f"Loaded configuration for ticker: {config.ticker}")
        logger.info(f"Rolling window: {config.rolling_window_days} days")
        logger.info(f"Trigger percentage: {config.percentage_trigger:.1%}")
        logger.info(f"Monthly DCA amount: ${config.monthly_dca_amount:.2f}")
        
        if args.validate_config:
            logger.info("Configuration validation successful")
            return
        
        # Initialize strategy system
        price_monitor = PriceMonitor()
        
        # Handle cache management commands first
        if args.clear_cache:
            if args.clear_cache.lower() == "all":
                price_monitor.clear_cache()
                logger.info("Cleared all price data cache")
            else:
                price_monitor.clear_cache(args.clear_cache.upper())
                logger.info(f"Cleared cache for {args.clear_cache.upper()}")
            return
        
        if args.cache_info:
            cache_info = price_monitor.get_cache_info(args.cache_info.upper())
            print(f"\n📁 CACHE INFO - {cache_info['ticker']}")
            print("=" * 40)
            if cache_info['cached']:
                print(f"Status: ✅ Cached")
                print(f"Records: {cache_info['records']}")
                print(f"Date Range: {cache_info['date_range']['start']} to {cache_info['date_range']['end']}")
            else:
                print(f"Status: ❌ No cached data")
            return
        
        if args.validate_cache:
            # This will be handled by the new cache validation functionality
            ticker = args.validate_cache.upper()
            logger.info(f"Validating cached data for {ticker} against live API data...")
            
            try:
                # Run cache validation
                validation_result = validate_cached_data(price_monitor, ticker)
                print(f"\n🔍 CACHE VALIDATION - {ticker}")
                print("=" * 50)
                print(f"Validation Status: {'✅ PASSED' if validation_result['valid'] else '❌ FAILED'}")
                print(f"Records Checked: {validation_result['records_checked']}")
                print(f"Mismatches Found: {validation_result['mismatches']}")
                
                # Show sampling information
                if 'sampling_info' in validation_result:
                    info = validation_result['sampling_info']
                    print(f"\n📊 VALIDATION STRATEGY: {info['validation_strategy'].replace('_', ' ').title()}")
                    print(f"Total Cached Records: {info['total_cached_records']}")
                    print(f"Cache Date Range: {info['cache_date_range_days']} days")
                    
                    if info['validation_strategy'] == 'full_cache':
                        print(f"Validated All Records: {info['total_records_checked']}")
                    else:
                        print(f"Recent Records Checked: {info['recent_records_checked']} ({info['recent_percentage']}% of total)")
                        if info['random_records_checked'] > 0:
                            print(f"Random Sample Checked: {info['random_records_checked']} ({info['random_percentage']}% of remaining)")
                        print(f"Total Validation Coverage: {info['total_records_checked']} records")
                
                if validation_result['mismatches'] > 0:
                    print("\n⚠️  Cache data does not match API data!")
                    print("Consider clearing the cache with --clear-cache")
                    
                    if validation_result.get('sample_mismatches'):
                        print("\nSample Mismatches:")
                        for mismatch in validation_result['sample_mismatches'][:3]:
                            print(f"  {mismatch['date']}: Cached=${mismatch['cached']:.2f}, API=${mismatch['api']:.2f}")
                else:
                    print("\n✅ Cache data matches API data perfectly!")
                    
            except Exception as e:
                logger.error(f"Cache validation failed: {e}")
                sys.exit(1)
            return
        
        investment_tracker = InvestmentTracker()
        strategy_system = StrategySystem(config, price_monitor, investment_tracker)
        
        # Set ignore cache flag if specified
        if args.ignore_cache:
            logger.info("Ignoring cached data - will fetch fresh data from API")
            # Clear cache temporarily for this run
            price_monitor.clear_cache(config.ticker)
        
        if args.backtest:
            # Run backtest
            try:
                start_date, end_date = resolve_date_range(args)
                
                logger.info(f"Running backtest from {start_date} to {end_date}")
                result = strategy_system.run_backtest(start_date, end_date)
                
                # Log final API stats before displaying results
                api_stats = price_monitor.get_api_stats()
                logging.getLogger(__name__).info(f"Session total - API calls: {api_stats['api_calls_made']}, Cache hits: {api_stats['cache_hits']}")
                
                formatted_result = format_backtest_result(result, config, price_monitor)
                print(formatted_result)
                
            except argparse.ArgumentTypeError as e:
                logger.error(f"Date range error: {e}")
                sys.exit(1)
                
        elif args.evaluate:
            # Evaluate specific date
            try:
                eval_date = parse_date(args.evaluate)
                result = strategy_system.evaluate_trading_day(eval_date)
                
                formatted_result = format_evaluation_result(result, config)
                print(formatted_result)
                
            except argparse.ArgumentTypeError as e:
                logger.error(f"Date format error: {e}")
                sys.exit(1)
            except ValueError as e:
                logger.error(f"Evaluation error: {e}")
                sys.exit(1)
                
        elif args.status:
            # Show portfolio status
            try:
                current_price = price_monitor.get_current_price(config.ticker)
                formatted_status = format_portfolio_status(investment_tracker, current_price, config)
                print(formatted_status)
                
            except Exception as e:
                logger.error(f"Failed to get portfolio status: {e}")
                sys.exit(1)
        
        elif args.check:
            # Check if today is a buying day
            try:
                today = date.today()
                
                # Get price data for rolling window
                start_date = today - timedelta(days=config.rolling_window_days + 30)
                prices = price_monitor.get_closing_prices(config.ticker, start_date, today)
                
                if prices.empty:
                    logger.error(f"No price data available for {config.ticker}")
                    sys.exit(1)
                
                # Get yesterday's price
                yesterday = today - timedelta(days=1)
                available_dates = [d for d in prices.index if d <= yesterday]
                
                if not available_dates:
                    logger.error(f"No price data available before {today}")
                    sys.exit(1)
                
                yesterday_actual = max(available_dates)
                yesterday_price = float(prices[yesterday_actual])
                
                # Calculate trigger price
                historical_prices = prices[prices.index <= yesterday_actual]
                trigger_price = strategy_system.calculate_trigger_price(
                    historical_prices,
                    config.rolling_window_days,
                    config.percentage_trigger
                )
                
                rolling_max = price_monitor.calculate_rolling_maximum(
                    historical_prices,
                    config.rolling_window_days
                )
                
                # Check if trigger is met
                trigger_met = yesterday_price <= trigger_price
                
                # Display result
                print(f"\n🔍 BUY SIGNAL CHECK - {config.ticker} ({today})")
                print("=" * 50)
                print(f"Yesterday's Price: ${yesterday_price:.2f}")
                print(f"Trigger Price: ${trigger_price:.2f}")
                print(f"Rolling Maximum ({config.rolling_window_days}d): ${rolling_max:.2f}")
                print(f"Trigger Percentage: {config.percentage_trigger:.1%}")
                print("")
                
                if trigger_met:
                    print("✅ BUY SIGNAL: Trigger condition is met!")
                    print(f"   Yesterday's price (${yesterday_price:.2f}) is at or below")
                    print(f"   the trigger price (${trigger_price:.2f})")
                else:
                    print("❌ NO BUY SIGNAL: Trigger condition not met")
                    print(f"   Yesterday's price (${yesterday_price:.2f}) is above")
                    print(f"   the trigger price (${trigger_price:.2f})")
                    pct_from_trigger = ((yesterday_price - trigger_price) / trigger_price) * 100
                    print(f"   Price is {pct_from_trigger:.1f}% above trigger")
                
                print("")
                print("Note: This check ignores the 28-day constraint.")
                print("      Use --evaluate to see if an investment would actually execute.")
                
            except Exception as e:
                logger.error(f"Failed to check buy signal: {e}")
                sys.exit(1)
                
        else:
            # Default: show help
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()