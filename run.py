import time
import argparse
import threading
import json
import os
import random
from core.device import DeviceNode
from core.scheduler import TaskScheduler
from core.model import ModelInterface

def simulate_device_failure(device, failure_chance=0.2, min_runtime=10):
    """Randomly simulate a device failure after some time"""
    # Wait at least min_runtime seconds
    time.sleep(min_runtime)
    
    # Random chance of failure each interval
    while device.running:
        if random.random() < failure_chance:
            device.simulate_crash()
            break
        time.sleep(5)

def process_image_collaborative(image_path, scheduler, model):
    """Process an image collaboratively across devices"""
    print(f"\nProcessing image: {image_path}")
    
    # Assign partitions to devices
    assignments = scheduler.assign_image_partitions(image_path)
    
    # Show assignments
    print("\nTask assignments:")
    for device_id, tasks in assignments.items():
        if device_id == scheduler.local_node.id:
            device_name = "Local device"
        else:
            device_name = f"Remote device {device_id}"
        print(f"  {device_name}: {len(tasks)} tasks")
    
    # Distribute tasks to devices
    distribution_results = scheduler.distribute_tasks_to_devices(assignments)
    
    # Collect results with fault tolerance
    print("\nCollecting results (with fault tolerance)...")
    start_time = time.time()
    results = scheduler.collect_results(assignments, timeout=30)
    total_time = time.time() - start_time
    
    # Check if any tasks were reassigned
    reassigned_count = len(scheduler.reassigned_tasks)
    if reassigned_count > 0:
        print(f"\n{reassigned_count} tasks were reassigned due to device failures!")
    
    # Process and combine results
    result_values = list(results.values())
    if result_values:
        combined_results = model.combine_results(result_values)
        combined_results['total_wall_time'] = total_time
        combined_results['devices_used'] = len(assignments)
        combined_results['tasks_reassigned'] = reassigned_count
        return combined_results
    else:
        return {"error": "No results collected"}

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='EdgeShift Node')
    parser.add_argument('--port', type=int, default=5555,
                        help='Port for device communication')
    parser.add_argument('--broadcast-port', type=int, default=5556,
                        help='Port for discovery broadcasts')
    parser.add_argument('--coordinator', action='store_true',
                        help='Run as the coordinator node')
    parser.add_argument('--simulate-failure', action='store_true',
                        help='Randomly simulate device failures')
    parser.add_argument('--demo-mode', action='store_true',
                        help='Run in demo mode with simulated workload')
    parser.add_argument('--run-time', type=int, default=60,
                        help='How long to run in demo mode (seconds)')
    args = parser.parse_args()
    
    # Create the local device node
    device = DeviceNode(
        port=args.port,
        broadcast_port=args.broadcast_port,
        is_coordinator=args.coordinator
    )
    
    # Create the scheduler and model interface
    scheduler = TaskScheduler(device)
    model = ModelInterface()
    
    # Start the device node services
    device.start()
    
    print(f"EdgeShift node started with ID: {device.id}")
    print(f"Running on port: {args.port}, broadcast port: {args.broadcast_port}")
    print(f"Coordinator mode: {'enabled' if args.coordinator else 'disabled'}")
    
    # Start failure simulation if enabled
    if args.simulate_failure:
        print("Failure simulation enabled - devices may randomly crash")
        threading.Thread(target=simulate_device_failure, 
                        args=(device,), daemon=True).start()
    
    try:
        if args.demo_mode:
            # In demo mode, run for a fixed time with simulated workload
            print(f"\nRunning in demo mode for {args.run_time} seconds...")
            
            # Create a directory for results
            os.makedirs("results", exist_ok=True)
            
            # Simulate workload with multiple images
            start_time = time.time()
            run_end_time = start_time + args.run_time
            
            # List of simulated images to process
            simulated_images = [
                "sample_image_1.jpg", 
                "sample_image_2.jpg",
                "sample_image_3.jpg",
                "sample_image_4.jpg",
                "sample_image_5.jpg"
            ]
            
            image_index = 0
            results_list = []
            
            while time.time() < run_end_time:
                # Process next image in the list
                image_path = simulated_images[image_index % len(simulated_images)]
                
                # Wait for devices to join the network (first run only)
                if image_index == 0:
                    print("\nWaiting for devices to join the network...")
                    time.sleep(5)
                
                # Process image collaboratively
                result = process_image_collaborative(image_path, scheduler, model)
                results_list.append({
                    'image': image_path,
                    'result': result
                })
                
                # Save incremental results
                with open("results/edgeshift_results.json", "w") as f:
                    json.dump(results_list, f, indent=2)
                
                # Move to next image
                image_index += 1
                
                # Wait a bit before next processing
                if time.time() < run_end_time:
                    time.sleep(3)
            
            # Print summary
            print("\n===== Demo Summary =====")
            print(f"Images processed: {image_index}")
            print(f"Tasks reassigned due to failures: {len(scheduler.reassigned_tasks)}")
            print(f"Results saved to: results/edgeshift_results.json")
        else:
            # In interactive mode, just keep the node running
            print("\nNode is running. Press Ctrl+C to exit...")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        device.stop()
        print("Node stopped")

if __name__ == "__main__":
    main()