"""Metrics collection for chaos experiments."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import nomad
except ImportError:
    nomad = None


class MetricsCollector:
    """
    Collects system metrics before, during, and after chaos experiments.
    
    Supports metrics from:
    - Nomad allocations (CPU, Memory usage)
    - Kubernetes pods (if available)
    - Custom metric endpoints
    """
    
    def __init__(self, nomad_client=None, kubernetes_client=None):
        """Initialize metrics collector with platform clients."""
        self.nomad_client = nomad_client
        self.kubernetes_client = kubernetes_client
        self.metrics_history: List[Dict[str, Any]] = []
    
    def collect_nomad_allocation_metrics(
        self, 
        allocation_id: str,
        label: str = "snapshot"
    ) -> Dict[str, Any]:
        """
        Collect metrics for a specific Nomad allocation.
        
        Args:
            allocation_id: Nomad allocation ID
            label: Label for this snapshot (e.g., "before", "during", "after")
            
        Returns:
            Dictionary with metrics data
        """
        if not self.nomad_client:
            return {"error": "Nomad client not available"}
        
        try:
            # Get allocation details
            allocation = self.nomad_client.allocation.get_allocation(allocation_id)
            
            # Get allocation stats
            stats = self.nomad_client.allocation.get_allocation_stats(allocation_id)
            
            # Extract resource stats
            resource_usage = stats.get("ResourceUsage", {})
            cpu_stats = resource_usage.get("CpuStats", {})
            memory_stats = resource_usage.get("MemoryStats", {})
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "allocation_id": allocation_id,
                "allocation_name": allocation.get("Name", "unknown"),
                "job_id": allocation.get("JobID", "unknown"),
                "task_group": allocation.get("TaskGroup", "unknown"),
                "client_status": allocation.get("ClientStatus", "unknown"),
                "desired_status": allocation.get("DesiredStatus", "unknown"),
                "cpu": {
                    "percent": cpu_stats.get("Percent", 0),
                    "system_mode": cpu_stats.get("SystemMode", 0),
                    "user_mode": cpu_stats.get("UserMode", 0),
                    "total_ticks": cpu_stats.get("TotalTicks", 0),
                    "throttled_periods": cpu_stats.get("ThrottledPeriods", 0),
                    "throttled_time": cpu_stats.get("ThrottledTime", 0),
                },
                "memory": {
                    "rss": memory_stats.get("RSS", 0),
                    "cache": memory_stats.get("Cache", 0),
                    "swap": memory_stats.get("Swap", 0),
                    "usage": memory_stats.get("Usage", 0),
                    "max_usage": memory_stats.get("MaxUsage", 0),
                    "kernel_usage": memory_stats.get("KernelUsage", 0),
                    "kernel_max_usage": memory_stats.get("KernelMaxUsage", 0),
                },
                "disk": {
                    "read_bytes": 0,
                    "write_bytes": 0,
                    "read_ops": 0,
                    "write_ops": 0,
                    "total_bytes": 0,
                    "total_ops": 0,
                },
            }
            
            # Extract disk I/O stats if available
            if "Tasks" in stats:
                total_read_bytes = 0
                total_write_bytes = 0
                total_read_ops = 0
                total_write_ops = 0
                
                for task_name, task_data in stats["Tasks"].items():
                    task_resource = task_data.get("ResourceUsage", {})
                    
                    # Get device stats for disk I/O
                    device_stats = task_resource.get("DeviceStats", [])
                    for device in device_stats:
                        # Aggregate read/write stats
                        read_stats = device.get("ReadStats", {})
                        write_stats = device.get("WriteStats", {})
                        
                        total_read_bytes += read_stats.get("BytesTransferred", 0)
                        total_write_bytes += write_stats.get("BytesTransferred", 0)
                        total_read_ops += read_stats.get("Ops", 0)
                        total_write_ops += write_stats.get("Ops", 0)
                
                metrics["disk"] = {
                    "read_bytes": total_read_bytes,
                    "write_bytes": total_write_bytes,
                    "read_ops": total_read_ops,
                    "write_ops": total_write_ops,
                    "total_bytes": total_read_bytes + total_write_bytes,
                    "total_ops": total_read_ops + total_write_ops,
                }
            
            # Add task-level stats if available
            if "Tasks" in stats:
                task_stats = {}
                for task_name, task_data in stats["Tasks"].items():
                    task_resource = task_data.get("ResourceUsage", {})
                    task_cpu = task_resource.get("CpuStats", {})
                    task_mem = task_resource.get("MemoryStats", {})
                    
                    task_stats[task_name] = {
                        "cpu_percent": task_cpu.get("Percent", 0),
                        "memory_rss": task_mem.get("RSS", 0),
                        "memory_usage": task_mem.get("Usage", 0),
                    }
                
                metrics["tasks"] = task_stats
            
            self.metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "allocation_id": allocation_id,
                "error": str(e),
            }
            self.metrics_history.append(error_data)
            return error_data
    
    def collect_nomad_job_metrics(
        self,
        job_id: str,
        label: str = "snapshot"
    ) -> Dict[str, Any]:
        """
        Collect metrics for all allocations of a Nomad job.
        
        Args:
            job_id: Nomad job ID
            label: Label for this snapshot
            
        Returns:
            Dictionary with aggregated metrics
        """
        if not self.nomad_client:
            return {"error": "Nomad client not available"}
        
        try:
            # Get all allocations for the job
            allocations = self.nomad_client.job.get_allocations(job_id)
            
            job_metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "job_id": job_id,
                "allocation_count": len(allocations),
                "allocations": [],
            }
            
            # Collect metrics for each allocation
            for alloc in allocations:
                alloc_id = alloc.get("ID")
                if alloc_id:
                    alloc_metrics = self.collect_nomad_allocation_metrics(
                        allocation_id=alloc_id,
                        label=label
                    )
                    job_metrics["allocations"].append(alloc_metrics)
            
            # Calculate aggregate stats
            total_cpu = 0
            total_memory = 0
            running_count = 0
            
            for alloc_metrics in job_metrics["allocations"]:
                if "cpu" in alloc_metrics:
                    total_cpu += alloc_metrics["cpu"].get("percent", 0)
                if "memory" in alloc_metrics:
                    total_memory += alloc_metrics["memory"].get("usage", 0)
                if alloc_metrics.get("client_status") == "running":
                    running_count += 1
            
            job_metrics["aggregate"] = {
                "total_cpu_percent": total_cpu,
                "average_cpu_percent": total_cpu / len(allocations) if allocations else 0,
                "total_memory_bytes": total_memory,
                "running_allocations": running_count,
            }
            
            return job_metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "job_id": job_id,
                "error": str(e),
            }
    
    def collect_node_metrics(
        self,
        node_id: str,
        label: str = "snapshot"
    ) -> Dict[str, Any]:
        """
        Collect metrics for a Nomad node by aggregating allocation metrics.
        
        Args:
            node_id: Nomad node ID
            label: Label for this snapshot
            
        Returns:
            Dictionary with node metrics (aggregated from allocations)
        """
        if not self.nomad_client:
            return {"error": "Nomad client not available"}
        
        try:
            # Get node details
            node = self.nomad_client.node.get_node(node_id)
            
            # Get allocations on this node
            allocations = self.nomad_client.node.get_allocations(node_id)
            
            # Get node resources (capacity)
            resources = node.get("Resources", {})
            reserved = node.get("Reserved", {})
            
            # Aggregate metrics from all running allocations on this node
            total_cpu_percent = 0
            total_memory_usage = 0
            total_disk_read = 0
            total_disk_write = 0
            running_count = 0
            
            for alloc in allocations:
                if alloc.get("ClientStatus") == "running":
                    alloc_id = alloc.get("ID")
                    try:
                        # Get stats for this allocation
                        stats = self.nomad_client.allocation.get_allocation_stats(alloc_id)
                        resource_usage = stats.get("ResourceUsage", {})
                        cpu_stats = resource_usage.get("CpuStats", {})
                        memory_stats = resource_usage.get("MemoryStats", {})
                        
                        # Aggregate CPU and memory
                        total_cpu_percent += cpu_stats.get("Percent", 0)
                        total_memory_usage += memory_stats.get("RSS", 0)
                        
                        # Aggregate disk I/O from tasks
                        tasks_stats = stats.get("Tasks", {})
                        for task_name, task_stats in tasks_stats.items():
                            task_resource_usage = task_stats.get("ResourceUsage", {})
                            device_stats_list = task_resource_usage.get("DeviceStats", [])
                            if device_stats_list:
                                for device_stats in device_stats_list:
                                    total_disk_read += device_stats.get("ReadBytes", 0)
                                    total_disk_write += device_stats.get("WriteBytes", 0)
                        
                        running_count += 1
                    except Exception as e:
                        # Skip allocations we can't get stats for
                        pass
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "node_id": node_id,
                "node_name": node.get("Name", "unknown"),
                "status": node.get("Status", "unknown"),
                "drain": node.get("Drain", False),
                "resources": {
                    "cpu_mhz": resources.get("CPU", 0),
                    "memory_mb": resources.get("MemoryMB", 0),
                    "disk_mb": resources.get("DiskMB", 0),
                },
                "reserved": {
                    "cpu_mhz": reserved.get("CPU", 0),
                    "memory_mb": reserved.get("MemoryMB", 0),
                    "disk_mb": reserved.get("DiskMB", 0),
                },
                "allocation_count": len(allocations),
                "running_allocations": running_count,
                # Aggregated real-time metrics from allocations
                "cpu": {
                    "percent": total_cpu_percent,
                },
                "memory": {
                    "usage": total_memory_usage,
                    "rss": total_memory_usage,
                },
                "disk": {
                    "read_bytes": total_disk_read,
                    "write_bytes": total_disk_write,
                    "total_bytes": total_disk_read + total_disk_write,
                    "read_ops": 0,  # Not available at node level
                    "write_ops": 0,
                },
            }
            
            self.metrics_history.append(metrics)
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "label": label,
                "node_id": node_id,
                "error": str(e),
            }
    
    def collect_continuous_metrics(
        self,
        target_type: str,
        target_id: str,
        duration_seconds: int = 60,
        interval_seconds: int = 5,
        label: str = "during"
    ) -> List[Dict[str, Any]]:
        """
        Collect metrics continuously during chaos experiment.
        
        Args:
            target_type: Type of target ("allocation", "job", "node")
            target_id: Target identifier
            duration_seconds: How long to collect metrics
            interval_seconds: Time between collections
            label: Label for snapshots
            
        Returns:
            List of metric snapshots
        """
        snapshots = []
        iterations = duration_seconds // interval_seconds
        
        for i in range(iterations):
            if target_type == "allocation":
                snapshot = self.collect_nomad_allocation_metrics(
                    allocation_id=target_id,
                    label=f"{label}_{i}"
                )
            elif target_type == "job":
                snapshot = self.collect_nomad_job_metrics(
                    job_id=target_id,
                    label=f"{label}_{i}"
                )
            elif target_type == "node":
                snapshot = self.collect_node_metrics(
                    node_id=target_id,
                    label=f"{label}_{i}"
                )
            else:
                snapshot = {"error": f"Unknown target type: {target_type}"}
            
            snapshots.append(snapshot)
            
            if i < iterations - 1:  # Don't sleep after last iteration
                time.sleep(interval_seconds)
        
        return snapshots
    
    def compare_metrics(
        self,
        before: Dict[str, Any],
        during: List[Dict[str, Any]],
        after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare metrics from before, during, and after chaos experiment.
        
        Args:
            before: Metrics snapshot before experiment
            during: List of metrics snapshots during experiment
            after: Metrics snapshot after experiment
            
        Returns:
            Comparison report with analysis
        """
        comparison = {
            "before": before,
            "during": during,
            "after": after,
            "analysis": {},
        }
        
        # Analyze CPU changes
        if "cpu" in before and "cpu" in after:
            before_cpu = before["cpu"].get("percent", 0)
            after_cpu = after["cpu"].get("percent", 0)
            
            # Get peak CPU during experiment
            peak_cpu = max(
                [s.get("cpu", {}).get("percent", 0) for s in during if "cpu" in s],
                default=0
            )
            
            comparison["analysis"]["cpu"] = {
                "before_percent": before_cpu,
                "peak_during_percent": peak_cpu,
                "after_percent": after_cpu,
                "change_during": peak_cpu - before_cpu,
                "recovery": before_cpu - after_cpu,
                "recovered": abs(after_cpu - before_cpu) < 5,  # Within 5%
            }
        
        # Analyze memory changes
        if "memory" in before and "memory" in after:
            before_mem = before["memory"].get("usage", 0)
            after_mem = after["memory"].get("usage", 0)
            
            # Get peak memory during experiment
            peak_mem = max(
                [s.get("memory", {}).get("usage", 0) for s in during if "memory" in s],
                default=0
            )
            
            comparison["analysis"]["memory"] = {
                "before_bytes": before_mem,
                "peak_during_bytes": peak_mem,
                "after_bytes": after_mem,
                "change_during_bytes": peak_mem - before_mem,
                "recovery_bytes": before_mem - after_mem,
                "recovered": abs(after_mem - before_mem) < (before_mem * 0.1),  # Within 10%
            }
        
        # Analyze status changes
        if "client_status" in before and "client_status" in after:
            comparison["analysis"]["status"] = {
                "before": before.get("client_status"),
                "after": after.get("client_status"),
                "stable": before.get("client_status") == after.get("client_status"),
            }
        
        # Analyze disk I/O changes
        if "disk" in before and "disk" in after:
            before_read = before["disk"].get("read_bytes", 0)
            before_write = before["disk"].get("write_bytes", 0)
            before_total = before["disk"].get("total_bytes", 0)
            
            after_read = after["disk"].get("read_bytes", 0)
            after_write = after["disk"].get("write_bytes", 0)
            after_total = after["disk"].get("total_bytes", 0)
            
            # Get peak disk I/O during experiment
            peak_read = max(
                [s.get("disk", {}).get("read_bytes", 0) for s in during if "disk" in s],
                default=before_read
            )
            peak_write = max(
                [s.get("disk", {}).get("write_bytes", 0) for s in during if "disk" in s],
                default=before_write
            )
            peak_total = max(
                [s.get("disk", {}).get("total_bytes", 0) for s in during if "disk" in s],
                default=before_total
            )
            
            # Calculate rates (bytes per second) if we have timing info
            # For now, just track absolute changes
            comparison["analysis"]["disk"] = {
                "before_read_bytes": before_read,
                "before_write_bytes": before_write,
                "before_total_bytes": before_total,
                "peak_read_bytes": peak_read,
                "peak_write_bytes": peak_write,
                "peak_total_bytes": peak_total,
                "after_read_bytes": after_read,
                "after_write_bytes": after_write,
                "after_total_bytes": after_total,
                "read_increase": peak_read - before_read,
                "write_increase": peak_write - before_write,
                "total_increase": peak_total - before_total,
                "read_ops_before": before["disk"].get("read_ops", 0),
                "write_ops_before": before["disk"].get("write_ops", 0),
                "read_ops_after": after["disk"].get("read_ops", 0),
                "write_ops_after": after["disk"].get("write_ops", 0),
            }
        
        return comparison
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get all collected metrics."""
        return self.metrics_history
    
    def clear_history(self):
        """Clear metrics history."""
        self.metrics_history = []
