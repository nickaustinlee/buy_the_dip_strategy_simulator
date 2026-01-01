# Buy the Dip Strategy

A Python-based stock trading strategy simulator that implements a "buy the dip" approach using dollar-cost averaging. The system monitors configurable stock tickers (default: S&P 500 via SPY) and automatically triggers investment when prices drop below a threshold relative to recent highs, continuing until prices recover to the original trigger level.

## 🚀 Features

- **Configurable Strategy Parameters**: Customize ticker symbol, rolling window, trigger percentage, and DCA amount via YAML configuration
- **Price Monitoring**: Real-time price data fetching using yfinance with intelligent caching
- **Dollar-Cost Averaging**: Automated monthly investments during market dips with state machine management
- **Multiple DCA Sessions**: Support for overlapping DCA periods with independent trigger prices
- **State Management**: Persistent storage of strategy state and investment history across sessions
- **Performance Analysis**: Comprehensive CAGR analysis comparing strategy vs buy-and-hold performance
- **CLI Interface**: Easy-to-use command-line interface for running different strategies
- **Robust Error Handling**: Graceful handling of network failures, invalid data, and configuration errors

## 📦 Installation

### Prerequisites
- Python 3.13 or higher
- Poetry (recommended) or pip

### Using Poetry (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd buy-the-dip-strategy
```

2. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies and the package:
```bash
poetry install
```

### Using pip

1. Clone the repository:
```bash
git clone <repository-url>
cd buy-the-dip-strategy
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

## 🎯 Quick Start

### Run with Default Configuration
```bash
# Using Poetry
poetry run python buy_the_dip.py

# Using pip installation
python buy_the_dip.py

# Using installed console script (if available)
buy-the-dip
```

This will:
1. Monitor SPY (S&P 500 ETF) 
2. Calculate 90-day rolling maximum
3. Trigger DCA when price drops to 90% of recent high
4. Invest $2,000 monthly during active periods
5. Display progress and generate performance reports

## 📋 Usage Examples

### Basic Usage

Run the strategy with default configuration:
```bash
poetry run python buy_the_dip.py
```

### Custom Configuration

Run with a custom configuration file:
```bash
poetry run python buy_the_dip.py --config my_config.yaml
```

### Generate Performance Report

Generate a detailed performance report:
```bash
poetry run python buy_the_dip.py --report
```

### Validate Configuration

Validate a configuration file without running the strategy:
```bash
poetry run python buy_the_dip.py --config my_config.yaml --validate-config
```

### Example Configurations

The `config_examples/` directory contains several pre-configured strategies:

#### Conservative Strategy
```bash
poetry run python buy_the_dip.py --config config_examples/conservative.yaml
```
- 180-day rolling window (6 months)
- Triggers on 15% drops
- $1,000 monthly investment

#### Aggressive Strategy  
```bash
poetry run python buy_the_dip.py --config config_examples/aggressive.yaml
```
- 30-day rolling window (1 month)
- Triggers on 5% drops  
- $3,000 monthly investment
- Monitors QQQ (NASDAQ-100)

#### Individual Stock Strategy
```bash
poetry run python buy_the_dip.py --config config_examples/individual_stock.yaml
```
- 60-day rolling window (2 months)
- Triggers on 12% drops
- $1,500 monthly investment
- Monitors AAPL (Apple stock)

## ⚙️ Configuration

The strategy is configured via YAML files. The default configuration is in `config.yaml`.

### Configuration Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `ticker` | string | Any valid ticker | "SPY" | Stock ticker symbol to monitor |
| `rolling_window_days` | integer | 1-365 | 90 | Days for rolling maximum calculation |
| `percentage_trigger` | float | 0.0-1.0 | 0.90 | Percentage of rolling max that triggers DCA |
| `monthly_dca_amount` | float | > 0.0 | 2000.0 | Monthly dollar amount for investments |
| `data_cache_days` | integer | ≥ 1 | 30 | Days to cache price data locally |

### Example Configuration

```yaml
# Monitor the S&P 500
ticker: "SPY"

# Use 3-month rolling window  
rolling_window_days: 90

# Trigger on 10% drops
percentage_trigger: 0.90

# Invest $2,000 monthly
monthly_dca_amount: 2000.0

# Cache data for 30 days
data_cache_days: 30
```

### Configuration Tips

**Rolling Window Selection:**
- **30 days**: More sensitive, catches short-term dips
- **90 days**: Balanced approach (recommended)
- **180+ days**: Less sensitive, focuses on major corrections

