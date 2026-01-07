#!/bin/bash
set -e

echo "🐳 Testing Buy-the-Dip Strategy across Python versions using Docker"
echo "=================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests for a specific Python version
test_python_version() {
    local version=$1
    echo -e "\n${YELLOW}🐍 Testing Python ${version}...${NC}"
    
    if docker-compose -f docker-compose.test.yml run --rm test-python-${version}; then
        echo -e "${GREEN}✅ Python ${version} tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ Python ${version} tests FAILED${NC}"
        return 1
    fi
}

# Function to cleanup Docker resources
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up Docker resources...${NC}"
    docker-compose -f docker-compose.test.yml down --volumes --remove-orphans
    docker system prune -f
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Build all test images first
echo -e "${YELLOW}🔨 Building test images...${NC}"
docker-compose -f docker-compose.test.yml build

# Test each Python version
FAILED_VERSIONS=()

for version in "3-11" "3-12" "3-13"; do
    if ! test_python_version $version; then
        FAILED_VERSIONS+=($version)
    fi
done

# Summary
echo -e "\n${YELLOW}📊 TEST SUMMARY${NC}"
echo "================"

if [ ${#FAILED_VERSIONS[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All Python versions passed!${NC}"
    echo -e "${GREEN}✅ Python 3.11, 3.12, 3.13 are all compatible${NC}"
    exit 0
else
    echo -e "${RED}❌ Some versions failed:${NC}"
    for version in "${FAILED_VERSIONS[@]}"; do
        echo -e "${RED}  - Python ${version}${NC}"
    done
    exit 1
fi