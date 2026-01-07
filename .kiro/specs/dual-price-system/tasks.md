# Implementation Plan: Dual Price System

## Overview

Simple implementation to add Adjusted Close price support for performance analysis. The approach: fetch both Close and Adj Close from Yahoo Finance, use Close for trading decisions (unchanged), use Adj Close for performance comparisons.

## Tasks

- [x] 1. Update PriceMonitor to fetch both Close and Adj Close
  - Change `data[["Close"]]` to `data[["Close", "Adj Close"]]` in fetch methods
  - Update cache to store both columns
  - Clear existing cache to avoid compatibility issues
  - _Requirements: 1.1, 1.2_

- [x] 1.1 Write basic tests for dual price fetching
  - Test that both price columns are fetched and cached
  - **Validates: Requirements 1.1, 1.2**

- [x] 2. Add method to get Adjusted Close prices
  - Add `get_adjusted_closing_prices()` method that returns Adj Close column
  - Keep all existing methods unchanged (they return Close prices)
  - _Requirements: 4.1, 4.3_

- [x] 2.1 Write tests for adjusted price method
  - Test that new method returns Adj Close prices
  - Test that existing methods still return Close prices
  - **Validates: Requirements 4.1, 4.3**

- [x] 3. Update performance reporting to use Adjusted Close
  - Modify performance calculations in strategy system to use Adj Close for total return
  - Keep existing price-only return using Close prices
  - Show both returns in output with clear labels
  - _Requirements: 3.1, 6.1, 6.3_

- [x] 3.1 Write tests for performance calculations
  - Test that total return uses Adj Close prices
  - Test that price return uses Close prices
  - **Validates: Requirements 3.1, 6.1, 6.3**

- [x] 4. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- This is a simple enhancement: just add Adj Close column and use it for performance analysis
- Trading logic remains completely unchanged (uses Close prices)
- Cache will be cleared to avoid migration complexity
- The core change is literally just adding one more column from Yahoo Finance