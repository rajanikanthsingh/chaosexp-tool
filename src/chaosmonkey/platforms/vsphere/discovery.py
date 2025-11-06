"""VSphere environment discovery utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .client import VSpherePlatform


class VSphereDiscovery:
    """
    Helper class for discovering vSphere environments.
    
    Provides simplified methods for common discovery patterns.
    """
    
    def __init__(self, platform: VSpherePlatform):
        """
        Initialize discovery helper.
        
        Args:
            platform: Connected VSpherePlatform instance
        """
        self.platform = platform
    
    def discover_by_datacenter(self, datacenter: str) -> List[Dict[str, Any]]:
        """
        Discover all VMs in a specific datacenter.
        
        Args:
            datacenter: Datacenter name
            
        Returns:
            List of VM information dictionaries
        """
        vms = self.platform.discover_vms(datacenter=datacenter)
        return [self._vm_to_dict(vm) for vm in vms]
    
    def discover_by_cluster(
        self,
        datacenter: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover VMs grouped by cluster.
        
        Args:
            datacenter: Optional datacenter filter
            
        Returns:
            Dictionary mapping cluster names to lists of VMs
        """
        vms = self.platform.discover_vms(datacenter=datacenter)
        
        clusters: Dict[str, List[Dict[str, Any]]] = {}
        for vm in vms:
            cluster = vm.cluster or "unclustered"
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(self._vm_to_dict(vm))
        
        return clusters
    
    def discover_by_host(
        self,
        datacenter: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover VMs grouped by host.
        
        Args:
            datacenter: Optional datacenter filter
            
        Returns:
            Dictionary mapping host names to lists of VMs
        """
        vms = self.platform.discover_vms(datacenter=datacenter)
        
        hosts: Dict[str, List[Dict[str, Any]]] = {}
        for vm in vms:
            host = vm.host or "unknown"
            if host not in hosts:
                hosts[host] = []
            hosts[host].append(self._vm_to_dict(vm))
        
        return hosts
    
    def discover_powered_on(
        self,
        datacenter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover only powered-on VMs.
        
        Args:
            datacenter: Optional datacenter filter
            
        Returns:
            List of powered-on VM information dictionaries
        """
        from ..base import VMPowerState
        
        vms = self.platform.discover_vms(datacenter=datacenter)
        powered_on = [
            vm for vm in vms
            if vm.power_state == VMPowerState.POWERED_ON
        ]
        return [self._vm_to_dict(vm) for vm in powered_on]
    
    def get_environment_summary(
        self,
        datacenter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary statistics for the vSphere environment.
        
        Args:
            datacenter: Optional datacenter filter
            
        Returns:
            Dictionary with environment statistics
        """
        from ..base import VMPowerState
        
        vms = self.platform.discover_vms(datacenter=datacenter)
        
        total = len(vms)
        powered_on = sum(1 for vm in vms if vm.power_state == VMPowerState.POWERED_ON)
        powered_off = sum(1 for vm in vms if vm.power_state == VMPowerState.POWERED_OFF)
        suspended = sum(1 for vm in vms if vm.power_state == VMPowerState.SUSPENDED)
        
        datacenters = set(vm.datacenter for vm in vms if vm.datacenter)
        clusters = set(vm.cluster for vm in vms if vm.cluster)
        hosts = set(vm.host for vm in vms if vm.host)
        
        total_cpu = sum(vm.cpu_count for vm in vms if vm.cpu_count)
        total_memory_gb = sum(
            (vm.memory_mb / 1024) for vm in vms if vm.memory_mb
        )
        
        return {
            "total_vms": total,
            "power_states": {
                "powered_on": powered_on,
                "powered_off": powered_off,
                "suspended": suspended,
            },
            "datacenters": len(datacenters),
            "clusters": len(clusters),
            "hosts": len(hosts),
            "resources": {
                "total_cpus": total_cpu,
                "total_memory_gb": round(total_memory_gb, 2),
            }
        }
    
    @staticmethod
    def _vm_to_dict(vm) -> Dict[str, Any]:
        """Convert VMInfo to dictionary."""
        return {
            "name": vm.name,
            "id": vm.id,
            "power_state": vm.power_state.value,
            "platform": vm.platform,
            "host": vm.host,
            "datacenter": vm.datacenter,
            "cluster": vm.cluster,
            "cpu_count": vm.cpu_count,
            "memory_mb": vm.memory_mb,
            "guest_os": vm.guest_os,
            "tools_status": vm.tools_status,
            "metadata": vm.metadata,
        }
