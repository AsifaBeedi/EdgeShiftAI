import zmq
import time
import threading
import socket
import json
import psutil
import os
import platform
import uuid

class EdgeDevice:
    def __init__(self, is_coordinator=False, port=5555, broadcast_port=5558):
        """Initialize an EdgeDevice instance
        
        Args:
            is_coordinator (bool): Whether this is a coordinator node
            port (int): Port to run the device on
            broadcast_port (int): Port to use for discovery broadcasts
        """
        self.is_coordinator = is_coordinator
        self.port = port
        self.broadcast_port = broadcast_port
        self.address = self._get_local_ip()
        self.node_id = str(uuid.uuid4())
        self.capabilities = self.check_device_capabilities()
        self.peers = []
        self.peer_connections = {}
        self.worker_capabilities = {}
        self._discovery_active = False
        
        # Start ZeroMQ context
        self.context = zmq.Context()
        
        # Set up main socket based on node type
        if is_coordinator:
            # Coordinator uses REP socket to receive registration and task requests
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{port}")
            print(f"Coordinator listening on port {port}")
        else:
            # Worker uses REP socket to receive tasks from coordinator
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{port}")
            print(f"Worker listening on port {port}")
            
        # Start message handling thread
        self._start_message_handler()
    
    def _get_local_ip(self):
        """Get the local IP address"""
        try:
            # Create a socket to determine the outgoing IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def check_device_capabilities(self):
        """Check the capabilities of this device"""
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_total_gb = memory.total / (1024 ** 3)
        memory_available_gb = memory.available / (1024 ** 3)
        
        # Check for GPU (simplified)
        has_gpu = False
        try:
            # This is a simple check that might work on some systems
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
                has_gpu = result.returncode == 0
            elif platform.system() == "Linux":
                has_gpu = os.path.exists("/dev/nvidia0")
        except:
            pass
        
        # Calculate capability score (simple example)
        score = (cpu_count * (100 - cpu_percent) / 100) + (memory_available_gb * 5)
        if has_gpu:
            score *= 2
        
        capabilities = {
            "cpu_count": cpu_count,
            "cpu_percent": cpu_percent,
            "memory_total_gb": memory_total_gb,
            "memory_available_gb": memory_available_gb,
            "has_gpu": has_gpu,
            "system": platform.system(),
            "score": score
        }
        
        return capabilities
    
    def _start_message_handler(self):
        """Start a thread to handle incoming messages"""
        def message_loop():
            while True:
                try:
                    # Wait for incoming message with a timeout
                    message = self.socket.recv_json(flags=zmq.NOBLOCK)
                    
                    # Process the message
                    response = self._process_message(message)
                    
                    # Send response back
                    self.socket.send_json(response)
                except zmq.error.Again:
                    # No message available, continue
                    pass
                except Exception as e:
                    print(f"Error handling message: {e}")
                
                # Sleep briefly to avoid tight loop
                time.sleep(0.1)
        
        # Start the message handling thread
        threading.Thread(target=message_loop, daemon=True).start()
    
    def _process_message(self, message):
        """Process an incoming message and return the response"""
        action = message.get("action", "")
        
        if action == "ping":
            # Simple ping response
            return {"status": "ok", "node_type": "coordinator" if self.is_coordinator else "worker"}
        
        elif action == "register" and self.is_coordinator:
            # Handle worker registration
            node_type = message.get("node_type")
            address = message.get("address")
            port = message.get("port")
            capabilities = message.get("capabilities", {})
            
            if node_type == "worker":
                worker_url = f"tcp://{address}:{port}"
                print(f"Worker registered: {worker_url}")
                
                # Add to peers if not already there
                if worker_url not in [p["url"] for p in self.peers]:
                    self.peers.append({
                        "url": worker_url,
                        "type": "worker",
                        "address": address,
                        "port": port,
                        "capabilities": capabilities
                    })
                    
                    # Store worker capabilities
                    self.worker_capabilities[worker_url] = capabilities
                    
                    # Set up connection to worker
                    self._setup_connection_to_peer(self.peers[-1])
                
                return {"status": "registered", "coordinator_id": self.node_id}
            
            return {"status": "error", "message": "Invalid registration"}
        
        elif action == "task" and not self.is_coordinator:
            # Handle incoming task for worker
            task_id = message.get("task_id", "unknown")
            payload = message.get("payload", {})
            
            print(f"Received task {task_id}: {payload}")
            
            # Process task based on type
            task_type = payload.get("type", "")
            if task_type == "echo":
                # Simple echo task
                result = payload.get("data", "")
            else:
                # Unknown task type
                result = f"Unknown task type: {task_type}"
            
            return {
                "status": "completed",
                "task_id": task_id,
                "result": result
            }
            
        # Default response for unknown actions
        return {"status": "error", "message": f"Unknown action: {action}"}
    
    def _discover_peers(self):
        """Discover peers on the network by listening for broadcast messages"""
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        
        # Subscribe to all messages
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Critical: Set receive timeout to avoid blocking forever
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Bind to the broadcast port
        broadcast_port = self.port + 1 if self.is_coordinator else self.broadcast_port
        try:
            # Listen on all interfaces for discovery broadcasts
            socket.bind(f"tcp://*:{broadcast_port}")
            print(f"Listening for peer discovery on port {broadcast_port}")
        except zmq.error.ZMQError as e:
            print(f"Error binding to broadcast port {broadcast_port}: {e}")
            return []
        
        # Set a time limit for discovery
        start_time = time.time()
        discovery_time = 10  # seconds
        
        peers = []
        
        print(f"Discovering peers for {discovery_time} seconds...")
        
        while time.time() - start_time < discovery_time:
            try:
                # Attempt to receive a message
                message = socket.recv_json()
                peer_info = message.get("peer_info", {})
                peer_addr = peer_info.get("address")
                peer_port = peer_info.get("port")
                peer_type = peer_info.get("type")
                
                if peer_addr and peer_port:
                    # Skip self-identification
                    if (peer_addr == self.address or peer_addr == "localhost" or 
                        peer_addr == "127.0.0.1") and peer_port == self.port:
                        continue
                    
                    # Add to peers list if not already there
                    peer_url = f"tcp://{peer_addr}:{peer_port}"
                    if peer_url not in [p["url"] for p in peers]:
                        print(f"Discovered {peer_type} peer at {peer_url}")
                        peers.append({
                            "url": peer_url,
                            "type": peer_type,
                            "address": peer_addr,
                            "port": peer_port
                        })
            except zmq.error.Again:
                # Timeout, continue looping
                pass
            except Exception as e:
                print(f"Error during peer discovery: {e}")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
        
        print(f"Discovered {len(peers)} peers")
        socket.close()
        return peers
    
    def _broadcast_presence(self):
        """Broadcast this node's presence on the network"""
        context = zmq.Context()
        socket = context.socket(zmq.PUB)

        # For workers, send to coordinator's broadcast port
        # For coordinator, send to worker's broadcast port
        target_port = self.broadcast_port if self.is_coordinator else self.port + 1
        
        print(f"Broadcasting presence to port {target_port}...")
        
        # Use broadcast address to send to all potential listeners
        socket.connect(f"tcp://localhost:{target_port}")
        
        # Allow time for connection to establish
        time.sleep(1)
        
        # Prepare peer information message
        peer_info = {
            "address": self.address,
            "port": self.port,
            "type": "coordinator" if self.is_coordinator else "worker",
            "capabilities": self.capabilities,
            "timestamp": time.time()
        }
        
        message = {
            "peer_info": peer_info,
            "action": "discovery"
        }
        
        # Send a few times to increase chances of receipt
        for i in range(5):  # Try 5 times
            try:
                socket.send_json(message)
                print(f"Broadcast attempt {i+1}: Sent presence announcement")
                time.sleep(0.5)  # Small delay between sends
            except Exception as e:
                print(f"Error broadcasting presence: {e}")
        
        # Also try broadcasting on loopback explicitly for same-machine discovery
        if not self.address == "localhost" and not self.address == "127.0.0.1":
            # Try connecting to localhost explicitly as a backup
            try:
                alt_socket = context.socket(zmq.PUB)
                alt_socket.connect(f"tcp://127.0.0.1:{target_port}")
                time.sleep(1)  # Allow time for connection
                
                # Update peer info with localhost address
                local_peer_info = peer_info.copy()
                local_peer_info["address"] = "127.0.0.1"
                
                local_message = {
                    "peer_info": local_peer_info,
                    "action": "discovery"
                }
                
                for i in range(3):
                    alt_socket.send_json(local_message)
                    print(f"Local broadcast attempt {i+1}: Sent presence on localhost")
                    time.sleep(0.5)
                
                alt_socket.close()
            except Exception as e:
                print(f"Error broadcasting on localhost: {e}")
        
        socket.close()
    
    def _start_discovery(self):
        """Set up peer discovery mechanism"""
        if not self._discovery_active:
            # First attempt direct connection to well-known coordinator if we're a worker
            if not self.is_coordinator:
                # Try both localhost and IP variants
                coordinator_hosts = ["localhost", "127.0.0.1"]
                if self.address != "localhost" and self.address != "127.0.0.1":
                    coordinator_hosts.append(self.address)
                
                for host in coordinator_hosts:
                    coordinator_url = f"tcp://{host}:5555"  # Assuming coordinator is on default port 5555
                    print(f"Worker attempting direct connection to coordinator at {coordinator_url}")
                    try:
                        # Test if coordinator is reachable
                        context = zmq.Context()
                        socket = context.socket(zmq.REQ)
                        socket.setsockopt(zmq.LINGER, 0)
                        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
                        socket.connect(coordinator_url)
                        socket.send_json({"action": "ping"})
                        response = socket.recv_json()
                        
                        if response.get("status") == "ok":
                            print(f"Connected directly to coordinator at {coordinator_url}")
                            # Add coordinator to peers
                            self.peers.append({
                                "url": coordinator_url,
                                "type": "coordinator",
                                "address": host,
                                "port": 5555
                            })
                            socket.close()
                            break
                        socket.close()
                    except Exception as e:
                        print(f"Could not connect directly to coordinator at {coordinator_url}: {e}")
                        # Continue to next host or to broadcast discovery
            
            # Broadcast our presence first to let others know about us
            self._broadcast_presence()
            
            # Then discover others on the network
            discovered_peers = self._discover_peers()
            
            # Add newly discovered peers to our list if not already there
            for peer in discovered_peers:
                if peer["url"] not in [p["url"] for p in self.peers]:
                    self.peers.append(peer)
            
            print(f"Total peers after discovery: {len(self.peers)}")
            self._setup_connections()
            
            # Mark discovery as active
            self._discovery_active = True
            
            # Start continuous discovery thread for workers
            if not self.is_coordinator:
                self._start_continuous_discovery()
        
        return self.peers
    
    def _start_continuous_discovery(self):
        """Start a thread for continuous peer discovery (only for worker nodes)"""
        if hasattr(self, '_continuous_discovery_thread') and self._continuous_discovery_thread.is_alive():
            return  # Already running
        
        def discovery_loop():
            while self._discovery_active:
                # Broadcast presence and look for new peers periodically
                self._broadcast_presence()
                new_peers = self._discover_peers()
                
                # Add newly discovered peers
                for peer in new_peers:
                    if peer["url"] not in [p["url"] for p in self.peers]:
                        print(f"Found new peer: {peer['url']}")
                        self.peers.append(peer)
                        self._setup_connection_to_peer(peer)
                
                # Wait before next discovery cycle
                time.sleep(30)  # Check every 30 seconds
        
        self._continuous_discovery_thread = threading.Thread(target=discovery_loop)
        self._continuous_discovery_thread.daemon = True
        self._continuous_discovery_thread.start()
        print("Started continuous discovery thread")
    
    def _setup_connections(self):
        """Set up connections to all discovered peers"""
        for peer in self.peers:
            self._setup_connection_to_peer(peer)

    def _setup_connection_to_peer(self, peer):
        """Set up connection to a specific peer"""
        context = zmq.Context()
        
        try:
            # Different connection setup based on peer type
            if peer["type"] == "coordinator" and not self.is_coordinator:
                # Workers connect to coordinator with REQ socket for tasks
                socket = context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 1000)
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second receive timeout
                socket.connect(peer["url"])
                
                # Register with coordinator
                registration = {
                    "action": "register",
                    "node_type": "worker",
                    "address": self.address,
                    "port": self.port,
                    "capabilities": self.capabilities
                }
                
                print(f"Registering with coordinator at {peer['url']}")
                socket.send_json(registration)
                
                try:
                    response = socket.recv_json()
                    if response.get("status") == "registered":
                        print(f"Successfully registered with coordinator at {peer['url']}")
                    else:
                        print(f"Failed to register with coordinator: {response.get('message', 'Unknown error')}")
                except zmq.error.Again:
                    print(f"Timeout waiting for registration response from coordinator")
                
                # Store the socket reference
                self.peer_connections[peer["url"]] = socket
                
            elif peer["type"] == "worker" and self.is_coordinator:
                # Coordinator connects to workers with PUSH socket for task distribution
                socket = context.socket(zmq.PUSH)
                socket.setsockopt(zmq.LINGER, 1000)
                socket.connect(peer["url"])
                
                print(f"Coordinator connected to worker at {peer['url']}")
                self.peer_connections[peer["url"]] = socket
                
                # Record worker capabilities
                self.worker_capabilities[peer["url"]] = peer.get("capabilities", {})
            
            else:
                # For other peer types or coordinator-to-coordinator connections
                print(f"No connection setup needed for peer type: {peer['type']}")
        
        except Exception as e:
            print(f"Error setting up connection to peer {peer['url']}: {e}")
    
    def send_task_to_worker(self, worker_url, task_id, task_type, data):
        """Send a task to a specific worker"""
        if not self.is_coordinator:
            raise Exception("Only coordinator nodes can send tasks to workers")
        
        if worker_url not in self.peer_connections:
            raise Exception(f"No connection to worker at {worker_url}")
        
        # Create task message
        task = {
            "action": "task",
            "task_id": task_id,
            "payload": {
                "type": task_type,
                "data": data
            }
        }
        
        # Send task to worker
        socket = self.peer_connections[worker_url]
        socket.send_json(task)
        
        print(f"Sent {task_type} task {task_id} to worker at {worker_url}")
    
    def distribute_task(self, task_id, task_type, data):
        """Distribute a task to the most suitable worker"""
        if not self.is_coordinator:
            raise Exception("Only coordinator nodes can distribute tasks")
        
        if not self.peers:
            raise Exception("No workers available to process task")
        
        # Filter peers to only include workers
        workers = [p for p in self.peers if p["type"] == "worker"]
        
        if not workers:
            raise Exception("No worker nodes available")
        
        # Select the worker with the highest capability score
        # (A more sophisticated selection strategy could be implemented)
        selected_worker = max(workers, key=lambda w: 
                           self.worker_capabilities.get(w["url"], {}).get("score", 0))
        
        # Send the task to the selected worker
        worker_url = selected_worker["url"]
        self.send_task_to_worker(worker_url, task_id, task_type, data)
        
        return {
            "task_id": task_id,
            "worker": worker_url
        }