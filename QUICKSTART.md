# Quick Start Guide

Get up and running with the Buy the Dip Strategy in 5 minutes.

## 🚀 Installation (2 minutes)

### Option 1: Poetry (Recommended)
```bash
# Install Poetry if you don't have it
curl -sSL https://install.python-poetry.org | python3 -

# Clone and install
git clone <repository-url>
cd buy-the-dip-strategy
poetry install
```

### Option 2: pip + venv
```bash
# Clone and setup
git clone <repository-url>
cd buy-the-dip-strategy
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## 🎯 First Run (1 minute)

### Test the Installation
```bash
# Using Poetry
poetry run python buy_the_dip.py --help

# Using pip
python buy_the_dip.py --help
```

You should see the help message with available options.

### Run with Default Settings
```bash
# Using Poetry
poetry run python buy_the_dip.py

# Using pip
python buy_the_dip.py
```

This will:
- Monitor SPY (S&P 500 ETF)
- Use 90-day rolling maximum
- Trigger on 10% drops
- Simulate $2,000 monthly investments

## 📊 Understanding the Output

### Normal Monitoring
```
Buy the Dip Strategy Starting...
Configuration: SPY, 90-day window, 90% trigger, $2000/month
Current Price: $450.25
Rolling Max (90d): $475.30
Trigger Price: $427.77
Status: MONITORING (price above trigger)
```

**What this means**:
- Current SPY price: $450.25
- Highest price in last 90 days: $475.30
- Will start buying if price drops to $427.77 or below
- Currently just monitoring (no buying)

### When a Dip is Detected
```
[Price Update] SPY: $425.50 (Drop detected: -10.5%)
🔥 DCA ACTIVATED! Starting session: dca_20241201_001
Target: Invest $2000/month until price recovers to $427.77

[Investment] Session dca_20241201_001: $2000 → 4.70 shares @ $425.50
Portfolio: $2000 invested, 4.70 shares, Value: $2001.35 (+0.07%)
```

**What this means**:
- Price dropped to $425.50 (below trigger of $427.77)
- Strategy activated and bought $2,000 worth of shares
- Will continue buying $2,000 monthly until price recovers

## 🛠️ Cache Management

The system caches price data to reduce API calls. Sometimes you might need to manage this cache:

### Check Cache Status
```bash
poetry run python buy_the_dip.py --cache-info SPY
```

### Validate Cache Data
```bash
# Check if cached data matches live API data
poetry run python buy_the_dip.py --validate-cache SPY
```

### Clear Cache if Needed
```bash
# Clear cache for specific ticker
poetry run python buy_the_dip.py --clear-cache SPY

# Clear all cache
poetry run python buy_the_dip.py --clear-cache all
```

### Force Fresh Data
```bash
# Ignore cache for one run (gets fresh data)
poetry run python buy_the_dip.py --ignore-cache --backtest
```

## 🎛️ Try Different Strategies (2 minutes)

### Conservative (Less Risk)
```bash
poetry run python buy_the_dip.py --config config_examples/conservative.yaml
```
- Only buys on 15% drops
- $1,000 monthly investments
- More stable, less frequent trading

### Aggressive (More Risk)
```bash
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml
```
- Buys on 5% drops
- $3,000 monthly investments
- More frequent trading, higher potential returns

### Balanced (Middle Ground)
```bash
poetry run python buy_the_dip.py --config config_examples/balanced.yaml
```
- Buys on 8% drops
- $2,000 monthly investments
- Good balance of risk and opportunity

## 📈 Generate Performance Report

```bash
poetry run python buy_the_dip.py --report
```

This shows:
- Total investments made
- Current portfolio value
- Performance vs buy-and-hold
- CAGR (Compound Annual Growth Rate) analysis

## 🛠️ Customize Your Strategy

### Create Your Own Configuration
```bash
# Copy the default config
cp config.yaml my_strategy.yaml

# Edit with your preferred settings
nano my_strategy.yaml  # or use your favorite editor
```

### Key Settings to Adjust
```yaml
ticker: "SPY"           # Change to QQQ, VTI, AAPL, etc.
percentage_trigger: 0.90  # 0.95 = more sensitive, 0.85 = less sensitive
monthly_dca_amount: 2000.0  # Adjust based on your budget
```

### Test Your Configuration
```bash
# Validate before running
poetry run python buy_the_dip.py --config my_strategy.yaml --validate-config

# Run your strategy
poetry run python buy_the_dip.py --config my_strategy.yaml
```

## 🎯 Common Use Cases

### "I want to invest in Apple stock"
```yaml
# apple_strategy.yaml
ticker: "AAPL"
rolling_window_days: 60
percentage_trigger: 0.88
monthly_dca_amount: 1500.0
```

### "I want a very conservative approach"
```yaml
# ultra_conservative.yaml
ticker: "SPY"
rolling_window_days: 180
percentage_trigger: 0.80  # Only 20%+ drops
monthly_dca_amount: 500.0
```

### "I want to catch every small dip"
```yaml
# catch_all_dips.yaml
ticker: "QQQ"
rolling_window_days: 30
percentage_trigger: 0.97  # Even 3% drops
monthly_dca_amount: 1000.0
```

## 🚨 Important Notes

### This is a Simulator
- **No real money is involved**
- **No actual trades are executed**
- **For educational purposes only**

### Key Concepts
- **Rolling Maximum**: Highest price in the last N days
- **Trigger Price**: Rolling maximum × trigger percentage
- **DCA (Dollar-Cost Averaging)**: Investing fixed amounts regularly
- **CAGR**: Compound Annual Growth Rate (annualized returns)

### Risk Considerations
- Past performance doesn't guarantee future results
- All investments carry risk of loss
- This tool is for learning and backtesting only
- Consult financial advisors for real investment decisions

## 🆘 Need Help?

### Validate Your Setup
```bash
# Check if everything is working
poetry run python buy_the_dip.py --validate-config
```

### Common Issues

**"No data found for ticker"**
- Check internet connection
- Verify ticker symbol is correct (use Yahoo Finance symbols)

**"Configuration validation failed"**
- Check YAML syntax (indentation matters)
- Ensure all values are in valid ranges

**"Command not found"**
- Make sure you're in the project directory
- Activate virtual environment if using pip method

### Get More Examples
- Check `EXAMPLES.md` for detailed usage scenarios
- Look at `CONFIGURATION_GUIDE.md` for parameter explanations
- Read `README.md` for comprehensive documentation

## 🎉 Next Steps

1. **Experiment**: Try different configurations and see how they perform
2. **Learn**: Read about dollar-cost averaging and market timing strategies
3. **Analyze**: Use the `--report` flag to understand performance metrics
4. **Customize**: Create configurations that match your investment philosophy
5. **Share**: Contribute improvements or share interesting configurations

Remember: This is a learning tool. Use it to understand investment strategies before applying concepts with real money!