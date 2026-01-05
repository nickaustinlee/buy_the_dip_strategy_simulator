# Buy the Dip Strategy

A Python-based stock trading strategy simulator that implements a simplified "buy the dip" approach. The system evaluates each trading day independently, checking if yesterday's closing price dropped below a dynamically calculated trigger price. When conditions are met and no investment has been made in the past 28 days, it executes a buy at the current day's closing price.

## 🚀 Key Features

- **Automated Buy Signal Alerts**: Get macOS notifications when buy signals are detected - perfect for daily cron jobs
- **Multi-Ticker Buy Signal Check**: Instantly compare buy signals across multiple tickers to prioritize investments
- **Simplified Daily Evaluation**: Clean, stateless daily evaluation logic - no complex session management
- **28-Day Investment Spacing**: Automatic constraint enforcement preventing investments within 28 days
- **Configurable Strategy Parameters**: Customize ticker, rolling window, trigger percentage, and investment amount via YAML
- **Intelligent Price Monitoring**: Real-time price data fetching with smart caching and validation
- **Calendar vs Trading Days**: Choose between calendar days (default, intuitive) or trading days for rolling window calculations
- **Comprehensive Testing**: 233 tests including property-based testing for universal correctness guarantees
- **Robust CLI Interface**: Full-featured command-line interface with backtesting and reporting
- **Performance Analysis**: Portfolio metrics and performance tracking with buy-and-hold comparison
- **Production Ready**: Thoroughly tested with comprehensive error handling

## 🎯 How It Works

The strategy follows a simple daily evaluation process:

1. **Calculate Trigger Price**: `rolling_maximum * percentage_trigger` (e.g., 90% of 90-day high)
2. **Check Yesterday's Price**: Did it drop to or below the trigger price?
3. **Enforce 28-Day Rule**: Has it been at least 28 days since the last investment?
4. **Execute Investment**: If both conditions are met, invest the configured amount

**Example**: If SPY's 90-day high is $500 and your trigger is 90%, the system will invest when the price drops to $450 or below (assuming no recent investments).

## 📦 Installation

### Quick Start
New to the project? Check out the [Quick Start Guide](QUICKSTART.md) for a 5-minute setup and first run.

### Prerequisites
- Python 3.13 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd buy-the-dip-strategy

# Install Poetry if needed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

### Using pip

```bash
# Clone and setup
git clone <repository-url>
cd buy-the-dip-strategy
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

For detailed installation instructions, see [INSTALLATION.md](INSTALLATION.md).

## 🎯 Quick Start

### Run with Default Configuration
```bash
# Using Poetry
poetry run python buy_the_dip.py

# Using pip installation
python buy_the_dip.py
```

This monitors SPY with a 90-day rolling window, triggers on 10% drops, and simulates $1,000 monthly investments.

### Run a Backtest
```bash
# Backtest the last year
poetry run python buy_the_dip.py --backtest --period 1y

# Backtest specific date range
poetry run python buy_the_dip.py --backtest --start-date 2023-01-01 --end-date 2023-12-31
```

### Check Current Status
```bash
# Show current portfolio status
poetry run python buy_the_dip.py --status

# Evaluate a specific date
poetry run python buy_the_dip.py --evaluate 2024-01-15
```

## 📋 Usage Examples

For comprehensive usage examples, see [EXAMPLES.md](EXAMPLES.md).

### Quick Buy Signal Check (Multi-Ticker)

**The fastest way to check which tickers have buy signals right now:**

```bash
# Check multiple tickers at once
poetry run buy-the-dip --tickers QQQ SPY AAPL VTI BND \
  --check \
  --rolling-window 30 \
  --trigger-pct 0.95
```

**Output:**
```
🔍 MULTI-TICKER BUY SIGNAL CHECK (2026-01-04)
================================================================================

Ticker   Yesterday    Trigger      Signal   % from Trigger 
--------------------------------------------------------------------------------
QQQ      $613.12      $595.46      ❌ NO     +3.0%          
SPY      $683.17      $655.86      ❌ NO     +4.2%          
AAPL     $271.01      $271.88      ✅ BUY    -0.3%          
VTI      $336.31      $322.89      ❌ NO     +4.2%          
BND      $74.04       $70.69       ❌ NO     +4.7%          

Summary: ✅ 1 of 5 tickers have buy signals
```

**Use Case**: "I have money to invest today. Which of my favorite tickers are showing buy signals according to the buy-the-dip strategy?"

This helps you prioritize which ticker to invest in when you have capital available. The check ignores the 28-day constraint and simply tells you which tickers are currently at attractive entry points based on your strategy parameters.

### Automated Buy Signal Alerts (macOS)

**Get notified automatically when buy signals are detected:**

```bash
# Add --notify flag to get macOS notifications
poetry run buy-the-dip --tickers QQQ SPY AAPL VTI BND \
  --check \
  --rolling-window 30 \
  --trigger-pct 0.95 \
  --notify
