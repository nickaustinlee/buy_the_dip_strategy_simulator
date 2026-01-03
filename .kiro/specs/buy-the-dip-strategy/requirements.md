# Requirements Document

## Introduction

A Python-based stock trading strategy that implements a simplified "buy the dip" approach. The system evaluates each trading day independently, checking if yesterday's closing price was at or below a dynamically calculated trigger price. When conditions are met and no investment has been made in the past 27 days (allowing same weekday pattern with 28-day spacing), it executes a buy at the closing price.

## Glossary

- **Strategy_System**: The core system that executes the buy-the-dip trading strategy
- **Price_Monitor**: Component that fetches and manages stock price data
- **Configuration_Manager**: Component that loads and validates YAML configuration files
- **Trigger_Price**: Daily calculated price level (rolling_maximum * percentage_trigger)
- **Rolling_Maximum**: The maximum closing price over the trailing window days
- **Percentage_Trigger**: The threshold percentage of rolling maximum that triggers buying
- **Monthly_DCA_Amount**: The fixed dollar amount invested when conditions are met
- **Stock_Ticker**: The stock symbol to monitor
- **Rolling_Window_Days**: Number of trailing days for calculating rolling maximum
- **Data_Cache_Days**: Number of days to cache price data locally

## Requirements

### Requirement 1: YAML Configuration Management

**User Story:** As a user, I want to configure strategy parameters via YAML files, so that I can easily customize the trading strategy.

#### Acceptance Criteria

1. THE Configuration_Manager SHALL load ticker symbol from YAML configuration
2. THE Configuration_Manager SHALL load rolling_window_days from YAML configuration  
3. THE Configuration_Manager SHALL load percentage_trigger from YAML configuration
4. THE Configuration_Manager SHALL load monthly_dca_amount from YAML configuration
5. THE Configuration_Manager SHALL load data_cache_days from YAML configuration
6. WHEN a configuration file is invalid or missing required fields, THE Configuration_Manager SHALL use default values and log warnings
7. THE Configuration_Manager SHALL validate that percentage_trigger is between 0.0 and 1.0
8. THE Configuration_Manager SHALL validate that rolling_window_days is a positive integer
9. THE Configuration_Manager SHALL validate that monthly_dca_amount is positive

### Requirement 2: Price Data Management

**User Story:** As a strategy system, I want to fetch and cache stock price data, so that I can perform daily evaluations efficiently.

#### Acceptance Criteria

1. WHEN the system needs price data, THE Price_Monitor SHALL fetch closing prices using yfinance
2. THE Price_Monitor SHALL cache price data locally for the configured cache duration
3. WHEN cached data is available and fresh, THE Price_Monitor SHALL use cached data instead of fetching
4. WHEN price data is unavailable for a specific date, THE Price_Monitor SHALL handle the error gracefully
5. THE Price_Monitor SHALL return daily closing prices for requested date ranges

### Requirement 3: Daily Trigger Price Calculation

**User Story:** As a strategy system, I want to calculate the trigger price daily, so that I can determine when buying conditions are met.

#### Acceptance Criteria

1. WHEN evaluating a trading day, THE Strategy_System SHALL calculate the rolling maximum over the trailing window days
2. WHEN calculating rolling maximum, THE Strategy_System SHALL use closing prices only
3. WHEN the rolling maximum is calculated, THE Strategy_System SHALL compute trigger price as rolling_maximum * percentage_trigger
4. THE Strategy_System SHALL recalculate the trigger price fresh each trading day
5. WHEN insufficient historical data exists for the full window, THE Strategy_System SHALL use available data

### Requirement 4: Daily Buy Decision Logic

**User Story:** As a strategy system, I want to evaluate buy conditions each trading day, so that I can execute investments when the strategy criteria are met.

#### Acceptance Criteria

1. WHEN evaluating a trading day, THE Strategy_System SHALL check if yesterday's closing price is less than or equal to the trigger price
2. WHEN yesterday's closing price meets the trigger condition, THE Strategy_System SHALL check if any investment was made in the past 28 days
2. WHEN no investment was made in the past 27 days AND trigger condition is met, THE Strategy_System SHALL execute a buy
4. WHEN a buy is executed, THE Strategy_System SHALL use the current day's closing price
5. WHEN a buy is executed, THE Strategy_System SHALL invest exactly the monthly_dca_amount
6. THE Strategy_System SHALL evaluate each trading day independently

### Requirement 5: Investment Constraint Enforcement

**User Story:** As a strategy system, I want to enforce the 28-day investment limit, so that investments are properly spaced and the investor cannot double up.

#### Acceptance Criteria

1. WHEN checking investment eligibility, THE Strategy_System SHALL examine all investments in the past 27 calendar days (exclusive of the 28th day)
2. WHEN any investment exists within the past 27 days, THE Strategy_System SHALL prevent new investments
3. WHEN no investments exist within the past 27 days, THE Strategy_System SHALL allow new investments if other conditions are met
4. THE Strategy_System SHALL use calendar days (not trading days) for the 28-day calculation
5. THE Strategy_System SHALL maintain this constraint as an invariant across all operations
6. WHEN an investment was made exactly 28 days ago, THE Strategy_System SHALL allow a new investment (enabling same weekday pattern)

### Requirement 6: Investment Execution and Logging

**User Story:** As an investor, I want my investments to be executed and logged properly, so that I can track my strategy performance.

#### Acceptance Criteria

1. WHEN executing a buy, THE Strategy_System SHALL record the date of investment
2. WHEN executing a buy, THE Strategy_System SHALL record the closing price used
3. WHEN executing a buy, THE Strategy_System SHALL record the dollar amount invested
4. WHEN executing a buy, THE Strategy_System SHALL calculate and record the number of shares purchased
5. THE Strategy_System SHALL log each investment immediately when executed
6. THE Strategy_System SHALL maintain a complete history of all investments

### Requirement 7: Data Persistence

**User Story:** As a user, I want my investment history to be saved, so that the system can enforce the 28-day constraint across sessions.

#### Acceptance Criteria

1. WHEN an investment is made, THE Strategy_System SHALL persist the investment record immediately
2. WHEN the system starts, THE Strategy_System SHALL load previous investment history
3. WHEN checking the 28-day constraint, THE Strategy_System SHALL use persisted investment history
4. WHEN state files are corrupted or missing, THE Strategy_System SHALL initialize with empty history and log the issue

### Requirement 8: Performance Reporting

**User Story:** As an investor, I want to see my strategy performance, so that I can evaluate the effectiveness of the buy-the-dip approach.

#### Acceptance Criteria

1. THE Strategy_System SHALL calculate total amount invested across all investments
2. THE Strategy_System SHALL calculate total shares owned across all investments  
3. THE Strategy_System SHALL calculate current portfolio value using latest closing price
4. THE Strategy_System SHALL calculate total return as current value minus total invested
5. THE Strategy_System SHALL calculate percentage return as total return divided by total invested
6. WHEN no investments have been made, THE Strategy_System SHALL report zero for all metrics