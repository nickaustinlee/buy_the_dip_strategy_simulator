#!/bin/bash
# Test notification script

echo "Testing Buy the Dip notifications..."
echo ""
echo "Test 1: Multi-ticker check with notification"
poetry run buy-the-dip --tickers AAPL --check --rolling-window 30 --trigger-pct 0.95 --notify

echo ""
echo "Test 2: Single ticker check with notification"
poetry run buy-the-dip --config config.yaml --check --notify

echo ""
echo "Done! Did you see the notifications?"