**Trigger Percentage Selection:**
- **0.95 (5% drop)**: Very aggressive, frequent triggers
- **0.90 (10% drop)**: Balanced approach (recommended)
- **0.85 (15% drop)**: Conservative, major dips only
- **0.80 (20% drop)**: Very conservative, crash scenarios

**Ticker Selection:**
- **SPY**: S&P 500, broad market exposure
- **QQQ**: NASDAQ-100, tech-heavy, more volatile
- **VTI**: Total stock market, maximum diversification
- **Individual stocks**: Higher risk/reward, more volatile

## 📊 Understanding the Output

### Strategy Execution Output
```
Buy the Dip Strategy Starting...
Configuration: SPY, 90-day window, 90% trigger, $2000/month
Current Price: $450.25
Rolling Max (90d): $475.30
Trigger Price: $427.77
Status: MONITORING (price above trigger)

[Price Update] SPY: $425.50 (Drop detected: -10.5%)
🔥 DCA ACTIVATED! Starting session: dca_20241201_001
Target: Invest $2000/month until price recovers to $427.77

[Investment] Session dca_20241201_001: $2000 → 4.70 shares @ $425.50
Portfolio: $2000 invested, 4.70 shares, Value: $2001.35 (+0.07%)
```

### Performance Report Output
```
=== Buy the Dip Strategy Performance Report ===

Analysis Period: 2023-01-01 to 2024-12-01 (335 days)
First Investment: 2023-03-15 (74 days after start)

📈 CAGR Analysis:
Full Period (335 days):
  Strategy CAGR: 12.5%
  Buy & Hold CAGR: 8.2%
  Outperformance: +4.3%

Active Period (261 days):  
  Strategy CAGR: 15.8%
  Buy & Hold CAGR: 9.1%
  Outperformance: +6.7%

💰 Investment Summary:
  Total Invested: $24,000
  Total Shares: 52.3
  Current Value: $26,950
  Total Return: +12.3%
  
🎯 Strategy Effectiveness:
  DCA Sessions: 3 completed, 1 active
  Average Session Duration: 4.2 months
  Opportunity Cost: -1.2% (cost of waiting for dips)
```

## 🏗️ Architecture

The system follows a modular architecture with clear separation of concerns:

### Core Components

- **Configuration Manager**: Loads and validates YAML configuration files using Pydantic
- **Price Monitor**: Fetches stock price data via yfinance with intelligent caching
- **DCA Controller**: Manages dollar-cost averaging sessions using state machine pattern
- **Strategy Engine**: Orchestrates the overall trading strategy and coordinates components
- **State Manager**: Handles persistent storage of strategy state and investment history
- **CAGR Analysis Engine**: Calculates performance metrics and comparisons
- **CLI Interface**: Provides command-line interaction and reporting

### Data Flow
```
CLI → Config Manager → Strategy Engine → Price Monitor → yfinance API
                           ↓
                    DCA Controller → State Manager → JSON Storage
                           ↓
                    CAGR Analysis → Performance Reports
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=buy_the_dip --cov-report=html

# Run specific test categories
poetry run pytest tests/unit/          # Unit tests
poetry run pytest tests/property/      # Property-based tests  
poetry run pytest tests/integration/   # Integration tests

# Run tests with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/test_strategy_engine.py
```

### Code Quality

```bash
# Format code with Black
poetry run black buy_the_dip/ tests/

# Lint code with flake8
poetry run flake8 buy_the_dip/ tests/

# Type checking with mypy
poetry run mypy buy_the_dip/

# Run all quality checks
poetry run black buy_the_dip/ tests/ && poetry run flake8 buy_the_dip/ tests/ && poetry run mypy buy_the_dip/
```

### Project Structure

```
buy_the_dip/
├── analysis/           # CAGR analysis and performance metrics
├── cli/               # Command-line interface
├── config/            # Configuration management and models
├── dca_controller/    # Dollar-cost averaging logic
├── persistence/       # State management and data storage
├── price_monitor/     # Price data fetching and caching
├── strategy_engine/   # Core strategy orchestration
└── models.py         # Shared data models

tests/
├── unit/             # Unit tests for individual components
├── property/         # Property-based tests using Hypothesis
└── integration/      # End-to-end integration tests

config_examples/      # Example configuration files
├── conservative.yaml
├── aggressive.yaml
└── individual_stock.yaml
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `poetry run pytest`
5. Run code quality checks: `poetry run black . && poetry run flake8 . && poetry run mypy buy_the_dip/`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

This is a trading strategy simulator for educational and research purposes only. It does not execute real trades or provide investment advice. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.