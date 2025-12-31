# Buy the Dip Strategy

A Python-based stock trading strategy simulator that implements a "buy the dip" approach using dollar-cost averaging. The system monitors the S&P 500 (via SPY proxy) and automatically triggers investment when prices drop below a configurable threshold, continuing until prices recover to the original trigger level.

## Features

- **Configurable Strategy Parameters**: Customize ticker symbol, rolling window, trigger percentage, and DCA amount via YAML configuration
- **Price Monitoring**: Real-time price data fetching using yfinance with intelligent caching
- **Dollar-Cost Averaging**: Automated monthly investments during market dips
- **State Management**: Persistent storage of strategy state and investment history
- **Performance Reporting**: Comprehensive reporting of investment performance and metrics
- **CLI Interface**: Easy-to-use command-line interface for running different strategies

## Installation

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

## Usage

### Basic Usage

Run the strategy with default configuration:
```bash
poetry run python buy_the_dip.py
# or using the installed script
poetry run buy-the-dip
```

### Custom Configuration

Run with a custom configuration file:
```bash
poetry run python buy_the_dip.py --config my_config.yaml
# or
poetry run buy-the-dip --config my_config.yaml
```

### Generate Report

Generate a performance report:
```bash
poetry run python buy_the_dip.py --report
# or
poetry run buy-the-dip --report
```

### Validate Configuration

Validate a configuration file:
```bash
poetry run python buy_the_dip.py --config my_config.yaml --validate-config
# or
poetry run buy-the-dip --config my_config.yaml --validate-config
```

## Configuration

The strategy is configured via YAML files. See `config.yaml` for the default configuration with documentation for each parameter.

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=buy_the_dip

# Run property-based tests only
poetry run pytest tests/property/

# Run unit tests only
poetry run pytest tests/unit/
```

### Code Quality

```bash
# Format code
poetry run black buy_the_dip/ tests/

# Lint code
poetry run flake8 buy_the_dip/ tests/

# Type checking
poetry run mypy buy_the_dip/
```

## Architecture

The system follows a modular architecture with the following components:

- **Configuration Manager**: Loads and validates YAML configuration files
- **Price Monitor**: Fetches and analyzes stock price data
- **DCA Controller**: Manages dollar-cost averaging sessions
- **Strategy Engine**: Orchestrates the overall trading strategy
- **CLI Interface**: Provides command-line interaction

## License

MIT License - see LICENSE file for details.