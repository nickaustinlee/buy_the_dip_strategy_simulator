# Configuration Guide

This guide explains how to configure the Buy the Dip Strategy for different investment approaches and risk tolerances.

## Configuration File Structure

All configuration files use YAML format with the following parameters:

```yaml
ticker: "SPY"                    # Stock/ETF ticker symbol
rolling_window_days: 90          # Days for rolling maximum calculation
percentage_trigger: 0.90         # Trigger threshold (0.0-1.0)
monthly_dca_amount: 2000.0       # Monthly investment amount ($)
data_cache_days: 30              # Price data cache duration (days)
```

## Parameter Explanations

### ticker
**Purpose**: Specifies which stock or ETF to monitor  
**Format**: String (valid ticker symbol)  
**Examples**: "SPY", "QQQ", "AAPL", "MSFT"

**Popular Options**:
- **SPY**: S&P 500 ETF (broad market, low volatility)
- **QQQ**: NASDAQ-100 ETF (tech-heavy, higher volatility)
- **VTI**: Total Stock Market ETF (maximum diversification)
- **IWM**: Russell 2000 ETF (small-cap exposure)
- **Individual stocks**: AAPL, MSFT, GOOGL, etc.

### rolling_window_days
**Purpose**: Number of days to look back when calculating the rolling maximum price  
**Range**: 1-365 days  
**Impact**: Shorter windows = more sensitive to recent price movements

**Recommendations**:
- **30 days**: Very sensitive, catches short-term dips
- **60 days**: Balanced sensitivity for most strategies
- **90 days**: Standard approach, good for broad market ETFs
- **120+ days**: Conservative, focuses on major corrections

### percentage_trigger
**Purpose**: Percentage of rolling maximum that triggers investment  
**Range**: 0.0-1.0 (0% to 100%)  
**Formula**: `trigger_price = rolling_maximum * percentage_trigger`

**Examples**:
- **0.95**: Triggers on 5% drops (very aggressive)
- **0.92**: Triggers on 8% drops (moderate)
- **0.90**: Triggers on 10% drops (balanced)
- **0.85**: Triggers on 15% drops (conservative)
- **0.80**: Triggers on 20% drops (very conservative)

### monthly_dca_amount
**Purpose**: Dollar amount to invest each month during active DCA periods  
**Range**: Any positive number  
**Considerations**: Should align with your risk tolerance and available capital

**Guidelines**:
- Start with amounts you're comfortable losing
- Consider your total investment portfolio
- Higher amounts = higher potential returns and losses

### data_cache_days
**Purpose**: How long to cache price data locally to reduce API calls  
**Range**: 1+ days  
**Impact**: Longer caching = fewer API calls but potentially stale data

**Recommendations**:
- **15-30 days**: For frequently changing strategies
- **30-60 days**: Standard usage
- **90+ days**: For development or infrequent usage

## Pre-Built Configuration Examples

### 1. Default Configuration (`config.yaml`)
**Best for**: First-time users, general market exposure
```yaml
ticker: "SPY"
rolling_window_days: 90
percentage_trigger: 0.90
monthly_dca_amount: 2000.0
data_cache_days: 30
```

**Characteristics**:
- Broad market exposure via S&P 500
- Balanced sensitivity (10% drops)
- Standard investment amount
- Suitable for most investors

### 2. Conservative Strategy (`config_examples/conservative.yaml`)
**Best for**: Risk-averse investors, retirement accounts
```yaml
ticker: "SPY"
rolling_window_days: 180
percentage_trigger: 0.85
monthly_dca_amount: 1000.0
data_cache_days: 90
```

**Characteristics**:
- Long-term perspective (6-month window)
- Only triggers on major drops (15%)
- Lower investment amount
- Stable, predictable approach

### 3. Aggressive Strategy (`config_examples/aggressive.yaml`)
**Best for**: High risk tolerance, growth-focused investors
```yaml
ticker: "QQQ"
rolling_window_days: 30
percentage_trigger: 0.95
monthly_dca_amount: 3000.0
data_cache_days: 30
```

