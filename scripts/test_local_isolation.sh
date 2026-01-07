#!/bin/bash
set -e

echo "🧪 Local Python Compatibility Testing with Isolation"
echo "===================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create a temporary directory for test environments
TEST_DIR=$(mktemp -d)
echo -e "${BLUE}📁 Using temporary directory: ${TEST_DIR}${NC}"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up test environments...${NC}"
    rm -rf "${TEST_DIR}"
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Function to test with current Python
test_current_python() {
    echo -e "\n${YELLOW}🐍 Testing with current Python version...${NC}"
    
    # Create isolated virtual environment
    local venv_dir="${TEST_DIR}/test_env"
    python3 -m venv "${venv_dir}"
    
    # Activate virtual environment
    source "${venv_dir}/bin/activate"
    
    echo -e "${BLUE}Python version: $(python --version)${NC}"
    
    # Install the package in development mode
    pip install -e .
    
    # Run compatibility test
    echo -e "${BLUE}Running compatibility test...${NC}"
    if python scripts/test_compatibility.py; then
        echo -e "${GREEN}✅ Compatibility test passed${NC}"
    else
        echo -e "${RED}❌ Compatibility test failed${NC}"
        deactivate
        return 1
    fi
    
    # Run a subset of unit tests
    echo -e "${BLUE}Running sample unit tests...${NC}"
    pip install pytest hypothesis
    if python -m pytest tests/unit/test_strategy_system.py -v --tb=short; then
        echo -e "${GREEN}✅ Unit tests passed${NC}"
    else
        echo -e "${RED}❌ Unit tests failed${NC}"
        deactivate
        return 1
    fi
    
    # Test CLI
    echo -e "${BLUE}Testing CLI functionality...${NC}"
    if buy-the-dip --help > /dev/null; then
        echo -e "${GREEN}✅ CLI test passed${NC}"
    else
        echo -e "${RED}❌ CLI test failed${NC}"
        deactivate
        return 1
    fi
    
    deactivate
    return 0
}

# Function to test with Poetry (if available)
test_with_poetry() {
    if command -v poetry &> /dev/null; then
        echo -e "\n${YELLOW}📦 Testing with Poetry...${NC}"
        
        # Create a separate Poetry environment
        local poetry_dir="${TEST_DIR}/poetry_test"
        mkdir -p "${poetry_dir}"
        cp pyproject.toml poetry.lock "${poetry_dir}/" 2>/dev/null || true
        cp -r buy_the_dip tests scripts "${poetry_dir}/"
        
        cd "${poetry_dir}"
        
        # Install dependencies
        poetry install --with test,dev
        
        # Run tests
        echo -e "${BLUE}Running Poetry-based tests...${NC}"
        if poetry run python scripts/test_compatibility.py; then
            echo -e "${GREEN}✅ Poetry compatibility test passed${NC}"
        else
            echo -e "${RED}❌ Poetry compatibility test failed${NC}"
            cd - > /dev/null
            return 1
        fi
        
        cd - > /dev/null
        return 0
    else
        echo -e "${YELLOW}⚠️  Poetry not found, skipping Poetry test${NC}"
        return 0
    fi
}

# Main execution
echo -e "${BLUE}Starting isolated compatibility tests...${NC}"

FAILED_TESTS=()

# Test current Python
if ! test_current_python; then
    FAILED_TESTS+=("current_python")
fi

# Test with Poetry
if ! test_with_poetry; then
    FAILED_TESTS+=("poetry")
fi

# Summary
echo -e "\n${YELLOW}📊 TEST SUMMARY${NC}"
echo "================"

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo -e "${GREEN}✅ Your current Python environment is compatible${NC}"
    echo -e "${BLUE}💡 Ready for PyPI publication with python = \"^3.11\"${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "${RED}  - ${test}${NC}"
    done
    echo -e "${YELLOW}⚠️  Check the output above for details${NC}"
    exit 1
fi