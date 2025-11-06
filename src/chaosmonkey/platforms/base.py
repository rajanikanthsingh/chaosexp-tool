"""Base platform interface for virtualization providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class VMPowerState(str, Enum):
    """VM power states normalized across platforms."""
    
    POWERED_ON = "powered_on"
    POWERED_OFF = "powered_off"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


@dataclass
class VMInfo:
    """Normalized VM information across platforms."""
    
    name: str
    id: str
    power_state: VMPowerState
    platform: str  # "olvm", "vsphere", etc.
    host: Optional[str] = None
    datacenter: Optional[str] = None
    cluster: Optional[str] = None
    cpu_count: Optional[int] = None
    memory_mb: Optional[int] = None
    guest_os: Optional[str] = None
    tools_status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Platform(ABC):
    """
    Abstract base class for virtualization platform integrations.
    
    All platform implementations (OLVM, vSphere, etc.) must implement this interface
    to ensure consistent behavior across different virtualization providers.
    """
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the platform."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the platform."""
        pass
    
    @abstractmethod
    def discover_vms(
        self,
        name_pattern: Optional[str] = None,
        datacenter: Optional[str] = None,
        **filters: Any
    ) -> List[VMInfo]:
        """
        Discover VMs on the platform.
        
        Args:
            name_pattern: Optional regex or glob pattern to filter VM names
            datacenter: Optional datacenter filter
            **filters: Platform-specific filter parameters
            
        Returns:
            List of VMInfo objects
        """
        pass
    
    @abstractmethod
    def get_vm(self, vm_name: str) -> VMInfo:
        """
        Get detailed information about a specific VM.
        
        Args:
            vm_name: Name of the VM
            
        Returns:
            VMInfo object
            
        Raises:
            ValueError: If VM not found
        """
        pass
    
    @abstractmethod
    def power_on(self, vm_name: str, timeout: int = 300) -> bool:
        """
        Power on a VM.
        
        Args:
            vm_name: Name of the VM to power on
            timeout: Maximum time to wait for operation (seconds)
            
        Returns:
            True if successful
            
        Raises:
            RuntimeError: If operation fails
        """
        pass
    
    @abstractmethod
    def power_off(
        self,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """
        Power off a VM.
        
        Args:
            vm_name: Name of the VM to power off
            graceful: If True, attempt guest shutdown first; if False, force power off
            timeout: Maximum time to wait for operation (seconds)
            
        Returns:
            True if successful
            
        Raises:
            RuntimeError: If operation fails
        """
        pass
    
    @abstractmethod
    def reboot(
        self,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """
        Reboot a VM.
        
        Args:
            vm_name: Name of the VM to reboot
            graceful: If True, attempt guest reboot; if False, force hard reset
            timeout: Maximum time to wait for operation (seconds)
            
        Returns:
            True if successful
            
        Raises:
            RuntimeError: If operation fails
        """
        pass
    
    @abstractmethod
    def suspend(self, vm_name: str, timeout: int = 300) -> bool:
        """
        Suspend a VM.
        
        Args:
            vm_name: Name of the VM to suspend
            timeout: Maximum time to wait for operation (seconds)
            
        Returns:
            True if successful
            
        Raises:
            RuntimeError: If operation fails
        """
        pass
    
    def batch_power_on(
        self,
        vm_names: List[str],
        parallel: int = 5,
        timeout: int = 300
    ) -> Dict[str, bool]:
        """
        Power on multiple VMs in parallel.
        
        Args:
            vm_names: List of VM names to power on
            parallel: Maximum number of parallel operations
            timeout: Timeout per VM operation (seconds)
            
        Returns:
            Dict mapping VM names to success status
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(self.power_on, name, timeout): name
                for name in vm_names
            }
            for future in as_completed(futures):
                vm_name = futures[future]
                try:
                    results[vm_name] = future.result()
                except Exception:
                    results[vm_name] = False
        return results
    
    def batch_power_off(
        self,
        vm_names: List[str],
        graceful: bool = True,
        parallel: int = 5,
        timeout: int = 300
    ) -> Dict[str, bool]:
        """
        Power off multiple VMs in parallel.
        
        Args:
            vm_names: List of VM names to power off
            graceful: If True, attempt graceful shutdown
            parallel: Maximum number of parallel operations
            timeout: Timeout per VM operation (seconds)
            
        Returns:
            Dict mapping VM names to success status
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(self.power_off, name, graceful, timeout): name
                for name in vm_names
            }
            for future in as_completed(futures):
                vm_name = futures[future]
                try:
                    results[vm_name] = future.result()
                except Exception:
                    results[vm_name] = False
        return results
    
    def batch_reboot(
        self,
        vm_names: List[str],
        graceful: bool = True,
        parallel: int = 5,
        timeout: int = 300
    ) -> Dict[str, bool]:
        """
        Reboot multiple VMs in parallel.
        
        Args:
            vm_names: List of VM names to reboot
            graceful: If True, attempt graceful reboot
            parallel: Maximum number of parallel operations
            timeout: Timeout per VM operation (seconds)
            
        Returns:
            Dict mapping VM names to success status
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(self.reboot, name, graceful, timeout): name
                for name in vm_names
            }
            for future in as_completed(futures):
                vm_name = futures[future]
                try:
                    results[vm_name] = future.result()
                except Exception:
                    results[vm_name] = False
        return results
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
