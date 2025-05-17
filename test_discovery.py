import zmq
import time
import threading
import socket

def run_publisher(port=5556):
    """Run a simple ZMQ publisher on the specified port"""
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")
    
    print(f"Publisher started on port {port}")
    
    count = 0
    try:
        while True:
            message = f"Test message #{count}"
            print(f"Publishing: {message}")
            socket.send_string(message)
            count += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("Publisher stopped")
    finally:
        socket.close()
        context.term()

def run_subscriber(port=5556):
    """Run a simple ZMQ subscriber connecting to localhost on the specified port"""
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt_string(zmq.SUBSCRIBE, "")
    socket.connect(f"tcp://localhost:{port}")
    
    print(f"Subscriber started, connecting to localhost:{port}")
    
    try:
        while True:
            try:
                message = socket.recv_string(flags=zmq.NOBLOCK)
                print(f"Received: {message}")
            except zmq.Again:
                # No message available yet
                pass
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Subscriber stopped")
    finally:
        socket.close()
        context.term()

if __name__ == "__main__":
    # Start publisher and subscriber in separate threads
    pub_thread = threading.Thread(target=run_publisher, args=(5557,), daemon=True)
    sub_thread = threading.Thread(target=run_subscriber, args=(5557,), daemon=True)
    
    pub_thread.start()
    sub_thread.start()
    
    print("Test running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Test stopped")