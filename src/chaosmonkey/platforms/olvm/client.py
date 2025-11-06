"""OLVM/oVirt platform client implementation."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

try:
    import ovirtsdk4 as sdk
    import ovirtsdk4.types as types
    OLVM_AVAILABLE = True
except ImportError:
    OLVM_AVAILABLE = False
    sdk = None  # type: ignore
    types = None  # type: ignore

from ..base import Platform, VMInfo, VMPowerState


class OLVMPlatform(Platform):
    """
    OLVM/oVirt platform implementation.
    
    Supports batch operations on multiple VMs with parallel execution.
    """
    
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        ca_file: Optional[str] = None,
        insecure: bool = False,
        timeout: int = 60
    ):
        """
        Initialize OLVM platform client.
        
        Args:
            url: OLVM engine API URL (e.g., https://engine.example.com/ovirt-engine/api)
            username: Username (e.g., admin@internal)
            password: Password
            ca_file: Path to CA certificate file (recommended)
            insecure: Skip TLS verification (dev/lab only)
            timeout: Connection timeout in seconds
        """
        if not OLVM_AVAILABLE:
            raise ImportError(
                "ovirtsdk4 is required for OLVM support. "
                "Install with: pip install ovirt-engine-sdk-python"
            )
        
        self.url = url
        self.username = username
        self.password = password
        self.ca_file = ca_file
        self.insecure = insecure
        self.timeout = timeout
        self._connection: Optional[sdk.Connection] = None
    
    def connect(self) -> None:
        """Establish connection to OLVM engine."""
        try:
            self._connection = sdk.Connection(
                url=self.url,
                username=self.username,
                password=self.password,
                ca_file=self.ca_file,
                insecure=self.insecure,
                timeout=self.timeout,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to OLVM engine: {e}")
    
    def disconnect(self) -> None:
        """Close connection to OLVM engine."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _ensure_connected(self) -> sdk.Connection:
        """Ensure connection is established."""
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first or use context manager.")
        return self._connection
    
    def _get_vm_service(self, vm_name: str):
        """Get VM service object for a specific VM."""
        conn = self._ensure_connected()
        sys_svc = conn.system_service()
        vms_svc = sys_svc.vms_service()
        
        matches = vms_svc.list(search=f"name={vm_name}")
        vm = next((v for v in matches if v.name == vm_name), None)
        
        if vm is None:
            raise ValueError(f"VM '{vm_name}' not found")
        
        return vm, vms_svc.vm_service(vm.id)
    
    def _wait_for_status(
        self,
        vm_svc,
        expected: types.VmStatus,
        timeout: int = 300,
        poll: float = 2.0
    ) -> bool:
        """Wait for VM to reach expected status."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = vm_svc.get().status
            if status == expected:
                return True
            time.sleep(poll)
        return vm_svc.get().status == expected
    
    def _normalize_power_state(self, ovirt_status: types.VmStatus) -> VMPowerState:
        """Convert oVirt VM status to normalized power state."""
        if ovirt_status == types.VmStatus.UP:
            return VMPowerState.POWERED_ON
        elif ovirt_status == types.VmStatus.DOWN:
            return VMPowerState.POWERED_OFF
        elif ovirt_status == types.VmStatus.SUSPENDED:
            return VMPowerState.SUSPENDED
        else:
            return VMPowerState.UNKNOWN
    
    def discover_vms(
        self,
        name_pattern: Optional[str] = None,
        datacenter: Optional[str] = None,
        **filters: Any
    ) -> List[VMInfo]:
        """
        Discover VMs on OLVM platform.
        
        Args:
            name_pattern: Optional search pattern (e.g., "web-*")
            datacenter: Optional datacenter filter
            **filters: Additional oVirt search parameters
            
        Returns:
            List of VMInfo objects
        """
        conn = self._ensure_connected()
        sys_svc = conn.system_service()
        vms_svc = sys_svc.vms_service()
        
        # Build search query
        search_parts = []
        if name_pattern:
            search_parts.append(f"name={name_pattern}")
        if datacenter:
            search_parts.append(f"datacenter={datacenter}")
        
        search_query = " and ".join(search_parts) if search_parts else None
        vms = vms_svc.list(search=search_query)
        
        vm_list = []
        for vm in vms:
            # Get host information if available
            host_name = None
            if vm.host and vm.host.id:
                try:
                    hosts_svc = sys_svc.hosts_service()
                    host = hosts_svc.host_service(vm.host.id).get()
                    host_name = host.name
                except Exception:
                    pass
            
            # Get cluster information
            cluster_name = None
            if vm.cluster and vm.cluster.id:
                try:
                    clusters_svc = sys_svc.clusters_service()
                    cluster = clusters_svc.cluster_service(vm.cluster.id).get()
                    cluster_name = cluster.name
                except Exception:
                    pass
            
            vm_info = VMInfo(
                name=vm.name,
                id=vm.id,
                power_state=self._normalize_power_state(vm.status),
                platform="olvm",
                host=host_name,
                cluster=cluster_name,
                cpu_count=vm.cpu.topology.cores * vm.cpu.topology.sockets if vm.cpu else None,
                memory_mb=vm.memory // (1024 * 1024) if vm.memory else None,
                guest_os=vm.os.type if vm.os else None,
                metadata={
                    "fqdn": vm.fqdn,
                    "description": vm.description,
                }
            )
            vm_list.append(vm_info)
        
        return vm_list
    
    def get_vm(self, vm_name: str) -> VMInfo:
        """Get detailed information about a specific VM."""
        vm, vm_svc = self._get_vm_service(vm_name)
        
        conn = self._ensure_connected()
        sys_svc = conn.system_service()
        
        # Get host information
        host_name = None
        if vm.host and vm.host.id:
            try:
                hosts_svc = sys_svc.hosts_service()
                host = hosts_svc.host_service(vm.host.id).get()
                host_name = host.name
            except Exception:
                pass
        
        # Get cluster information
        cluster_name = None
        if vm.cluster and vm.cluster.id:
            try:
                clusters_svc = sys_svc.clusters_service()
                cluster = clusters_svc.cluster_service(vm.cluster.id).get()
                cluster_name = cluster.name
            except Exception:
                pass
        
        return VMInfo(
            name=vm.name,
            id=vm.id,
            power_state=self._normalize_power_state(vm.status),
            platform="olvm",
            host=host_name,
            cluster=cluster_name,
            cpu_count=vm.cpu.topology.cores * vm.cpu.topology.sockets if vm.cpu else None,
            memory_mb=vm.memory // (1024 * 1024) if vm.memory else None,
            guest_os=vm.os.type if vm.os else None,
            metadata={
                "fqdn": vm.fqdn,
                "description": vm.description,
            }
        )
    
    def power_on(self, vm_name: str, timeout: int = 300) -> bool:
        """Power on a VM."""
        vm, vm_svc = self._get_vm_service(vm_name)
        
        if vm.status == types.VmStatus.UP:
            return True
        
        vm_svc.start()
        
        if self._wait_for_status(vm_svc, types.VmStatus.UP, timeout=timeout):
            return True
        
        raise RuntimeError(f"VM '{vm_name}' failed to reach UP state in {timeout}s")
    
    def power_off(
        self,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """
        Power off a VM.
        
        Args:
            vm_name: Name of the VM
            graceful: If True, attempt graceful shutdown; if False, force stop
            timeout: Timeout in seconds
        """
        vm, vm_svc = self._get_vm_service(vm_name)
        
        if vm.status == types.VmStatus.DOWN:
            return True
        
        if not graceful:
            # Force hard stop
            vm_svc.stop()
            if self._wait_for_status(vm_svc, types.VmStatus.DOWN, timeout=min(timeout, 180)):
                return True
            raise RuntimeError(f"VM '{vm_name}' hard stop timeout")
        
        # Try graceful shutdown
        try:
            vm_svc.shutdown()
        except Exception as e:
            # Fallback to hard stop
            vm_svc.stop()
            if self._wait_for_status(vm_svc, types.VmStatus.DOWN, timeout=min(timeout, 180)):
                return True
            raise RuntimeError(
                f"VM '{vm_name}' graceful shutdown failed ({e}) and hard stop timeout"
            )
        
        if self._wait_for_status(vm_svc, types.VmStatus.DOWN, timeout=timeout):
            return True
        
        # Graceful timed out, try hard stop
        vm_svc.stop()
        if self._wait_for_status(vm_svc, types.VmStatus.DOWN, timeout=min(timeout, 180)):
            return True
        
        raise RuntimeError(
            f"VM '{vm_name}' graceful shutdown timed out and hard stop failed"
        )
    
    def reboot(
        self,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """
        Reboot a VM.
        
        Args:
            vm_name: Name of the VM
            graceful: Currently ignored (always hard reboot in oVirt)
            timeout: Timeout in seconds
        """
        vm, vm_svc = self._get_vm_service(vm_name)
        
        if vm.status != types.VmStatus.UP:
            # Start instead of reboot
            vm_svc.start()
            if self._wait_for_status(vm_svc, types.VmStatus.UP, timeout=min(timeout, 300)):
                return True
            raise RuntimeError(f"VM '{vm_name}' failed to start (was DOWN)")
        
        vm_svc.reboot()
        
        if self._wait_for_status(vm_svc, types.VmStatus.UP, timeout=timeout):
            return True
        
        raise RuntimeError(
            f"VM '{vm_name}' did not report UP after reboot within {timeout}s"
        )
    
    def suspend(self, vm_name: str, timeout: int = 300) -> bool:
        """Suspend a VM."""
        vm, vm_svc = self._get_vm_service(vm_name)
        
        if vm.status == types.VmStatus.SUSPENDED:
            return True
        
        if vm.status != types.VmStatus.UP:
            raise RuntimeError(f"VM '{vm_name}' must be UP to suspend (current: {vm.status})")
        
        vm_svc.suspend()
        
        if self._wait_for_status(vm_svc, types.VmStatus.SUSPENDED, timeout=timeout):
            return True
        
        raise RuntimeError(f"VM '{vm_name}' failed to suspend within {timeout}s")
