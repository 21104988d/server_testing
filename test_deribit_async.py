import pytest
import pytest_asyncio
import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class AsyncDeribitTester:
    """Async version of Deribit testing for performance testing"""
    
    def __init__(self):
        self.base_url = os.getenv('DERIBIT_BASE_URL', 'https://test.deribit.com')
        self.timeout = int(os.getenv('TEST_TIMEOUT', '30'))
        self.max_concurrent = int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

@pytest.mark.asyncio
class TestDeribitConnectivity:
    """Pytest test cases for Deribit connectivity"""
    
    @pytest_asyncio.fixture
    async def deribit_tester(self):
        async with AsyncDeribitTester() as tester:
            yield tester
    
    async def test_basic_connectivity(self, deribit_tester):
        """Test basic HTTP connectivity"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/test"
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
    
    async def test_server_time(self, deribit_tester):
        """Test server time endpoint"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/get_time"
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
            
            server_time = data["result"]
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            # Allow 5 second difference
            assert time_diff < 5000, f"Time difference too large: {time_diff}ms"
    
    async def test_get_instruments(self, deribit_tester):
        """Test get instruments endpoint"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/get_instruments",
            params={"currency": "BTC"}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
            assert len(data["result"]) > 0
    
    async def test_get_ticker(self, deribit_tester):
        """Test get ticker endpoint"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/ticker",
            params={"instrument_name": "BTC-PERPETUAL"}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
            assert "last_price" in data["result"]
    
    async def test_get_order_book(self, deribit_tester):
        """Test get order book endpoint"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/get_order_book",
            params={"instrument_name": "BTC-PERPETUAL", "depth": 5}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
            result = data["result"]
            assert len(result["bids"]) > 0
            assert len(result["asks"]) > 0
    
    async def test_invalid_endpoint(self, deribit_tester):
        """Test error handling for invalid endpoints"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/invalid_endpoint"
        ) as response:
            assert response.status == 404
    
    async def test_concurrent_requests(self, deribit_tester):
        """Test concurrent request handling"""
        
        async def make_request():
            async with deribit_tester.session.get(
                f"{deribit_tester.base_url}/api/v2/public/test"
            ) as response:
                return response.status == 200
        
        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(deribit_tester.max_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successful requests
        successful = sum(1 for result in results if result is True)
        
        # At least 80% should succeed
        assert successful >= deribit_tester.max_concurrent * 0.8
    
    @pytest.mark.parametrize("currency", ["BTC", "ETH", "SOL"])
    async def test_multiple_currencies(self, deribit_tester, currency):
        """Test instruments for multiple currencies"""
        async with deribit_tester.session.get(
            f"{deribit_tester.base_url}/api/v2/public/get_instruments",
            params={"currency": currency}
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "result" in data
            # Some currencies might not have instruments, so we just check the response format
            assert isinstance(data["result"], list)

@pytest.mark.asyncio
class TestPerformance:
    """Performance testing for Deribit API"""
    
    @pytest_asyncio.fixture
    async def deribit_tester(self):
        async with AsyncDeribitTester() as tester:
            yield tester
    
    async def test_response_time_benchmark(self, deribit_tester):
        """Benchmark response times for various endpoints"""
        endpoints = [
            "/api/v2/public/test",
            "/api/v2/public/get_time",
            "/api/v2/public/get_instruments?currency=BTC",
            "/api/v2/public/ticker?instrument_name=BTC-PERPETUAL"
        ]
        
        response_times = {}
        
        for endpoint in endpoints:
            start_time = time.time()
            async with deribit_tester.session.get(
                f"{deribit_tester.base_url}{endpoint}"
            ) as response:
                response_time = time.time() - start_time
                response_times[endpoint] = response_time
                
                # Assert reasonable response times (under 2000ms)
                assert response_time < 2.0, f"Slow response for {endpoint}: {response_time*1000:.1f}ms"
                assert response.status == 200
        
        print(f"\nResponse Time Benchmark:")
        for endpoint, rt in response_times.items():
            print(f"  {endpoint}: {rt*1000:.1f}ms")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
