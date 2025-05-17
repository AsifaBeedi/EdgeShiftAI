import time

class TaskScheduler:
    def __init__(self, local_node):
        self.local_node = local_node
        
    def get_device_scores(self):
        """Calculate capability scores for all available devices"""
        scores = {}
        
        # Include local device
        local_profile = self.local_node.get_profile()
        scores[self.local_node.id] = self._calculate_device_score(local_profile)
        
        # Include peers
        peers = self.local_node.get_available_peers()
        for peer_id, peer_info in peers.items():
            if peer_info['profile']:
                scores[peer_id] = self._calculate_device_score(peer_info['profile'])
        
        return scores
    
    def _calculate_device_score(self, profile):
        """Calculate a simple capability score based on device profile
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
        
        return assignments
    
    def assign_image_partitions(self, image_data, num_partitions=2):
        """Partition an image and assign parts to different devices
        
        For image classification/detection tasks, we can split the image
        into sections and have different devices process each section.
        
        Args:
            image_data: Raw image data (bytes)
            num_partitions: Number of sections to split into
            
        Returns:
            Dictionary mapping device_ids to their assigned image sections
        """
        # Create task list with image partitions
        tasks = []
        
        # Create equal divisions of the image (simplified)
        # In a real implementation, you'd use numpy to actually split the image
        for i in range(num_partitions):
            tasks.append({
                'id': f'partition_{i}',
                'weight': 5,  # Medium weight
                'data': {
                    'type': 'image_partition',
                    'partition_index': i,
                    'total_partitions': num_partitions,
                    'image_data': image_data  # In reality, just one section of the image
                }
            })
            
        # Distribute these tasks to devices
        return self.distribute_tasks(tasks)
    
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
        
        # Wait until timeout or all results collected
        while time.time() - start_time < timeout and pending_devices:
            # Try to collect from each pending device
            for device_id in list(pending_devices):  # Copy to avoid modification during iteration
                if device_id == self.local_node.id:
                    # Local tasks are handled differently (direct function call)
                    # This would be implemented when integrating with the ML processing
                    pending_devices.remove(device_id)
                    continue
                    
                # Collect from remote device
                response = self.local_node.collect_result_from_peer(device_id)
                if response and response.get('status') != 'not_implemented_yet':
                    # Got results from this device
                    task_results = response.get('results', {})
                    results.update(task_results)
                    pending_devices.remove(device_id)
            
            # Wait a bit before next collection attempt
            time.sleep(1)
        
        return results
    
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
                # Local tasks are handled differently (direct function call)
                # This would be implemented when integrating with the ML processing
                results[device_id] = True
                continue
                
            # Send tasks to remote device
            success = self.local_node.send_task_to_peer(device_id, tasks)
            results[device_id] = success
            
        return results