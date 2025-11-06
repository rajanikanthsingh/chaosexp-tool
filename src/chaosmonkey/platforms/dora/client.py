"""Dora API client for environment discovery."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests


# Environment configuration mapping
DORA_ENVIRONMENTS: Dict[str, Dict[str, str]] = {
    "Dev1": {
        "vcenter": "OracleQA",
        "patternPath": "ORA-DEV",
        "vmPath": "ORA-DEV",
        "hostfilter": "dev1",
    }
}


class DoraClient:
    """
    Client for Dora API to discover vSphere environments.
    
    Dora provides centralized vSphere inventory and management APIs.
    """
    
    def __init__(
        self,
        dora_host: str = "hostname",
        api_port: int = 8000,
        auth_port: int = 51051,
        timeout: int = 20
    ):
        """
        Initialize Dora client.
        
        Args:
            dora_host: Dora server hostname
            api_port: API service port (default: 8000)
            auth_port: Authentication service port (default: 51051)
            timeout: HTTP request timeout in seconds
        """
        self.dora_host = dora_host
        self.api_port = api_port
        self.auth_port = auth_port
        self.timeout = timeout
        self._token: Optional[str] = None
    
    def authenticate(self, username: str, password: str) -> str:
        """
        Authenticate with Dora and get token.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Authentication token
            
        Raises:
            RuntimeError: If authentication fails
        """
        enc_pass = quote(password, safe="")
        url = (
            f"http://{self.dora_host}:{self.auth_port}/v1/GetLoginToken/"
            f"{quote(username, safe='')}/{enc_pass}"
        )
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            token = data.get("token")
            
            if not token:
                raise RuntimeError("No 'token' in authentication response")
            
            self._token = token
            return token
        except requests.RequestException as e:
            raise RuntimeError(f"Dora authentication failed: {e}")
    
    def get_hypervisors(
        self,
        environment: str,
        username: str,
        password: str,
        hostfilter_mode: str = ".*"
    ) -> Dict[str, Any]:
        """
        Get hypervisors for an environment.
        
        Args:
            environment: Environment name (from DORA_ENVIRONMENTS)
            username: Dora username
            password: Dora password
            hostfilter_mode: How to apply host filter: pattern to perform regex search
            
        Returns:
            Hypervisors data from Dora API
            
        Raises:
            ValueError: If environment not found
            RuntimeError: If API call fails
        """
        if environment not in DORA_ENVIRONMENTS:
            raise ValueError(
                f"Unknown environment: {environment}. "
                f"Available: {', '.join(DORA_ENVIRONMENTS.keys())}"
            )
        
        # Authenticate if not already done
        if not self._token:
            self.authenticate(username, password)
        
        config = DORA_ENVIRONMENTS[environment]
        vcenter = config["vcenter"]
        pattern_path = config["patternPath"]
        hostfilter_value = config["hostfilter"]
        
        url = (
            f"http://{self.dora_host}:{self.api_port}/v1/GetHypervisors/"
            f"{self._token}/{vcenter}/{pattern_path}"
        )
        
        # Build query parameters based on hostfilter mode
        params = {"listing_only": "false"}
        params["host_filter"] = hostfilter_value
        # else: omit (don't include host_filter parameter)
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch hypervisors: {e}")
    
    def get_virtual_machines(
        self,
        environment: str,
        username: str,
        password: str,
        hostfilter_mode: str = ".*"
    ) -> Dict[str, Any]:
        """
        Get virtual machines for an environment.
        
        Args:
            environment: Environment name (from DORA_ENVIRONMENTS)
            username: Dora username
            password: Dora password
            hostfilter_mode: How to apply host filter: pattern to perform regex search
            
        Returns:
            Virtual machines data from Dora API
            
        Raises:
            ValueError: If environment not found
            RuntimeError: If API call fails
        """
        if environment not in DORA_ENVIRONMENTS:
            raise ValueError(
                f"Unknown environment: {environment}. "
                f"Available: {', '.join(DORA_ENVIRONMENTS.keys())}"
            )
        
        # Authenticate if not already done
        if not self._token:
            self.authenticate(username, password)
        
        config = DORA_ENVIRONMENTS[environment]
        vcenter = config["vcenter"]
        vm_path = config["vmPath"]
        hostfilter_value = config["hostfilter"]
        
        url = (
            f"http://{self.dora_host}:{self.api_port}/v1/GetVirtualMachines/"
            f"{self._token}/{vcenter}/{vm_path}"
        )
        
        # Build query parameters based on hostfilter mode
        params = {"listing_only": "false"}
        params["host_filter"] = hostfilter_value
        # else: omit (don't include host_filter parameter)
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch virtual machines: {e}")
    
    def get_environment_data(
        self,
        environment: str,
        username: str,
        password: str,
        hypervisors_hostfilter: str = ".*",
        vms_hostfilter: str = ".*"
    ) -> Dict[str, Any]:
        """
        Get complete environment data (hypervisors + VMs).
        
        Args:
            environment: Environment name
            username: Dora username
            password: Dora password
            hypervisors_hostfilter: Host filter mode for hypervisors
            vms_hostfilter: Host filter mode for VMs
            
        Returns:
            Dictionary with 'hypervisors' and 'vms' keys
        """
        hypervisors = self.get_hypervisors(
            environment, username, password, hypervisors_hostfilter
        )
        vms = self.get_virtual_machines(
            environment, username, password, vms_hostfilter
        )
        
        return {
            "environment": environment,
            "hypervisors": hypervisors,
            "vms": vms,
        }
    
    @staticmethod
    def list_environments() -> List[str]:
        """List all available Dora environments."""
        return list(DORA_ENVIRONMENTS.keys())
    
    @staticmethod
    def get_environment_config(environment: str) -> Dict[str, str]:
        """Get configuration for a specific environment."""
        if environment not in DORA_ENVIRONMENTS:
            raise ValueError(f"Unknown environment: {environment}")
        return DORA_ENVIRONMENTS[environment].copy()
