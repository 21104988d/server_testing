import asyncio
import aiohttp
import websockets
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class PerformanceMetric:
    """Data class for performance metrics"""
    timestamp: datetime
    endpoint: str
    response_time: float
    status_code: int
    success: bool
    payload_size: int = 0
    error: str = None

class PerformanceMonitor:
    """Advanced performance monitoring for Deribit API"""
    
    def __init__(self, duration_minutes: int = 5):
        self.base_url = os.getenv('DERIBIT_BASE_URL', 'https://test.deribit.com')
        self.ws_url = os.getenv('DERIBIT_WS_URL', 'wss://test.deribit.com/ws/api/v2')
        self.duration = timedelta(minutes=duration_minutes)
        self.metrics: List[PerformanceMetric] = []
        self.ws_metrics: List[Dict] = []
        
    async def monitor_http_performance(self):
        """Monitor HTTP API performance"""
        print(f"🚀 Starting HTTP performance monitoring for {self.duration.total_seconds()/60:.1f} minutes...")
        
        endpoints = [
            "/api/v2/public/test",
            "/api/v2/public/get_time",
            "/api/v2/public/get_instruments?currency=BTC",
            "/api/v2/public/ticker?instrument_name=BTC-PERPETUAL",
            "/api/v2/public/get_order_book?instrument_name=BTC-PERPETUAL&depth=5"
        ]
        
        start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            while datetime.now() - start_time < self.duration:
                tasks = []
                
                for endpoint in endpoints:
                    tasks.append(self._make_request(session, endpoint))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(1)  # 1 second between rounds
        
        print(f"✅ HTTP monitoring completed. Collected {len(self.metrics)} metrics.")
    
    async def _make_request(self, session: aiohttp.ClientSession, endpoint: str):
        """Make a single HTTP request and record metrics"""
        start_time = time.time()
        
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                response_time = time.time() - start_time
                content = await response.text()
                
                metric = PerformanceMetric(
                    timestamp=datetime.now(),
                    endpoint=endpoint,
                    response_time=response_time,
                    status_code=response.status,
                    success=response.status == 200,
                    payload_size=len(content)
                )
                
                self.metrics.append(metric)
                
        except Exception as e:
            response_time = time.time() - start_time
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                endpoint=endpoint,
                response_time=response_time,
                status_code=0,
                success=False,
                error=str(e)
            )
            self.metrics.append(metric)
    
    async def monitor_websocket_performance(self):
        """Monitor WebSocket performance"""
        print(f"🔌 Starting WebSocket performance monitoring...")
        
        start_time = datetime.now()
        message_count = 0
        latencies = []
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                # Subscribe to ticker updates
                subscribe_msg = {
                    "jsonrpc": "2.0",
                    "id": 42,
                    "method": "public/subscribe",
                    "params": {
                        "channels": ["ticker.BTC-PERPETUAL.100ms"]
                    }
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                while datetime.now() - start_time < self.duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        receive_time = datetime.now()
                        
                        data = json.loads(message)
                        message_count += 1
                        
                        # Calculate latency if timestamp is available
                        if 'params' in data and 'data' in data['params']:
                            ticker_data = data['params']['data']
                            if 'timestamp' in ticker_data:
                                server_timestamp = datetime.fromtimestamp(ticker_data['timestamp'] / 1000)
                                latency = (receive_time - server_timestamp).total_seconds() * 1000
                                latencies.append(latency)
                        
                        self.ws_metrics.append({
                            'timestamp': receive_time,
                            'message_count': message_count,
                            'latency': latencies[-1] if latencies else None,
                            'message_type': data.get('method', 'unknown')
                        })
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        print(f"WebSocket error: {e}")
                        break
                        
        except Exception as e:
            print(f"WebSocket connection error: {e}")
        
        print(f"✅ WebSocket monitoring completed. Received {message_count} messages.")
        if latencies:
            avg_latency = statistics.mean(latencies)
            print(f"📊 Average latency: {avg_latency:.2f}ms")
    
    def analyze_performance(self):
        """Analyze collected performance data"""
        if not self.metrics:
            print("❌ No metrics collected for analysis")
            return
        
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS REPORT")
        print("="*60)
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame([asdict(m) for m in self.metrics])
        
        # Overall statistics
        total_requests = len(df)
        successful_requests = len(df[df['success'] == True])
        success_rate = (successful_requests / total_requests) * 100
        
        print(f"\n📈 Overall Statistics:")
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Success Rate: {success_rate:.2f}%")
        
        # Response time statistics
        response_times = df['response_time']
        print(f"\n⏱️  Response Time Statistics:")
        print(f"Average: {response_times.mean()*1000:.1f}ms")
        print(f"Median: {response_times.median()*1000:.1f}ms")
        print(f"95th Percentile: {response_times.quantile(0.95)*1000:.1f}ms")
        print(f"99th Percentile: {response_times.quantile(0.99)*1000:.1f}ms")
        print(f"Min: {response_times.min()*1000:.1f}ms")
        print(f"Max: {response_times.max()*1000:.1f}ms")
        
        # Per-endpoint analysis
        print(f"\n📊 Per-Endpoint Performance:")
        endpoint_stats = df.groupby('endpoint').agg({
            'response_time': ['mean', 'median', 'max', 'count'],
            'success': 'mean'
        }).round(3)
        
        print(endpoint_stats)
        
        # Error analysis
        errors = df[df['success'] == False]
        if not errors.empty:
            print(f"\n❌ Error Analysis:")
            error_counts = errors['endpoint'].value_counts()
            print(error_counts)
        
        # Generate visualizations
        self._create_visualizations(df)
        
        # WebSocket analysis
        if self.ws_metrics:
            self._analyze_websocket_performance()
    
    def _analyze_websocket_performance(self):
        """Analyze WebSocket performance data"""
        print(f"\n🔌 WebSocket Performance:")
        
        ws_df = pd.DataFrame(self.ws_metrics)
        
        if not ws_df.empty:
            total_messages = len(ws_df)
            duration_seconds = (ws_df['timestamp'].max() - ws_df['timestamp'].min()).total_seconds()
            messages_per_second = total_messages / duration_seconds if duration_seconds > 0 else 0
            
            print(f"Total Messages: {total_messages}")
            print(f"Duration: {duration_seconds:.1f}s")
            print(f"Messages/Second: {messages_per_second:.2f}")
            
            # Latency analysis
            latencies = [m for m in ws_df['latency'] if m is not None]
            if latencies:
                print(f"Average Latency: {statistics.mean(latencies):.2f}ms")
                print(f"Median Latency: {statistics.median(latencies):.2f}ms")
                print(f"Max Latency: {max(latencies):.2f}ms")
    
    def _create_visualizations(self, df: pd.DataFrame):
        """Create performance visualization charts"""
        print(f"\n📊 Generating performance visualizations...")
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Deribit API Performance Analysis', fontsize=16)
        
        # 1. Response time over time
        axes[0, 0].plot(df['timestamp'], df['response_time']*1000, alpha=0.7)
        axes[0, 0].set_title('Response Time Over Time')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Response Time (milliseconds)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. Response time distribution
        axes[0, 1].hist(df['response_time']*1000, bins=30, alpha=0.7, edgecolor='black')
        axes[0, 1].set_title('Response Time Distribution')
        axes[0, 1].set_xlabel('Response Time (milliseconds)')
        axes[0, 1].set_ylabel('Frequency')
        
        # 3. Response time by endpoint
        endpoint_response_times = [df[df['endpoint'] == endpoint]['response_time'].values * 1000
                                 for endpoint in df['endpoint'].unique()]
        axes[1, 0].boxplot(endpoint_response_times, labels=df['endpoint'].unique())
        axes[1, 0].set_title('Response Time by Endpoint')
        axes[1, 0].set_ylabel('Response Time (milliseconds)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. Success rate by endpoint
        success_rates = df.groupby('endpoint')['success'].mean() * 100
        axes[1, 1].bar(range(len(success_rates)), success_rates.values)
        axes[1, 1].set_title('Success Rate by Endpoint')
        axes[1, 1].set_ylabel('Success Rate (%)')
        axes[1, 1].set_xticks(range(len(success_rates)))
        axes[1, 1].set_xticklabels(success_rates.index, rotation=45)
        axes[1, 1].set_ylim(0, 105)
        
        plt.tight_layout()
        
        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_analysis_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"📈 Visualizations saved to {filename}")
        plt.show()
    
    def save_metrics(self):
        """Save metrics to CSV files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save HTTP metrics
        if self.metrics:
            df = pd.DataFrame([asdict(m) for m in self.metrics])
            http_filename = f"http_metrics_{timestamp}.csv"
            df.to_csv(http_filename, index=False)
            print(f"💾 HTTP metrics saved to {http_filename}")
        
        # Save WebSocket metrics
        if self.ws_metrics:
            ws_df = pd.DataFrame(self.ws_metrics)
            ws_filename = f"websocket_metrics_{timestamp}.csv"
            ws_df.to_csv(ws_filename, index=False)
            print(f"💾 WebSocket metrics saved to {ws_filename}")
    
    async def run_full_monitoring(self):
        """Run complete monitoring suite"""
        print("🔍 Starting comprehensive performance monitoring...")
        start_time = datetime.now()
        
        # Run HTTP and WebSocket monitoring concurrently
        await asyncio.gather(
            self.monitor_http_performance(),
            self.monitor_websocket_performance()
        )
        
        total_time = datetime.now() - start_time
        print(f"\n⏱️  Total monitoring time: {total_time.total_seconds()*1000:.0f}ms")
        
        # Analyze results
        self.analyze_performance()
        
        # Save data
        self.save_metrics()

async def main():
    """Main function to run performance monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deribit API Performance Monitor')
    parser.add_argument('--duration', type=int, default=5, 
                       help='Monitoring duration in minutes (default: 5)')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(duration_minutes=args.duration)
    await monitor.run_full_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
