# Usage Examples

This document provides detailed examples of how to use the Buy the Dip Strategy simulator in various scenarios.

## Basic Examples

### 1. Default Strategy (S&P 500)

Run the strategy with default settings:

```bash
poetry run python buy_the_dip.py
```

**What this does:**
- Monitors SPY (S&P 500 ETF)
- Uses 90-day rolling maximum
- Triggers DCA on 10% drops
- Invests $2,000 monthly during dips

**Expected output:**
```
Buy the Dip Strategy Starting...
Configuration: SPY, 90-day window, 90% trigger, $2000/month
Loading price data for SPY...
Current Price: $450.25
Rolling Max (90d): $475.30
Trigger Price: $427.77
Status: MONITORING (price above trigger)
```

### 2. Generate Performance Report

```bash
poetry run python buy_the_dip.py --report
```

**What this does:**
- Loads existing strategy state
- Calculates CAGR metrics
- Compares strategy vs buy-and-hold
- Shows detailed performance analysis

## Configuration Examples

### 3. Conservative Long-term Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/conservative.yaml
```

**Configuration details:**
```yaml
ticker: "SPY"
rolling_window_days: 180  # 6-month window
percentage_trigger: 0.85  # 15% drop required
monthly_dca_amount: 1000.0  # $1,000/month
```

**Best for:**
- Risk-averse investors
- Long-term wealth building
- Stable, predictable approach

### 4. Aggressive Growth Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml
```

**Configuration details:**
```yaml
ticker: "QQQ"  # NASDAQ-100 (more volatile)
rolling_window_days: 30   # 1-month window
percentage_trigger: 0.95  # 5% drop triggers
monthly_dca_amount: 3000.0  # $3,000/month
```

**Best for:**
- Higher risk tolerance
- Frequent market participation
- Tech-focused exposure

### 5. Individual Stock Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/individual_stock.yaml
```

**Configuration details:**
```yaml
ticker: "AAPL"  # Apple stock
rolling_window_days: 60   # 2-month window
percentage_trigger: 0.88  # 12% drop triggers
monthly_dca_amount: 1500.0  # $1,500/month
```

**Best for:**
- Stock-specific strategies
- Company-focused investing
- Higher volatility tolerance

### 6. Balanced Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/balanced.yaml
```

**Configuration details:**
```yaml
ticker: "SPY"  # S&P 500 ETF
rolling_window_days: 60   # 2-month window
percentage_trigger: 0.92  # 8% drop triggers
monthly_dca_amount: 2000.0  # $2,000/month
```

**Best for:**
- Moderate risk tolerance
- Balanced approach between aggressive and conservative
- Most general-purpose investors

### 7. Dividend-Focused Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/dividend_focused.yaml
```

**Configuration details:**
```yaml
ticker: "VIG"  # Vanguard Dividend Appreciation ETF
rolling_window_days: 120  # 4-month window
percentage_trigger: 0.89  # 11% drop triggers
monthly_dca_amount: 2000.0  # $2,000/month
```

**Best for:**
- Income-oriented investors
- Dividend growth focus
- Lower volatility preference

### 8. Small Cap Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/small_cap.yaml
```

**Configuration details:**
```yaml
ticker: "IWM"  # Russell 2000 Small Cap ETF
rolling_window_days: 75   # 2.5-month window
percentage_trigger: 0.87  # 13% drop triggers
monthly_dca_amount: 1500.0  # $1,500/month
```

**Best for:**
- Growth-focused investors
- Higher risk tolerance
- Small company exposure

### 9. Crypto ETF Strategy

```bash
poetry run python buy_the_dip.py --config config_examples/crypto_etf.yaml
```

**Configuration details:**
```yaml
ticker: "BITO"  # Bitcoin ETF
rolling_window_days: 45   # 1.5-month window
percentage_trigger: 0.82  # 18% drop triggers
monthly_dca_amount: 1000.0  # $1,000/month
```

**Best for:**
- Cryptocurrency exposure
- Very high risk tolerance
- Speculative investing
- **Warning**: Extremely volatile

## Advanced Usage

