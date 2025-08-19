# Deribit Server Testing Suite

**Version 2.0.0** - Enhanced Performance & Reliability Testing Framework

A comprehensive testing framework for testing server connectivity to Deribit exchange API. This suite includes multiple testing modules for different aspects of connectivity, performance, and reliability with millisecond-precision timing measurements.

## 🚀 Features

### Key Improvements in v2.0.0
- **Millisecond Precision**: All timing measurements now display in milliseconds for better accuracy
- **Enhanced WebSocket Testing**: Improved tick-by-tick delay analysis
- **Better Performance Metrics**: More detailed performance monitoring and reporting
- **Improved Error Handling**: Enhanced error detection and reporting capabilities

### Test Modules

1. **Basic Connectivity Tests** (`deribit_tester.py`)
   - HTTP API connectivity
   - Authentication testing
   - Market data endpoints
   - Error handling
   - Rate limit testing

2. **Async Performance Tests** (`test_deribit_async.py`)
   - Pytest-based async testing
   - Concurrent request testing
   - Performance benchmarks
   - Multi-currency testing

3. **Performance Monitoring** (`performance_monitor.py`)
   - Real-time performance metrics
   - WebSocket latency monitoring
   - Response time analysis
   - Visual performance reports

4. **WebSocket Testing** (`websocket_tester.py`)
   - WebSocket connectivity stress testing
   - Millisecond-precision latency measurements
   - Reconnection testing
   - Multi-connection testing
   - **Tick-by-tick delay analysis** - Detailed analysis of delay per tick for subscribed data streams

5. **Automated Test Runner** (`run_tests.sh`)
   - One-command test execution
   - Environment setup
   - Dependency installation
   - Report generation

## 📋 Prerequisites

- Python 3.7 or higher
- pip (Python package installer)
- Internet connection
- Optional: Deribit API credentials for authenticated tests

## 🛠️ Installation

1. Clone or create the project directory:
```bash
git clone <your-repo> server_testing
cd server_testing
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## 🏃‍♂️ Quick Start

### Run All Tests (Recommended)
```bash
./run_tests.sh
```

### Run Specific Test Types
```bash
# Basic connectivity tests only
./run_tests.sh basic

# Async tests only
./run_tests.sh async

# Performance monitoring only
./run_tests.sh performance

# Load tests only
./run_tests.sh load

# WebSocket tick analysis only  
./run_tests.sh websocket-ticks
```

### Manual Test Execution

#### Basic Tests
```bash
python deribit_tester.py
```

#### Async Tests with Pytest
```bash
pytest test_deribit_async.py -v
```

#### Performance Monitoring
```bash
# 5-minute monitoring session
python performance_monitor.py --duration 5
```

#### WebSocket Testing
```bash
# Stress test with 10 connections
python websocket_tester.py --test-type stress --connections 10 --duration 60

# Latency test
python websocket_tester.py --test-type latency --duration 30

# Reconnection test
python websocket_tester.py --test-type reconnection --duration 60

# Tick-by-tick delay analysis
python websocket_tester.py --test-type tick-analysis --duration 60 --channels ticker.BTC-PERPETUAL.100ms book.BTC-PERPETUAL.100ms.10
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Deribit API Configuration
DERIBIT_CLIENT_ID=your_client_id_here
DERIBIT_CLIENT_SECRET=your_client_secret_here
DERIBIT_BASE_URL=https://test.deribit.com
DERIBIT_WS_URL=wss://test.deribit.com/ws/api/v2

# Your Server Configuration
SERVER_HOST=localhost
SERVER_PORT=8080
SERVER_BASE_URL=http://localhost:8080

# Test Settings
TEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
RATE_LIMIT_PER_SECOND=20
```

### Test URLs

- **Testnet (Default)**: `https://test.deribit.com`
- **Production**: `https://www.deribit.com` (use with caution)

## 📊 Test Reports and Output

### Generated Files

- `test_results_YYYYMMDD_HHMMSS.json` - Detailed test results
- `performance_analysis_YYYYMMDD_HHMMSS.png` - Performance visualizations
- `http_metrics_YYYYMMDD_HHMMSS.csv` - HTTP performance data
- `websocket_metrics_YYYYMMDD_HHMMSS.csv` - WebSocket performance data
- `test_report_YYYYMMDD_HHMMSS.md` - Comprehensive test report

### Sample Output

```
```
==============================================================
  BASIC CONNECTIVITY TESTS
==============================================================

✓ PASSED Basic HTTP Connectivity (245.0ms)
✓ PASSED Server Time Sync (123.0ms)

