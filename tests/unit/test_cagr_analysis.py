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
        self.assertIsNotNone(analysis.opportunity_cost)
    
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
            opportunity_cost=-0.04,
            strategy_start_value=0.0,
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
        self.assertIn("Opportunity Cost", report)


if __name__ == '__main__':
    unittest.main()