"""Platform orchestration for VM-based chaos experiments."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from ..config import Settings
from ..platforms.olvm import OLVMPlatform
from ..platforms.vsphere import VSpherePlatform
from ..platforms.dora import DoraClient
from ..platforms.base import VMInfo

console = Console()


class PlatformOrchestrator:
    """
    Orchestrates platform-based chaos experiments.
    
    Provides discovery and experiment execution for VM-based targets
    across OLVM and vSphere platforms.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize platform orchestrator.
        
        Args:
            settings: Application settings with platform credentials
        """
        self.settings = settings
        self._olvm_client: Optional[OLVMPlatform] = None
        self._vsphere_client: Optional[VSpherePlatform] = None
        self._dora_client: Optional[DoraClient] = None
    
    def get_olvm_client(self) -> OLVMPlatform:
        """Get or create OLVM client."""
        if not self._olvm_client:
            cfg = self.settings.platforms.olvm
            if not cfg.url or not cfg.username or not cfg.password:
                raise RuntimeError(
                    "OLVM configuration incomplete. Please set OLVM_URL, "
                    "OLVM_USERNAME, and OLVM_PASSWORD in environment or config file."
                )
            self._olvm_client = OLVMPlatform(
                url=cfg.url,
                username=cfg.username,
                password=cfg.password,
                ca_file=cfg.ca_file,
                insecure=cfg.insecure
            )
        return self._olvm_client
    
    def get_vsphere_client(self) -> VSpherePlatform:
        """Get or create vSphere client."""
        if not self._vsphere_client:
            cfg = self.settings.platforms.vsphere
            if not cfg.server or not cfg.username or not cfg.password:
                raise RuntimeError(
                    "vSphere configuration incomplete. Please set VSPHERE_SERVER, "
                    "VSPHERE_USERNAME, and VSPHERE_PASSWORD in environment or config file."
                )
            self._vsphere_client = VSpherePlatform(
                server=cfg.server,
                username=cfg.username,
                password=cfg.password,
                port=cfg.port,
                insecure=cfg.insecure
            )
        return self._vsphere_client
    
    def get_dora_client(self) -> DoraClient:
        """Get or create Dora client."""
        if not self._dora_client:
            cfg = self.settings.platforms.dora
            self._dora_client = DoraClient(
                dora_host=cfg.host,
                api_port=cfg.api_port,
                auth_port=cfg.auth_port
            )
        return self._dora_client
    
    def discover_vms(
        self,
        platform: str,
        name_pattern: Optional[str] = None,
        datacenter: Optional[str] = None,
        **filters: Any
    ) -> List[VMInfo]:
        """
        Discover VMs on a platform.
        
        Args:
            platform: Platform type ('olvm' or 'vsphere')
            name_pattern: Optional VM name pattern
            datacenter: Optional datacenter filter
            **filters: Additional platform-specific filters
            
        Returns:
            List of discovered VMs
        """
        console.print(f"[cyan]Discovering VMs on {platform}...[/cyan]")
        
        if platform == "olvm":
            client = self.get_olvm_client()
            with client:
                vms = client.discover_vms(
                    name_pattern=name_pattern,
                    datacenter=datacenter,
                    **filters
                )
        elif platform == "vsphere":
            client = self.get_vsphere_client()
            with client:
                vms = client.discover_vms(
                    name_pattern=name_pattern,
                    datacenter=datacenter,
                    **filters
                )
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        console.print(f"[green]✓ Discovered {len(vms)} VMs[/green]")
        return vms
    
    def discover_dora_environment(
        self,
        environment: str,
        username: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Discover environment using Dora API.
        
        Args:
            environment: Environment name
            username: Optional username (uses config if not provided)
            password: Optional password (uses config if not provided)
            
        Returns:
            Dictionary with environment data
        """
        client = self.get_dora_client()
        
        # Use config credentials if not provided
        cfg = self.settings.platforms.dora
        username = username or cfg.username
        password = password or cfg.password
        
        if not username or not password:
            raise RuntimeError(
                "Dora credentials not provided. Please set DORA_USERNAME and "
                "DORA_PASSWORD in environment or config file, or pass them as arguments."
            )
        
        console.print(f"[cyan]Discovering environment: {environment}[/cyan]")
        data = client.get_environment_data(environment, username, password)
        console.print(f"[green]✓ Retrieved environment data[/green]")
        
        return data
    
    def list_dora_environments(self) -> List[str]:
        """List available Dora environments."""
        return DoraClient.list_environments()
    
    def get_vm_info(self, platform: str, vm_name: str) -> VMInfo:
        """
        Get detailed information about a specific VM.
        
        Args:
            platform: Platform type ('olvm' or 'vsphere')
            vm_name: VM name
            
        Returns:
            VM information
        """
        if platform == "olvm":
            client = self.get_olvm_client()
            with client:
                return client.get_vm(vm_name)
        elif platform == "vsphere":
            client = self.get_vsphere_client()
            with client:
                return client.get_vm(vm_name)
        else:
            raise ValueError(f"Unknown platform: {platform}")
    
    def power_on_vm(
        self,
        platform: str,
        vm_name: str,
        timeout: int = 300
    ) -> bool:
        """Power on a VM."""
        console.print(f"[yellow]Powering on VM: {vm_name}[/yellow]")
        
        if platform == "olvm":
            client = self.get_olvm_client()
            with client:
                success = client.power_on(vm_name, timeout=timeout)
        elif platform == "vsphere":
            client = self.get_vsphere_client()
            with client:
                success = client.power_on(vm_name, timeout=timeout)
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        if success:
            console.print(f"[green]✓ VM {vm_name} powered on[/green]")
        else:
            console.print(f"[red]✗ Failed to power on VM {vm_name}[/red]")
        
        return success
    
    def power_off_vm(
        self,
        platform: str,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """Power off a VM."""
        console.print(f"[yellow]Powering off VM: {vm_name} (graceful={graceful})[/yellow]")
        
        if platform == "olvm":
            client = self.get_olvm_client()
            with client:
                success = client.power_off(vm_name, graceful=graceful, timeout=timeout)
        elif platform == "vsphere":
            client = self.get_vsphere_client()
            with client:
                success = client.power_off(vm_name, graceful=graceful, timeout=timeout)
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        if success:
            console.print(f"[green]✓ VM {vm_name} powered off[/green]")
        else:
            console.print(f"[red]✗ Failed to power off VM {vm_name}[/red]")
        
        return success
    
    def reboot_vm(
        self,
        platform: str,
        vm_name: str,
        graceful: bool = True,
        timeout: int = 300
    ) -> bool:
        """Reboot a VM."""
        console.print(f"[yellow]Rebooting VM: {vm_name} (graceful={graceful})[/yellow]")
        
        if platform == "olvm":
            client = self.get_olvm_client()
            with client:
                success = client.reboot(vm_name, graceful=graceful, timeout=timeout)
        elif platform == "vsphere":
            client = self.get_vsphere_client()
            with client:
                success = client.reboot(vm_name, graceful=graceful, timeout=timeout)
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        if success:
            console.print(f"[green]✓ VM {vm_name} rebooted[/green]")
        else:
            console.print(f"[red]✗ Failed to reboot VM {vm_name}[/red]")
        
        return success