### 10. Custom Configuration

Create your own configuration file:

```yaml
# my_strategy.yaml
ticker: "MSFT"
rolling_window_days: 120
percentage_trigger: 0.92
monthly_dca_amount: 2500.0
data_cache_days: 60
```

Run with custom config:
```bash
poetry run python buy_the_dip.py --config my_strategy.yaml
```

### 11. Validate Configuration Before Running

```bash
poetry run python buy_the_dip.py --config my_strategy.yaml --validate-config
```

**Expected output:**
```
Validating configuration: my_strategy.yaml
✓ Configuration is valid
✓ Ticker: MSFT
✓ Rolling window: 120 days
✓ Trigger: 92% (8% drop)
✓ DCA amount: $2500/month
✓ Cache: 60 days
```

### 12. Multiple Strategy Comparison

Run different strategies and compare results:

```bash
# Run conservative strategy
poetry run python buy_the_dip.py --config config_examples/conservative.yaml

# Generate report
poetry run python buy_the_dip.py --config config_examples/conservative.yaml --report > conservative_report.txt

# Run aggressive strategy  
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml

# Generate report
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml --report > aggressive_report.txt

# Compare the reports
diff conservative_report.txt aggressive_report.txt
```

## Real-World Scenarios

### 13. Market Crash Simulation

Test how the strategy performs during market downturns:

```yaml
# crash_strategy.yaml
ticker: "SPY"
rolling_window_days: 30   # Quick response
percentage_trigger: 0.95  # Catch early drops
monthly_dca_amount: 5000.0  # Aggressive buying
```

```bash
poetry run python buy_the_dip.py --config crash_strategy.yaml
```

### 14. Sector-Specific Strategy

Focus on specific market sectors:

```yaml
# tech_strategy.yaml
ticker: "XLK"  # Technology Select Sector SPDR Fund
rolling_window_days: 45
percentage_trigger: 0.90
monthly_dca_amount: 2000.0
```

```yaml
# finance_strategy.yaml  
ticker: "XLF"  # Financial Select Sector SPDR Fund
rolling_window_days: 60
percentage_trigger: 0.88
monthly_dca_amount: 1800.0
```

### 15. International Markets

Apply strategy to international ETFs:

```yaml
# international_strategy.yaml
ticker: "VEA"  # Vanguard FTSE Developed Markets ETF
rolling_window_days: 90
percentage_trigger: 0.89
monthly_dca_amount: 1500.0
```

```yaml
# emerging_markets.yaml
ticker: "VWO"  # Vanguard FTSE Emerging Markets ETF  
rolling_window_days: 75
percentage_trigger: 0.87  # More volatile, bigger drops
monthly_dca_amount: 1000.0
```

## Monitoring and Analysis

### 16. Continuous Monitoring Setup

For ongoing strategy execution, you might want to run the strategy periodically:

```bash
# Create a simple monitoring script
cat > monitor_strategy.sh << 'EOF'
#!/bin/bash
echo "$(date): Running Buy the Dip Strategy"
poetry run python buy_the_dip.py --config config.yaml
echo "$(date): Strategy execution completed"
echo "---"
EOF

chmod +x monitor_strategy.sh

# Run daily (add to cron or task scheduler)
./monitor_strategy.sh
```

### 17. Performance Tracking

Track performance over time:

```bash
# Generate daily reports
poetry run python buy_the_dip.py --report > "report_$(date +%Y%m%d).txt"

# Compare performance over time
ls report_*.txt | sort | tail -5  # Last 5 reports
```

### 18. Backtesting Different Parameters

Test various trigger percentages:

```bash
# Test different trigger levels
for trigger in 0.85 0.90 0.95; do
    echo "Testing trigger: $trigger"
    
    # Create temporary config
    cat > temp_config.yaml << EOF
ticker: "SPY"
rolling_window_days: 90
percentage_trigger: $trigger
monthly_dca_amount: 2000.0
data_cache_days: 30
EOF
    
    # Run strategy
    poetry run python buy_the_dip.py --config temp_config.yaml --report > "backtest_${trigger}.txt"
    
    # Clean up
    rm temp_config.yaml
done

# Compare results
echo "Trigger 0.85:"; grep "Strategy CAGR" backtest_0.85.txt
echo "Trigger 0.90:"; grep "Strategy CAGR" backtest_0.90.txt  
echo "Trigger 0.95:"; grep "Strategy CAGR" backtest_0.95.txt
```