**Characteristics**:
- Tech-heavy exposure (NASDAQ-100)
- Very sensitive to drops (5% trigger)
- Higher investment amounts
- More frequent trading activity

### 4. Balanced Strategy (`config_examples/balanced.yaml`)
**Best for**: Moderate risk tolerance, steady growth seekers
```yaml
ticker: "SPY"
rolling_window_days: 60
percentage_trigger: 0.92
monthly_dca_amount: 2000.0
data_cache_days: 45
```

**Characteristics**:
- Moderate sensitivity (8% drops)
- 2-month rolling window
- Standard investment amount
- Good middle ground approach

### 5. Individual Stock Strategy (`config_examples/individual_stock.yaml`)
**Best for**: Stock-specific strategies, company-focused investing
```yaml
ticker: "AAPL"
rolling_window_days: 60
percentage_trigger: 0.88
monthly_dca_amount: 1500.0
data_cache_days: 60
```

**Characteristics**:
- Single stock exposure (higher risk)
- Adjusted for individual stock volatility
- Moderate investment amounts
- Requires more monitoring

### 6. Dividend-Focused Strategy (`config_examples/dividend_focused.yaml`)
**Best for**: Income-oriented investors, retirees
```yaml
ticker: "VIG"
rolling_window_days: 120
percentage_trigger: 0.89
monthly_dca_amount: 2000.0
data_cache_days: 60
```

**Characteristics**:
- Dividend appreciation focus
- Longer window (dividend stocks less volatile)
- Moderate trigger threshold
- Income + growth combination

### 7. Small Cap Strategy (`config_examples/small_cap.yaml`)
**Best for**: Growth-focused investors, higher risk tolerance
```yaml
ticker: "IWM"
rolling_window_days: 75
percentage_trigger: 0.87
monthly_dca_amount: 1500.0
data_cache_days: 30
```

**Characteristics**:
- Small-cap exposure (higher volatility)
- Adjusted parameters for volatility
- Moderate investment amounts
- Higher growth potential

### 8. Crypto ETF Strategy (`config_examples/crypto_etf.yaml`)
**Best for**: Crypto exposure, very high risk tolerance
```yaml
ticker: "BITO"
rolling_window_days: 45
percentage_trigger: 0.82
monthly_dca_amount: 1000.0
data_cache_days: 15
```

**Characteristics**:
- Cryptocurrency exposure (very high risk)
- Shorter window due to volatility
- Larger drops required (18% trigger)
- Lower investment amounts
- **Warning**: Extremely volatile

## Creating Custom Configurations

### Step 1: Choose Your Base Strategy
Start with the pre-built configuration that most closely matches your goals:
- Conservative → Long-term, low risk
- Balanced → Moderate risk/reward
- Aggressive → High risk, high reward
- Individual Stock → Company-specific

### Step 2: Adjust Parameters
Modify parameters based on your preferences:

**For Higher Sensitivity** (more frequent buying):
- Decrease `rolling_window_days` (30-60)
- Increase `percentage_trigger` (0.92-0.95)

**For Lower Sensitivity** (less frequent buying):
- Increase `rolling_window_days` (120-180)
- Decrease `percentage_trigger` (0.80-0.87)

**For Different Risk Levels**:
- Higher risk: Increase `monthly_dca_amount`, choose volatile tickers
- Lower risk: Decrease `monthly_dca_amount`, choose stable ETFs

### Step 3: Test Your Configuration
Always validate before running:
```bash
poetry run buy-the-dip --config my_config.yaml --validate-config
```

### Step 4: Monitor and Adjust
- Start with conservative parameters
- Monitor performance over time
- Gradually adjust based on results
- Keep detailed records of changes

## Advanced Configuration Tips

### Market Condition Adjustments

**Bull Markets** (rising prices):
- Use shorter rolling windows (30-60 days)
- Higher trigger percentages (0.92-0.95)
- Catch smaller dips more frequently

**Bear Markets** (falling prices):
- Use longer rolling windows (90-180 days)
- Lower trigger percentages (0.80-0.87)
- Wait for larger drops, avoid catching falling knives

**Volatile Markets**:
- Adjust trigger percentages based on typical volatility
- Consider smaller investment amounts
- Use shorter cache periods for fresher data

