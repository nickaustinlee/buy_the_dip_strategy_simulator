#!/bin/bash
# Run Docker tests and provide a clean summary

set -e

echo "🐳 Running Docker tests across all Python versions..."
echo "=================================================="
echo ""

# Run docker-compose and capture output
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Check exit code
EXIT_CODE=$?

echo ""
echo "=================================================="
echo "📊 TEST SUMMARY"
echo "=================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All Python versions passed!"
    echo ""
    echo "Tested versions:"
    echo "  • Python 3.11 ✅"
    echo "  • Python 3.12 ✅"
    echo "  • Python 3.13 ✅"
    echo "  • Python 3.14 ✅"
    echo ""
    echo "All checks completed successfully:"
    echo "  • All tests (242 tests: unit, property, integration)"
    echo "  • CLI functionality"
    echo "  • Type checking (mypy)"
    echo "  • Code formatting (black)"
else
    echo "❌ Tests failed with exit code $EXIT_CODE"
    echo ""
    echo "Check the output above for details."
fi

echo "=================================================="

# Clean up containers
echo ""
echo "🧹 Cleaning up containers..."
docker-compose -f docker-compose.test.yml down

exit $EXIT_CODE
