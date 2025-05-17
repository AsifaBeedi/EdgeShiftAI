import threading
import time
import uuid
import zmq
import random
import psutil

class DeviceNode:
    """Represents a device in the network that can process tasks"""
    
    def __init__(self, port=5555, broadcast_port=5556,is_coordinator=False):
        self.id = str(uuid.uuid4())
        self.port = port
        self.broadcast_port = broadcast_port# For discovery
        self.is_coordinator = is_coordinator
        self.device_status = "Initializing"
        self.running = False
        
        # ZeroMQ context
        self.context = zmq.Context()
        
        # For receiving tasks
        self.socket = self.context.socket(zmq.REP)
        
        # For device discovery
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)
        self.sub.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Known devices on the network
        self.network = {}
        
    def start(self):
        """Start the device node"""
        try:
            self.socket.bind(f"tcp://*:{self.port}")
            self.running = True
            self.device_status = "Active"
            
            # Start message handling thread
            threading.Thread(target=self._handle_messages, daemon=True).start()
            
            # Start discovery service if not already running on these ports
            try:
                # Use a try-except block for binding the discovery port
                # Instead of binding to fixed broadcast ports like port+1, 
                # use an alternate port that's less likely to conflict
                self.pub.bind(f"tcp://*:{self.broadcast_port}")
                threading.Thread(target=self._start_discovery, daemon=True).start()
                print(f"Discovery service started on port {self.broadcast_port}")
            except zmq.error.ZMQError as e:
                print(f"Could not bind discovery service to port {self.broadcast_port}: {e}")
                print("Discovery service will not be available, but main functionality should work")
            
            print(f"Device {self.id[:8]} started on port {self.port}")
            return True
        except Exception as e:
            print(f"Failed to start device: {e}")
            self.device_status = "Error"
            return False
    
    def _start_discovery(self):
        """Broadcast device presence and discover others"""
        while self.running:
            try:
                # Broadcast device info
                message = {
                    "type": "discovery",
                    "device_id": self.id,
                    "port": self.port,
                    "status": self.device_status,
                    "is_coordinator": self.is_coordinator
                }
                self.pub.send_json(message)
                time.sleep(2)
            except Exception as e:
                print(f"Discovery error: {e}")
                time.sleep(5)  # Longer delay on error
    
    def _handle_messages(self):
        """Handle incoming messages"""
        while self.running:
            try:
                try:
                    # Set a timeout for polling
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout
                    socks = dict(poller.poll(1000))  # 1 second timeout
                    
                    if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                        message = self.socket.recv_json()
                        response = self._process_message(message)
                        self.socket.send_json(response)
                except zmq.error.Again:
                    # Timeout occurred, just continue loop
                    pass
                
            except Exception as e:
                print(f"Message handling error: {e}")
                time.sleep(0.1)
    
    def _process_message(self, message):
        """Process incoming message"""
        msg_type = message.get("type", "unknown")
        
        if msg_type == "ping":
            return {"status": self.device_status}
        
        elif msg_type == "task":
            # Process task would go here
            # For now, just return success
            return {"status": "completed", "result": "Task processed"}
        
        elif msg_type == "status":
            return {
                "id": self.id,
                "status": self.device_status,
                "profile": self.get_profile()
            }
        
        return {"status": "error", "message": "Unknown message type"}
    
    def get_profile(self):
        """Get device profile including CPU, memory, etc."""
        try:
            profile = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "battery": self._get_battery_level(),
            }
            return profile
        except Exception as e:
            print(f"Error getting profile: {e}")
            return {
                "cpu_percent": random.uniform(10, 90),
                "memory_percent": random.uniform(20, 80),
                "battery": random.uniform(30, 100)
            }
    
    def _get_battery_level(self):
        """Get battery level or simulate one if not available"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return battery.percent
        except:
            pass
        
        # Simulate battery level if not available
        return random.uniform(30, 100)
    
    def stop(self):
        """Stop the device node"""
        self.running = False
        self.device_status = "Stopped"
        time.sleep(0.5)  # Give threads time to close
        self.socket.close()
        self.pub.close()
        self.sub.close()
        print(f"Device {self.id[:8]} stopped")