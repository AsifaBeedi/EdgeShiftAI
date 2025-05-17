import gradio as gr
import time
import threading
import random
import json
import zmq
import pandas as pd
import numpy as np
from PIL import Image
import os
# Mock DeviceNode, TaskScheduler, and ModelInterface classes for standalone module
# In your actual code, you'd import these from their respective modules
class DeviceNode:
    def __init__(self, port=5555, is_coordinator=False):
        self.port = port
        self.is_coordinator = is_coordinator
        self.id = f"device_{random.randint(1000, 9999)}"
        self.device_status = "Active"
        
    def start(self):
        print(f"DeviceNode started on port {self.port}")
        
    def stop(self):
        print(f"DeviceNode stopped on port {self.port}")
        
    def get_profile(self):
        return {
            "cpu_percent": random.uniform(10, 90),
            "memory_percent": random.uniform(20, 80),
            "battery": random.uniform(30, 100)
        }

class TaskScheduler:
    def __init__(self, device):
        self.device = device
        
class ModelInterface:
    def __init__(self):
        pass


def create_interface(core):
    """Create enhanced Gradio interface"""
    with gr.Blocks(title="EdgeShift: Distributed Edge Computing", theme="soft") as app:
        gr.Markdown("""
        # 📡 EdgeShift: Distributed Image Processing
        *Harness the power of distributed edge computing for image analysis*
        """)
        
        with gr.Tabs():
            # Network Status Tab - Enhanced
            with gr.Tab("🔄 Network Status"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("### 📊 Real-time Device Status")
                        device_table = gr.Dataframe(
                            headers=["Device", "Status", "CPU", "Memory", "Battery"],
                            interactive=False,
                            elem_id="device_table"
                        )
                        
                        with gr.Row():
                            refresh_btn = gr.Button("🔄 Refresh", variant="secondary")
                            # Add auto-refresh toggle
                            auto_refresh = gr.Checkbox(label="Auto-refresh (3s)", value=True)
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 📈 Network Overview")
                        stats = gr.JSON(label="Network Statistics")
                        
                        # Add network health indicator
                        with gr.Row():
                            health_indicator = gr.Label(label="Network Health")
                            connectivity_status = gr.StatusTracker(label="Connectivity")
                
                # Enhanced graph section
                gr.Markdown("### 📊 Network Activity Monitor")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        # Network activity plot - improved with dynamic updates
                        activity_plot = gr.LinePlot(
                            x="time", 
                            y=["Active", "Tasks", "Load"],
                            title="Network Activity",
                            x_title="Time",
                            y_title="Count/Percentage",
                            height=300,
                            width=600
                        )
                    
                    with gr.Column(scale=1):
                        # Add a device distribution chart
                        device_pie = gr.Plot(label="Device Distribution")
                        
                        # Refresh both charts with one button
                        refresh_plot_btn = gr.Button("📊 Update Charts", variant="primary")
            
            # Processing Tab - Enhanced with image display
            with gr.Tab("🖼️ Image Processing"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### 📷 Image Input")
                        # Allow both file upload and text path
                        with gr.Tab("Upload"):
                            image_upload = gr.Image(type="pil", label="Upload Image")
                        
                        with gr.Tab("Path"):
                            image_path = gr.Textbox(label="Image Path")
                        
                        process_btn = gr.Button("🚀 Process Image", variant="primary")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔍 Image Preview")
                        image_preview = gr.Image(label="Selected Image")
                
                gr.Markdown("### 📋 Processing Results")
                
                with gr.Row():
                    with gr.Column():
                        result_text = gr.Textbox(label="Results Summary", lines=4)
                        assignments_table = gr.Dataframe(
                            headers=["Device", "Tasks", "Performance Score"],
                            interactive=False,
                            elem_id="assignments_table"
                        )
                    
                    with gr.Column():
                        detailed_results = gr.JSON(label="Detailed Detection Results")
                        # Add visualization of object detection results
                        detection_image = gr.Image(label="Detection Results")
        
        # Event handlers
        def update_health_indicator():
            """Update network health indicator"""
            devices = core.get_device_status()
            active_count = len([d for d in devices if d[1] == 'Active'])
            total = len(devices)
            
            if total == 0:
                return "No Devices", "warning"
            
            health_percent = (active_count / total) * 100
            
            if health_percent > 80:
                return f"Excellent ({active_count}/{total} devices)", "success"
            elif health_percent > 50:
                return f"Good ({active_count}/{total} devices)", "secondary"
            elif health_percent > 30:
                return f"Fair ({active_count}/{total} devices)", "warning"
            else:
                return f"Poor ({active_count}/{total} devices)", "error"
        
        def update_network_stats():
            """Get updated network statistics"""
            devices = core.get_device_status()
            active_count = len([d for d in devices if d[1] == 'Active'])
            disconnected = len([d for d in devices if d[1] == 'Disconnected'])
            
            # Generate more comprehensive stats
            return {
                "total_devices": len(devices),
                "active_devices": active_count,
                "disconnected_devices": disconnected,
                "network_health": f"{(active_count/max(1, len(devices))*100):.1f}%",
                "last_updated": time.strftime("%H:%M:%S"),
                "pending_tasks": random.randint(0, 5),  # Sample data (would be real in full impl)
                "average_latency": f"{random.uniform(5, 50):.1f}ms"  # Sample data
            }
        
        def update_device_distribution():
            """Update the device distribution pie chart"""
            import matplotlib.pyplot as plt
            import numpy as np
            
            devices = core.get_device_status()
            
            # Count devices by status
            status_counts = {}
            for device in devices:
                status = device[1]
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
                
            # Create pie chart
            fig, ax = plt.subplots(figsize=(4, 4))
            
            if status_counts:
                labels = list(status_counts.keys())
                sizes = list(status_counts.values())
                colors = ['#4CAF50', '#FFC107', '#F44336'][:len(labels)]
                
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
                plt.title('Device Status Distribution')
            else:
                ax.text(0.5, 0.5, 'No device data available', 
                       horizontalalignment='center', verticalalignment='center')
                
            return fig
        
        def update_activity_plot():
            """Update the network activity plot with more metrics"""
            # Create a DataFrame with historical data
            # In a real app, you'd store this data in a database or file
            times = []
            active_devices = []
            tasks = []
            loads = []
            
            # Generate some sample data for the past few minutes
            for i in range(10):
                past_time = time.time() - (9-i) * 30  # 30 seconds intervals
                times.append(time.strftime("%H:%M:%S", time.localtime(past_time)))
                active_devices.append(random.randint(1, 3))  # Sample data
                tasks.append(random.randint(0, 5))  # Sample data
                loads.append(random.uniform(20, 80))  # Sample data
            
            # Add current time data
            current_time = time.strftime("%H:%M:%S")
            current_active = len([d for d in core.get_device_status() if d[1] == 'Active'])
            
            times.append(current_time)
            active_devices.append(current_active)
            tasks.append(random.randint(0, current_active * 3))  # Sample data
            loads.append(random.uniform(20, 80))  # Sample data
            
            return pd.DataFrame({
                "time": times,
                "Active": active_devices,
                "Tasks": tasks,
                "Load": loads
            })
        
        def handle_image_selection(upload_img, path_str):
            """Handle image selection from either upload or path"""
            if upload_img is not None:
                # Use the uploaded image
                return upload_img
            elif path_str and os.path.exists(path_str):
                # Use the image from the provided path
                try:
                    return Image.open(path_str)
                except Exception as e:
                    return None
            return None
        
        def process_image_wrapper(upload_img, path_str):
            """Wrapper for the process_image function that handles both upload and path"""
            image = handle_image_selection(upload_img, path_str)
            
            if image is None:
                return "No valid image provided", {}, [], None, None
            
            # Save temporary file if uploaded image
            temp_path = ""
            if upload_img is not None and path_str == "":
                temp_path = "temp_uploaded_image.jpg"
                image.save(temp_path)
                path_to_use = temp_path
            else:
                path_to_use = path_str
            
            # Call the core processing function
            result_text, detailed_results, assignment_display = core.process_image(path_to_use)
            
            # Create detection visualization
            detection_result = create_detection_visualization(image, detailed_results)
            
            # Clean up temp file
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                
            return result_text, detailed_results, assignment_display, image, detection_result
        
        def create_detection_visualization(image, results):
            """Create a visualization of detection results"""
            if image is None or not results:
                return None
                
            # This is a placeholder - in a real implementation you would
            # draw bounding boxes based on actual detection coordinates
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle
            
            # Create a copy of the image for drawing
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.imshow(np.array(image))
            
            # Draw simulated detections
            detections = results.get("detections", [])
            for i, det in enumerate(detections):
                # Generate random positions for demo purposes
                # In real app, these would come from actual detection coordinates
                x = random.uniform(0.1, 0.9) * image.width
                y = random.uniform(0.1, 0.9) * image.height
                w = random.uniform(50, 150)
                h = random.uniform(50, 150)
                
                label = f"{det.get('class', 'unknown')}: {det.get('confidence', 0):.2f}"
                color = 'r' if det.get('confidence', 0) > 0.8 else 'y'
                
                # Add bounding box
                rect = Rectangle((x, y), w, h, linewidth=2, edgecolor=color, facecolor='none')
                ax.add_patch(rect)
                
                # Add label
                plt.text(x, y-5, label, color='white', fontsize=12, 
                         bbox=dict(facecolor=color, alpha=0.7))
            
            plt.title(f"{len(detections)} objects detected")
            plt.axis('off')
            
            return fig
        
        # Connect event handlers
        refresh_btn.click(
            fn=lambda: (core.get_device_status(), update_network_stats(), update_health_indicator()),
            outputs=[device_table, stats, health_indicator]
        )
        
        refresh_plot_btn.click(
            fn=lambda: (update_activity_plot(), update_device_distribution()),
            outputs=[activity_plot, device_pie]
        )
        
        # Handle both image upload and path
        image_path.change(
            fn=lambda p: handle_image_selection(None, p),
            inputs=[image_path],
            outputs=[image_preview]
        )
        
        image_upload.change(
            fn=lambda img: img,
            inputs=[image_upload],
            outputs=[image_preview]
        )
        
        process_btn.click(
            fn=process_image_wrapper,
            inputs=[image_upload, image_path],
            outputs=[result_text, detailed_results, assignments_table, image_preview, detection_image]
        )
        
        # Auto-refresh functionality based on checkbox
        def conditional_refresh():
            if auto_refresh.value:
                return (
                    core.get_device_status(),
                    update_network_stats(),
                    update_health_indicator(),
                    update_activity_plot()
                )
            else:
                # Return current values if auto-refresh is disabled
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update()
                )
        
        # Setup app events
        app.load(
            fn=lambda: (
                core.get_device_status(),
                update_network_stats(), 
                update_health_indicator(),
                update_activity_plot(),
                update_device_distribution()
            ),
            outputs=[device_table, stats, health_indicator, activity_plot, device_pie]
        )
        
        # Add interval refresh that respects the auto-refresh toggle
        app.load(
            fn=conditional_refresh,
            outputs=[device_table, stats, health_indicator, activity_plot],
            every=3
        )
        
        # Enable queue for responsiveness
        app.queue()
        
        return app

# Define EdgeShiftCore class here to fix import issue
class EdgeShiftCore:
    def __init__(self, zmq_port=5555):
        # ZeroMQ setup
        self.context = zmq.Context()
        
        # Main device setup
        self.main_device = DeviceNode(port=zmq_port, is_coordinator=True)
        self.main_device.start()
        
        # Peer connections
        self.peers = {}  # Format: {peer_id: {'port': int, 'socket': zmq.Socket}}
        self.peer_lock = threading.Lock()
        
        # System components
        self.scheduler = TaskScheduler(self.main_device)
        self.model = ModelInterface()
        self.running = True
        
        # Start services
        threading.Thread(target=self._discover_peers, daemon=True).start()
        threading.Thread(target=self._monitor_peers, daemon=True).start()

    def _discover_peers(self):
        """Discover and connect to peer devices"""
        while self.running:
            # In a real system, this would use broadcast discovery
            # For demo, we'll simulate finding peers on ports 5556 and 5557
            for peer_port in [5556, 5557]:
                peer_id = f"peer_{peer_port}"
                
                if peer_id not in self.peers and peer_port != self.main_device.port:
                    try:
                        socket = self.context.socket(zmq.REQ)
                        socket.connect(f"tcp://localhost:{peer_port}")
                        socket.setsockopt(zmq.LINGER, 0)
                        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
                        
                        with self.peer_lock:
                            self.peers[peer_id] = {
                                'port': peer_port,
                                'socket': socket,
                                'status': 'Active',
                                'last_seen': time.time()
                            }
                        print(f"Connected to peer {peer_id}")
                    except Exception as e:
                        print(f"Failed to connect to peer on port {peer_port}: {e}")
            
            time.sleep(5)

    def _monitor_peers(self):
        """Monitor peer connections and status"""
        while self.running:
            with self.peer_lock:
                to_remove = []
                for peer_id, peer in self.peers.items():
                    try:
                        # Send heartbeat
                        peer['socket'].send_json({'type': 'ping'})
                        response = peer['socket'].recv_json()
                        peer['status'] = response.get('status', 'Unknown')
                        peer['last_seen'] = time.time()
                    except Exception as e:
                        print(f"Peer {peer_id} unreachable: {e}")
                        peer['status'] = 'Disconnected'
                        if time.time() - peer['last_seen'] > 10:  # 10s timeout
                            to_remove.append(peer_id)
                
                # Remove dead peers
                for peer_id in to_remove:
                    self.peers[peer_id]['socket'].close()
                    del self.peers[peer_id]
                    print(f"Removed peer {peer_id}")
            
            time.sleep(3)

    def _send_to_peer(self, peer_id, task):
        """Send task to peer device"""
        with self.peer_lock:
            if peer_id not in self.peers:
                return None
            
            try:
                peer = self.peers[peer_id]
                peer['socket'].send_json({
                    'type': 'task',
                    'task': task
                })
                return peer['socket'].recv_json()
            except Exception as e:
                print(f"Failed to send task to {peer_id}: {e}")
                return None

    def process_image(self, image_path):
        """Process image with real distributed processing"""
        try:
            if not image_path.strip():
                return "No image provided", {}, []
            
            # Create partitions
            partitions = [
                {"id": f"part_{i}", "weight": random.randint(1, 3), "data": "..."}
                for i in range(3)  # 3 partitions
            ]
            
            # Distribute tasks
            assignments = self._distribute_tasks(partitions)
            
            # Process tasks
            results = {}
            start_time = time.time()
            
            for peer_id, tasks in assignments.items():
                if peer_id == "local":
                    results[peer_id] = self._process_local(tasks)
                else:
                    peer_result = self._send_to_peer(peer_id, tasks)
                    if peer_result:
                        results[peer_id] = peer_result
            
            # Format results
            return self._format_results(results, assignments, time.time() - start_time)
            
        except Exception as e:
            return f"Error: {str(e)}", {}, []

    def _distribute_tasks(self, partitions):
        """Distribute tasks based on device capabilities"""
        capabilities = {
            "local": self._calculate_capability(self.main_device)
        }
        
        # Get peer capabilities
        with self.peer_lock:
            for peer_id, peer in self.peers.items():
                if peer['status'] == 'Active':
                    capabilities[peer_id] = self._estimate_peer_capability(peer)
        
        # Sort devices by capability
        sorted_devices = sorted(capabilities.items(), key=lambda x: -x[1])
        sorted_partitions = sorted(partitions, key=lambda x: -x['weight'])
        
        # Assign tasks
        assignments = {}
        for partition in sorted_partitions:
            for dev_id, _ in sorted_devices:
                if dev_id not in assignments:
                    assignments[dev_id] = []
                assignments[dev_id].append(partition)
                break
        
        return assignments

    def _calculate_capability(self, device):
        """Calculate capability score for main device"""
        profile = device.get_profile()
        return (profile.get('cpu_percent', 0) * 0.5 + 
               (100 - profile.get('memory_percent', 0)) * 0.3 +
               profile.get('battery', 0) * 0.2)

    def _estimate_peer_capability(self, peer):
        """Estimate capability for peer devices"""
        # In a real system, peers would report their capabilities
        # For demo, we'll use random values
        return random.uniform(30, 80)

    def _process_local(self, tasks):
        """Process tasks locally"""
        time.sleep(0.5 * sum(t['weight'] for t in tasks))
        return {
            "detections": [
                {"class": random.choice(["cat", "dog", "car"]), 
                 "confidence": round(random.uniform(0.7, 0.95), 2)}
                for _ in tasks
            ]
        }

    def _format_results(self, results, assignments, processing_time):
        """Format results for display"""
        all_detections = []
        for res in results.values():
            all_detections.extend(res.get("detections", []))
        
        assignment_display = []
        for dev_id, tasks in assignments.items():
            name = "Local" if dev_id == "local" else f"Peer {dev_id}"
            assignment_display.append([name, len(tasks), "N/A"])  # Capability would be real in full impl
        
        result_text = (
            f"Processing completed in {processing_time:.2f}s\n"
            f"Devices used: {len(assignments)}\n"
            f"Objects found: {len(all_detections)}"
        )
        
        detailed_results = {
            "processing_time": processing_time,
            "detections": all_detections,
            "devices_used": list(assignments.keys())
        }
        
        return result_text, detailed_results, assignment_display

    def get_device_status(self):
        """Get current device status"""
        devices = []
        
        # Main device
        profile = self.main_device.get_profile()
        devices.append([
            f"{self.main_device.id[:8]} (local)",
            self.main_device.device_status,
            f"{profile.get('cpu_percent', 0):.1f}%",
            f"{profile.get('memory_percent', 0):.1f}%",
            f"{profile.get('battery', 0):.1f}%"
        ])
        
        # Peer devices
        with self.peer_lock:
            for peer_id, peer in self.peers.items():
                devices.append([
                    peer_id,
                    peer['status'],
                    "N/A",  # Would be real data in full impl
                    "N/A",
                    "N/A"
                ])
        
        return devices

    def update_plot_data(self):
        """Get data for plot"""
        active_devices = len([d for d in self.get_device_status() if d[1] == 'Active'])
        return pd.DataFrame({
            "time": [time.strftime("%H:%M:%S")],
            "Active": [active_devices]
        })

    def stop(self):
        """Clean shutdown"""
        self.running = False
        with self.peer_lock:
            for peer in self.peers.values():
                peer['socket'].close()
        self.main_device.stop()

def run_peer(port):
    """Run a peer device instance (for testing)"""
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    
    try:
        socket.bind(f"tcp://*:{port}")
        print(f"Peer running on port {port}")
        
        while True:
            message = socket.recv_json()
            if message.get('type') == 'ping':
                socket.send_json({'status': 'Active'})
            elif message.get('type') == 'task':
                # Simulate processing
                time.sleep(random.uniform(0.5, 2.0))
                socket.send_json({
                    "detections": [
                        {"class": random.choice(["cat", "dog", "car"]), 
                         "confidence": round(random.uniform(0.6, 0.9), 2)}
                        for _ in message['task']
                    ]
                })
    except zmq.error.ZMQError as e:
        print(f"Error starting peer on port {port}: {e}")
        print("The port may already be in use. Try a different port.")
        return
    except KeyboardInterrupt:
        pass
    finally:
        socket.close()
        context.term()

# Modify the main function to use the enhanced interface
def main():
    """Main application entry point"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--zmq-port", type=int, default=5555, help="Port for ZeroMQ communication")
    parser.add_argument("--web-port", type=int, default=7860, help="Port for Gradio web interface")
    parser.add_argument("--peer", action="store_true", help="Run in peer mode")
    parser.add_argument("--broadcast-start", type=int, default=6000, 
                       help="Starting port for peer broadcast discovery")
    args = parser.parse_args()
    
    if args.peer:
        run_peer(args.zmq_port)
    else:
        core = EdgeShiftCore(zmq_port=args.zmq_port)
        app = create_interface(core)
        
        try:
            print(f"EdgeShift UI is starting on port {args.web_port}...")
            print(f"Open your browser to http://localhost:{args.web_port} to access the interface")
            app.launch(server_port=args.web_port, share=False)
        finally:
            print("Shutting down EdgeShift...")
            core.stop()
            print("Shutdown complete.")

if __name__ == "__main__":
    main()