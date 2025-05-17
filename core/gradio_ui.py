import gradio as gr
import time
import threading
import random
import json
import zmq
import pandas as pd
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
from core.device import DeviceNode
from core.scheduler import TaskScheduler
from core.model import ModelInterface
import io
import argparse
# Mock DeviceNode, TaskScheduler, and ModelInterface classes for standalone module
# In your actual code, you'd import these from their respective modules


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
                            # You can use this to display connectivity status as text
                
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
                        device_pie = gr.Textbox(label="Device Distribution", lines=4)
                        
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
                return "No Devices"
            
            health_percent = (active_count / total) * 100
            
            if health_percent > 80:
                return f"Excellent ({active_count}/{total} devices)"
            elif health_percent > 50:
                return f"Good ({active_count}/{total} devices)"
            elif health_percent > 30:
                return f"Fair ({active_count}/{total} devices)"
            else:
                return f"Poor ({active_count}/{total} devices)"
        
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
            """Update the device distribution as text"""
            devices = core.get_device_status()
            
            # Count devices by status
            status_counts = {}
            for device in devices:
                status = device[1]
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
            
            # Create text representation
            if status_counts:
                text = "Device Status Distribution:\n"
                total = sum(status_counts.values())
                for status, count in status_counts.items():
                    percentage = (count / total) * 100
                    text += f"{status}: {count} ({percentage:.1f}%)\n"
            else:
                text = "No device data available"
            
            return text
        
        def update_activity_plot():
            """Update the network activity plot with real metrics"""
            # Get current device status
            devices = core.get_device_status()
            
            # Calculate real metrics
            active_devices = len([d for d in devices if d[1] == 'Active'])
            total_tasks = sum(1 for d in devices if d[1] == 'Active')
            
            # Get current time
            current_time = time.strftime("%H:%M:%S")
            
            # Create DataFrame with real data
            return pd.DataFrame({
                "time": [current_time],
                "Active": [active_devices],
                "Tasks": [total_tasks],
                "Load": [active_devices * 20]  # Simple load calculation
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
                # Ensure the temp directory exists
                os.makedirs(os.path.dirname(temp_path) or '.', exist_ok=True)
                image.save(temp_path)
                path_to_use = temp_path
            else:
                path_to_use = path_str
            
            # Ensure the file exists before processing
            if not os.path.exists(path_to_use):
                 return f"Error: Image file not found at {path_to_use}", {}, [], None, None

            try:
                # Use the core's ModelInterface to process the image
                # This is assuming ModelInterface is initialized in the EdgeShiftCore
                # and is accessible as self.model in the core instance passed to create_interface.
                # If not, we might need to adjust where the ModelInterface is created/accessed.

                # For now, let's assume core has a .model attribute
                if not hasattr(core, 'model') or core.model is None:
                     return "Error: Model interface not initialized in EdgeShiftCore.", {}, [], None, None

                # The original demo code in run.py uses a collaborative processing function
                # that involves partitioning and distributing. The Gradio UI version
                # currently has a simplified process_image method in EdgeShiftCore.
                # Let's directly use the model for inference in the UI for now,
                # and indicate that the full distributed processing would happen elsewhere.

                # Perform local inference using the TFLite model
                # The ModelInterface has preprocess_image and process_image_partition
                # which does the actual inference.
                
                # The process_image_partition function returns results in a dictionary format
                # suitable for combined_results, but let's simplify for just displaying
                # the top predictions in the UI for now.

                # Preprocess the image (ModelInterface expects a path)
                input_data = core.model.preprocess_image(path_to_use)

                # Run inference
                core.model.interpreter.set_tensor(core.model.input_index, input_data)
                core.model.interpreter.invoke()
                output = core.model.interpreter.get_tensor(core.model.output_index)

                # Get top predictions
                if output.ndim == 2 and output.shape[0] == 1:
                     output = output[0]

                top_k = 5
                top_k_idx = np.argsort(output)[-top_k:][::-1]

                predictions = []
                for idx in top_k_idx:
                    # Ensure the index is within the bounds of the labels list
                    if idx < len(core.model.labels):
                        label = core.model.labels[idx]
                        confidence = float(output[idx])
                        predictions.append({
                            'class': label,
                            'confidence': confidence
                        })
                    else:
                         predictions.append({
                            'class': f"Unknown Label Index {idx}",
                            'confidence': float(output[idx])
                        })

                # Format results for display
                result_text = "Top Predictions:\n"
                for pred in predictions:
                    result_text += f"{pred['class']}: {pred['confidence']:.2f}\n" # Use .2f for confidence

                detailed_results = {
                    'predictions': predictions,
                    'image_path': path_to_use,
                    # Indicate this was local processing for the UI demo
                    'processing_mode': 'local_inference'
                }

                # For visualization, use the same predictions structure
                detection_result_image = create_detection_visualization(image, {
                     'predictions': predictions
                })

                # The assignments_table might not be relevant for local inference,
                # but we return an empty list to match the expected output structure.
                assignment_display = [] # No assignments for local processing

                # Clean up temp file
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # Return the results in the correct order
                return result_text, detailed_results, assignment_display, image, detection_result_image
                
            except Exception as e:
                # Log the error for debugging
                print(f"Error during image processing: {e}")
                import traceback
                traceback.print_exc()
                return f"Error processing image: {str(e)}", {}, [], None, None
        
        def create_detection_visualization(image, results):
            """Create a visualization of detection results using PIL"""
            if image is None or not results:
                return None
            
            # Create a copy of the image to draw on
            img = image.copy()
            draw = ImageDraw.Draw(img)
            
            # Load a font (use default if not available)
            try:
                font_path = "arial.ttf"
                font_size = 25 # You can adjust this value
                font = ImageFont.load_default() # Start with default
                draw_text_with_background = False # Assume no background needed initially

                if os.path.exists(font_path):
                    try:
                        font = ImageFont.truetype(font_path, font_size)
                        draw_text_with_background = False # Truetype usually fine
                    except Exception as e:
                         print(f"Error loading truetype font {font_path}: {e}. Falling back to default.")
                         font = ImageFont.load_default()
                         # If using default, consider background for readability
                         draw_text_with_background = True # Might need background for default font

                else:
                     # Try other common font names if arial.ttf isn't found
                     common_fonts = ["Arial.ttf", "LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"] # Add other common paths/names
                     font_loaded = False
                     for f_name in common_fonts:
                         if os.path.exists(f_name):
                            try:
                                font = ImageFont.truetype(f_name, font_size)
                                draw_text_with_background = False
                                font_loaded = True
                                break
                            except:
                                continue
                     if not font_loaded:
                         print("No common truetype fonts found, using default.")
                         font = ImageFont.load_default()
                         draw_text_with_background = True # Might need background for default font

                # If using default font, make sure image is RGBA to draw with alpha background
                if draw_text_with_background and img.mode != 'RGBA':
                    img = img.convert('RGBA')
                    draw = ImageDraw.Draw(img) # Re-create draw object for RGBA image
                    bg_color = (0, 0, 0, 128) # Semi-transparent black background

            except Exception as e:
                 print(f"Unexpected error during font loading: {e}. Using default font without background.")
                 font = ImageFont.load_default()
                 draw_text_with_background = False # Fallback to default without background

            # Determine text color based on confidence (optional)
            def get_text_color(confidence):
                return (255, 255, 0) if confidence > 0.7 else (255, 255, 255) # Yellow for high confidence, White otherwise

            # Get predictions, expecting a list of dicts with 'class' and 'confidence'
            predictions = results.get('predictions', [])
            
            top_k = 5 # Define top_k within this function

            # Draw predictions at the top of the image
            y_offset = 10
            x_offset = 10 # Starting from the left
            img_width, img_height = img.size

            for i, pred in enumerate(predictions):
                # Limit the number of predictions drawn on the image if there are too many
                if i >= top_k: # Now top_k is defined here
                     break
                     
                label = f"{i+1}. {pred.get('class', 'Unknown')}: {pred.get('confidence', 0):.2f}"
                text_color = get_text_color(pred.get('confidence', 0))

                if draw_text_with_background:
                     # Calculate text size to draw background rectangle
                     try:
                         # Use textbbox for more accurate bounding box calculation
                         text_bbox = draw.textbbox((x_offset, y_offset), label, font=font)
                         text_width = text_bbox[2] - text_bbox[0]
                         text_height = text_bbox[3] - text_bbox[1]
                         # Draw background rectangle slightly larger than text
                         padding = 5
                         draw.rectangle([x_offset, y_offset, x_offset + text_width + padding, y_offset + text_height + padding], fill=bg_color)
                     except Exception as bbox_e:
                          # Fallback if textbbox fails (e.g., with default font)
                          print(f"Error calculating text bbox for background: {bbox_e}. Drawing text without background.")
                          draw_text_with_background = False # Fallback


                draw.text((x_offset, y_offset), label, fill=text_color, font=font)
                
                # Move down for the next line of text
                # Use textbbox to get accurate height for the next line calculation
                try:
                     text_bbox = draw.textbbox((x_offset, y_offset), label, font=font)
                     y_offset += (text_bbox[3] - text_bbox[1]) + 5 # text height + padding
                except:
                     # Fallback height if textbbox fails
                     y_offset += 20 + 5 # Estimate height + padding


            return img
        
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
            outputs=[device_table, stats, health_indicator, activity_plot]
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
        # Define the list of peer addresses to attempt connecting to
        # Include localhost peers for local testing and remote peers
        peer_addresses_to_try = [
            "tcp://localhost:5556",  # Local peer 1
            "tcp://localhost:5557",  # Local peer 2
            # --- ADD THE REMOTE PEER ADDRESS HERE ---
            "tcp://192.168.200.206:5556", # Added Computer B's IP and peer port
            # ---------------------------------------
        ]

        while self.running:
            for peer_address in peer_addresses_to_try:
                # Extract peer_id from the address (e.g., "peer_192.168.1.101:5556")
                peer_id = f"peer_{peer_address.split('://')[1].replace(':', '_')}"

                if peer_id not in self.peers and peer_address != f"tcp://localhost:{self.main_device.port}":
                    try:
                        socket = self.context.socket(zmq.REQ)
                        socket.connect(peer_address)
                        socket.setsockopt(zmq.LINGER, 0)
                        socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
                        
                        with self.peer_lock:
                            self.peers[peer_id] = {
                                'port': peer_address.split(':')[-1],
                                'socket': socket,
                                'status': 'Active',
                                'last_seen': time.time()
                            }
                        print(f"Connected to peer {peer_id}")
                    except Exception as e:
                        print(f"Failed to connect to peer on address {peer_address}: {e}")
            
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
                        
                        # Receive response - expect status and metrics
                        # This will block for RCVTIMEO (2 seconds)
                        response = peer['socket'].recv_json() 
                        
                        # Update peer status and metrics from the response
                        peer['status'] = response.get('status', 'Unknown')
                        peer['last_seen'] = time.time()
                        
                        # --- Store received metrics ---
                        # Expecting keys like 'cpu_percent', 'memory_percent', 'battery' in the response
                        peer['cpu_percent'] = response.get('cpu_percent', 'N/A')
                        peer['memory_percent'] = response.get('memory_percent', 'N/A')
                        peer['battery'] = response.get('battery', 'N/A') # Assuming battery can be reported
                        # ------------------------------

                    except Exception as e:
                        # If there's an error (timeout, disconnection, etc.)
                        print(f"Peer {peer_id} unreachable or error receiving status: {e}")
                        peer['status'] = 'Disconnected'
                        # Clear metrics or mark as N/A if disconnected
                        peer['cpu_percent'] = 'N/A' 
                        peer['memory_percent'] = 'N/A'
                        peer['battery'] = 'N/A'
                        
                        if time.time() - peer['last_seen'] > 10:  # 10s timeout for removal
                            to_remove.append(peer_id)
                
                # Remove dead peers
                for peer_id in to_remove:
                    print(f"Removing unresponsive peer {peer_id}") # Improved message
                    try:
                        self.peers[peer_id]['socket'].close()
                    except Exception as close_e:
                        print(f"Error closing socket for peer {peer_id}: {close_e}")
                    del self.peers[peer_id]
                    print(f"Removed peer {peer_id} from list.")
            
            time.sleep(3) # Check peer status every 3 seconds

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

        # Main device (gets real profile data)
        profile = self.main_device.get_profile()
        devices.append([
            f"{self.main_device.id[:8]} (local)",
            self.main_device.device_status,
            f"{profile.get('cpu_percent', 0):.1f}%",
            f"{profile.get('memory_percent', 0):.1f}%",
            f"{profile.get('battery', 0):.1f}%" if isinstance(profile.get('battery', 0), (int, float)) else profile.get('battery', '---')
        ])

        # Peer devices (now displays simulated metrics)
        with self.peer_lock:
            for peer_id, peer in self.peers.items():
                # --- Generate simulated metrics for display ---
                simulated_cpu = random.uniform(5, 85) # Simulate CPU usage between 5% and 85%
                simulated_memory = random.uniform(20, 90) # Simulate Memory usage between 20% and 90%
                simulated_battery = random.uniform(10, 100) # Simulate Battery between 10% and 100%
                # ----------------------------------------------

                devices.append([
                    peer_id,
                    peer['status'], # Use the real status (Active/Disconnected)
                    f"{simulated_cpu:.1f}%", # Display simulated CPU
                    f"{simulated_memory:.1f}%", # Display simulated Memory
                    f"{simulated_battery:.1f}%" # Display simulated Battery
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
                        {"class": random.choice(["cat", "dog", "car"]), # Simulate some detection results
                         "confidence": round(random.uniform(0.6, 0.9), 2)}
                        for _ in message['task']
                    ]
                })
    except zmq.error.ZMQError as e:
        print(f"Error starting peer on port {port}: {e}")
        print("The port may already be in use. Try a different port.")
        # Return or sys.exit(1) if the peer is critical
    except KeyboardInterrupt:
        print(f"\nPeer on port {port} stopped by user.")
    except Exception as e:
         print(f"An unexpected error occurred in peer on port {port}: {e}")
         import traceback
         traceback.print_exc()
    finally:
        print(f"Peer on port {port} shutting down ZeroMQ resources.")
        socket.close()
        context.term()

# Modify the main function to use the enhanced interface
def main():
    """Main application entry point"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='EdgeShift Gradio UI')
    parser.add_argument('--zmq-port', type=int, default=5555, help='ZeroMQ port for the main device')
    parser.add_argument('--web-port', type=int, default=7860, help='Web port for the Gradio UI')
    # Add an argument to optionally start a test peer
    parser.add_argument('--start-peer', type=int, help='Start a test peer on the specified port')

    args = parser.parse_args()

    # Initialize EdgeShiftCore (which includes the ModelInterface)
    core = EdgeShiftCore(zmq_port=args.zmq_port)

    # --- Add Peer Starting Logic Here ---
    peer_thread = None
    if args.start_peer:
        print(f"Starting test peer on port {args.start_peer}...")
        # run_peer function is defined later in this file
        peer_thread = threading.Thread(target=run_peer, args=(args.start_peer,))
        peer_thread.daemon = True  # Allow the main program to exit even if the thread is running
        peer_thread.start()
        # Give the peer a moment to start up
        time.sleep(1)
    # --- End Peer Starting Logic ---

    # Create the Gradio interface
    app = create_interface(core)

    # Launch the Gradio app
    print(f"EdgeShift UI is starting on port {args.web_port}...")
    app.launch(server_name="0.0.0.0", server_port=args.web_port) # Use 0.0.0.0 to be accessible externally

    # Optional: Clean up when the UI exits
    # This might not be strictly necessary with daemon=True for the peer thread,
    # but good practice for other resources.
    core.stop()
    if peer_thread and peer_thread.is_alive():
         # In a real application, you'd signal the thread to stop gracefully
         # For this simple example, we rely on daemon=True
         pass # Or add a signaling mechanism if needed

if __name__ == "__main__":
    main()