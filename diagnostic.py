# Diagnostic Tool for EdgeShift
# Save this as diagnostic.py

import zmq
import socket
import time
import argparse
import json

def run_diagnostics(target_port=5556):
    """Run network diagnostics to check if ZeroMQ pub/sub is working correctly"""
    print(f"Running EdgeShift diagnostics...")
    
    # Get network information
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"Local hostname: {hostname}")
    print(f"Local IP: {local_ip}")
    
    # Try to create a ZMQ subscriber to test reception
    context = zmq.Context()
    sub = context.socket(zmq.SUB)
    sub.setsockopt_string(zmq.SUBSCRIBE, "")
    sub.connect(f"tcp://127.0.0.1:{target_port}")
    
    print(f"Listening for broadcasts on port {target_port}...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            try:
                # Try to receive a message with timeout
                sub.RCVTIMEO = 1000  # 1 second timeout
                message = sub.recv_json()
                print(f"Received message: {message}")
            except zmq.error.Again:
                print("No message received (timeout)")
            except Exception as e:
                print(f"Error: {str(e)}")
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("Diagnostics stopped")
    finally:
        sub.close()
        context.term()

def send_test_message(port=5556):
    """Send a test broadcast message"""
    context = zmq.Context()
    pub = context.socket(zmq.PUB)
    pub.bind(f"tcp://*:{port}")
    
    print(f"Sending test message on port {port}...")
    
    # Wait for connections to establish
    time.sleep(1)
    
    # Send test message
    message = {
        'type': 'diagnostic_test',
        'id': 'test_sender',
        'timestamp': time.time()
    }
    
    pub.send_json(message)
    print(f"Test message sent: {message}")
    
    # Keep socket open briefly to ensure message is sent
    time.sleep(1)
    pub.close()
    context.term()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='EdgeShift Diagnostics')
    parser.add_argument('--listen', action='store_true',
                        help='Listen for broadcast messages')
    parser.add_argument('--send', action='store_true',
                        help='Send a test broadcast message')
    parser.add_argument('--port', type=int, default=5556,
                        help='Port to use for testing')
    
    args = parser.parse_args()
    
    if args.listen:
        run_diagnostics(args.port)
    elif args.send:
        send_test_message(args.port)
    else:
        print("Please specify either --listen or --send")