```

**Notification shows:**
```
Buy Signals Detected (1 of 5):

✅ AAPL: $271.01 (trigger $271.88, -0.3%)
```

![macOS Desktop Alert Example](screenshots/osx_desktop_alert_example.png)

**Set up daily automated alerts with cron:**

1. **Create a check script** (`~/check_buy_signals.sh`):
```bash
#!/bin/bash
cd /path/to/buy-the-dip
/usr/local/bin/poetry run buy-the-dip \
  --tickers QQQ SPY AAPL VTI BND \
  --check \
  --rolling-window 30 \
  --trigger-pct 0.95 \
  --notify
```

2. **Make it executable**:
```bash
chmod +x ~/check_buy_signals.sh
```

3. **Add to crontab** (runs weekdays at 5 PM after market close):
```bash
# Edit crontab
crontab -e

# Add this line (replace /path/to with your actual path):
0 17 * * 1-5 /Users/yourusername/check_buy_signals.sh
```

4. **Test it manually**:
```bash
~/check_buy_signals.sh
```

**How it works:**
- Runs automatically every weekday at 5 PM (after market close)
- Checks all your tickers for buy signals
- Sends macOS notification only when buy signals are detected
- No terminal needs to be open - runs in background
- Notification shows which tickers have signals with prices

**Customize the schedule:**
- `0 17 * * 1-5` = 5:00 PM, Monday-Friday
- `30 16 * * 1-5` = 4:30 PM, Monday-Friday
- `0 9 * * 1-5` = 9:00 AM, Monday-Friday

**Note**: macOS notifications only work when your Mac is awake. Consider adjusting your Energy Saver settings or using `pmset` to wake your Mac for the cron job if needed.

### Single Ticker Check

```bash
# Check if a single ticker has a buy signal today
poetry run buy-the-dip --config config.yaml --check

# With notifications
poetry run buy-the-dip --config config.yaml --check --notify
```

### Basic Commands

```bash
# Run with custom configuration
poetry run python buy_the_dip.py --config my_config.yaml

# Validate configuration without running
poetry run python buy_the_dip.py --config my_config.yaml --validate-config

# Run backtest with different periods
poetry run python buy_the_dip.py --backtest --period 6m    # 6 months
poetry run python buy_the_dip.py --backtest --period 90d   # 90 days
poetry run python buy_the_dip.py --backtest --period 2y    # 2 years
```

### Advanced Options

```bash
# Use trading days instead of calendar days for rolling window
poetry run python buy_the_dip.py --count-trading-days --backtest

# Check multiple tickers with trading days
poetry run buy-the-dip --tickers QQQ SPY AAPL \
  --check \
  --rolling-window 60 \
  --trigger-pct 0.95 \
  --count-trading-days

# Force fresh data (ignore cache)
poetry run python buy_the_dip.py --ignore-cache --backtest
```

### Calendar Days vs Trading Days

**Default Behavior (Calendar Days)**:
- A 60-day rolling window includes weekends and holidays
- More intuitive for humans ("last 2 months")
- Includes all calendar days in the calculation

**Trading Days Mode** (`--count-trading-days`):
- A 60-day rolling window includes only trading days (Mon-Fri, excluding holidays)
- More precise for market analysis
- Excludes weekends and market holidays

**Example**: For a 60-day window on January 15, 2024:
- **Calendar days**: Looks back to November 16, 2023 (includes weekends)
- **Trading days**: Looks back to October 25, 2023 (only trading days)

**When to use trading days**:
- You want more precise market-based calculations
- You're comparing with other trading systems that use trading days
- You want to exclude the "noise" of weekends and holidays

**Configuration**:
```yaml
# In your config.yaml
use_trading_days: true  # Override with --count-trading-days CLI flag
```

### Cache Management

```bash
# Show cache information
poetry run python buy_the_dip.py --cache-info SPY

# Validate cached data against live API
poetry run python buy_the_dip.py --validate-cache SPY

# Clear cache for specific ticker
poetry run python buy_the_dip.py --clear-cache SPY

# Force fresh data (ignore cache)
poetry run python buy_the_dip.py --ignore-cache --backtest
```

### Try Different Strategies

```bash
# Conservative: 15% drops, $1K monthly
poetry run python buy_the_dip.py --config config_examples/conservative.yaml

# Aggressive: 5% drops, $3K monthly  
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml

