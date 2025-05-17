import time
import random

class TaskScheduler:
    def __init__(self, local_node):
        self.local_node = local_node
        self.task_assignments = {}  # Store which device is handling which task
        self.reassigned_tasks = set()  # Track tasks that were reassigned due to failures
        
    def get_device_scores(self):
        """Calculate capability scores for all available devices"""
        scores = {}
        
        # Include local device (if it's active)
        if self.local_node.device_status == "Active":
            local_profile = self.local_node.get_profile()
            scores[self.local_node.id] = self._calculate_device_score(local_profile)
        
        # Include peers
        peers = self.local_node.get_available_peers()
        for peer_id, peer_info in peers.items():
            if peer_info['status'] == "Active" and peer_info['profile']:
                scores[peer_id] = self._calculate_device_score(peer_info['profile'])
        
        return scores
    
    def _calculate_device_score(self, profile):
        """Calculate a capability score based on device profile
        Higher score = more available resources = better for tasks
        """
        if not profile:
            return 0
            
        # Basic formula: Available resources (100 - used resources)
        cpu_available = 100 - profile.get('cpu_percent', 0)
        memory_available = 100 - profile.get('memory_percent', 0)
        
        # Battery bonus (if device has battery)
        battery_bonus = 0
        battery = profile.get('battery')
        if battery is not None:
            if battery > 80:  # High battery
                battery_bonus = 15
            elif battery > 50:  # Medium battery
                battery_bonus = 10
            elif battery > 20:  # Low battery
                battery_bonus = 5
                
        # Calculate final score (CPU and memory are most important)
        score = (0.5 * cpu_available) + (0.4 * memory_available) + (0.1 * battery_bonus)
        return score
    
    def distribute_tasks(self, task_list):
        """Distribute tasks to devices based on their scores
        
        Args:
            task_list: List of task objects with fields:
                - id: Task identifier
                - weight: Estimated computational weight (1-10)
                - data: Actual task data
                
        Returns:
            Dictionary mapping device_ids to their assigned tasks
        """
        # Get scores for all available devices
        device_scores = self.get_device_scores()
        
        # Sort devices by score (highest first)
        sorted_devices = sorted(device_scores.items(), 
                               key=lambda x: x[1], reverse=True)
        
        # If no capable devices, return empty assignment
        if not sorted_devices:
            return {}
            
        # Sort tasks by weight (heaviest first)
        sorted_tasks = sorted(task_list, key=lambda t: t.get('weight', 1), reverse=True)
        
        # Simple greedy assignment algorithm:
        # - Heaviest tasks go to most capable devices
        # - Distribute proportionally to capability scores
        assignments = {}
        
        # Calculate total score for proportional assignment
        total_score = sum(score for _, score in sorted_devices)
        
        if total_score == 0:
            # Fallback: Even distribution if all scores are 0
            tasks_per_device = len(sorted_tasks) // len(sorted_devices)
            remainder = len(sorted_tasks) % len(sorted_devices)
            
            for i, (device_id, _) in enumerate(sorted_devices):
                start_idx = i * tasks_per_device + min(i, remainder)
                end_idx = start_idx + tasks_per_device + (1 if i < remainder else 0)
                assignments[device_id] = sorted_tasks[start_idx:end_idx]
        else:
            # Proportional task assignment
            task_idx = 0
            remaining_tasks = len(sorted_tasks)
            
            for device_id, score in sorted_devices:
                # Calculate tasks for this device proportionally to its score
                device_share = score / total_score
                task_count = int(device_share * len(sorted_tasks))
                
                # Ensure every device gets at least one task if available
                task_count = max(task_count, 1) if remaining_tasks > 0 else 0
                
                # Don't assign more than remaining tasks
                task_count = min(task_count, remaining_tasks)
                
                # Assign tasks
                assignments[device_id] = sorted_tasks[task_idx:task_idx + task_count]
                task_idx += task_count
                remaining_tasks -= task_count
                
                # Stop if all tasks assigned
                if remaining_tasks <= 0:
                    break
        
        # Store assignments for potential reassignment later
        self.task_assignments = assignments
        
        return assignments
        
    def distribute_tasks_to_devices(self, task_assignments):
        """Send tasks to their assigned devices
        
        Args:
            task_assignments: Dictionary mapping device_ids to tasks
            
        Returns:
            Dictionary of device_id -> success status
        """
        results = {}
        
        for device_id, tasks in task_assignments.items():
            if device_id == self.local_node.id:
                # Local tasks are handled directly
                for task in tasks:
                    self.local_node.tasks.append(task)
                    # Process in background
                    import threading
                    threading.Thread(
                        target=self.local_node._process_task, 
                        args=(task,), 
                        daemon=True
                    ).start()
                results[device_id] = True
                continue
                
            # Send tasks to remote device
            success = True
            for task in tasks:
                # Track which device is handling this task
                task_id = task.get('id')
                if not self.local_node.send_task_to_peer(device_id, task):
                    success = False
                    break
                    
            results[device_id] = success
            
        return results
    
    def check_device_health(self):
        """Check all devices for failures"""
        failed_devices = []
        
        # Check local device
        if self.local_node.device_status != "Active":
            failed_devices.append(self.local_node.id)
            
        # Check peer devices
        peers = self.local_node.get_available_peers()
        for peer_id, peer_info in peers.items():
            if peer_info['status'] != "Active":
                failed_devices.append(peer_id)
            elif not self.local_node.check_peer_status(peer_id):
                failed_devices.append(peer_id)
                
        return failed_devices
    
    def reassign_tasks(self, failed_devices):
        """Reassign tasks from failed devices to healthy ones"""
        if not failed_devices:
            return {}
            
        # Collect tasks to reassign
        tasks_to_reassign = []
        for device_id in failed_devices:
            if device_id in self.task_assignments:
                tasks_to_reassign.extend(self.task_assignments[device_id])
                del self.task_assignments[device_id]
                
        if not tasks_to_reassign:
            return {}
            
        print(f"Reassigning {len(tasks_to_reassign)} tasks from failed devices")
        
        # Mark these tasks as reassigned
        for task in tasks_to_reassign:
            task_id = task.get('id')
            self.reassigned_tasks.add(task_id)
            
        # Get scores for remaining healthy devices
        device_scores = self.get_device_scores()
        
        # Remove failed devices from scores
        for device_id in failed_devices:
            if device_id in device_scores:
                del device_scores[device_id]
                
        if not device_scores:
            print("No healthy devices available for reassignment!")
            return {}
            
        # Sort devices by score (highest first)
        sorted_devices = sorted(device_scores.items(), 
                               key=lambda x: x[1], reverse=True)
        
        # Simple round-robin assignment
        reassignments = {}
        for i, task in enumerate(tasks_to_reassign):
            device_id = sorted_devices[i % len(sorted_devices)][0]
            if device_id not in reassignments:
                reassignments[device_id] = []
            reassignments[device_id].append(task)
            
        # Update task assignments with new assignments
        for device_id, tasks in reassignments.items():
            if device_id in self.task_assignments:
                self.task_assignments[device_id].extend(tasks)
            else:
                self.task_assignments[device_id] = tasks
                
        return reassignments
    
    def collect_results(self, task_assignments, timeout=30):
        """Collect results from all assigned tasks
        
        Args:
            task_assignments: Dictionary of device_id -> assigned_tasks
            timeout: Maximum time to wait for results (seconds)
            
        Returns:
            Dictionary of task_id -> result
        """
        results = {}
        start_time = time.time()
        
        # Keep track of which devices we're waiting for
        pending_devices = list(task_assignments.keys())
        
        # First collect from local device
        if self.local_node.id in pending_devices:
            # Get local results
            local_results = self.local_node.results
            results.update(local_results)
            pending_devices.remove(self.local_node.id)
        
        # Wait until timeout or all results collected
        while time.time() - start_time < timeout and pending_devices:
            # Check for device failures
            failed_devices = self.check_device_health()
            if failed_devices:
                # Reassign tasks from failed devices
                reassignments = self.reassign_tasks(failed_devices)
                if reassignments:
                    # Distribute reassigned tasks
                    self.distribute_tasks_to_devices(reassignments)
                    
                # Remove failed devices from pending list
                for device_id in failed_devices:
                    if device_id in pending_devices:
                        pending_devices.remove(device_id)
            
            # Try to collect from each pending device
            for device_id in list(pending_devices):  # Copy to avoid modification during iteration
                # Collect from remote device
                device_results = self.local_node.collect_result_from_peer(device_id)
                if device_results:
                    results.update(device_results)
                    pending_devices.remove(device_id)
            
            # Wait a bit before next collection attempt
            time.sleep(1)
        
        return results
    
    def assign_image_partitions(self, image_path, num_partitions=None):
        """Partition an image and assign parts to different devices
        
        Args:
            image_path: Path to the image file
            num_partitions: Number of sections to split into (default: auto-determine)
            
        Returns:
            Dictionary mapping device_ids to their assigned image sections
        """
        # Get available devices
        device_scores = self.get_device_scores()
        
        # Auto-determine partitions if not specified
        if num_partitions is None:
            num_partitions = len(device_scores)
            
        if num_partitions <= 0:
            num_partitions = 1
        
        # Create task list with image partitions
        tasks = []
        
        # In a real implementation, you'd use PIL/OpenCV to split the image
        # For demo, we'll just simulate it
        for i in range(num_partitions):
            task_id = f"img_{image_path.split('/')[-1]}_{i}"
            tasks.append({
                'id': task_id,
                'weight': random.randint(3, 7),  # Randomize weights for demo
                'data': {
                    'type': 'image_partition',
                    'partition_index': i,
                    'total_partitions': num_partitions,
                    'image_path': image_path
                }
            })
            
        # Distribute these tasks to devices
        assignments = self.distribute_tasks(tasks)
        return assignments