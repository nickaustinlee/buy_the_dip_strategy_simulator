"""
Investment tracking and persistence for the buy-the-dip strategy.
"""

import json
import logging
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .models import Investment, PortfolioMetrics

logger = logging.getLogger(__name__)


class InvestmentTracker:
    """Manages investment history and enforces 28-day constraint."""
    
    DEFAULT_FILENAME = "investments.json"
    BACKUP_SUFFIX = ".backup"
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize investment tracker with specified directory.
        
        Args:
            data_dir: Directory for investment files. If None, uses default location.
        """
        if data_dir is None:
            data_dir = Path.home() / ".buy_the_dip" / "data"
        
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._investments: List[Investment] = []
        
        logger.debug(f"InvestmentTracker initialized with directory: {self._data_dir}")
    
    def add_investment(self, investment: Investment) -> None:
        """
        Add a new investment to the tracker.
        
        Args:
            investment: The investment to add
        """
        # Validate shares calculation
        expected_shares = investment.amount / investment.price
        if abs(investment.shares - expected_shares) > 0.0001:  # Allow small floating point errors
            logger.warning(f"Investment shares calculation mismatch: expected {expected_shares:.6f}, got {investment.shares:.6f}")
        
        self._investments.append(investment)
        logger.info(f"Added investment: {investment.date} - ${investment.amount:.2f} at ${investment.price:.2f}")
    
    def has_recent_investment(self, check_date: date, days: int = 28) -> bool:
        """
        Check if any investment was made within the specified number of days.
        
        Args:
            check_date: Date to check from
            days: Number of calendar days to look back (default: 28)
            
        Returns:
            True if any investment exists within the time window (exclusive of the Nth day)
        """
        cutoff_date = check_date - timedelta(days=days)
        
        for investment in self._investments:
            if investment.date > cutoff_date and investment.date < check_date:
                logger.debug(f"Found recent investment on {investment.date} within {days} days of {check_date}")
                return True
        
        return False
    
    def get_all_investments(self) -> List[Investment]:
        """
        Get all investments.
        
        Returns:
            List of all investments
        """
        return self._investments.copy()
    
    def calculate_portfolio_metrics(self, current_price: float) -> PortfolioMetrics:
        """
        Calculate portfolio performance metrics.
        
        Args:
            current_price: Current price per share
            
        Returns:
            Portfolio metrics
        """
        if not self._investments:
            return PortfolioMetrics(
                total_invested=0.0,
                total_shares=0.0,
                current_value=0.0,
                total_return=0.0,
                percentage_return=0.0
            )
        
        total_invested = sum(inv.amount for inv in self._investments)
        total_shares = sum(inv.shares for inv in self._investments)
        current_value = total_shares * current_price
        total_return = current_value - total_invested
        percentage_return = (total_return / total_invested) if total_invested > 0 else 0.0
        
        return PortfolioMetrics(
            total_invested=total_invested,
            total_shares=total_shares,
            current_value=current_value,
            total_return=total_return,
            percentage_return=percentage_return
        )
    
    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        """
        Save investments to file.
        
        Args:
            filepath: Optional custom filepath. If None, uses default location.
            
        Returns:
            True if save was successful, False otherwise
        """
        if filepath is None:
            filepath = self._data_dir / self.DEFAULT_FILENAME
        else:
            filepath = Path(filepath)
        
        backup_filepath = filepath.with_suffix(filepath.suffix + self.BACKUP_SUFFIX)
        
        try:
            # Create backup of existing file if it exists
            if filepath.exists():
                shutil.copy2(filepath, backup_filepath)
                logger.debug(f"Created backup of existing investment file")
            
            # Convert investments to JSON-serializable format
            investments_data = []
            for investment in self._investments:
                inv_dict = investment.model_dump(mode='json')
                investments_data.append(inv_dict)
            
            # Write to temporary file first (atomic write)
            temp_filepath = filepath.with_suffix('.tmp')
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'investments': investments_data,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2, default=str)
            
            # Atomically replace the main file
            temp_filepath.replace(filepath)
            
            logger.info(f"Successfully saved {len(self._investments)} investments to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save investments to {filepath}: {e}")
            return False
    
    def load_from_file(self, filepath: Optional[str] = None) -> bool:
        """
        Load investments from file.
        
        Args:
            filepath: Optional custom filepath. If None, uses default location.
            
        Returns:
            True if load was successful, False otherwise
        """
        if filepath is None:
            filepath = self._data_dir / self.DEFAULT_FILENAME
        else:
            filepath = Path(filepath)
        
        backup_filepath = filepath.with_suffix(filepath.suffix + self.BACKUP_SUFFIX)
        
        # Try to load from main file first
        success = self._load_from_specific_file(filepath)
        
        if not success and backup_filepath.exists():
            logger.warning("Main investment file corrupted or missing, attempting to load from backup")
            success = self._load_from_specific_file(backup_filepath)
            
            if success:
                logger.info("Successfully recovered investments from backup file")
                # Save the recovered data as the new main file
                self.save_to_file(filepath)
        
        if not success:
            logger.info("No valid investment file found, starting with empty history")
            self._investments = []
        
        return success
    
    def _load_from_specific_file(self, filepath: Path) -> bool:
        """
        Load investments from a specific file.
        
        Args:
            filepath: Path to the investment file
            
        Returns:
            True if loading was successful, False otherwise
        """
        if not filepath.exists():
            logger.debug(f"Investment file does not exist: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract investments data
            investments_data = data.get('investments', [])
            
            # Convert to Investment objects
            investments = []
            for inv_dict in investments_data:
                investment = Investment.model_validate(inv_dict)
                investments.append(investment)
            
            self._investments = investments
            logger.info(f"Successfully loaded {len(investments)} investments from {filepath}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in investment file {filepath}: {e}")
            self._handle_corrupted_file(filepath)
            return False
            
        except Exception as e:
            logger.error(f"Failed to load investments from {filepath}: {e}")
            self._handle_corrupted_file(filepath)
            return False
    
    def _handle_corrupted_file(self, filepath: Path) -> None:
        """
        Handle a corrupted investment file by creating a backup.
        
        Args:
            filepath: Path to the corrupted file
        """
        try:
            corrupted_backup = filepath.with_suffix(f'.corrupted.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.move(filepath, corrupted_backup)
            logger.warning(f"Moved corrupted investment file to {corrupted_backup}")
        except Exception as e:
            logger.error(f"Failed to backup corrupted file {filepath}: {e}")
    
    def get_investments_in_period(self, start_date: date, end_date: date) -> List[Investment]:
        """
        Get investments within a specific date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of investments within the date range
        """
        return [
            inv for inv in self._investments
            if start_date <= inv.date <= end_date
        ]
    
    def get_total_invested_in_period(self, start_date: date, end_date: date) -> float:
        """
        Get total amount invested within a specific date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Total amount invested in the period
        """
        investments = self.get_investments_in_period(start_date, end_date)
        return sum(inv.amount for inv in investments)
    
    def clear_all_investments(self) -> None:
        """Clear all investments from memory (does not affect saved files)."""
        self._investments.clear()
        logger.info("Cleared all investments from memory")