# Individual stock: Apple with custom parameters
poetry run python buy_the_dip.py --config config_examples/individual_stock.yaml
```

## ⚙️ Configuration

The strategy is configured via YAML files. For comprehensive configuration guidance, see the [Configuration Guide](CONFIGURATION_GUIDE.md).

### Basic Configuration

```yaml
# config.yaml
ticker: "SPY"                    # Stock/ETF to monitor
rolling_window_days: 90          # Days for rolling maximum calculation
percentage_trigger: 0.90         # Trigger at 90% of rolling max (10% drop)
monthly_dca_amount: 1000.0       # Dollar amount to invest
data_cache_days: 30              # Days to cache price data
use_trading_days: false          # Use calendar days (default) vs trading days
```

### Available Example Configurations

| Configuration | Risk Level | Trigger | Amount | Description |
|---------------|------------|---------|---------|-------------|
| `conservative.yaml` | Low | 15% drops | $1K | Stable, infrequent trading |
| `balanced.yaml` | Medium | 8% drops | $2K | Good balance of risk/reward |
| `aggressive.yaml` | High | 5% drops | $3K | Frequent trading, higher risk |
| `individual_stock.yaml` | High | 12% drops | $1.5K | Single stock (Apple) |
| `dividend_focused.yaml` | Low-Med | 11% drops | $2K | Income-focused ETF |
| `small_cap.yaml` | High | 13% drops | $1.5K | Small-cap growth |
| `crypto_etf.yaml` | Very High | 18% drops | $1K | Bitcoin ETF exposure |

## 💼 How Portfolio Tracking Works

The system maintains a **persistent portfolio** that accumulates investments across multiple program runs. This simulates how a real buy-the-dip strategy would build a portfolio over time.

### Portfolio Persistence

**Investment Storage**: All investments are saved to `~/.buy_the_dip/data/investments.json`
- **Persists across runs**: Your simulated portfolio continues growing between program executions
- **28-day constraint tracking**: The system remembers when you last invested to enforce spacing rules
- **Performance tracking**: Calculate returns based on accumulated investments

### How Investments Are Added

**Daily Evaluation Mode**: Run the strategy on specific dates
```bash
# Evaluate today (defaults to current date)
poetry run python buy_the_dip.py --evaluate

# Or explicitly specify today's date (macOS/Linux)
poetry run python buy_the_dip.py --evaluate $(date +%Y-%m-%d)

# Evaluate a historical date when there was likely a dip
poetry run python buy_the_dip.py --evaluate 2024-03-15
```

**Automatic Mode**: Run the strategy regularly (e.g., daily cron job)
```bash
# Simple cron job - runs daily at 5 PM (after market close)
# Add this to your crontab with: crontab -e
0 17 * * 1-5 cd /path/to/buy-the-dip && poetry run python buy_the_dip.py --evaluate

# Or with explicit date (same result)
0 17 * * 1-5 cd /path/to/buy-the-dip && poetry run python buy_the_dip.py --evaluate $(date +%Y-%m-%d)

# macOS: Use full path to poetry
0 17 * * 1-5 cd /path/to/buy-the-dip && /usr/local/bin/poetry run python buy_the_dip.py --evaluate
```

**Note**: The cron job runs Monday-Friday (1-5) at 5 PM, after market close. Adjust timing based on your timezone and when you want to check for dips.

### Portfolio Status

**Check Current Portfolio**:
```bash
poetry run python buy_the_dip.py --status
```

**Empty Portfolio** (when starting):
```
📊 PORTFOLIO STATUS - SPY
==================================================
No investments found.
```

**Active Portfolio** (after investments):
```
📊 PORTFOLIO STATUS - SPY
==================================================
Current Price: $445.20
Total Invested: $4,000.00
Total Shares: 9.2341
Current Value: $4,620.50
Total Return: $620.50
Percentage Return: 15.51%

💰 RECENT INVESTMENTS (Last 5)
------------------------------
2024-03-15: $1,000.00 at $395.20 = 2.5304 shares
2024-05-22: $1,000.00 at $410.80 = 2.4342 shares
2024-08-18: $1,000.00 at $425.60 = 2.3502 shares
2024-11-02: $1,000.00 at $438.90 = 2.2783 shares
```

### Backtests vs Portfolio

**Important Distinction**:
- **Backtests** (`--backtest`): Temporary simulations that don't affect your persistent portfolio
- **Daily Evaluations** (`--evaluate`): Add investments to your persistent portfolio when conditions are met

**Backtest Example** (doesn't save investments):
```bash
poetry run python buy_the_dip.py --backtest --period 1y
# Shows what would have happened, but doesn't modify your portfolio
```

**Daily Evaluation** (saves investments):
```bash
poetry run python buy_the_dip.py --evaluate 2024-03-15
# If conditions are met, adds investment to your persistent portfolio
```

### Typical Usage Pattern

1. **Start with empty portfolio**: No investments initially
2. **Run daily evaluations**: Check conditions and invest when appropriate
3. **Monitor with --status**: Track your growing portfolio over time
4. **Use backtests for analysis**: Test different strategies without affecting your portfolio

### Managing Your Portfolio

**Reset Portfolio** (start over):
```bash
rm ~/.buy_the_dip/data/investments.json
```

**Backup Portfolio**:
```bash
cp ~/.buy_the_dip/data/investments.json ~/my_portfolio_backup.json
```

**View Portfolio File**:
```bash
cat ~/.buy_the_dip/data/investments.json
```

## 📊 Understanding the Output

### Daily Evaluation Output
```
🎯 EVALUATION RESULT - SPY on 2024-01-15
============================================================
Yesterday's Price: $445.20
Trigger Price: $450.00
Rolling Maximum (90d): $500.00
Trigger Met: ✅ YES
Recent Investment Exists: ❌ NO

