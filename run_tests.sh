#!/bin/bash

# Deribit Server Testing Suite
# Comprehensive testing script for Deribit API connectivity

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

print_header() {
    echo
    print_color $CYAN "=============================================================="
    print_color $CYAN "  $1"
    print_color $CYAN "=============================================================="
    echo
}

print_success() {
    print_color $GREEN "✓ $1"
}

print_error() {
    print_color $RED "✗ $1"
}

print_warning() {
    print_color $YELLOW "⚠ $1"
}

print_info() {
    print_color $BLUE "ℹ $1"
}

# Check if Python is installed
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        print_success "Python 3 found: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        print_success "Python found: $(python --version)"
    else
        print_error "Python not found. Please install Python 3.6 or later."
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        print_success "pip3 found"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
        print_success "pip found"
    else
        print_error "pip not found. Please install pip."
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_header "INSTALLING DEPENDENCIES"
    
    if [ -f "requirements.txt" ]; then
        print_info "Installing Python dependencies..."
        $PIP_CMD install -r requirements.txt
        print_success "Dependencies installed successfully"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    print_header "ENVIRONMENT SETUP"
    
    if [ ! -f ".env" ]; then
        print_warning ".env file not found, creating template..."
        cat > .env << EOF
# Deribit API credentials (optional - for authenticated tests)
DERIBIT_CLIENT_ID=your_client_id_here
DERIBIT_CLIENT_SECRET=your_client_secret_here

# Test configuration
DERIBIT_BASE_URL=https://test.deribit.com
DERIBIT_WS_URL=wss://test.deribit.com/ws/api/v2

# Your server configuration
SERVER_HOST=localhost
SERVER_PORT=8080
SERVER_BASE_URL=http://localhost:8080

# Test settings
TEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
RATE_LIMIT_PER_SECOND=20
EOF
        print_info "Template .env file created. Please update with your credentials."
    else
        print_success ".env file exists"
    fi
}

# Run basic tests
run_basic_tests() {
    print_header "RUNNING BASIC CONNECTIVITY TESTS"
    
    print_info "Starting comprehensive Deribit testing..."
    $PYTHON_CMD deribit_tester.py
}

# Run async tests with pytest
run_async_tests() {
    print_header "RUNNING ASYNC TESTS WITH PYTEST"
    
    print_info "Running async test suite..."
    $PYTHON_CMD -m pytest test_deribit_async.py -v --tb=short
}

# Run performance monitoring
run_performance_tests() {
    print_header "RUNNING PERFORMANCE MONITORING"
    
    print_info "Starting 2-minute performance monitoring session..."
    $PYTHON_CMD performance_monitor.py --duration 2
}

# Run WebSocket tick analysis
run_websocket_tick_analysis() {
    print_header "WEBSOCKET TICK-BY-TICK DELAY ANALYSIS"
    
# Run load tests
run_load_tests() {
    print_header "RUNNING LOAD TESTS"
    
    print_info "Running concurrent load tests..."
    $PYTHON_CMD -c "
import asyncio
import aiohttp
import time
from datetime import datetime

async def load_test():
    url = 'https://test.deribit.com/api/v2/public/test'
    concurrent_requests = 50
    total_requests = 200
    
    print(f'Starting load test: {total_requests} requests with {concurrent_requests} concurrent connections')
    
    start_time = time.time()
    successful = 0
    failed = 0
    
    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(concurrent_requests)
        
        async def make_request():
            nonlocal successful, failed
            async with semaphore:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            successful += 1
                        else:
                            failed += 1
                except Exception as e:
                    failed += 1
        
        tasks = [make_request() for _ in range(total_requests)]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    requests_per_second = total_requests / total_time
    
    print(f'Load test completed in {total_time:.2f} seconds')
    print(f'Successful requests: {successful}/{total_requests}')
    print(f'Failed requests: {failed}/{total_requests}')
    print(f'Success rate: {(successful/total_requests)*100:.2f}%')
    print(f'Requests per second: {requests_per_second:.2f}')

asyncio.run(load_test())
"
}

# Generate test report
generate_report() {
    print_header "GENERATING TEST REPORT"
    
    timestamp=$(date +"%Y%m%d_%H%M%S")
    report_file="test_report_${timestamp}.md"
    
    cat > $report_file << EOF
# Deribit Server Testing Report

**Generated:** $(date)

## Test Environment
- **Python Version:** $($PYTHON_CMD --version)
- **Test Target:** $(grep DERIBIT_BASE_URL .env | cut -d'=' -f2)
- **Timestamp:** $timestamp

## Test Results Summary

### Basic Connectivity Tests
- See \`test_results_*.json\` for detailed results

### Performance Tests
- See \`performance_analysis_*.png\` for visualizations
- See \`http_metrics_*.csv\` for raw data
- See \`websocket_metrics_*.csv\` for WebSocket data

### Files Generated
EOF

    # List all generated files
    echo "### Generated Files:" >> $report_file
    for file in test_results_*.json performance_analysis_*.png *_metrics_*.csv; do
        if [ -f "$file" ]; then
            echo "- \`$file\`" >> $report_file
        fi
    done
    
    print_success "Test report generated: $report_file"
}

# Cleanup function
cleanup() {
    print_header "CLEANUP"
    
    # Optional: Clean up old test files
    read -p "Do you want to clean up old test files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up old test files..."
        find . -name "test_results_*.json" -mtime +7 -delete 2>/dev/null || true
        find . -name "performance_analysis_*.png" -mtime +7 -delete 2>/dev/null || true
        find . -name "*_metrics_*.csv" -mtime +7 -delete 2>/dev/null || true
        print_success "Cleanup completed"
    fi
}

# Main execution
main() {
    print_header "DERIBIT SERVER TESTING SUITE"
    print_info "Starting comprehensive testing suite..."
    
    # Check prerequisites
    check_python
    check_pip
    
    # Setup
    setup_environment
    install_dependencies
    
    # Run tests based on arguments
    case "${1:-all}" in
        "basic")
            run_basic_tests
            ;;
        "async")
            run_async_tests
            ;;
        "performance")
            run_performance_tests
            ;;
        "load")
            run_load_tests
            ;;
        "websocket-ticks")
            run_websocket_tick_analysis
            ;;
        "all")
            run_basic_tests
            echo
            run_async_tests
            echo
            run_performance_tests
            echo
            run_load_tests
            echo
            run_websocket_tick_analysis
            ;;
        *)
            print_error "Unknown test type: $1"
            print_info "Usage: $0 [basic|async|performance|load|websocket-ticks|all]"
            exit 1
            ;;
    esac
    
    # Generate report and cleanup
    generate_report
    cleanup
    
    print_header "TESTING COMPLETED"
    print_success "All tests have been executed successfully!"
    print_info "Check the generated files for detailed results."
}

# Handle script arguments
if [ $# -eq 0 ]; then
    main "all"
else
    main "$1"
fi