### Sector-Specific Considerations

**Technology Stocks/ETFs** (QQQ, XLK):
- Higher volatility → lower trigger percentages
- Shorter rolling windows for responsiveness
- Expect larger price swings

**Utility/Consumer Staples** (XLU, XLP):
- Lower volatility → higher trigger percentages
- Longer rolling windows for stability
- More predictable price movements

**Financial Sector** (XLF):
- Sensitive to interest rates and economic cycles
- Medium rolling windows (60-90 days)
- Moderate trigger percentages

### Cache Management

The system automatically caches price data to reduce API calls and improve performance. However, sometimes you may need to manage this cache manually.

### Cache Validation

**Why validate cache?**
- Cached data might become stale or corrupted
- API data might have been corrected after initial fetch
- Network issues during initial fetch might have caused incomplete data

**How to validate:**
```bash
# Validate cached data against live API
poetry run buy-the-dip --validate-cache SPY
```

**Validation process:**
1. Loads cached data for the ticker
2. Fetches fresh data from yfinance API
3. Compares prices for matching dates
4. Reports any discrepancies (tolerance: 1 cent)

### Cache Information

**Check cache status:**
```bash
poetry run buy-the-dip --cache-info SPY
```

**Output includes:**
- Cache status (cached or not)
- Number of cached records
- Date range of cached data

### Cache Clearing

**Clear specific ticker:**
```bash
poetry run buy-the-dip --clear-cache SPY
```

**Clear all cache:**
```bash
poetry run buy-the-dip --clear-cache all
```

**When to clear cache:**
- Validation shows mismatches
- Suspected data corruption
- Want to ensure fresh data
- Troubleshooting price-related issues

### Ignore Cache (Temporary)

**Force fresh data for one run:**
```bash
poetry run buy-the-dip --ignore-cache --backtest
```

**Use cases:**
- Testing with guaranteed fresh data
- Troubleshooting cache-related issues
- One-time fresh data needs
- Comparing cached vs fresh results

### Cache Best Practices

1. **Regular Validation**: Validate cache monthly or when you notice unusual results
2. **Clear on Issues**: Clear cache if validation fails or data seems incorrect
3. **Monitor Size**: Cache grows over time - clear periodically if disk space is limited
4. **Fresh Data Testing**: Use `--ignore-cache` to test with guaranteed fresh data

### Cache Troubleshooting

**Problem**: Strategy shows unexpected results
**Solution**: Validate cache, clear if mismatches found

**Problem**: "No data found" errors
**Solution**: Clear cache and retry

**Problem**: Very old cached data
**Solution**: Clear cache to get recent data

**Problem**: Disk space issues
**Solution**: Clear cache with `--clear-cache all`

## Risk Management Guidelines

1. **Position Sizing**: Never invest more than you can afford to lose
2. **Diversification**: Consider multiple strategies with different tickers
3. **Regular Review**: Reassess configurations quarterly
4. **Market Awareness**: Adjust parameters during extreme market conditions
5. **Backtesting**: Test configurations with historical data before live use

## Troubleshooting Common Issues

### Configuration Validation Errors

**Error**: `percentage_trigger: ensure this value is less than or equal to 1.0`
**Solution**: Use decimal format (0.90, not 90)

**Error**: `rolling_window_days: ensure this value is greater than 0`
**Solution**: Use positive integers only

**Error**: `monthly_dca_amount: ensure this value is greater than 0`
**Solution**: Use positive numbers only

### Performance Issues

**Problem**: Strategy not triggering investments
**Solutions**:
- Check if trigger percentage is too low
- Verify ticker symbol is correct
- Ensure sufficient price history exists

**Problem**: Too many investments being triggered
**Solutions**:
- Lower the trigger percentage
- Increase the rolling window days
- Choose less volatile tickers

**Problem**: Poor performance vs buy-and-hold
**Solutions**:
- Consider the "opportunity cost" of waiting for dips
- Adjust trigger sensitivity
- Evaluate over longer time periods

Remember: This is a simulation tool for educational purposes. Always test configurations thoroughly and consult financial advisors for real investment decisions.