==============================================================
  AUTHENTICATION TESTS
==============================================================

✓ PASSED API Authentication (1234.0ms)

==============================================================
  MARKET DATA TESTS
==============================================================

✓ PASSED Get Instruments (BTC) (456.0ms)
✓ PASSED Get Ticker (BTC-PERPETUAL) (234.0ms)
✓ PASSED Get Order Book (BTC-PERPETUAL) (345.0ms)
```
```

## 🧪 Test Categories

### 1. Connectivity Tests
- Basic HTTP connectivity to Deribit API
- SSL/TLS verification
- DNS resolution
- Response time measurements

### 2. Authentication Tests
- API key authentication
- Token refresh mechanisms
- Permission validation

### 3. Market Data Tests
- Instrument listings
- Real-time ticker data
- Order book data
- Trade history

### 4. WebSocket Tests
- Connection establishment
- Subscription management
- Real-time data streaming
- Connection stability

### 5. Performance Tests
- Response time analysis
- Throughput measurements
- Concurrent connection limits
- Rate limiting behavior

### 6. Error Handling Tests
- Invalid endpoints
- Malformed requests
- Network timeout scenarios
- Rate limit exceeded

### 7. Load Testing
- Stress testing with multiple connections
- Sustained load over time
- Recovery after failures

## 📈 Performance Metrics

The testing suite tracks various performance metrics:

- **Response Time**: HTTP request/response latency (in milliseconds)
- **WebSocket Latency**: Real-time data delivery delay (in milliseconds)
- **Throughput**: Requests per second
- **Success Rate**: Percentage of successful requests
- **Connection Stability**: WebSocket connection uptime
- **Error Rates**: Failed request percentages

## 🛡️ Error Handling

The testing suite includes comprehensive error handling:

- Network connectivity issues
- API rate limiting
- Authentication failures
- Invalid API responses
- WebSocket disconnections
- Timeout scenarios

## 🔧 Customization

### Adding New Tests

1. **HTTP Tests**: Add to `deribit_tester.py`
```python
def test_custom_endpoint(self):
    # Your test implementation
    pass
```

2. **Async Tests**: Add to `test_deribit_async.py`
```python
async def test_custom_async_feature(self, deribit_tester):
    # Your async test implementation
    pass
```

3. **WebSocket Tests**: Add to `websocket_tester.py`
```python
async def custom_websocket_test(self):
    # Your WebSocket test implementation
    pass
```

### Custom Monitoring

Extend `performance_monitor.py` to add custom metrics:

```python
def custom_metric_collector(self):
    # Your custom metric collection
    pass
```

## 🐛 Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check internet connectivity
   - Verify Deribit API status
   - Check firewall settings

2. **Authentication Failed**
   - Verify API credentials in `.env`
   - Check API key permissions
   - Ensure using correct environment (test/prod)

3. **Rate Limiting**
   - Reduce `RATE_LIMIT_PER_SECOND` in `.env`
   - Add delays between requests
   - Check Deribit rate limit documentation

4. **WebSocket Issues**
   - Check WebSocket URL in `.env`
   - Verify network supports WebSocket connections
   - Check for proxy/firewall interference

### Debug Mode

Enable verbose logging:

```bash
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
import deribit_tester
tester = deribit_tester.DeribitTester()
tester.run_all_tests()
"
```

## 📚 API Documentation

- [Deribit API Documentation](https://docs.deribit.com/)
- [Deribit WebSocket API](https://docs.deribit.com/#json-rpc-websocket)
- [Rate Limiting](https://docs.deribit.com/#rate-limiting)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is open source. See LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section
2. Review Deribit API documentation
3. Create an issue with detailed logs
4. Include environment configuration (without credentials)

## 🔄 Updates

To update the testing suite:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## � Version History

### v2.0.0 (August 2025)
- **Major Enhancement**: Converted all timing measurements to milliseconds for better precision
- **Improved Performance**: Enhanced WebSocket testing with better latency analysis
- **Better UX**: More readable timing outputs and performance metrics
- **Framework Stability**: Improved error handling and test reliability

### v1.x
- Initial framework development
- Basic connectivity and performance testing
- WebSocket functionality implementation

## �📋 Test Checklist

Before deploying to production:

- [ ] All connectivity tests pass
- [ ] Authentication works correctly
- [ ] WebSocket connections are stable
- [ ] Performance metrics are acceptable
- [ ] Error handling works as expected
- [ ] Rate limiting is properly handled
- [ ] SSL/TLS certificates are valid
- [ ] Monitoring and alerting are configured