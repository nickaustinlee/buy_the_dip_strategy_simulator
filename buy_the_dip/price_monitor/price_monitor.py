"""
Price monitoring implementation for fetching and analyzing stock data.
"""

import pandas as pd
import logging
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from typing import Dict, Optional

from .models import PriceData


logger = logging.getLogger(__name__)


class PriceMonitor:
    """Monitors stock prices and calculates rolling statistics with persistent caching."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the price monitor with optional cache directory."""
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._yf = None
        
        # Set up persistent cache directory
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".buy_the_dip", "price_cache")
        
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Price cache directory: {self._cache_dir}")
    
    def _is_likely_non_trading_day(self, check_date: date) -> bool:
        """
        Check if a date is likely a non-trading day (weekend or common holiday).
        
        Args:
            check_date: Date to check
            
        Returns:
            True if likely a non-trading day
        """
        # Check if it's a weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return True
        
        # Check for common US holidays (simplified list)
        year = check_date.year
        
        # New Year's Day
        if check_date.month == 1 and check_date.day == 1:
            return True
        
        # Independence Day
        if check_date.month == 7 and check_date.day == 4:
            return True
        
        # Christmas Day
        if check_date.month == 12 and check_date.day == 25:
            return True
        
        # Thanksgiving (4th Thursday in November) - simplified check
        if check_date.month == 11 and check_date.weekday() == 3 and 22 <= check_date.day <= 28:
            return True
        
        return False
    
    def _log_no_data_reason(self, ticker: str, start_date: date, end_date: date) -> None:
        """
        Log an appropriate message when no data is available for a date range.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date of the range
            end_date: End date of the range
        """
        # Check if the entire range consists of non-trading days
        current_date = start_date
        all_non_trading = True
        
        while current_date <= end_date:
            if not self._is_likely_non_trading_day(current_date):
                all_non_trading = False
                break
            current_date += timedelta(days=1)
        
        if all_non_trading:
            if start_date == end_date:
                day_name = start_date.strftime("%A")
                if start_date.weekday() >= 5:
                    logger.debug(f"No data for {ticker} on {start_date} ({day_name}) - markets closed on weekends")
                else:
                    logger.debug(f"No data for {ticker} on {start_date} ({day_name}) - likely a market holiday")
            else:
                logger.debug(f"No data for {ticker} from {start_date} to {end_date} - range contains only weekends/holidays")
        else:
            # Some trading days in range, but still no data - this might be more concerning
            logger.warning(f"No price data available for {ticker} from {start_date} to {end_date} - "
                         f"this range includes trading days, check if ticker is valid")
    
    def _get_cache_file_path(self, ticker: str) -> Path:
        """Get the cache file path for a ticker."""
        return self._cache_dir / f"{ticker.upper()}_prices.json"
    
    def _load_cached_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load cached price data from disk."""
        cache_file = self._get_cache_file_path(ticker)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Convert back to DataFrame
            df = pd.DataFrame(data['prices'])
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            
            logger.debug(f"Loaded {len(df)} cached price records for {ticker}")
            return df
            
        except Exception as e:
            logger.warning(f"Failed to load cached data for {ticker}: {e}")
            return None
    
    def _save_cached_data(self, ticker: str, data: pd.DataFrame) -> None:
        """Save price data to disk cache."""
        if data.empty:
            return
        
        cache_file = self._get_cache_file_path(ticker)
        
        try:
            # Convert DataFrame to JSON-serializable format
            cache_data = {
                'ticker': ticker.upper(),
                'last_updated': datetime.now().isoformat(),
                'prices': data.to_dict('records')
            }
            
            # Convert date objects to strings for JSON serialization
            for record in cache_data['prices']:
                if isinstance(record['Date'], date):
                    record['Date'] = record['Date'].isoformat()
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} price records to cache for {ticker}")
            
        except Exception as e:
            logger.warning(f"Failed to save cached data for {ticker}: {e}")
    
    def _merge_cached_and_new_data(self, cached_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
        """Merge cached data with new data, avoiding duplicates."""
        if cached_data.empty:
            return new_data
        
        if new_data.empty:
            return cached_data
        
        # Combine and remove duplicates based on Date
        combined = pd.concat([cached_data, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset=['Date'], keep='last')
        combined = combined.sort_values('Date').reset_index(drop=True)
        
        return combined
    
    def _get_missing_date_ranges(self, ticker: str, start_date: date, end_date: date) -> list:
        """Determine what date ranges need to be fetched from API."""
        cached_data = self._load_cached_data(ticker)
        
        if cached_data is None or cached_data.empty:
            return [(start_date, end_date)]
        
        # Convert cached dates to a set for fast lookup
        cached_dates = set(cached_data['Date'])
        
        # Generate all business days in the requested range
        date_range = pd.bdate_range(start=start_date, end=end_date)
        requested_dates = set(date_range.date)
        
        # Find missing dates
        missing_dates = requested_dates - cached_dates
        
        if not missing_dates:
            return []  # All data is cached
        
        # Convert missing dates to contiguous ranges
        missing_dates_sorted = sorted(missing_dates)
        ranges = []
        range_start = missing_dates_sorted[0]
        range_end = missing_dates_sorted[0]
        
        for current_date in missing_dates_sorted[1:]:
            if (current_date - range_end).days <= 3:  # Allow for weekends
                range_end = current_date
            else:
                ranges.append((range_start, range_end))
                range_start = current_date
                range_end = current_date
        
        ranges.append((range_start, range_end))
        return ranges
    
    def _get_yfinance(self) -> Any:
        """Lazy import of yfinance to avoid SSL issues during package setup."""
        if self._yf is None:
            import yfinance as yf
            self._yf = yf
        return self._yf
    
    def fetch_price_data(self, ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Fetch price data for a ticker within the specified date range.
        Uses persistent cache to avoid redundant API calls.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            
        Returns:
            DataFrame with price data
        """
        ticker = ticker.upper()
        
        # Check if we have all the data in cache
        cached_data = self._load_cached_data(ticker)
        missing_ranges = self._get_missing_date_ranges(ticker, start_date, end_date)
        
        if not missing_ranges:
            # All data is cached, filter and return
            logger.debug(f"All data for {ticker} ({start_date} to {end_date}) found in cache")
            if cached_data is not None:
                mask = (cached_data['Date'] >= start_date) & (cached_data['Date'] <= end_date)
                return cached_data[mask].reset_index(drop=True)
            return pd.DataFrame()
        
        # Fetch missing data from API
        all_new_data = pd.DataFrame()
        
        for range_start, range_end in missing_ranges:
            logger.debug(f"Fetching {ticker} data from API for {range_start} to {range_end}")
            
            try:
                yf = self._get_yfinance()
                stock = yf.Ticker(ticker)
                data = stock.history(start=range_start, end=range_end + timedelta(days=1))
                
                if not data.empty:
                    # Keep only the Close column and reset index to have Date as a column
                    range_data = data[['Close']].reset_index()
                    range_data.columns = ['Date', 'Close']
                    range_data['Date'] = range_data['Date'].dt.date
                    
                    all_new_data = pd.concat([all_new_data, range_data], ignore_index=True)
                else:
                    # No data returned - provide helpful context
                    self._log_no_data_reason(ticker, range_start, range_end)
                
            except Exception as e:
                # Check if this looks like a weekend/holiday issue vs a real error
                if self._is_likely_non_trading_day(range_start) and self._is_likely_non_trading_day(range_end):
                    logger.debug(f"No data for {ticker} ({range_start} to {range_end}) - likely non-trading days")
                else:
                    logger.error(f"Failed to fetch price data for {ticker} ({range_start} to {range_end}): {e}")
        
        # Merge with cached data and save
        if cached_data is None:
            cached_data = pd.DataFrame()
        
        combined_data = self._merge_cached_and_new_data(cached_data, all_new_data)
        
        if not combined_data.empty:
            self._save_cached_data(ticker, combined_data)
            # Update in-memory cache
            self._cache[ticker] = combined_data.copy()
            self._cache_timestamps[ticker] = datetime.now()
        
        # Filter to requested date range
        if not combined_data.empty:
            mask = (combined_data['Date'] >= start_date) & (combined_data['Date'] <= end_date)
            result = combined_data[mask].reset_index(drop=True)
        else:
            result = pd.DataFrame()
        
        if result.empty:
            self._log_no_data_reason(ticker, start_date, end_date)
        
        return result
    
    def get_rolling_maximum(self, prices: pd.Series, window: int) -> pd.Series:
        """
        Calculate rolling maximum for the given price series.
        
        Args:
            prices: Series of price values
            window: Rolling window size in periods
            
        Returns:
            Series with rolling maximum values
        """
        return prices.rolling(window=window, min_periods=1).max()
    
    def get_current_price(self, ticker: str) -> float:
        """
        Get the current (most recent) closing price for a ticker.
        First checks cache for recent data, then fetches from API if needed.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Current closing price
        """
        ticker = ticker.upper()
        
        # Check if we have recent data in cache (within last day)
        cached_data = self._load_cached_data(ticker)
        if cached_data is not None and not cached_data.empty:
            latest_cached_date = cached_data['Date'].max()
            if (date.today() - latest_cached_date).days <= 1:
                latest_price = cached_data[cached_data['Date'] == latest_cached_date]['Close'].iloc[-1]
                logger.debug(f"Using cached current price for {ticker}: {latest_price}")
                return float(latest_price)
        
        # Fetch current data from API
        try:
            yf = self._get_yfinance()
            stock = yf.Ticker(ticker)
            # Get the most recent trading day's data
            data = stock.history(period="1d")
            
            if data.empty:
                # Check if today is a non-trading day
                today = date.today()
                if self._is_likely_non_trading_day(today):
                    day_name = today.strftime("%A")
                    if today.weekday() >= 5:
                        raise ValueError(f"No current price data for {ticker} - markets are closed on {day_name}s")
                    else:
                        raise ValueError(f"No current price data for {ticker} - markets appear to be closed today ({day_name}, likely a holiday)")
                else:
                    raise ValueError(f"No current price data available for {ticker} - check if ticker is valid")
            
            current_price = float(data['Close'].iloc[-1])
            
            # Update cache with current data
            current_date = data.index[-1].date()
            new_record = pd.DataFrame({
                'Date': [current_date],
                'Close': [current_price]
            })
            
            if cached_data is None:
                cached_data = pd.DataFrame()
            
            updated_cache = self._merge_cached_and_new_data(cached_data, new_record)
            self._save_cached_data(ticker, updated_cache)
            
            return current_price
            
        except Exception as e:
            logger.error(f"Failed to get current price for {ticker}: {e}")
            raise
    
    def update_cache(self, ticker: str, new_data: pd.DataFrame) -> None:
        """
        Update the price data cache for a ticker (both in-memory and persistent).
        
        Args:
            ticker: Stock ticker symbol
            new_data: New price data to cache
        """
        ticker = ticker.upper()
        
        # Update in-memory cache
        self._cache[ticker] = new_data.copy()
        self._cache_timestamps[ticker] = datetime.now()
        
        # Update persistent cache
        self._save_cached_data(ticker, new_data)
        
        logger.debug(f"Updated cache for {ticker} with {len(new_data)} records")
    
    def clear_cache(self, ticker: Optional[str] = None) -> None:
        """
        Clear cached data for a specific ticker or all tickers.
        
        Args:
            ticker: Stock ticker symbol to clear, or None to clear all
        """
        if ticker is not None:
            ticker = ticker.upper()
            # Clear in-memory cache
            self._cache.pop(ticker, None)
            self._cache_timestamps.pop(ticker, None)
            
            # Clear persistent cache
            cache_file = self._get_cache_file_path(ticker)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Cleared cache for {ticker}")
        else:
            # Clear all caches
            self._cache.clear()
            self._cache_timestamps.clear()
            
            # Clear all persistent cache files
            for cache_file in self._cache_dir.glob("*_prices.json"):
                cache_file.unlink()
            logger.debug("Cleared all price caches")
    
    def get_cache_info(self, ticker: str) -> Dict:
        """
        Get information about cached data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with cache information
        """
        ticker = ticker.upper()
        cached_data = self._load_cached_data(ticker)
        
        if cached_data is None or cached_data.empty:
            return {
                'ticker': ticker,
                'cached': False,
                'records': 0,
                'date_range': None
            }
        
        return {
            'ticker': ticker,
            'cached': True,
            'records': len(cached_data),
            'date_range': {
                'start': cached_data['Date'].min().isoformat(),
                'end': cached_data['Date'].max().isoformat()
            }
        }