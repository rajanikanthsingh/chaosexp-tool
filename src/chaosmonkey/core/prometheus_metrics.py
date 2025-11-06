"""Prometheus-based metrics collection for chaos experiments."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from prometheus_api_client import PrometheusConnect
except ImportError:
    PrometheusConnect = None

logger = logging.getLogger(__name__)


@dataclass
class PrometheusMetric:
    """Represents a single Prometheus metric value."""
    timestamp: datetime
    value: float


class PrometheusMetricsCollector:
    """
    Collects resource usage metrics from Prometheus for chaos monitoring.
    
    This collector queries Prometheus node_exporter metrics to get real-time
    CPU, memory, and disk I/O statistics for monitored nodes.
    """
    
    def __init__(self, prometheus_url: str, timeout: int = 10):
        """
        Initialize the Prometheus metrics collector.
        
        Args:
            prometheus_url: URL of the Prometheus server (e.g., http://prometheus:9090)
            timeout: Request timeout in seconds
        """
        if PrometheusConnect is None:
            raise ImportError(
                "prometheus-api-client is required for Prometheus metrics collection. "
                "Install it with: pip install prometheus-api-client"
            )
        
        self.prometheus_url = prometheus_url
        self.timeout = timeout
        self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        logger.info(f"Initialized Prometheus metrics collector: {prometheus_url}")
    
    def collect_node_metrics(
        self,
        node_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Collect metrics for a specific node from Prometheus.
        
        Args:
            node_name: Name of the node to collect metrics for
            start_time: Start time for metrics collection (defaults to now)
            end_time: End time for metrics collection (defaults to now)
        
        Returns:
            Dictionary containing CPU, memory, and disk I/O metrics
        """
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time
        
        logger.debug(f"Collecting metrics for node: {node_name}")
        
        # Get the Prometheus instance name for this node
        # Try both short hostname and FQDN patterns
        instance_patterns = [
            f"{node_name}:9100",
            f"{node_name}.$domain:9100",
            f"{node_name}.$domain:9100",
        ]
        
        metrics = {
            "node_name": node_name,
            "timestamp": end_time.isoformat(),
            "cpu_percent": 0.0,
            "memory_used_bytes": 0,
            "memory_total_bytes": 0,
            "memory_percent": 0.0,
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "disk_read_ops": 0,
            "disk_write_ops": 0,
        }
        
        # Try to find the instance
        instance = None
        for pattern in instance_patterns:
            if self._check_instance_exists(pattern):
                instance = pattern
                logger.debug(f"Found Prometheus instance: {instance}")
                break
        
        if not instance:
            logger.warning(f"Node {node_name} not found in Prometheus metrics")
            return metrics
        
        # Collect CPU metrics
        try:
            cpu_percent = self._get_cpu_usage(instance, end_time)
            if cpu_percent is not None:
                metrics["cpu_percent"] = cpu_percent
                logger.debug(f"CPU usage: {cpu_percent:.2f}%")
        except Exception as e:
            logger.error(f"Failed to collect CPU metrics: {e}")
        
        # Collect memory metrics
        try:
            memory_metrics = self._get_memory_usage(instance, end_time)
            metrics.update(memory_metrics)
            if memory_metrics.get("memory_percent", 0) > 0:
                logger.debug(f"Memory usage: {memory_metrics['memory_percent']:.2f}%")
        except Exception as e:
            logger.error(f"Failed to collect memory metrics: {e}")
        
        # Collect disk I/O metrics
        try:
            disk_metrics = self._get_disk_io(instance, end_time)
            metrics.update(disk_metrics)
            logger.debug(f"Disk I/O - Read: {disk_metrics.get('disk_read_bytes', 0)}, "
                        f"Write: {disk_metrics.get('disk_write_bytes', 0)}")
        except Exception as e:
            logger.error(f"Failed to collect disk I/O metrics: {e}")
        
        # Transform to nested structure expected by metrics report
        return self._transform_to_nested_format(metrics)
    
    def collect_time_series(
        self,
        node_name: str,
        start_time: datetime,
        end_time: datetime,
        step: str = "30s"
    ) -> Dict[str, List[PrometheusMetric]]:
        """
        Collect time-series metrics for a node over a time range.
        
        Args:
            node_name: Name of the node to collect metrics for
            start_time: Start time for the time series
            end_time: End time for the time series
            step: Step size for the time series (e.g., "30s", "1m")
        
        Returns:
            Dictionary containing time-series data for each metric type
        """
        logger.info(f"Collecting time-series metrics for {node_name} "
                   f"from {start_time} to {end_time}")
        
        # Get the Prometheus instance name
        instance_patterns = [
            f"{node_name}:9100",
            f"{node_name}.$domain:9100",
            f"{node_name}.$domain:9100",
        ]
        
        instance = None
        for pattern in instance_patterns:
            if self._check_instance_exists(pattern):
                instance = pattern
                break
        
        if not instance:
            logger.warning(f"Node {node_name} not found in Prometheus metrics")
            return {}
        
        time_series = {
            "cpu_percent": [],
            "memory_percent": [],
            "disk_read_bytes": [],
            "disk_write_bytes": [],
        }
        
        # Query time-series data
        try:
            # CPU usage over time
            cpu_query = (
                f'100 - (avg by (instance) '
                f'(rate(node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[1m])) * 100)'
            )
            cpu_data = self.prom.custom_query_range(
                query=cpu_query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            if cpu_data:
                for timestamp, value in cpu_data[0].get('values', []):
                    time_series["cpu_percent"].append(
                        PrometheusMetric(
                            timestamp=datetime.fromtimestamp(timestamp),
                            value=float(value)
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to collect CPU time-series: {e}")
        
        try:
            # Memory usage over time
            mem_query = (
                f'(1 - (node_memory_MemAvailable_bytes{{instance="{instance}"}} / '
                f'node_memory_MemTotal_bytes{{instance="{instance}"}})) * 100'
            )
            mem_data = self.prom.custom_query_range(
                query=mem_query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            if mem_data:
                for timestamp, value in mem_data[0].get('values', []):
                    time_series["memory_percent"].append(
                        PrometheusMetric(
                            timestamp=datetime.fromtimestamp(timestamp),
                            value=float(value)
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to collect memory time-series: {e}")
        
        try:
            # Disk read rate over time
            disk_read_query = f'rate(node_disk_read_bytes_total{{instance="{instance}"}}[1m])'
            disk_read_data = self.prom.custom_query_range(
                query=disk_read_query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            if disk_read_data:
                for result in disk_read_data:
                    for timestamp, value in result.get('values', []):
                        time_series["disk_read_bytes"].append(
                            PrometheusMetric(
                                timestamp=datetime.fromtimestamp(timestamp),
                                value=float(value)
                            )
                        )
        except Exception as e:
            logger.error(f"Failed to collect disk read time-series: {e}")
        
        try:
            # Disk write rate over time
            disk_write_query = f'rate(node_disk_written_bytes_total{{instance="{instance}"}}[1m])'
            disk_write_data = self.prom.custom_query_range(
                query=disk_write_query,
                start_time=start_time,
                end_time=end_time,
                step=step
            )
            if disk_write_data:
                for result in disk_write_data:
                    for timestamp, value in result.get('values', []):
                        time_series["disk_write_bytes"].append(
                            PrometheusMetric(
                                timestamp=datetime.fromtimestamp(timestamp),
                                value=float(value)
                            )
                        )
        except Exception as e:
            logger.error(f"Failed to collect disk write time-series: {e}")
        
        return time_series
    
    def _check_instance_exists(self, instance: str) -> bool:
        """Check if an instance exists in Prometheus."""
        try:
            query = f'up{{instance="{instance}"}}'
            result = self.prom.custom_query(query=query)
            return len(result) > 0
        except Exception as e:
            logger.debug(f"Instance check failed for {instance}: {e}")
            return False
    
    def _get_cpu_usage(self, instance: str, timestamp: datetime) -> Optional[float]:
        """Get CPU usage percentage for an instance."""
        query = (
            f'100 - (avg by (instance) '
            f'(rate(node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[5m])) * 100)'
        )
        result = self.prom.custom_query(query=query)
        
        if result and len(result) > 0:
            value = result[0].get('value', [None, None])[1]
            if value is not None:
                return float(value)
        
        return None
    
    def _get_memory_usage(self, instance: str, timestamp: datetime) -> Dict[str, Any]:
        """Get memory usage metrics for an instance."""
        metrics = {
            "memory_used_bytes": 0,
            "memory_total_bytes": 0,
            "memory_percent": 0.0,
        }
        
        # Get total memory
        total_query = f'node_memory_MemTotal_bytes{{instance="{instance}"}}'
        total_result = self.prom.custom_query(query=total_query)
        if total_result and len(total_result) > 0:
            total_value = total_result[0].get('value', [None, None])[1]
            if total_value is not None:
                metrics["memory_total_bytes"] = int(float(total_value))
        
        # Get available memory
        avail_query = f'node_memory_MemAvailable_bytes{{instance="{instance}"}}'
        avail_result = self.prom.custom_query(query=avail_query)
        if avail_result and len(avail_result) > 0:
            avail_value = avail_result[0].get('value', [None, None])[1]
            if avail_value is not None and metrics["memory_total_bytes"] > 0:
                avail_bytes = int(float(avail_value))
                metrics["memory_used_bytes"] = metrics["memory_total_bytes"] - avail_bytes
                metrics["memory_percent"] = (
                    (metrics["memory_used_bytes"] / metrics["memory_total_bytes"]) * 100
                )
        
        return metrics
    
    def _get_disk_io(self, instance: str, timestamp: datetime) -> Dict[str, Any]:
        """Get disk I/O metrics for an instance."""
        metrics = {
            "disk_read_bytes": 0,
            "disk_write_bytes": 0,
            "disk_read_ops": 0,
            "disk_write_ops": 0,
        }
        
        # Get disk read rate (bytes/sec)
        read_query = f'rate(node_disk_read_bytes_total{{instance="{instance}"}}[5m])'
        read_result = self.prom.custom_query(query=read_query)
        if read_result and len(read_result) > 0:
            # Sum across all disks
            total_read = sum(
                float(r.get('value', [None, 0])[1] or 0) 
                for r in read_result
            )
            metrics["disk_read_bytes"] = int(total_read)
        
        # Get disk write rate (bytes/sec)
        write_query = f'rate(node_disk_written_bytes_total{{instance="{instance}"}}[5m])'
        write_result = self.prom.custom_query(query=write_query)
        if write_result and len(write_result) > 0:
            # Sum across all disks
            total_write = sum(
                float(r.get('value', [None, 0])[1] or 0) 
                for r in write_result
            )
            metrics["disk_write_bytes"] = int(total_write)
        
        # Get disk read ops rate (ops/sec)
        read_ops_query = f'rate(node_disk_reads_completed_total{{instance="{instance}"}}[5m])'
        read_ops_result = self.prom.custom_query(query=read_ops_query)
        if read_ops_result and len(read_ops_result) > 0:
            total_read_ops = sum(
                float(r.get('value', [None, 0])[1] or 0) 
                for r in read_ops_result
            )
            metrics["disk_read_ops"] = int(total_read_ops)
        
        # Get disk write ops rate (ops/sec)
        write_ops_query = f'rate(node_disk_writes_completed_total{{instance="{instance}"}}[5m])'
        write_ops_result = self.prom.custom_query(query=write_ops_query)
        if write_ops_result and len(write_ops_result) > 0:
            total_write_ops = sum(
                float(r.get('value', [None, 0])[1] or 0) 
                for r in write_ops_result
            )
            metrics["disk_write_ops"] = int(total_write_ops)
        
        return metrics
    
    def _transform_to_nested_format(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform flat Prometheus metrics to nested format expected by metrics report.
        
        Converts:
            {"cpu_percent": 12.5, "memory_used_bytes": 1024, ...}
        To:
            {"cpu": {"percent": 12.5}, "memory": {"usage": 1024}, ...}
        
        Args:
            metrics: Flat metrics dictionary from Prometheus
            
        Returns:
            Nested metrics dictionary compatible with metrics report
        """
        return {
            "node_name": metrics.get("node_name"),
            "timestamp": metrics.get("timestamp"),
            "cpu": {
                "percent": metrics.get("cpu_percent", 0.0),
            },
            "memory": {
                "usage": metrics.get("memory_used_bytes", 0),
                "total": metrics.get("memory_total_bytes", 0),
                "percent": metrics.get("memory_percent", 0.0),
            },
            "disk": {
                "read_bytes": metrics.get("disk_read_bytes", 0),
                "write_bytes": metrics.get("disk_write_bytes", 0),
                "total_bytes": metrics.get("disk_read_bytes", 0) + metrics.get("disk_write_bytes", 0),
                "read_ops": metrics.get("disk_read_ops", 0),
                "write_ops": metrics.get("disk_write_ops", 0),
            }
        }
