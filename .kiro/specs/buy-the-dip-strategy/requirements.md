# Requirements Document

## Introduction

A Python-based stock trading strategy simulator that implements a "buy the dip" approach using dollar-cost averaging. The system monitors the S&P 500 (via SPY proxy) and automatically triggers investment when prices drop below a configurable threshold, continuing until prices recover to the original trigger level.

## Glossary

- **Strategy_Engine**: The core system that executes the buy-the-dip trading strategy
- **Price_Monitor**: Component that tracks and analyzes stock price movements
- **DCA_Controller**: Component that manages dollar-cost averaging investments
- **Configuration_Manager**: Component that loads and validates YAML configuration files
- **CLI_Interface**: Command-line interface for running the strategy with different configurations
- **Trigger_Price**: The price level that activates the buying strategy (max_price * percentage_trigger)
- **Max_Price_Window**: The rolling maximum price over a configurable number of days (default 90)
- **Percentage_Trigger**: The threshold percentage below max price that triggers buying (default 90%)
- **DCA_Rate**: The monthly dollar amount for dollar-cost averaging (default $2000)
- **Stock_Ticker**: The stock symbol to monitor (default "SPY")

## Requirements

### Requirement 1: Price Data Collection

**User Story:** As a strategy analyst, I want to collect historical and current stock price data, so that I can monitor market movements and identify buying opportunities.

#### Acceptance Criteria

1. WHEN the system starts, THE Price_Monitor SHALL fetch SPY price data using yfinance
2. WHEN price data is requested for a date range, THE Price_Monitor SHALL return daily closing prices
3. WHEN price data is unavailable for a specific date, THE Price_Monitor SHALL handle the error gracefully
4. THE Price_Monitor SHALL cache price data to minimize API calls

### Requirement 2: Rolling Maximum Price Tracking

**User Story:** As a strategy analyst, I want to track the maximum price over a rolling window, so that I can identify when prices have dropped significantly from recent highs.

#### Acceptance Criteria

1. WHEN new price data is available, THE Price_Monitor SHALL calculate the rolling maximum over the specified window (default 90 days)
2. WHEN the window size is configured, THE Price_Monitor SHALL use the new window size for all subsequent calculations
3. THE Price_Monitor SHALL maintain the rolling maximum efficiently as new data arrives
4. WHEN insufficient historical data exists, THE Price_Monitor SHALL use available data and indicate the limitation

### Requirement 3: Trigger Price Detection

**User Story:** As a strategy analyst, I want to detect when prices drop below the trigger threshold, so that I can initiate the buying strategy.

#### Acceptance Criteria

1. WHEN the current price drops below the trigger price (max_price * percentage_trigger), THE Strategy_Engine SHALL activate the DCA strategy
2. WHEN the percentage trigger is configured, THE Strategy_Engine SHALL recalculate all trigger prices using the new percentage
3. THE Strategy_Engine SHALL continuously monitor for trigger conditions on each price update
4. WHEN multiple trigger conditions occur simultaneously, THE Strategy_Engine SHALL handle them in chronological order

### Requirement 4: Dollar-Cost Averaging Execution

**User Story:** As an investor, I want to automatically invest a fixed amount monthly when the strategy is active, so that I can systematically build my position during market dips.

#### Acceptance Criteria

1. WHEN the DCA strategy is active, THE DCA_Controller SHALL simulate monthly investments at the configured rate
2. WHEN the DCA rate is configured, THE DCA_Controller SHALL use the new rate for all subsequent investments
3. THE DCA_Controller SHALL track the total amount invested and shares purchased during each DCA period
4. WHEN calculating share purchases, THE DCA_Controller SHALL use the closing price on the investment date

### Requirement 5: Strategy Deactivation

**User Story:** As a strategy analyst, I want the buying strategy to stop when prices recover, so that I don't continue investing when the dip opportunity has passed.

#### Acceptance Criteria

1. WHEN the current price reaches or exceeds the original trigger price, THE Strategy_Engine SHALL deactivate the DCA strategy
2. WHEN the strategy deactivates, THE Strategy_Engine SHALL continue monitoring for new trigger conditions
3. THE Strategy_Engine SHALL maintain separate trigger prices for multiple overlapping DCA periods
4. WHEN the rolling maximum increases, THE Strategy_Engine SHALL update trigger calculations for future activations

### Requirement 6: YAML Configuration Management

**User Story:** As a user, I want to configure strategy parameters via YAML files, so that I can easily customize and version control different trading strategies.

#### Acceptance Criteria

1. THE Configuration_Manager SHALL load strategy parameters from YAML configuration files
2. THE Configuration_Manager SHALL support configuration for stock ticker symbol (default "SPY")
3. THE Configuration_Manager SHALL support configuration for rolling window days (default 90)
4. THE Configuration_Manager SHALL support configuration for percentage trigger (default 0.90)
5. THE Configuration_Manager SHALL support configuration for monthly DCA rate (default $2000)
6. WHEN a configuration file is invalid or missing required fields, THE Configuration_Manager SHALL use default values and log warnings
7. THE Configuration_Manager SHALL validate configuration values are within reasonable ranges

### Requirement 7: CLI Interface

**User Story:** As a user, I want to run the strategy with different configuration files via command line, so that I can easily test different scenarios and manage multiple strategies.

#### Acceptance Criteria

1. THE CLI_Interface SHALL accept a configuration file path as a command line argument
2. WHEN no configuration file is specified, THE CLI_Interface SHALL use a default configuration file
3. THE CLI_Interface SHALL validate that the specified configuration file exists before starting
4. THE CLI_Interface SHALL display current configuration parameters when starting the strategy
5. WHEN configuration file path is invalid, THE CLI_Interface SHALL display an error message and exit gracefully

### Requirement 8: Investment Tracking and Reporting

**User Story:** As an investor, I want to track my simulated investments and performance, so that I can evaluate the strategy's effectiveness.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL maintain a record of all simulated purchases including date, price, and shares
2. THE Strategy_Engine SHALL calculate total invested amount and total shares owned
3. THE Strategy_Engine SHALL calculate current portfolio value based on latest prices
4. THE Strategy_Engine SHALL provide performance metrics including total return and percentage gain/loss

### Requirement 9: Data Persistence

**User Story:** As a user, I want my strategy state and investment history to be saved, so that I can resume monitoring and analysis across sessions.

#### Acceptance Criteria

1. WHEN the system shuts down, THE Strategy_Engine SHALL save current state to persistent storage
2. WHEN the system starts, THE Strategy_Engine SHALL restore previous state from persistent storage
3. THE Strategy_Engine SHALL save investment transactions immediately when they occur
4. WHEN state files are corrupted or missing, THE Strategy_Engine SHALL initialize with default state and log the issue

### Requirement 10: CAGR Performance Analysis

**User Story:** As an analyst, I want to compare strategy performance using CAGR metrics over different time periods, so that I can make fair apples-to-apples comparisons between my buy-the-dip strategy and buy-and-hold baseline.

#### Acceptance Criteria

1. THE Strategy_Engine SHALL calculate full-period CAGR for both strategy and buy-and-hold over the entire analysis timespan
2. THE Strategy_Engine SHALL calculate active-period CAGR for both strategy and buy-and-hold from first investment date to end date
3. WHEN no investments have been made, THE Strategy_Engine SHALL return zero strategy CAGR and full buy-and-hold CAGR
4. THE Strategy_Engine SHALL provide CAGR comparison metrics including strategy outperformance and opportunity cost analysis
5. THE Strategy_Engine SHALL support CAGR calculations for custom date ranges specified by the user