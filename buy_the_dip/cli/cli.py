"""
Command-line interface implementation.
"""

import argparse
import logging
import sys
from pathlib import Path

from ..config import ConfigurationManager
from ..strategy_engine import StrategyEngine


def setup_logging(level: str = "INFO") -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


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
            report = engine.generate_report(include_cagr=True)
            
            # Use the comprehensive formatted report
            formatted_report = engine.format_comprehensive_report(report)
            print(formatted_report)
        else:
            # Run the strategy
            engine.run_strategy()
            
    except Exception as e:
        logger.error(f"Strategy execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()