🚀 INVESTMENT EXECUTED!
Amount: $1,000.00
Price: $445.20
Shares: 2.2466
```

### Backtest Results
```
🎯 BACKTEST RESULTS - SPY
============================================================
Period: 2023-01-01 to 2024-01-01
Total Trading Days Evaluated: 252
Trigger Conditions Met: 15
Investments Executed: 4
Investments Blocked (28-day rule): 11

📊 PORTFOLIO PERFORMANCE
------------------------------
Total Invested: $4,000.00
Total Shares: 9.2341
Current Value: $4,620.50
Total Return: $620.50
Percentage Return: 15.51%

💰 INVESTMENT HISTORY
------------------------------
2023-03-15: $1,000.00 at $395.20 = 2.5304 shares
2023-05-22: $1,000.00 at $410.80 = 2.4342 shares
2023-08-18: $1,000.00 at $425.60 = 2.3502 shares
2023-11-02: $1,000.00 at $438.90 = 2.2783 shares
```

## 🏗️ Architecture

The system follows a clean, simplified architecture with clear separation of concerns:

### Core Components

- **StrategySystem**: Orchestrates daily evaluation and investment decisions
- **InvestmentTracker**: Manages investment history and enforces 28-day constraints
- **PriceMonitor**: Fetches and caches stock price data with validation
- **ConfigurationManager**: Loads and validates YAML configuration files

### Simplified Data Flow
```
CLI → ConfigurationManager → StrategySystem
                                    ↓
                            PriceMonitor → yfinance API
                                    ↓
                            InvestmentTracker → JSON Storage
```

### Key Simplifications

- **No Complex Sessions**: Eliminated DCA session management for simple daily evaluation
- **Stateless Logic**: Each day is evaluated independently with minimal state
- **28-Day Rule**: Simple constraint checking without complex state tracking
- **Clean Interfaces**: Clear separation between components with minimal coupling

## 🧪 Testing

The system includes comprehensive testing with 233 tests covering all functionality:

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=buy_the_dip --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/          # Unit tests
poetry run pytest tests/property/      # Property-based tests
poetry run pytest tests/integration/   # Integration tests
```

### Test Categories

- **Unit Tests**: Individual component testing with edge cases
- **Property-Based Tests**: Universal correctness guarantees using Hypothesis
- **Integration Tests**: End-to-end workflow validation

### Property-Based Testing

The system uses property-based testing to ensure correctness across all possible inputs:

- **Configuration Properties**: Validation and loading consistency
- **Investment Constraints**: 28-day rule enforcement
- **Price Calculations**: Trigger price accuracy
- **Portfolio Metrics**: Mathematical correctness
- **Persistence**: Round-trip data integrity

## 🛠️ Development

### Code Quality

```bash
# Format code
poetry run black buy_the_dip/ tests/

# Lint code
poetry run flake8 buy_the_dip/ tests/

# Type checking
poetry run mypy buy_the_dip/
```

### Project Structure

```
buy_the_dip/
├── cli/                   # Command-line interface
├── config/               # Configuration management
├── analysis/             # Performance analysis (CAGR)
├── strategy_system.py    # Core strategy logic
├── investment_tracker.py # Investment history and constraints
├── price_monitor/        # Price data fetching and caching
└── models.py            # Shared data models

tests/
├── unit/                # Unit tests
├── property/            # Property-based tests
└── integration/         # End-to-end tests

config_examples/         # Example configurations
```

## 📈 Performance Analysis

The system provides detailed performance metrics:

- **Total Return**: Absolute and percentage returns
- **Portfolio Value**: Current value based on latest prices
- **Investment History**: Complete record of all investments
- **28-Day Constraint Tracking**: Blocked vs executed investments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `poetry run pytest`
5. Run code quality checks: `poetry run black . && poetry run flake8 .`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

This is a trading strategy simulator for educational and research purposes only. It does not execute real trades or provide investment advice. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide
- **[INSTALLATION.md](INSTALLATION.md)** - Detailed installation instructions
- **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Complete configuration reference
- **[EXAMPLES.md](EXAMPLES.md)** - Usage examples and scenarios
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation overview