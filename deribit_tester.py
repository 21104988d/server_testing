import os
import time
import json
import asyncio
import requests
import websocket
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from tabulate import tabulate
from colorama import Fore, Style, init
from dotenv import load_dotenv
import threading
import queue
import statistics

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

@dataclass
class TestResult:
    """Data class to store test results"""
    test_name: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    data: Optional[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class DeribitTester:
    """Comprehensive testing class for Deribit server connectivity"""
    
    def __init__(self):
        self.base_url = os.getenv('DERIBIT_BASE_URL', 'https://test.deribit.com')
        self.ws_url = os.getenv('DERIBIT_WS_URL', 'wss://test.deribit.com/ws/api/v2')
        self.client_id = os.getenv('DERIBIT_CLIENT_ID')
        self.client_secret = os.getenv('DERIBIT_CLIENT_SECRET')
        self.server_url = os.getenv('SERVER_BASE_URL', 'http://localhost:8080')
        self.timeout = int(os.getenv('TEST_TIMEOUT', '30'))
        self.rate_limit = int(os.getenv('RATE_LIMIT_PER_SECOND', '20'))
        
        self.results: List[TestResult] = []
        self.session = requests.Session()
        self.access_token = None
        
        # Test statistics
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def log_result(self, result: TestResult):
        """Log test result and update statistics"""
        self.results.append(result)
        self.total_tests += 1
        
        if result.success:
            self.passed_tests += 1
            status = f"{Fore.GREEN}✓ PASSED{Style.RESET_ALL}"
        else:
            self.failed_tests += 1
            status = f"{Fore.RED}✗ FAILED{Style.RESET_ALL}"
            
        print(f"{status} {result.test_name} ({result.response_time*1000:.1f}ms)")
        if result.error_message:
            print(f"  └─ Error: {Fore.RED}{result.error_message}{Style.RESET_ALL}")
    
    def print_header(self, title: str):
        """Print a formatted test section header"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{title.center(60)}")
        print(f"{'='*60}{Style.RESET_ALL}")
    
    def test_basic_connectivity(self):
        """Test basic connectivity to Deribit"""
        self.print_header("BASIC CONNECTIVITY TESTS")
        
        # Test 1: Basic HTTP connectivity
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/v2/public/test", timeout=self.timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = TestResult(
                    test_name="Basic HTTP Connectivity",
                    success=True,
                    response_time=response_time,
                    status_code=response.status_code,
                    data=response.json()
                )
            else:
                result = TestResult(
                    test_name="Basic HTTP Connectivity",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Unexpected status code: {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Basic HTTP Connectivity",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
        
        # Test 2: Server time endpoint
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/v2/public/get_time", timeout=self.timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                server_time = data.get('result', 0)
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                
                result = TestResult(
                    test_name="Server Time Sync",
                    success=time_diff < 5000,  # Allow 5 second difference
                    response_time=response_time,
                    status_code=response.status_code,
                    data={'time_diff_ms': time_diff, 'server_time': server_time, 'local_time': local_time},
                    error_message=f"Time difference too large: {time_diff}ms" if time_diff >= 5000 else None
                )
            else:
                result = TestResult(
                    test_name="Server Time Sync",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Failed to get server time: {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Server Time Sync",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def test_authentication(self):
        """Test authentication with Deribit API"""
        self.print_header("AUTHENTICATION TESTS")
        
        if not self.client_id or not self.client_secret:
            result = TestResult(
                test_name="Authentication Setup",
                success=False,
                response_time=0,
                error_message="Client credentials not provided in environment variables"
            )
            self.log_result(result)
            return
        
        # Test authentication
        start_time = time.time()
        try:
            auth_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "public/auth",
                "params": {
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v2/public/auth",
                json=auth_data,
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'access_token' in data['result']:
                    self.access_token = data['result']['access_token']
                    result = TestResult(
                        test_name="API Authentication",
                        success=True,
                        response_time=response_time,
                        status_code=response.status_code,
                        data={'token_length': len(self.access_token)}
                    )
                else:
                    result = TestResult(
                        test_name="API Authentication",
                        success=False,
                        response_time=response_time,
                        status_code=response.status_code,
                        error_message="No access token in response"
                    )
            else:
                result = TestResult(
                    test_name="API Authentication",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Authentication failed: {response.text}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="API Authentication",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def test_market_data(self):
        """Test market data endpoints"""
        self.print_header("MARKET DATA TESTS")
        
        # Test 1: Get instruments
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/public/get_instruments",
                params={"currency": "BTC"},
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                instruments = data.get('result', [])
                result = TestResult(
                    test_name="Get Instruments (BTC)",
                    success=len(instruments) > 0,
                    response_time=response_time,
                    status_code=response.status_code,
                    data={'instrument_count': len(instruments)},
                    error_message="No instruments returned" if len(instruments) == 0 else None
                )
            else:
                result = TestResult(
                    test_name="Get Instruments (BTC)",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Failed to get instruments: {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Get Instruments (BTC)",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
        
        # Test 2: Get ticker for BTC-PERPETUAL
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/public/ticker",
                params={"instrument_name": "BTC-PERPETUAL"},
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                ticker_data = data.get('result', {})
                result = TestResult(
                    test_name="Get Ticker (BTC-PERPETUAL)",
                    success='last_price' in ticker_data,
                    response_time=response_time,
                    status_code=response.status_code,
                    data={'last_price': ticker_data.get('last_price', 0)},
                    error_message="No last_price in ticker data" if 'last_price' not in ticker_data else None
                )
            else:
                result = TestResult(
                    test_name="Get Ticker (BTC-PERPETUAL)",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Failed to get ticker: {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Get Ticker (BTC-PERPETUAL)",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
        
        # Test 3: Get order book
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/public/get_order_book",
                params={"instrument_name": "BTC-PERPETUAL", "depth": 5},
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                order_book = data.get('result', {})
                has_bids = len(order_book.get('bids', [])) > 0
                has_asks = len(order_book.get('asks', [])) > 0
                
                result = TestResult(
                    test_name="Get Order Book (BTC-PERPETUAL)",
                    success=has_bids and has_asks,
                    response_time=response_time,
                    status_code=response.status_code,
                    data={'bid_count': len(order_book.get('bids', [])), 'ask_count': len(order_book.get('asks', []))},
                    error_message="Order book missing bids or asks" if not (has_bids and has_asks) else None
                )
            else:
                result = TestResult(
                    test_name="Get Order Book (BTC-PERPETUAL)",
                    success=False,
                    response_time=response_time,
                    status_code=response.status_code,
                    error_message=f"Failed to get order book: {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Get Order Book (BTC-PERPETUAL)",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def test_websocket_connection(self):
        """Test WebSocket connectivity"""
        self.print_header("WEBSOCKET TESTS")
        
        test_results = []
        messages_received = queue.Queue()
        connection_established = threading.Event()
        
        def on_message(ws, message):
            messages_received.put(json.loads(message))
        
        def on_open(ws):
            connection_established.set()
            # Subscribe to ticker
            subscribe_msg = {
                "jsonrpc": "2.0",
                "id": 42,
                "method": "public/subscribe",
                "params": {
                    "channels": ["ticker.BTC-PERPETUAL.100ms"]
                }
            }
            ws.send(json.dumps(subscribe_msg))
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
        
        # Test WebSocket connection
        start_time = time.time()
        try:
            ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_open=on_open,
                on_error=on_error
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection
            connected = connection_established.wait(timeout=10)
            
            if connected:
                # Wait for some messages
                time.sleep(3)
                response_time = time.time() - start_time
                
                message_count = messages_received.qsize()
                result = TestResult(
                    test_name="WebSocket Connection & Subscription",
                    success=message_count > 0,
                    response_time=response_time,
                    data={'messages_received': message_count},
                    error_message="No messages received" if message_count == 0 else None
                )
            else:
                response_time = time.time() - start_time
                result = TestResult(
                    test_name="WebSocket Connection & Subscription",
                    success=False,
                    response_time=response_time,
                    error_message="Failed to establish WebSocket connection"
                )
            
            ws.close()
            
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="WebSocket Connection & Subscription",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def test_rate_limits(self):
        """Test API rate limits"""
        self.print_header("RATE LIMIT TESTS")
        
        # Test rapid requests
        start_time = time.time()
        successful_requests = 0
        failed_requests = 0
        response_times = []
        
        print(f"Sending {self.rate_limit} requests rapidly...")
        
        for i in range(self.rate_limit):
            try:
                req_start = time.time()
                response = self.session.get(
                    f"{self.base_url}/api/v2/public/test",
                    timeout=self.timeout
                )
                req_time = time.time() - req_start
                response_times.append(req_time)
                
                if response.status_code == 200:
                    successful_requests += 1
                else:
                    failed_requests += 1
                    
            except Exception as e:
                failed_requests += 1
                req_time = time.time() - req_start
                response_times.append(req_time)
        
        total_time = time.time() - start_time
        avg_response_time = statistics.mean(response_times) if response_times else 0
        requests_per_second = self.rate_limit / total_time
        
        result = TestResult(
            test_name=f"Rate Limit Test ({self.rate_limit} requests)",
            success=successful_requests >= self.rate_limit * 0.8,  # 80% success rate
            response_time=avg_response_time,
            data={
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'total_time': total_time,
                'requests_per_second': requests_per_second,
                'avg_response_time': avg_response_time
            },
            error_message=f"Low success rate: {successful_requests}/{self.rate_limit}" if successful_requests < self.rate_limit * 0.8 else None
        )
        
        self.log_result(result)
    
    def test_error_handling(self):
        """Test error handling for various scenarios"""
        self.print_header("ERROR HANDLING TESTS")
        
        # Test 1: Invalid endpoint
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/v2/invalid_endpoint", timeout=self.timeout)
            response_time = time.time() - start_time
            
            result = TestResult(
                test_name="Invalid Endpoint Error Handling",
                success=response.status_code == 404,
                response_time=response_time,
                status_code=response.status_code,
                error_message=f"Expected 404, got {response.status_code}" if response.status_code != 404 else None
            )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Invalid Endpoint Error Handling",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
        
        # Test 2: Invalid instrument
        start_time = time.time()
        try:
            response = self.session.get(
                f"{self.base_url}/api/v2/public/ticker",
                params={"instrument_name": "INVALID-INSTRUMENT"},
                timeout=self.timeout
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                has_error = 'error' in data
                result = TestResult(
                    test_name="Invalid Instrument Error Handling",
                    success=has_error,
                    response_time=response_time,
                    status_code=response.status_code,
                    data=data.get('error', {}),
                    error_message="No error returned for invalid instrument" if not has_error else None
                )
            else:
                result = TestResult(
                    test_name="Invalid Instrument Error Handling",
                    success=True,  # Non-200 status is expected for invalid instrument
                    response_time=response_time,
                    status_code=response.status_code
                )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Invalid Instrument Error Handling",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def test_server_endpoints(self):
        """Test your server endpoints (if applicable)"""
        self.print_header("SERVER ENDPOINT TESTS")
        
        # Test basic server connectivity
        start_time = time.time()
        try:
            response = self.session.get(f"{self.server_url}/health", timeout=self.timeout)
            response_time = time.time() - start_time
            
            result = TestResult(
                test_name="Server Health Check",
                success=response.status_code == 200,
                response_time=response_time,
                status_code=response.status_code,
                error_message=f"Health check failed: {response.status_code}" if response.status_code != 200 else None
            )
        except Exception as e:
            response_time = time.time() - start_time
            result = TestResult(
                test_name="Server Health Check",
                success=False,
                response_time=response_time,
                error_message=str(e)
            )
        
        self.log_result(result)
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        self.print_header("TEST REPORT")
        
        # Summary statistics
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        print(f"\n{Fore.CYAN}Test Summary:{Style.RESET_ALL}")
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {Fore.GREEN}{self.passed_tests}{Style.RESET_ALL}")
        print(f"Failed: {Fore.RED}{self.failed_tests}{Style.RESET_ALL}")
        print(f"Success Rate: {Fore.GREEN if success_rate >= 80 else Fore.YELLOW if success_rate >= 60 else Fore.RED}{success_rate:.1f}%{Style.RESET_ALL}")
        
        # Response time statistics
        response_times = [r.response_time for r in self.results]
        if response_times:
            print(f"\n{Fore.CYAN}Performance Statistics:{Style.RESET_ALL}")
            print(f"Average Response Time: {statistics.mean(response_times)*1000:.1f}ms")
            print(f"Median Response Time: {statistics.median(response_times)*1000:.1f}ms")
            print(f"Min Response Time: {min(response_times)*1000:.1f}ms")
            print(f"Max Response Time: {max(response_times)*1000:.1f}ms")
        
        # Failed tests details
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            print(f"\n{Fore.RED}Failed Tests:{Style.RESET_ALL}")
            for result in failed_results:
                print(f"  • {result.test_name}: {result.error_message}")
        
        # Generate detailed report table
        table_data = []
        for result in self.results:
            status = "✓ PASS" if result.success else "✗ FAIL"
            table_data.append([
                result.test_name,
                status,
                f"{result.response_time*1000:.1f}ms",
                result.status_code or "N/A",
                result.error_message or "None"
            ])
        
        print(f"\n{Fore.CYAN}Detailed Results:{Style.RESET_ALL}")
        print(tabulate(
            table_data,
            headers=["Test Name", "Status", "Response Time", "Status Code", "Error"],
            tablefmt="grid"
        ))
        
        # Save results to file
        self.save_results()
    
    def save_results(self):
        """Save test results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_data = {
            "timestamp": timestamp,
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "response_time": r.response_time,
                    "status_code": r.status_code,
                    "error_message": r.error_message,
                    "data": r.data,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }
        
        json_filename = f"test_results_{timestamp}.json"
        with open(json_filename, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        print(f"\n{Fore.GREEN}Results saved to {json_filename}{Style.RESET_ALL}")
    
    def run_all_tests(self):
        """Run all test suites"""
        print(f"{Fore.MAGENTA}{'='*80}")
        print(f"DERIBIT SERVER TESTING SUITE")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Run test suites
        self.test_basic_connectivity()
        self.test_authentication()
        self.test_market_data()
        self.test_websocket_connection()
        self.test_rate_limits()
        self.test_error_handling()
        self.test_server_endpoints()
        
        # Generate final report
        self.generate_report()

def main():
    """Main function to run the testing suite"""
    tester = DeribitTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
