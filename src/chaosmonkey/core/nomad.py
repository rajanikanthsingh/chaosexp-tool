"""Nomad integration stubs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict, List
from urllib.parse import urlparse

try:
    import nomad
except ImportError:  # pragma: no cover - optional dependency not installed by default
    nomad = None  # type: ignore

from .models import Target


class NomadClient:
    """Thin wrapper around python-nomad with injectable stub fallback."""

    def __init__(self, address: str, region: str | None = None, token: str | None = None, namespace: str | None = None) -> None:
        self._address = address
        self._region = region
        self._token = token
        self._namespace = namespace
        self._client = self._initialize_client()

    def _initialize_client(self):  # type: ignore[override]
        if nomad is None:
            return None
        
        # Parse the address to extract host and port
        parsed = urlparse(self._address)
        host = parsed.hostname or parsed.path.split(':')[0] if ':' in parsed.path else parsed.path
        port = parsed.port or 4646
        
        return nomad.Nomad(host=host, port=port, region=self._region, token=self._token, namespace=self._namespace)

    def discover_services(self) -> List[Dict[str, str]]:
        if self._should_use_stub():
            # Stub data for local development without Nomad
            return [
                {"Name": "web", "ID": "web-123", "Type": "service"},
                {"Name": "api", "ID": "api-456", "Type": "service"},
            ]

        try:
            # Use jobs API instead of services (which may not be available in all versions)
            jobs = self._client.jobs.get_jobs()
            return [
                {
                    "Name": job.get("Name", job.get("ID")),
                    "ID": job.get("ID"),
                    "Type": job.get("Type", "service"),
                }
                for job in jobs
            ]
        except Exception as e:
            print(f"Warning: Failed to discover services from Nomad: {e}")
            return [
                {"Name": "web", "ID": "web-123", "Type": "service"},
                {"Name": "api", "ID": "api-456", "Type": "service"},
            ]

    def list_allocations(self) -> List[Dict[str, str]]:
        if self._should_use_stub():
            return [
                {
                    "ID": "alloc-1",
                    "Name": "web",
                    "NodeID": "node-1",
                    "ClientStatus": "running",
                    "CreateTime": datetime.now(UTC).isoformat(),
                }
            ]

        try:
            allocs = self._client.allocations.get_allocations()
            return [
                {
                    "ID": alloc.get("ID"),
                    "Name": alloc.get("Name", alloc.get("JobID")),
                    "JobID": alloc.get("JobID"),  # Include JobID for matching
                    "NodeID": alloc.get("NodeID", "unknown"),
                    "ClientStatus": alloc.get("ClientStatus", "unknown"),
                    "CreateTime": str(alloc.get("CreateTime", datetime.now(UTC).isoformat())),
                }
                for alloc in allocs
            ]
        except Exception as e:
            print(f"Warning: Failed to list allocations from Nomad: {e}")
            return [
                {
                    "ID": "alloc-1",
                    "Name": "web",
                    "NodeID": "node-1",
                    "ClientStatus": "running",
                    "CreateTime": datetime.now(UTC).isoformat(),
                }
            ]

    def _should_use_stub(self) -> bool:
        if self._client is None:
            return True

        # Check if the client has the necessary attributes (jobs or agent)
        return not hasattr(self._client, "jobs") and not hasattr(self._client, "agent")

    def enumerate_targets(self) -> List[Target]:
        services = self.discover_services()
        allocations = self.list_allocations()
        
        # Create allocation index by JobID (not by allocation Name)
        # Multiple allocations can have the same JobID, so we take the first running one
        allocation_index = {}
        for alloc in allocations:
            job_id = alloc.get("JobID")
            if job_id and job_id not in allocation_index:
                # Prefer running allocations
                if alloc.get("ClientStatus", "").lower() == "running":
                    allocation_index[job_id] = alloc
                elif job_id not in allocation_index:
                    allocation_index[job_id] = alloc

        targets: List[Target] = []
        
        # Add service targets
        for service in services:
            # Match service (which is a job) to allocation by job ID
            service_job_id = service.get("ID") or service["Name"]
            alloc = allocation_index.get(service_job_id, {})
            
            # Enhanced service info extraction for k6 URL building
            service_info = self._extract_service_info(service, alloc)
            
            targets.append(
                Target(
                    identifier=service.get("ID", service["Name"]),
                    kind=service.get("Type", "service"),
                    attributes={
                        "name": service["Name"],
                        "node": alloc.get("NodeID", "unknown"),
                        "status": alloc.get("ClientStatus", "unknown"),
                        # Enhanced k6-specific attributes
                        "service_name": service_info.get("service_name"),
                        "address": service_info.get("address"),
                        "port": service_info.get("port", 8080),
                        "health_endpoint": service_info.get("health_endpoint", "/health"),
                    },
                )
            )
        
        # Add node targets
        nodes = self.list_nodes()
        for node in nodes:
            targets.append(
                Target(
                    identifier=node.get("ID"),
                    kind="node",
                    attributes={
                        "name": node.get("Name", "unknown"),
                        "status": node.get("Status", "unknown"),
                        "drain": node.get("Drain", False),
                        "scheduling_eligibility": node.get("SchedulingEligibility", "eligible"),
                    },
                )
            )
        
        return targets

    def _extract_service_info(self, service: Dict[str, str], alloc: Dict[str, str]) -> Dict[str, str]:
        """Extract service information for k6 URL building from Nomad job/service data."""
        service_name = service["Name"]
        
        # Try to get detailed job information for service discovery
        service_info = {
            "service_name": service_name,
            "address": "",
            "port": 8080,  # Default port
            "health_endpoint": "/health",
        }
        
        if not self._should_use_stub() and self._client:
            try:
                # Get job details to extract service configuration
                job_id = service.get("ID", service_name)
                job_details = self._client.job.get_job(job_id)
                
                # Extract service port from job specification
                task_groups = job_details.get("TaskGroups", []) or []
                for task_group in task_groups or []:
                    # Look for network configuration
                    networks = task_group.get("Networks", []) or []
                    for network in networks or []:
                        # Check for port mappings
                        reserved_ports = network.get("ReservedPorts", []) or []
                        dynamic_ports = network.get("DynamicPorts", []) or []
                        
                        # Use first port found (common pattern)
                        if reserved_ports:
                            service_info["port"] = reserved_ports[0].get("Value", 8080)
                        elif dynamic_ports:
                            service_info["port"] = dynamic_ports[0].get("Value", 8080)
                    
                    # Look for service definitions
                    services = task_group.get("Services", []) or []
                    for svc in services or []:
                        service_info["service_name"] = svc.get("Name", service_name)
                        service_info["port"] = svc.get("Port", service_info["port"])
                        
                        # Extract health check endpoint
                        checks = svc.get("Checks", []) or []
                        for check in checks or []:
                            if check.get("Type") == "http":
                                path = check.get("Path", "/health")
                                service_info["health_endpoint"] = path
                
                # Apply service-specific health endpoint overrides
                if service_name.lower() == "cadvisor":
                    service_info["health_endpoint"] = "/healthz"
                elif service_info["health_endpoint"] == "/health":
                    # Default most services to /monitoring/health unless specifically configured
                    service_info["health_endpoint"] = "/monitoring/health"
                
                # If we have node info, try to get node address
                node_id = alloc.get("NodeID")
                if node_id:
                    try:
                        node_details = self._client.node.get_node(node_id)
                        
                        # Try multiple fields to get the actual node IP address
                        # Priority: Address > HTTPAddr > Name
                        node_address = (
                            node_details.get("Address") or 
                            node_details.get("HTTPAddr", "").split(":")[0] if ":" in node_details.get("HTTPAddr", "") else node_details.get("HTTPAddr", "") or
                            node_details.get("Name", "")
                        )
                        
                        if node_address and node_address != "unknown":
                            service_info["address"] = node_address
                            # Also store node name for debugging
                            service_info["node_name"] = node_details.get("Name", "unknown")
                    except Exception:
                        pass  # Use fallback
                        
            except Exception as e:
                print(f"Warning: Could not extract detailed service info for {service_name}: {e}")
        
        return service_info

    def list_nodes(self) -> List[Dict[str, str]]:
        """List all Nomad client nodes."""
        if self._should_use_stub():
            return [
                {
                    "ID": "node-1a2b3c4d",
                    "Name": "client-01",
                    "Status": "ready",
                    "Drain": False,
                    "SchedulingEligibility": "eligible",
                },
                {
                    "ID": "node-5e6f7g8h",
                    "Name": "client-02", 
                    "Status": "ready",
                    "Drain": False,
                    "SchedulingEligibility": "eligible",
                }
            ]

        try:
            nodes = self._client.nodes.get_nodes()
            result = []
            for node in nodes:
                # Get detailed node info
                node_details = self._client.node.get_node(node["ID"])
                result.append({
                    "ID": node.get("ID"),
                    "Name": node.get("Name", "unknown"),
                    "Status": node.get("Status", "unknown"),
                    "Drain": node_details.get("Drain", False),
                    "SchedulingEligibility": node_details.get("SchedulingEligibility", "eligible"),
                })
            return result
        except Exception as e:
            print(f"Warning: Failed to list nodes from Nomad: {e}")
            return [
                {
                    "ID": "node-1a2b3c4d",
                    "Name": "client-01",
                    "Status": "ready",
                    "Drain": False,
                    "SchedulingEligibility": "eligible",
                }
            ]

    def drain_node(self, node_id: str, deadline_seconds: int = 300) -> bool:
        """Drain a node (make it ineligible and move allocations)."""
        if self._should_use_stub():
            print(f"STUB: Would drain node {node_id} with deadline {deadline_seconds}s")
            return True

        try:
            import requests
            
            drain_url = f"{self._address.rstrip('/')}/v1/node/{node_id}/drain"
            payload = {
                "DrainSpec": {
                    "Deadline": deadline_seconds * 1000000000,  # Convert to nanoseconds
                    "IgnoreSystemJobs": False
                },
                "MarkEligible": False
            }
            
            headers = {}
            if self._token:
                headers["X-Nomad-Token"] = self._token
            
            response = requests.post(drain_url, json=payload, headers=headers)
            return response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error draining node {node_id}: {e}")
            return False

    def list_drained_nodes(self) -> List[Dict[str, str]]:
        """List nodes that are currently drained."""
        nodes = self.list_nodes()
        return [
            node for node in nodes
            if node.get("Drain") == "true" or node.get("SchedulingEligibility") == "ineligible"
        ]

    def recover_node(self, node_id: str) -> bool:
        """Recover a drained node (disable drain and make eligible).""" 
        if self._should_use_stub():
            print(f"STUB: Would recover node {node_id}")
            return True

        try:
            import requests
            
            # Step 1: Disable drain
            drain_url = f"{self._address.rstrip('/')}/v1/node/{node_id}/drain"
            drain_payload = {
                "DrainSpec": None,
                "MarkEligible": False
            }
            
            headers = {}
            if self._token:
                headers["X-Nomad-Token"] = self._token
            
            drain_response = requests.post(drain_url, json=drain_payload, headers=headers)
            if drain_response.status_code not in [200, 204]:
                return False
            
            # Step 2: Set eligible
            eligibility_url = f"{self._address.rstrip('/')}/v1/node/{node_id}/eligibility"
            eligibility_payload = {"Eligibility": "eligible"}
            
            eligibility_response = requests.post(eligibility_url, json=eligibility_payload, headers=headers)
            return eligibility_response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error recovering node {node_id}: {e}")
            return False