## Error Handling Examples

## Error Handling Examples

### 21. Cache Management and Validation

```bash
# Check what data is cached for a ticker
poetry run python buy_the_dip.py --cache-info AAPL

# Validate cached data against live API data
poetry run python buy_the_dip.py --validate-cache AAPL

# If validation fails, clear the cache
poetry run python buy_the_dip.py --clear-cache AAPL

# Run strategy with fresh data (ignoring cache)
poetry run python buy_the_dip.py --ignore-cache --backtest
```

**Expected cache info output:**
```
📁 CACHE INFO - AAPL
========================================
Status: ✅ Cached
Records: 45
Date Range: 2024-10-15 to 2024-12-31
```

**Expected validation output (success):**
```
🔍 CACHE VALIDATION - AAPL
==================================================
Validation Status: ✅ PASSED
Records Checked: 30
Mismatches Found: 0

✅ Cache data matches API data perfectly!
```

**Expected validation output (failure):**
```
🔍 CACHE VALIDATION - AAPL
==================================================
Validation Status: ❌ FAILED
Records Checked: 30
Mismatches Found: 5

⚠️  Cache data does not match API data!
Consider clearing the cache with --clear-cache

Sample Mismatches:
  2024-12-20: Cached=$150.25, API=$150.30
  2024-12-19: Cached=$149.80, API=$149.85
  2024-12-18: Cached=$151.10, API=$151.15
```

### 22. Invalid Ticker Symbol

```bash
# This will show graceful error handling
cat > invalid_config.yaml << 'EOF'
ticker: "INVALID_TICKER"
rolling_window_days: 90
percentage_trigger: 0.90
monthly_dca_amount: 2000.0
EOF

poetry run python buy_the_dip.py --config invalid_config.yaml
```

**Expected output:**
```
ERROR: No data found for ticker INVALID_TICKER
Please verify the ticker symbol is correct and try again.
```

### 23. Invalid Configuration Values

```bash
# This will show validation errors
cat > bad_config.yaml << 'EOF'
ticker: "SPY"
rolling_window_days: 500  # Too large (max 365)
percentage_trigger: 1.5   # Too large (max 1.0)
monthly_dca_amount: -100  # Negative (must be > 0)
EOF

poetry run python buy_the_dip.py --config bad_config.yaml --validate-config
```

**Expected output:**
```
Configuration validation failed:
- rolling_window_days: ensure this value is less than or equal to 365
- percentage_trigger: ensure this value is less than or equal to 1.0  
- monthly_dca_amount: ensure this value is greater than 0
```

## Tips and Best Practices

### Configuration Guidelines

1. **Start Conservative**: Begin with longer rolling windows (90+ days) and lower trigger percentages (0.85-0.90)

2. **Test First**: Always validate configuration before running: `--validate-config`

3. **Monitor Regularly**: Check strategy status and performance periodically

4. **Diversify**: Consider running multiple strategies with different tickers

5. **Adjust Gradually**: Make small parameter changes and observe results

### Performance Optimization

1. **Cache Management**: Use appropriate `data_cache_days` values (30-90 days typical)

2. **Network Efficiency**: Avoid running multiple instances simultaneously to prevent API rate limits

3. **Storage**: Monitor disk space usage for state files and cache data

### Risk Management

1. **Position Sizing**: Adjust `monthly_dca_amount` based on your risk tolerance

2. **Diversification**: Don't put all capital into a single strategy or ticker

3. **Regular Review**: Periodically review and adjust strategy parameters

4. **Market Conditions**: Consider pausing during extreme market conditions

Remember: This is a simulation tool for educational purposes. Always consult with financial advisors for real investment decisions.