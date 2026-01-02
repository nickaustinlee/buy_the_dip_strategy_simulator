"""
Unit tests for CAGR analysis functionality.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch
import pandas as pd

from buy_the_dip.analysis.cagr_analysis import CAGRAnalysisEngine
from buy_the_dip.models import Transaction, CAGRAnalysis


class TestCAGRAnalysisEngine(unittest.TestCase):
    """Test cases for CAGR analysis engine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_price_monitor = Mock()
        self.cagr_engine = CAGRAnalysisEngine(self.mock_price_monitor)
        
        # Sample price data
        self.sample_price_data = pd.DataFrame({
            'Close': [100.0, 105.0, 110.0, 115.0, 120.0]
        }, index=pd.date_range('2023-01-01', periods=5, freq='D'))
    
    def test_calculate_cagr_basic(self):
        """Test basic CAGR calculation."""
        # 10% growth over 1 year
        cagr = self.cagr_engine._calculate_cagr(1000, 1100, 365)
        self.assertAlmostEqual(cagr, 0.10, places=3)
        
        # 20% growth over 2 years
        cagr = self.cagr_engine._calculate_cagr(1000, 1440, 730)
        self.assertAlmostEqual(cagr, 0.20, places=3)
    
    def test_calculate_cagr_known_values(self):
        """Test CAGR calculation with known precise values."""
        # Test case 1: $4000 invested, worth $4384.08 after 61 days
        # Expected CAGR = (4384.08/4000)^(365.25/61) - 1 ≈ 0.7315 (73.15%)
        start_value = 4000.0
        end_value = 4384.08
        days = 61
        expected_cagr = (end_value / start_value) ** (365.25 / days) - 1
        
        actual_cagr = self.cagr_engine._calculate_cagr(start_value, end_value, days)
        self.assertAlmostEqual(actual_cagr, expected_cagr, places=4)
        self.assertAlmostEqual(actual_cagr, 0.731495, places=4)  # ~73.15%
        
        # Test case 2: $1000 to $1200 over 90 days
        # Expected CAGR = (1200/1000)^(365.25/90) - 1 ≈ 1.0958 (109.58%)
        start_value = 1000.0
        end_value = 1200.0
        days = 90
        expected_cagr = (end_value / start_value) ** (365.25 / days) - 1
        
        actual_cagr = self.cagr_engine._calculate_cagr(start_value, end_value, days)
        self.assertAlmostEqual(actual_cagr, expected_cagr, places=4)
        self.assertAlmostEqual(actual_cagr, 1.095771, places=4)  # ~109.58%
        
        # Test case 3: $5000 to $4800 over 180 days (loss)
        # Expected CAGR = (4800/5000)^(365.25/180) - 1 ≈ -0.0795 (-7.95%)
        start_value = 5000.0
        end_value = 4800.0
        days = 180
        expected_cagr = (end_value / start_value) ** (365.25 / days) - 1
        
        actual_cagr = self.cagr_engine._calculate_cagr(start_value, end_value, days)
        self.assertAlmostEqual(actual_cagr, expected_cagr, places=4)
        self.assertAlmostEqual(actual_cagr, -0.079497, places=4)  # ~-7.95%
    
    def test_calculate_cagr_edge_cases(self):
        """Test CAGR calculation edge cases."""
        # Zero start value
        cagr = self.cagr_engine._calculate_cagr(0, 1000, 365)
        self.assertEqual(cagr, 0.0)
        
        # Zero days
        cagr = self.cagr_engine._calculate_cagr(1000, 1100, 0)
        self.assertEqual(cagr, 0.0)
        
        # Total loss
        cagr = self.cagr_engine._calculate_cagr(1000, 0, 365)
        self.assertEqual(cagr, -1.0)
    
    def test_calculate_strategy_portfolio_value(self):
        """Test strategy portfolio value calculation."""
        transactions = [
            Transaction(
                session_id="test1",
                date=date(2023, 1, 1),
                price=100.0,
                shares=10.0,
                amount=1000.0
            ),
            Transaction(
                session_id="test1",
                date=date(2023, 2, 1),
                price=105.0,
                shares=9.52,
                amount=1000.0
            )
        ]
        
        current_price = 110.0
        portfolio_value = self.cagr_engine._calculate_strategy_portfolio_value(
            transactions, current_price
        )
        
        expected_value = (10.0 + 9.52) * 110.0
        self.assertAlmostEqual(portfolio_value, expected_value, places=2)
    
    def test_get_price_on_date(self):
        """Test getting price on specific date."""
        # Test exact match
        target_date = date(2023, 1, 2)
        price = self.cagr_engine._get_price_on_date(self.sample_price_data, target_date)
        self.assertEqual(price, 105.0)
        
        # Test fallback to first available
        target_date = date(2022, 12, 1)  # Before data range
        price = self.cagr_engine._get_price_on_date(self.sample_price_data, target_date)
        self.assertEqual(price, 100.0)  # First available price
    
    @patch('buy_the_dip.analysis.cagr_analysis.CAGRAnalysisEngine._get_price_on_date')
    def test_analyze_performance_no_transactions(self, mock_get_price):
        """Test performance analysis with no transactions."""
        # Mock price monitor
        self.mock_price_monitor.get_current_price.return_value = 120.0
        self.mock_price_monitor.fetch_price_data.return_value = self.sample_price_data
        mock_get_price.return_value = 100.0
        
        transactions = []
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        analysis = self.cagr_engine.analyze_performance(
            transactions, "SPY", start_date, end_date, 120.0
        )
        
        # Verify analysis structure
        self.assertIsInstance(analysis, CAGRAnalysis)
        self.assertEqual(analysis.ticker, "SPY")
        self.assertEqual(analysis.strategy_full_period_cagr, 0.0)
        self.assertIsNone(analysis.first_investment_date)
        self.assertIsNone(analysis.active_period_days)
    
    @patch('buy_the_dip.analysis.cagr_analysis.CAGRAnalysisEngine._get_price_on_date')
    def test_analyze_performance_with_transactions(self, mock_get_price):
        """Test performance analysis with transactions."""
        # Mock price monitor
        self.mock_price_monitor.get_current_price.return_value = 120.0
        self.mock_price_monitor.fetch_price_data.return_value = self.sample_price_data
        mock_get_price.return_value = 105.0  # Price on first investment date
        
        transactions = [
            Transaction(
                session_id="test1",
                date=date(2023, 6, 1),
                price=105.0,
                shares=9.52,
                amount=1000.0
            )
        ]
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        analysis = self.cagr_engine.analyze_performance(
            transactions, "SPY", start_date, end_date, 120.0
        )
        
        # Verify analysis has investment data
        self.assertEqual(analysis.first_investment_date, date(2023, 6, 1))
        self.assertIsNotNone(analysis.active_period_days)
        self.assertIsNotNone(analysis.strategy_active_period_cagr)
    
    @patch('buy_the_dip.analysis.cagr_analysis.CAGRAnalysisEngine._get_price_on_date')
    def test_analyze_performance_known_scenario(self, mock_get_price):
        """Test performance analysis with known scenario matching real output."""
        # This test replicates the 2025-03-01 to 2025-05-01 scenario
        # $4000 invested, portfolio worth $4384.08, should show positive CAGR
        
        # Mock price data: start at $500, end at $553.88 (10.78% price increase)
        price_data = pd.DataFrame({
            'Close': [500.0, 553.88]
        }, index=pd.date_range('2025-03-01', periods=2, freq='61D'))
        
        self.mock_price_monitor.get_current_price.return_value = 553.88
        self.mock_price_monitor.fetch_price_data.return_value = price_data
        mock_get_price.return_value = 505.18  # Average investment price
        
        # Two transactions totaling $4000, resulting in 7.9185 shares
        transactions = [
            Transaction(
                session_id="session1",
                date=date(2025, 4, 4),
                price=500.92,
                shares=3.9927,
                amount=2000.0
            ),
            Transaction(
                session_id="session2", 
                date=date(2025, 4, 21),
                price=509.44,
                shares=3.9259,
                amount=2000.0
            )
        ]
        
        start_date = date(2025, 3, 1)
        end_date = date(2025, 5, 1)
        
        analysis = self.cagr_engine.analyze_performance(
            transactions, "SPY", start_date, end_date, 553.88
        )
        
        # Verify the strategy shows positive CAGR (not 0%)
        self.assertGreater(analysis.strategy_full_period_cagr, 0.0)
        
        # Calculate expected values
        total_invested = 4000.0
        portfolio_value = 7.9185 * 553.88  # Should be ~4384.08
        expected_return_pct = (portfolio_value - total_invested) / total_invested
        
        # Verify portfolio value calculation
        self.assertAlmostEqual(portfolio_value, 4385.90, places=1)
        
        # Verify return percentage is ~9.6%
        self.assertAlmostEqual(expected_return_pct, 0.096, places=3)
        
        # For 61-day period, CAGR should be much higher due to annualization
        # (4384.08/4000)^(365.25/61) - 1 ≈ 0.73 (73%)
        expected_cagr = (portfolio_value / total_invested) ** (365.25 / 61) - 1
        self.assertAlmostEqual(analysis.strategy_full_period_cagr, expected_cagr, places=3)
        
        # Verify it's not zero
        self.assertNotEqual(analysis.strategy_full_period_cagr, 0.0)
    
    def test_format_cagr_report(self):
        """Test CAGR report formatting."""
        analysis = CAGRAnalysis(
            ticker="SPY",
            analysis_start_date=date(2023, 1, 1),
            analysis_end_date=date(2023, 12, 31),
            first_investment_date=date(2023, 6, 1),
            full_period_days=365,
            strategy_full_period_cagr=0.08,
            buyhold_full_period_cagr=0.12,
            active_period_days=214,
            strategy_active_period_cagr=0.15,
            buyhold_active_period_cagr=0.10,
            full_period_outperformance=-0.04,
            active_period_outperformance=0.05,
            opportunity_cost=None,  # Removed
            strategy_start_value=1000.0,
            strategy_end_value=1080.0,
            buyhold_start_value=1000.0,
            buyhold_end_value=1120.0
        )
        
        report = self.cagr_engine.format_cagr_report(analysis)
        
        # Verify report contains key information
        self.assertIn("SPY", report)
        self.assertIn("8.00%", report)  # Strategy CAGR
        self.assertIn("12.00%", report)  # Buy-hold CAGR
        self.assertIn("-4.00%", report)  # Outperformance
    
    def test_strategy_cagr_never_zero_with_investments(self):
        """Test that strategy CAGR is never 0% when there are actual investments."""
        # This test prevents regression of the bug where strategy CAGR showed 0%
        # when it should show positive returns
        
        # Mock price monitor with realistic data
        price_data = pd.DataFrame({
            'Close': [100.0, 110.0]  # 10% price increase
        }, index=pd.date_range('2023-01-01', periods=2, freq='30D'))
        
        self.mock_price_monitor.get_current_price.return_value = 110.0
        self.mock_price_monitor.fetch_price_data.return_value = price_data
        
        # Create transactions that should result in positive returns
        transactions = [
            Transaction(
                session_id="test1",
                date=date(2023, 1, 15),
                price=105.0,
                shares=9.52,
                amount=1000.0
            )
        ]
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)
        
        with patch.object(self.cagr_engine, '_get_price_on_date', return_value=105.0):
            analysis = self.cagr_engine.analyze_performance(
                transactions, "SPY", start_date, end_date, 110.0
            )
        
        # The key assertion: strategy CAGR should NEVER be 0% when there are investments
        # and the portfolio has positive value
        self.assertNotEqual(analysis.strategy_full_period_cagr, 0.0)
        self.assertGreater(analysis.strategy_full_period_cagr, 0.0)
        
        # Verify the calculation makes sense
        total_invested = 1000.0
        portfolio_value = 9.52 * 110.0  # Should be 1047.2
        expected_return = (portfolio_value - total_invested) / total_invested
        self.assertGreater(expected_return, 0.0)  # Should be ~4.72%
        
        # For a 30-day period, CAGR should be much higher due to annualization
        expected_cagr = (portfolio_value / total_invested) ** (365.25 / 30) - 1
        self.assertAlmostEqual(analysis.strategy_full_period_cagr, expected_cagr, places=4)
        """Test CAGR report formatting when no investments were made."""
        analysis = CAGRAnalysis(
            ticker="SPY",
            analysis_start_date=date(2023, 1, 1),
            analysis_end_date=date(2023, 12, 31),
            first_investment_date=None,  # No investments
            full_period_days=365,
            strategy_full_period_cagr=0.0,  # 0% due to no investments
            buyhold_full_period_cagr=0.12,
            active_period_days=None,
            strategy_active_period_cagr=None,
            buyhold_active_period_cagr=None,
            full_period_outperformance=-0.12,
            active_period_outperformance=None,
            opportunity_cost=None,
            strategy_start_value=0.0,
            strategy_end_value=0.0,
            buyhold_start_value=1000.0,
            buyhold_end_value=1120.0
        )
        
        report = self.cagr_engine.format_cagr_report(analysis)
        
        # Verify report contains clarification for no investments
        self.assertIn("SPY", report)
        self.assertIn("0.00% (no positions opened during period)", report)
        self.assertIn("No investments made during period", report)
        self.assertIn("12.00%", report)  # Buy-hold CAGR


if __name__ == '__main__':
    unittest.main()