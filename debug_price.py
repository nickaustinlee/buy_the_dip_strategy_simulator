#!/usr/bin/env python3

from buy_the_dip.price_monitor import PriceMonitor
from datetime import date

pm = PriceMonitor()

try:
    # Try to get price for Jan 2, 2026 (future date)
    prices = pm.get_closing_prices("SPY", date(2026, 1, 2), date(2026, 1, 2))
    if prices.empty:
        print("No price data for Jan 2, 2026 (as expected)")
        # Try current price
        current = pm.get_current_price("SPY")
        print(f"Current price fallback: ${current:.2f}")
    else:
        print(f"Price for Jan 2, 2026: ${prices.iloc[0]:.2f}")

    # Also check what the price was around Dec 29, 2025
    dec_prices = pm.get_closing_prices("SPY", date(2025, 12, 27), date(2025, 12, 31))
    print(f"Prices around Dec 29, 2025:")
    for date_val, price in dec_prices.items():
        print(f"  {date_val}: ${price:.2f}")

except Exception as e:
    print(f"Error: {e}")
