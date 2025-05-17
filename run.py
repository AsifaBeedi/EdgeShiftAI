import sys
import time
import threading
import argparse
from pathlib import Path

# Add the project directory to the path so we can import local modules
sys.path.append(str(Path(__file__).parent))

from core.device import EdgeDevice

def main():
    """Main entry point for EdgeShift"""
    parser = argparse.ArgumentParser(description="EdgeShift distributed AI processing")
    parser.add_argument("--coordinator", action="store_true", help="Run as coordinator node")
    parser.add_argument("--port", type=int, default=5555, help="Port to run on (default: 5555)")
    parser.add_argument("--broadcast-port", type=int, default=5558, 
                       help="Port to use for discovery broadcasts (default: 5558)")
    args = parser.parse_args()
    
    # Start EdgeShift node
    if args.coordinator:
        print(f"Starting EdgeShift node on port {args.port}...")
        node = EdgeDevice(is_coordinator=True, port=args.port)
        
        # Sleep to initialize the node
        time.sleep(5)
        
        # Start discovery mechanism for coordinator
        peers = node._start_discovery()
        print(f"Discovered {len(peers)} peers:")
        for peer in peers:
            print(f"  - {peer['type']} at {peer['url']}")
            
        print("Running as coordinator node")
        
        # Check device capabilities periodically
        while True:
            print("\nChecking device capabilities...")
            capabilities = node.check_device_capabilities()
            print("Device capability scores:")
            print(f"  - Local node: {capabilities.get('score', 0):.2f}")
            
            # Check connected worker capabilities
            if node.worker_capabilities:
                print("Connected workers:")
                for worker_url, caps in node.worker_capabilities.items():
                    print(f"  - {worker_url}: {caps.get('score', 0):.2f}")
            
            # If we have workers, send a test task
            workers = [p for p in node.peers if p["type"] == "worker"]
            if workers:
                try:
                    print("\nSending test task to a worker...")
                    task_result = node.distribute_task(
                        task_id=f"test-{int(time.time())}", 
                        task_type="echo", 
                        data="Hello from coordinator!"
                    )
                    print(f"Task distributed to {task_result['worker']}")
                except Exception as e:
                    print(f"Error distributing task: {e}")
            
            time.sleep(10)
            
    else:
        # This is a worker node - will receive tasks
        print(f"Starting EdgeShift worker node on port {args.port}...")
        print(f"Using broadcast port {args.broadcast_port} for discovery")
        
        # Initialize worker node
        node = EdgeDevice(is_coordinator=False, port=args.port, broadcast_port=args.broadcast_port)
        
        # Give time for initialization
        time.sleep(5)
        
        # Start discovery mechanism for worker
        peers = node._start_discovery()
        print(f"Discovered {len(peers)} peers:")
        for peer in peers:
            print(f"  - {peer['type']} at {peer['url']}")
        
        print("Running as worker node")
        print("Waiting for tasks...")
        
        # Keep the application running
        try:
            while True:
                # Periodically check capabilities
                capabilities = node.check_device_capabilities()
                print(f"Current capability score: {capabilities.get('score', 0):.2f}")
                
                # Sleep to avoid tight loop
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nShutting down...")

if __name__ == "__main__":
    main()