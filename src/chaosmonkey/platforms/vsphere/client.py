"""VMware vSphere platform client implementation."""

from __future__ import annotations

import ssl
import time
from typing import Any, Dict, List, Optional

try:
    from pyVim import connect
    from pyVim.task import WaitForTask
    from pyVmomi import vim
    VSPHERE_AVAILABLE = True
except ImportError:
    VSPHERE_AVAILABLE = False
    connect = None  # type: ignore
    vim = None  # type: ignore
    WaitForTask = None  # type: ignore

from ..base import Platform, VMInfo, VMPowerState


class VSpherePlatform(Platform):
    """
    VMware vSphere platform implementation.
    
    Supports VM power operations with graceful fallback to hard operations.
    """
    
    def __init__(
        self,
        server: str,
        username: str,
        password: str,
        port: int = 443,
        insecure: bool = True
    ):
        """
        Initialize vSphere platform client.
        
        Args:
            server: vCenter/ESXi hostname or IP
            username: Username (e.g., administrator@vsphere.local)
            password: Password
            port: vSphere port (default: 443)
            insecure: Skip SSL verification (default: True for dev/lab)
        """
        if not VSPHERE_AVAILABLE:
            raise ImportError(
                "pyvmomi is required for vSphere support. "
                "Install with: pip install pyvmomi"
            )
        
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.insecure = insecure
        self._si = None
        self._content = None
    
    def connect(self) -> None:
        """Establish connection to vSphere."""
        try:
            if self.insecure:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            else:
                ctx = None
            
            self._si = connect.SmartConnect(
                host=self.server,
                user=self.username,
                pwd=self.password,
                port=self.port,
                sslContext=ctx
            )
            self._content = self._si.RetrieveContent()
        except vim.fault.InvalidLogin:
            raise RuntimeError("Invalid vSphere login credentials")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to vSphere: {e}")
    
    def disconnect(self) -> None:
        """Close connection to vSphere."""
        if self._si:
            connect.Disconnect(self._si)
            self._si = None
            self._content = None
    
    def _ensure_connected(self):
        """Ensure connection is established."""
        if not self._si or not self._content:
            raise RuntimeError("Not connected. Call connect() first or use context manager.")
        return self._content
    
    def _get_obj_by_name(self, vimtype, name: str):
        """Get a vSphere object by name."""
        content = self._ensure_connected()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vimtype], True
        )
        try:
            for obj in container.view:
                if obj.name == name:
                    return obj
        finally:
            container.Destroy()
        return None
    
    def _wait_for_power_state(
        self,
        vm: vim.VirtualMachine,
        expected: str,
        timeout: int = 300,
        poll: float = 2.0
    ) -> bool:
        """Wait until VM reaches expected power state."""
        end = time.time() + timeout
        while time.time() < end:
            vm.UpdateViewData(['runtime.powerState'])
            state = str(vm.runtime.powerState)
            if state == expected:
                return True
            time.sleep(poll)
        return False
    
    def _normalize_power_state(self, vsphere_state: str) -> VMPowerState:
        """Convert vSphere power state to normalized power state."""
        if vsphere_state == 'poweredOn':
            return VMPowerState.POWERED_ON
        elif vsphere_state == 'poweredOff':
            return VMPowerState.POWERED_OFF
        elif vsphere_state == 'suspended':
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
        Discover VMs on vSphere platform.
        
        Args:
            name_pattern: Optional name pattern (simple string matching)
            datacenter: Optional datacenter filter
            **filters: Additional filters
            
        Returns:
            List of VMInfo objects
        """
        content = self._ensure_connected()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        
        vm_list = []
        try:
            for vm in container.view:
                # Apply name filter
                if name_pattern and name_pattern not in vm.name:
                    continue
                
                # Get datacenter name
                dc_name = None
                obj = vm
                while obj:
                    if isinstance(obj, vim.Datacenter):
                        dc_name = obj.name
                        break
                    obj = obj.parent if hasattr(obj, 'parent') else None
                
                # Apply datacenter filter
                if datacenter and dc_name != datacenter:
                    continue
                
                # Get host information
                host_name = None
                if vm.runtime.host:
                    host_name = vm.runtime.host.name
                
                # Get cluster information
                cluster_name = None
                if vm.runtime.host and hasattr(vm.runtime.host, 'parent'):
                    parent = vm.runtime.host.parent
                    if isinstance(parent, vim.ClusterComputeResource):
                        cluster_name = parent.name
                
                # Get VMware Tools status
                tools_status = None
                if hasattr(vm.guest, 'toolsStatus'):
                    tools_status = str(vm.guest.toolsStatus)
                
                vm_info = VMInfo(
                    name=vm.name,
                    id=vm._moId,
                    power_state=self._normalize_power_state(str(vm.runtime.powerState)),
                    platform="vsphere",
                    host=host_name,
                    datacenter=dc_name,
                    cluster=cluster_name,
                    cpu_count=vm.config.hardware.numCPU if vm.config else None,
                    memory_mb=vm.config.hardware.memoryMB if vm.config else None,
                    guest_os=vm.config.guestFullName if vm.config else None,
                    tools_status=tools_status,
                    metadata={
                        "instance_uuid": vm.config.instanceUuid if vm.config else None,
                        "version": vm.config.version if vm.config else None,
                    }
                )
                vm_list.append(vm_info)
        finally:
            container.Destroy()
        
        return vm_list
    
    def get_vm(self, vm_name: str) -> VMInfo:
        """Get detailed information about a specific VM."""
        vm = self._get_obj_by_name(vim.VirtualMachine, vm_name)
        if not vm:
            raise ValueError(f"VM '{vm_name}' not found")
        
        # Get datacenter
        dc_name = None
        obj = vm
        while obj:
            if isinstance(obj, vim.Datacenter):
                dc_name = obj.name
                break
            obj = obj.parent if hasattr(obj, 'parent') else None
        
        # Get host
        host_name = None
        if vm.runtime.host:
            host_name = vm.runtime.host.name
        
        # Get cluster
        cluster_name = None
        if vm.runtime.host and hasattr(vm.runtime.host, 'parent'):
            parent = vm.runtime.host.parent
            if isinstance(parent, vim.ClusterComputeResource):
                cluster_name = parent.name
        
        # Get tools status
        tools_status = None
        if hasattr(vm.guest, 'toolsStatus'):
            tools_status = str(vm.guest.toolsStatus)
        
        return VMInfo(
            name=vm.name,
            id=vm._moId,
            power_state=self._normalize_power_state(str(vm.runtime.powerState)),
            platform="vsphere",
            host=host_name,
            datacenter=dc_name,
            cluster=cluster_name,
            cpu_count=vm.config.hardware.numCPU if vm.config else None,
            memory_mb=vm.config.hardware.memoryMB if vm.config else None,
            guest_os=vm.config.guestFullName if vm.config else None,
            tools_status=tools_status,
            metadata={
                "instance_uuid": vm.config.instanceUuid if vm.config else None,
                "version": vm.config.version if vm.config else None,
            }
        )
    
    def power_on(self, vm_name: str, timeout: int = 300) -> bool:
        """Power on a VM."""
        vm = self._get_obj_by_name(vim.VirtualMachine, vm_name)
        if not vm:
            raise ValueError(f"VM '{vm_name}' not found")
        
        if str(vm.runtime.powerState) == 'poweredOn':
            return True
        
        task = vm.PowerOnVM_Task()
        WaitForTask(task)
        return True
    
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
            graceful: If True, attempt guest shutdown; if False, force power off
            timeout: Timeout in seconds
        """
        vm = self._get_obj_by_name(vim.VirtualMachine, vm_name)
        if not vm:
            raise ValueError(f"VM '{vm_name}' not found")
        
        if str(vm.runtime.powerState) != 'poweredOn':
            return True
        
        if not graceful:
            # Hard power off
            task = vm.PowerOffVM_Task()
            WaitForTask(task)
            return True
        
        # Try graceful shutdown
        try:
            vm.ShutdownGuest()
        except vim.fault.ToolsUnavailable:
            # Fallback to hard power off
            task = vm.PowerOffVM_Task()
            WaitForTask(task)
            return True
        
        # Wait for graceful shutdown
        if self._wait_for_power_state(vm, 'poweredOff', timeout=timeout):
            return True
        
        # Graceful timed out, force power off
        task = vm.PowerOffVM_Task()
        WaitForTask(task)
        return True
    
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
            graceful: If True, attempt guest reboot; if False, force hard reset
            timeout: Timeout in seconds
        """
        vm = self._get_obj_by_name(vim.VirtualMachine, vm_name)
        if not vm:
            raise ValueError(f"VM '{vm_name}' not found")
        
        if str(vm.runtime.powerState) != 'poweredOn':
            # Power on instead
            task = vm.PowerOnVM_Task()
            WaitForTask(task)
            return True
        
        if not graceful:
            # Hard reset
            task = vm.ResetVM_Task()
            WaitForTask(task)
            return True
        
        # Try graceful reboot
        try:
            vm.RebootGuest()
            # No specific power state change to wait for
            time.sleep(10)
            return True
        except vim.fault.ToolsUnavailable:
            # Fallback to hard reset
            task = vm.ResetVM_Task()
            WaitForTask(task)
            return True
    
    def suspend(self, vm_name: str, timeout: int = 300) -> bool:
        """Suspend a VM."""
        vm = self._get_obj_by_name(vim.VirtualMachine, vm_name)
        if not vm:
            raise ValueError(f"VM '{vm_name}' not found")
        
        if str(vm.runtime.powerState) == 'suspended':
            return True
        
        if str(vm.runtime.powerState) != 'poweredOn':
            raise RuntimeError(
                f"VM '{vm_name}' must be powered on to suspend "
                f"(current: {vm.runtime.powerState})"
            )
        
        task = vm.SuspendVM_Task()
        WaitForTask(task)
        return True
