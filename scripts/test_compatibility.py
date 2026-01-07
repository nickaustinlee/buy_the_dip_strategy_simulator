#!/usr/bin/env python3
"""
Quick compatibility test script that can be run in any Python environment.
Tests basic imports and functionality without requiring full test suite.
"""

import sys
import traceback
from pathlib import Path


def test_basic_imports():
    """Test that all main modules can be imported."""
    print("🔍 Testing basic imports...")

    try:
        # Test core dependencies
        import pandas
        import pydantic
        import yaml
        import yfinance

        print(f"✅ Core dependencies imported successfully")

        # Test our modules
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from buy_the_dip.config.models import StrategyConfig
        from buy_the_dip.price_monitor.price_monitor import PriceMonitor
        from buy_the_dip.investment_tracker import InvestmentTracker
        from buy_the_dip.strategy_system import StrategySystem
        from buy_the_dip.cli.cli import main

        print(f"✅ All buy_the_dip modules imported successfully")
        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_basic_functionality():
    """Test basic functionality without external API calls."""
    print("🔍 Testing basic functionality...")

    try:
        from buy_the_dip.config.models import StrategyConfig
        from buy_the_dip.investment_tracker import InvestmentTracker
        from buy_the_dip.models import Investment
        from datetime import date

        # Test config creation
        config = StrategyConfig(
            ticker="SPY", rolling_window_days=90, percentage_trigger=0.90, monthly_dca_amount=1000.0
        )
        print(f"✅ StrategyConfig created: {config.ticker}")

        # Test investment tracker
        tracker = InvestmentTracker()
        investment = Investment(
            date=date.today(), ticker="SPY", price=400.0, amount=1000.0, shares=2.5
        )
        tracker.add_investment(investment)

        metrics = tracker.calculate_portfolio_metrics(420.0)
        print(f"✅ Portfolio calculation works: ${metrics.current_value:.2f}")

        return True

    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run compatibility tests."""
    print(f"🐍 Python {sys.version}")
    print("=" * 50)

    tests = [
        test_basic_imports,
        test_basic_functionality,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print("📊 RESULTS")
    print("=" * 20)
    if passed == len(tests):
        print(f"🎉 All {len(tests)} tests passed!")
        print("✅ This Python version is compatible")
        return 0
    else:
        print(f"❌ {len(tests) - passed} of {len(tests)} tests failed")
        print("⚠️  This Python version may have compatibility issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
