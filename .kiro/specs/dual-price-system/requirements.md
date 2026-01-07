# Requirements Document

## Introduction

Enhancement to the buy-the-dip strategy system to support dual price types: Close prices for trading decisions and Adjusted Close prices for performance analysis. This addresses the need for accurate dip detection (using real market prices) while enabling fair performance comparisons that account for dividends and other corporate actions.

## Glossary

- **Price_Monitor**: Component that fetches and manages stock price data
- **Close_Price**: The actual closing price of a stock on a trading day (includes split adjustments)
- **Adjusted_Close_Price**: The closing price adjusted for splits, dividends, and other corporate actions
- **Trading_Logic**: Components that make buy/sell decisions based on price movements
- **Performance_Analysis**: Components that calculate returns and compare performance over time
- **Total_Return**: Investment return including both price appreciation and dividend income
- **Price_Return**: Investment return from price changes only (excludes dividends)

## Requirements

### Requirement 1: Dual Price Data Fetching

**User Story:** As a price monitor, I want to fetch both Close and Adjusted Close prices, so that I can support both trading decisions and performance analysis.

#### Acceptance Criteria

1. WHEN fetching price data from Yahoo Finance, THE Price_Monitor SHALL retrieve both Close and Adjusted Close prices
2. THE Price_Monitor SHALL store both price types in the cache with clear identification
3. WHEN cached data exists, THE Price_Monitor SHALL return both price types from cache
4. WHEN merging new and cached data, THE Price_Monitor SHALL handle both price columns correctly
5. THE Price_Monitor SHALL maintain backward compatibility with existing cache files

### Requirement 2: Trading Decision Price Interface

**User Story:** As a trading system, I want to use Close prices for all buy/sell decisions, so that I react to real market price movements.

#### Acceptance Criteria

1. WHEN calculating trigger prices, THE Strategy_System SHALL use Close prices only
2. WHEN calculating rolling maximums for dip detection, THE Strategy_System SHALL use Close prices only
3. WHEN determining current market price for purchases, THE Strategy_System SHALL use Close prices only
4. WHEN evaluating if yesterday's price triggered a buy condition, THE Strategy_System SHALL use Close prices only
5. THE Strategy_System SHALL continue to use Close prices for all existing trading logic

### Requirement 3: Performance Analysis Price Interface

**User Story:** As a performance analyzer, I want to use Adjusted Close prices for return calculations, so that I can provide fair comparisons that include dividend effects.

#### Acceptance Criteria

1. WHEN calculating total return over a period, THE Performance_Analyzer SHALL use Adjusted Close prices
2. WHEN comparing performance against benchmarks like SPY, THE Performance_Analyzer SHALL use Adjusted Close prices for both
3. WHEN calculating annualized returns, THE Performance_Analyzer SHALL use Adjusted Close prices
4. WHEN displaying historical performance charts, THE Performance_Analyzer SHALL use Adjusted Close prices
5. THE Performance_Analyzer SHALL clearly indicate when returns include dividend effects

### Requirement 4: Price Type Method Separation

**User Story:** As a developer, I want clear method names that indicate which price type is being used, so that I can avoid confusion and bugs.

#### Acceptance Criteria

1. THE Price_Monitor SHALL provide separate methods for Close and Adjusted Close price retrieval
2. WHEN requesting closing prices for trading, THE Price_Monitor SHALL provide a method that returns Close prices
3. WHEN requesting adjusted prices for analysis, THE Price_Monitor SHALL provide a method that returns Adjusted Close prices
4. THE Price_Monitor SHALL maintain existing method names for backward compatibility
5. THE Price_Monitor SHALL add new methods with clear naming conventions for adjusted prices

### Requirement 5: Cache Storage Enhancement

**User Story:** As a price monitor, I want to efficiently cache both price types, so that I minimize API calls while supporting dual functionality.

#### Acceptance Criteria

1. WHEN saving price data to cache, THE Price_Monitor SHALL store both Close and Adjusted Close columns
2. WHEN loading cached data, THE Price_Monitor SHALL retrieve both price types if available
3. WHEN cached data contains only Close prices (legacy), THE Price_Monitor SHALL handle gracefully and fetch Adjusted Close as needed
4. THE Price_Monitor SHALL maintain cache file format compatibility with existing installations
5. THE Price_Monitor SHALL optimize storage to avoid data duplication

### Requirement 6: Performance Reporting Enhancement

**User Story:** As an investor, I want to see both price-only and total returns, so that I can understand the full impact of my investment including dividends.

#### Acceptance Criteria

1. WHEN displaying performance metrics, THE Strategy_System SHALL show both price return and total return
2. WHEN calculating price return, THE Strategy_System SHALL use Close prices (current behavior)
3. WHEN calculating total return, THE Strategy_System SHALL use Adjusted Close prices
4. THE Strategy_System SHALL clearly label which return type includes dividends
5. WHEN comparing against benchmarks, THE Strategy_System SHALL use total return (Adjusted Close) for fair comparison

### Requirement 7: Configuration Compatibility

**User Story:** As a user, I want the dual price system to work with my existing configuration, so that I don't need to change my setup.

#### Acceptance Criteria

1. THE Strategy_System SHALL continue to work with existing YAML configurations without changes
2. THE Strategy_System SHALL maintain all existing CLI arguments and behavior
3. WHEN users run existing commands, THE Strategy_System SHALL produce the same trading decisions as before
4. THE Strategy_System SHALL add new performance analysis features without breaking existing functionality
5. THE Strategy_System SHALL provide clear documentation about which metrics use which price type

### Requirement 8: Data Migration Support

**User Story:** As an existing user, I want my cached price data to be enhanced with Adjusted Close prices, so that I can benefit from improved performance analysis.

#### Acceptance Criteria

1. WHEN loading legacy cache files with only Close prices, THE Price_Monitor SHALL detect the missing Adjusted Close data
2. WHEN Adjusted Close data is missing, THE Price_Monitor SHALL fetch it from Yahoo Finance for the cached date range
3. WHEN updating legacy cache files, THE Price_Monitor SHALL add Adjusted Close data while preserving existing Close data
4. THE Price_Monitor SHALL handle this migration transparently without user intervention
5. THE Price_Monitor SHALL log the migration process for user awareness