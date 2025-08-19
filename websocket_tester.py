import asyncio
import websockets
import json
import time
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
from dataclasses import dataclass
import logging

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class WebSocketMessage:
    """Data class for WebSocket messages"""
    timestamp: datetime
    message_type: str
    channel: str
    data: Dict
    latency: Optional[float] = None

class DeribitWebSocketTester:
    """WebSocket stress testing and monitoring for Deribit"""
    
    def __init__(self):
        self.ws_url = os.getenv('DERIBIT_WS_URL', 'wss://test.deribit.com/ws/api/v2')
        self.client_id = os.getenv('DERIBIT_CLIENT_ID')
        self.client_secret = os.getenv('DERIBIT_CLIENT_SECRET')
        
        self.connections: List[websockets.WebSocketServerProtocol] = []
        self.messages: List[WebSocketMessage] = []
        self.is_running = True
        
        # Statistics
        self.total_messages = 0
        self.connection_count = 0
        self.reconnection_count = 0
        
        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.is_running = False
    
    async def authenticate(self, websocket):
        """Authenticate WebSocket connection"""
        if not self.client_id or not self.client_secret:
            logger.warning("No credentials provided, skipping authentication")
            return False
        
        auth_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "public/auth",
            "params": {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        }
        
        await websocket.send(json.dumps(auth_message))
        
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            
            if 'result' in data and 'access_token' in data['result']:
                logger.info("WebSocket authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {data}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def subscribe_to_channels(self, websocket, channels: List[str]):
        """Subscribe to multiple channels"""
        subscribe_message = {
            "jsonrpc": "2.0",
            "id": 42,
            "method": "public/subscribe",
            "params": {
                "channels": channels
            }
        }
        
        await websocket.send(json.dumps(subscribe_message))
        logger.info(f"Subscribed to channels: {channels}")
    
    async def single_connection_test(self, connection_id: int, channels: List[str], duration: int = 60):
        """Test a single WebSocket connection"""
        logger.info(f"Starting connection {connection_id}")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                self.connection_count += 1
                self.connections.append(websocket)
                
                # Authenticate if credentials are provided
                await self.authenticate(websocket)
                
                # Subscribe to channels
                await self.subscribe_to_channels(websocket, channels)
                
                start_time = time.time()
                connection_messages = 0
                
                while self.is_running and (time.time() - start_time) < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        receive_time = datetime.now()
                        
                        data = json.loads(message)
                        connection_messages += 1
                        self.total_messages += 1
                        
                        # Calculate latency if possible
                        latency = None
                        if 'params' in data and 'data' in data['params']:
                            if 'timestamp' in data['params']['data']:
                                server_time = data['params']['data']['timestamp'] / 1000
                                latency = (receive_time.timestamp() - server_time) * 1000
                        
                        # Store message data
                        ws_message = WebSocketMessage(
                            timestamp=receive_time,
                            message_type=data.get('method', 'unknown'),
                            channel=data.get('params', {}).get('channel', 'unknown'),
                            data=data,
                            latency=latency
                        )
                        
                        self.messages.append(ws_message)
                        
                        # Log progress every 100 messages
                        if connection_messages % 100 == 0:
                            logger.info(f"Connection {connection_id}: {connection_messages} messages received")
                    
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"Connection {connection_id} closed unexpectedly")
                        break
                    except Exception as e:
                        logger.error(f"Connection {connection_id} error: {e}")
                        break
                
                logger.info(f"Connection {connection_id} completed: {connection_messages} messages")
                
        except Exception as e:
            logger.error(f"Connection {connection_id} failed: {e}")
            self.reconnection_count += 1
    
    async def stress_test(self, num_connections: int = 5, duration: int = 60):
        """Run stress test with multiple connections"""
        logger.info(f"Starting WebSocket stress test: {num_connections} connections for {duration} seconds")
        
        channels = [
            "ticker.BTC-PERPETUAL.100ms",
            "ticker.ETH-PERPETUAL.100ms",
            "book.BTC-PERPETUAL.100ms.10",
            "trades.BTC-PERPETUAL.100ms"
        ]
        
        # Create multiple concurrent connections
        tasks = []
        for i in range(num_connections):
            task = asyncio.create_task(
                self.single_connection_test(i, channels, duration)
            )
            tasks.append(task)
        
        # Wait for all connections to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Stress test completed")
        self.print_statistics()
    
    async def latency_test(self, duration: int = 30):
        """Test WebSocket latency"""
        logger.info(f"Starting latency test for {duration} seconds")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                await self.authenticate(websocket)
                
                # Subscribe to high-frequency ticker
                await self.subscribe_to_channels(websocket, ["ticker.BTC-PERPETUAL.100ms"])
                
                latencies = []
                start_time = time.time()
                
                while (time.time() - start_time) < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        receive_time = time.time()
                        
                        data = json.loads(message)
                        
                        if ('params' in data and 'data' in data['params'] and 
                            'timestamp' in data['params']['data']):
                            
                            server_timestamp = data['params']['data']['timestamp'] / 1000
                            latency = (receive_time - server_timestamp) * 1000
                            
                            if latency > 0 and latency < 10000:  # Filter unrealistic values
                                latencies.append(latency)
                    
                    except asyncio.TimeoutError:
                        continue
                
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    min_latency = min(latencies)
                    max_latency = max(latencies)
                    
                    logger.info(f"Latency test results:")
                    logger.info(f"  Messages analyzed: {len(latencies)}")
                    logger.info(f"  Average latency: {avg_latency:.2f}ms")
                    logger.info(f"  Min latency: {min_latency:.2f}ms")
                    logger.info(f"  Max latency: {max_latency:.2f}ms")
                else:
                    logger.warning("No valid latency measurements collected")
                    
        except Exception as e:
            logger.error(f"Latency test failed: {e}")
    
    async def tick_by_tick_delay_test(self, duration: int = 60, channels: List[str] = None):
        """Test tick-by-tick delay analysis for subscribed data streams"""
        if channels is None:
            channels = [
                "ticker.BTC-PERPETUAL.100ms",
                "book.BTC-PERPETUAL.100ms.10",
                "trades.BTC-PERPETUAL.100ms"
            ]
        
        logger.info(f"Starting tick-by-tick delay analysis for {duration} seconds")
        logger.info(f"Subscribed channels: {channels}")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                await self.authenticate(websocket)
                await self.subscribe_to_channels(websocket, channels)
                
                # Storage for tick data
                tick_data = {channel: [] for channel in channels}
                start_time = time.time()
                tick_count = 0
                
                logger.info("Starting tick collection...")
                
                while (time.time() - start_time) < duration:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        receive_time = datetime.now()
                        
                        data = json.loads(message)
                        tick_count += 1
                        
                        # Process different message types
                        if 'params' in data and 'channel' in data['params']:
                            channel = data['params']['channel']
                            tick_data_point = data['params']['data']
                            
                            # Calculate delay if timestamp is available
                            delay = None
                            if 'timestamp' in tick_data_point:
                                server_timestamp = tick_data_point['timestamp'] / 1000
                                delay = (receive_time.timestamp() - server_timestamp) * 1000
                            
                            # Store tick information
                            tick_info = {
                                'tick_number': tick_count,
                                'channel': channel,
                                'receive_time': receive_time,
                                'server_timestamp': tick_data_point.get('timestamp'),
                                'delay_ms': delay,
                                'data_size': len(str(data)),
                                'price': tick_data_point.get('last_price') or tick_data_point.get('price'),
                                'volume': tick_data_point.get('volume'),
                                'bid_price': tick_data_point.get('best_bid_price'),
                                'ask_price': tick_data_point.get('best_ask_price')
                            }
                            
                            # Add to channel-specific storage
                            for ch in channels:
                                if ch in channel:
                                    tick_data[ch].append(tick_info)
                                    break
                            
                            # Log every 50 ticks
                            if tick_count % 50 == 0:
                                logger.info(f"Processed {tick_count} ticks, current delay: {delay:.2f}ms" if delay else f"Processed {tick_count} ticks")
                    
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing tick: {e}")
                        continue
                
                # Analyze tick-by-tick data
                self._analyze_tick_data(tick_data, duration)
                
        except Exception as e:
            logger.error(f"Tick-by-tick delay test failed: {e}")
    
    def _analyze_tick_data(self, tick_data: Dict[str, List], duration: int):
        """Analyze collected tick data and generate detailed statistics"""
        logger.info("="*80)
        logger.info("TICK-BY-TICK DELAY ANALYSIS")
        logger.info("="*80)
        
        total_ticks = sum(len(ticks) for ticks in tick_data.values())
        logger.info(f"Total duration: {duration} seconds")
        logger.info(f"Total ticks received: {total_ticks}")
        logger.info(f"Average ticks per second: {total_ticks / duration:.2f}")
        
        for channel, ticks in tick_data.items():
            if not ticks:
                logger.info(f"\n{channel}: No data received")
                continue
            
            logger.info(f"\n📊 Channel: {channel}")
            logger.info(f"Total ticks: {len(ticks)}")
            logger.info(f"Ticks per second: {len(ticks) / duration:.2f}")
            
            # Delay analysis
            delays = [tick['delay_ms'] for tick in ticks if tick['delay_ms'] is not None]
            if delays:
                logger.info(f"\n⏱️  Delay Statistics:")
                logger.info(f"  Average delay: {sum(delays) / len(delays):.2f}ms")
                logger.info(f"  Median delay: {sorted(delays)[len(delays)//2]:.2f}ms")
                logger.info(f"  Min delay: {min(delays):.2f}ms")
                logger.info(f"  Max delay: {max(delays):.2f}ms")
                logger.info(f"  Delay std dev: {self._calculate_std_dev(delays):.2f}ms")
                
                # Delay distribution
                delay_ranges = {
                    "0-50ms": len([d for d in delays if 0 <= d < 50]),
                    "50-100ms": len([d for d in delays if 50 <= d < 100]),
                    "100-200ms": len([d for d in delays if 100 <= d < 200]),
                    "200-500ms": len([d for d in delays if 200 <= d < 500]),
                    "500ms+": len([d for d in delays if d >= 500])
                }
                
                logger.info(f"\n📈 Delay Distribution:")
                for range_name, count in delay_ranges.items():
                    percentage = (count / len(delays)) * 100
                    logger.info(f"  {range_name}: {count} ticks ({percentage:.1f}%)")
            
            # Data size analysis
            data_sizes = [tick['data_size'] for tick in ticks]
            if data_sizes:
                logger.info(f"\n💾 Data Size Statistics:")
                logger.info(f"  Average message size: {sum(data_sizes) / len(data_sizes):.0f} bytes")
                logger.info(f"  Min message size: {min(data_sizes)} bytes")
                logger.info(f"  Max message size: {max(data_sizes)} bytes")
            
            # Price change analysis (for ticker data)
            prices = [tick['price'] for tick in ticks if tick['price'] is not None]
            if len(prices) > 1:
                price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
                non_zero_changes = [pc for pc in price_changes if pc > 0]
                
                logger.info(f"\n💰 Price Movement Analysis:")
                logger.info(f"  Total price updates: {len(prices)}")
                logger.info(f"  Price changes: {len(non_zero_changes)}")
                logger.info(f"  Change frequency: {(len(non_zero_changes) / len(prices)) * 100:.1f}%")
                if non_zero_changes:
                    logger.info(f"  Average price change: {sum(non_zero_changes) / len(non_zero_changes):.2f}")
            
            # Show sample ticks
            logger.info(f"\n🔍 Sample Ticks (first 5):")
            for i, tick in enumerate(ticks[:5]):
                delay_str = f"{tick['delay_ms']:.1f}ms" if tick['delay_ms'] else "N/A"
                price_str = f"${tick['price']:.2f}" if tick['price'] else "N/A"
                logger.info(f"  Tick #{tick['tick_number']}: Delay={delay_str}, Price={price_str}, Size={tick['data_size']}b")
        
        # Overall analysis
        all_delays = []
        for ticks in tick_data.values():
            all_delays.extend([tick['delay_ms'] for tick in ticks if tick['delay_ms'] is not None])
        
        if all_delays:
            logger.info(f"\n🎯 Overall Performance Summary:")
            logger.info(f"Total messages with delay data: {len(all_delays)}")
            logger.info(f"Overall average delay: {sum(all_delays) / len(all_delays):.2f}ms")
            
            # Performance rating
            avg_delay = sum(all_delays) / len(all_delays)
            if avg_delay < 50:
                rating = "EXCELLENT"
            elif avg_delay < 100:
                rating = "GOOD"
            elif avg_delay < 200:
                rating = "FAIR"
            else:
                rating = "POOR"
            
            logger.info(f"Performance Rating: {rating}")
    
    def _calculate_std_dev(self, values):
        """Calculate standard deviation"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    async def reconnection_test(self, disconnection_interval: int = 10, total_duration: int = 60):
        """Test reconnection handling"""
        logger.info(f"Starting reconnection test: disconnect every {disconnection_interval}s for {total_duration}s")
        
        start_time = time.time()
        
        while (time.time() - start_time) < total_duration:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    await self.authenticate(websocket)
                    await self.subscribe_to_channels(websocket, ["ticker.BTC-PERPETUAL.100ms"])
                    
                    # Stay connected for the interval
                    connection_start = time.time()
                    message_count = 0
                    
                    while (time.time() - connection_start) < disconnection_interval:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            message_count += 1
                        except asyncio.TimeoutError:
                            continue
                    
                    logger.info(f"Disconnecting after {message_count} messages...")
                    self.reconnection_count += 1
                    
            except Exception as e:
                logger.error(f"Reconnection test error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
        
        logger.info(f"Reconnection test completed. Total reconnections: {self.reconnection_count}")
    
    def print_statistics(self):
        """Print comprehensive statistics"""
        logger.info("="*60)
        logger.info("WEBSOCKET TEST STATISTICS")
        logger.info("="*60)
        logger.info(f"Total connections: {self.connection_count}")
        logger.info(f"Total messages received: {self.total_messages}")
        logger.info(f"Reconnections: {self.reconnection_count}")
        
        if self.messages:
            # Channel statistics
            channel_counts = {}
            latencies = []
            
            for msg in self.messages:
                channel_counts[msg.channel] = channel_counts.get(msg.channel, 0) + 1
                if msg.latency:
                    latencies.append(msg.latency)
            
            logger.info(f"\nMessages per channel:")
            for channel, count in channel_counts.items():
                logger.info(f"  {channel}: {count}")
            
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                logger.info(f"\nLatency statistics:")
                logger.info(f"  Messages with latency data: {len(latencies)}")
                logger.info(f"  Average latency: {avg_latency:.2f}ms")
                logger.info(f"  Min latency: {min(latencies):.2f}ms")
                logger.info(f"  Max latency: {max(latencies):.2f}ms")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deribit WebSocket Tester')
    parser.add_argument('--test-type', choices=['stress', 'latency', 'reconnection', 'tick-analysis'], 
                       default='stress', help='Type of test to run')
    parser.add_argument('--connections', type=int, default=5, 
                       help='Number of concurrent connections for stress test')
    parser.add_argument('--duration', type=int, default=60, 
                       help='Test duration in seconds')
    parser.add_argument('--disconnect-interval', type=int, default=10,
                       help='Disconnection interval for reconnection test')
    parser.add_argument('--channels', nargs='+', 
                       default=['ticker.BTC-PERPETUAL.100ms', 'book.BTC-PERPETUAL.100ms.10', 'trades.BTC-PERPETUAL.100ms'],
                       help='Channels to subscribe to for tick analysis')
    
    args = parser.parse_args()
    
    tester = DeribitWebSocketTester()
    
    try:
        if args.test_type == 'stress':
            await tester.stress_test(args.connections, args.duration)
        elif args.test_type == 'latency':
            await tester.latency_test(args.duration)
        elif args.test_type == 'reconnection':
            await tester.reconnection_test(args.disconnect_interval, args.duration)
        elif args.test_type == 'tick-analysis':
            await tester.tick_by_tick_delay_test(args.duration, args.channels)
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        tester.print_statistics()

if __name__ == "__main__":
    asyncio.run(main())
