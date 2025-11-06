"""Chaos Toolkit actions for Nomad service disruption."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict
from datetime import datetime

from rich.console import Console

try:
    import nomad
except ImportError:
    nomad = None

console = Console()


def _get_nomad_client():
    """Get a Nomad client from environment configuration."""
    if nomad is None:
        raise RuntimeError("python-nomad is required but not installed")
    
    from urllib.parse import urlparse
    
    address = os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646")
    parsed = urlparse(address)
    host = parsed.hostname or parsed.path.split(':')[0] if ':' in parsed.path else parsed.path
    port = parsed.port or 4646
    
    return nomad.Nomad(
        host=host,
        port=port,
        token=os.getenv("NOMAD_TOKEN"),
        namespace=os.getenv("NOMAD_NAMESPACE", "default")
    )


def drain_service_allocation(service_id: str, node_id: str | None = None, duration: str | int = 300, **_: Any) -> Dict[str, Any]:
    """
    Drain a Nomad node, causing all allocations (including the target service) to be rescheduled.
    
    This simulates a node going down by:
    1. Discovering which node the service is running on
    2. Enabling drain mode on that node
    3. Waiting for allocations to migrate
    4. Optionally re-enabling the node after duration
    
    This is one of the most disruptive chaos types as it affects ALL services on the node.
    """
    duration_int = int(duration) if isinstance(duration, str) else duration
    
    try:
        client = _get_nomad_client()
        
        # Smart discovery of service location
        node_info = _get_service_node_info(client, service_id)
        
        if not node_info.get("found"):
            return {
                "status": "failed",
                "service_id": service_id,
                "error": "Service not found or not running on any node"
            }
        
        target_node_id = node_info["node_id"]
        target_node_name = node_info["node_name"]
        datacenter = node_info.get("datacenter", "unknown")
        alloc_count = node_info.get("allocations_count", 0)
        
        console.log(f"[discovery] Target node: {target_node_name}")
        console.log(f"[discovery] Node ID: {target_node_id}")
        console.log(f"[discovery] Allocations on node: {alloc_count}")
        console.log(f"[warning] ⚠️  This will affect ALL {alloc_count} allocation(s) on this node!")
        
        # Get current node status before draining
        node_detail = client.node.get_node(target_node_id)
        current_drain = node_detail.get("Drain", False)
        current_status = node_detail.get("Status", "unknown")
        
        if current_drain:
            console.log(f"[warning] Node is already draining!")
            return {
                "status": "failed",
                "service_id": service_id,
                "node_id": target_node_id,
                "node_name": target_node_name,
                "error": "Node is already in drain mode"
            }
        
        console.log(f"[strategy] Current node status: {current_status}")
        console.log(f"[strategy] Action: Enable node drain for {duration_int} seconds")
        console.log(f"[impact] Expected impact: ALL services will be rescheduled to other nodes")
        
        # Enable drain mode on the node
        # This will:
        # 1. Mark the node as ineligible for new allocations
        # 2. Begin migrating existing allocations to other nodes
        # 3. Wait for allocations to gracefully stop
        console.log(f"[action] Enabling drain mode on {target_node_name}...")
        
        try:
            # Use direct HTTP request since python-nomad library has issues with drain API
            import requests
            from urllib.parse import urlparse
            
            # Get Nomad address
            addr = os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646")
            token = os.getenv("NOMAD_TOKEN")
            
            # Prepare drain request
            drain_url = f"{addr}/v1/node/{target_node_id}/drain"
            headers = {"Content-Type": "application/json"}
            if token:
                headers["X-Nomad-Token"] = token
            
            # Drain spec - simpler version that works with Nomad API
            drain_payload = {
                "DrainSpec": {
                    "Deadline": duration_int * 1000000000,  # Nanoseconds
                    "IgnoreSystemJobs": False
                },
                "MarkEligible": False
            }
            
            console.log(f"[debug] Sending drain request to: {drain_url}")
            response = requests.post(drain_url, json=drain_payload, headers=headers)
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Drain API returned {response.status_code}: {response.text}")
            
            console.log(f"[success] ✓ Node drain enabled successfully!")
            console.log(f"[impact] Allocations will begin migrating immediately")
            console.log(f"[impact] Service {service_id} will be rescheduled to another node")
            
            # Wait a moment to check drain status
            time.sleep(3)
            
            # Verify drain is active
            updated_node = client.node.get_node(target_node_id)
            drain_status = updated_node.get("Drain", False)
            scheduling_eligibility = updated_node.get("SchedulingEligibility", "unknown")
            
            console.log(f"[verify] Drain active: {drain_status}")
            console.log(f"[verify] Scheduling eligibility: {scheduling_eligibility}")
            
            # Note: In a real scenario, you might want to schedule a job to re-enable the node
            # after the duration expires. For now, we document that manual intervention is needed.
            console.log(f"[warning] ⚠️  Manual intervention required!")
            console.log(f"[warning] To re-enable the node after testing, run:")
            console.log(f"[warning]   nomad node eligibility -enable {target_node_id}")
            console.log(f"[warning] Or use: curl -X POST http://nomad:4646/v1/node/{target_node_id}/eligibility " + '\'{"Eligibility":"eligible"}\'')
            
            return {
                "status": "drained",
                "service_id": service_id,
                "node_id": target_node_id,
                "node_name": target_node_name,
                "datacenter": datacenter,
                "drain_deadline_seconds": duration_int,
                "affected_allocations": alloc_count,
                "scheduling_eligibility": scheduling_eligibility,
                "message": f"Node {target_node_name} is draining. {alloc_count} allocation(s) will migrate.",
                "recovery_command": f"nomad node eligibility -enable {target_node_id}"
            }
            
        except Exception as drain_error:
            console.log(f"[error] Failed to drain node: {drain_error}")
            import traceback
            console.log(traceback.format_exc())
            return {
                "status": "failed",
                "service_id": service_id,
                "node_id": target_node_id,
                "error": f"Failed to enable drain: {str(drain_error)}"
            }
        
    except Exception as e:
        console.log(f"[error] Failed to drain service allocation: {e}")
        import traceback
        console.log(traceback.format_exc())
        return {
            "status": "failed",
            "service_id": service_id,
            "error": str(e)
        }


def inject_latency(service_id: str, latency_ms: str | int = 250, duration: str | int = 60, **_: Any) -> Dict[str, Any]:
    """
    Inject network latency by deploying a tc (traffic control) job to the target node.
    
    This function:
    1. Discovers which node the target service is running on
    2. Deploys a privileged container with network capabilities
    3. Uses tc (traffic control) to add latency to the network interface
    4. Automatically removes the latency after duration expires
    """
    latency_ms_int = int(latency_ms) if isinstance(latency_ms, str) else latency_ms
    duration_int = int(duration) if isinstance(duration, str) else duration
    
    try:
        client = _get_nomad_client()
        
        # Smart discovery of service location
        node_info = _get_service_node_info(client, service_id)
        
        if not node_info.get("found"):
            return {
                "status": "failed",
                "service_id": service_id,
                "error": "Service not found or not running on any node"
            }
        
        node_id = node_info["node_id"]
        node_name = node_info["node_name"]
        datacenter = node_info.get("datacenter", "dc1")
        
        # Generate a unique job ID for the chaos latency job
        chaos_job_id = f"chaos-lat-{service_id}-{int(time.time())}"[:63]
        
        console.log(f"[strategy] Injecting {latency_ms_int}ms network latency")
        console.log(f"[strategy] Duration: {duration_int}s on {node_name}")
        console.log(f"[strategy] Using Pumba for Docker network chaos")
        
        # Using Pumba (https://github.com/alexei-led/pumba)
        # Pumba is a chaos testing tool that can inject network failures into Docker containers
        # It needs access to the Docker socket but doesn't require NET_ADMIN on the container itself
        
        # Get all containers on the node and find the target service container
        # We'll use a pattern to match the service name
        service_pattern = service_id.replace("-job", "")  # Remove -job suffix
        
        console.log(f"[strategy] Target pattern: {service_pattern}")
        
        # Create a Nomad job specification for network latency using Pumba
        # Pumba command structure: pumba netem <flags> delay <delay-flags> <container-pattern>
        latency_job = {
            "Job": {
                "ID": chaos_job_id,
                "Name": chaos_job_id,
                "Type": "batch",
                "Datacenters": [datacenter],
                "Constraints": [{
                    "LTarget": "${node.unique.id}",
                    "RTarget": node_id,
                    "Operand": "="
                }],
                "TaskGroups": [{
                    "Name": "latency",
                    "Count": 1,
                    "RestartPolicy": {
                        "Attempts": 0,
                        "Mode": "fail"
                    },
                    "Tasks": [{
                        "Name": "network-latency",
                        "Driver": "docker",
                        "Config": {
                            "image": "gaiaadm/pumba:latest",
                            "args": [
                                "netem",
                                "--duration", f"{duration_int}s",
                                "--interface", "eth0",
                                "delay",
                                "--time", str(latency_ms_int),
                                f"re2:{service_pattern}"
                            ],
                            "volumes": [
                                "/var/run/docker.sock:/var/run/docker.sock"
                            ]
                        },
                        "Resources": {
                            "CPU": 200,
                            "MemoryMB": 256
                        },
                        "LogConfig": {
                            "MaxFiles": 1,
                            "MaxFileSizeMB": 10
                        }
                    }]
                }]
            }
        }
        
        # Submit the chaos job to Nomad
        console.log(f"[deploy] Submitting chaos job: {chaos_job_id}")
        console.log(f"[deploy] Target: {service_id} on {node_name}")
        console.log(f"[deploy] Network latency: {latency_ms_int}ms for {duration_int}s")
        console.log(f"[impact] Expected impact: Slow network responses, increased timeouts")
        
        response = client.jobs.register_job(latency_job)
        eval_id = response.get("EvalID", "unknown")
        
        console.log(f"[success] ✓ Chaos job deployed successfully!")
        console.log(f"[verify] Evaluation ID: {eval_id}")
        
        # Wait a moment for the job to start
        time.sleep(2)
        
        # Check job status
        try:
            job_status = client.job.get_job(chaos_job_id)
            status = job_status.get("Status", "unknown")
            console.log(f"[verify] Job status: {status}")
            
            # Get allocations to show where it's running
            job_allocations = client.job.get_allocations(chaos_job_id)
            running_allocs = [a for a in job_allocations if a.get("ClientStatus") == "running"]
            
            if running_allocs:
                console.log(f"[impact] Network latency active on {len(running_allocs)} node(s)")
                console.log(f"[impact] All network traffic from {node_name} will experience {latency_ms_int}ms delay")
            else:
                console.log(f"[warning] Job submitted but not yet running (may take a few seconds)")
                
        except Exception as e:
            console.log(f"[warning] Could not verify job status: {e}")
        
        return {
            "status": "deployed",
            "service_id": service_id,
            "chaos_job_id": chaos_job_id,
            "node_name": node_name,
            "node_id": node_id,
            "datacenter": datacenter,
            "latency_ms": latency_ms_int,
            "duration_seconds": duration_int,
            "eval_id": eval_id,
            "message": f"Network latency of {latency_ms_int}ms injected for {duration_int}s"
        }
        
    except Exception as e:
        console.log(f"[error] Failed to inject latency: {e}")
        import traceback
        console.log(traceback.format_exc())
        return {
            "status": "failed",
            "service_id": service_id,
            "error": str(e)
        }


def inject_packet_loss(service_id: str, packet_loss: str | float = "15%", **_: Any) -> Dict[str, Any]:
    console.log(f"[stub] Would inject {packet_loss} packet loss for {service_id}")
    return {"status": "noop", "service_id": service_id, "packet_loss": packet_loss}


def _get_service_node_info(client, service_id: str) -> Dict[str, Any]:
    """
    Intelligently gather information about where a service is running OR get node info directly.
    
    Handles two cases:
    1. service_id is a job/service ID: finds which node it's running on
    2. service_id is a node ID (UUID format): uses it directly
    
    Returns:
        Dict with node_id, node_name, datacenter, and all allocations for the service
    """
    console.log(f"[discovery] Searching for target: {service_id}")
    
    # Check if service_id looks like a node UUID (contains dashes)
    # Node UUIDs look like: 13b3c90c-bf1c-399c-0a48-f15c36537312
    if "-" in service_id and len(service_id) == 36:
        console.log(f"[discovery] Detected node ID format, using directly")
        try:
            node_info = client.node.get_node(service_id)
            node_name = node_info.get("Name", "unknown")
            datacenter = node_info.get("Datacenter", "dc1")
            node_class = node_info.get("NodeClass", "unknown")
            
            # Get node resources
            resources = node_info.get("Resources", {})
            cpu_mhz = resources.get("CPU", "unknown")
            memory_mb = resources.get("MemoryMB", "unknown")
            
            # Count allocations on this node
            alloc_count = 0
            try:
                node_allocations = client.node.get_allocations(service_id)
                alloc_count = len([a for a in node_allocations if a.get("ClientStatus") == "running"])
            except:
                pass
            
            console.log(f"[discovery] Node: {node_name}")
            console.log(f"[discovery] Datacenter: {datacenter}, Class: {node_class}")
            console.log(f"[discovery] Node resources: CPU={cpu_mhz} MHz, Memory={memory_mb} MB")
            console.log(f"[discovery] Running allocations on node: {alloc_count}")
            
            return {
                "found": True,
                "node_id": service_id,
                "node_name": node_name,
                "datacenter": datacenter,
                "node_class": node_class,
                "allocations_count": alloc_count,
                "resources": {
                    "cpu_mhz": cpu_mhz,
                    "memory_mb": memory_mb
                }
            }
        except Exception as e:
            console.log(f"[error] Could not get node info: {e}")
            return {"found": False, "error": str(e)}
    
    # Otherwise, treat as service/job ID
    console.log(f"[discovery] Treating as service/job ID")
    
    # Get all allocations
    allocations = client.allocations.get_allocations()
    
    # Find all allocations for this service
    service_allocations = []
    for alloc in allocations:
        job_id = alloc.get("JobID", "")
        if job_id == service_id:
            # Only consider running allocations
            status = alloc.get("ClientStatus", "")
            if status == "running":
                service_allocations.append(alloc)
    
    if not service_allocations:
        console.log(f"[warning] No running allocations found for service: {service_id}")
        return {"found": False}
    
    # Pick the first running allocation (could enhance to pick randomly or by load)
    target_alloc = service_allocations[0]
    node_id = target_alloc.get("NodeID")
    node_name = target_alloc.get("NodeName", "unknown")
    
    console.log(f"[discovery] Found {len(service_allocations)} running allocation(s)")
    console.log(f"[discovery] Target node: {node_name} (ID: {node_id})")
    
    # Get node details to find datacenter
    try:
        node_info = client.node.get_node(node_id)
        datacenter = node_info.get("Datacenter", "dc1")
        node_class = node_info.get("NodeClass", "unknown")
        
        # Get node resources
        resources = node_info.get("Resources", {})
        cpu_mhz = resources.get("CPU", "unknown")
        memory_mb = resources.get("MemoryMB", "unknown")
        
        console.log(f"[discovery] Datacenter: {datacenter}, Class: {node_class}")
        console.log(f"[discovery] Node resources: CPU={cpu_mhz} MHz, Memory={memory_mb} MB")
        
        return {
            "found": True,
            "node_id": node_id,
            "node_name": node_name,
            "datacenter": datacenter,
            "node_class": node_class,
            "allocations_count": len(service_allocations),
            "resources": {
                "cpu_mhz": cpu_mhz,
                "memory_mb": memory_mb
            }
        }
    except Exception as e:
        console.log(f"[warning] Could not get node details: {e}")
        # Return basic info even if node details fail
        return {
            "found": True,
            "node_id": node_id,
            "node_name": node_name,
            "datacenter": "dc1",  # fallback
            "allocations_count": len(service_allocations)
        }


def run_cpu_stress(service_id: str, duration: str | int = 60, **_: Any) -> Dict[str, Any]:
    """
    Intelligently deploy a CPU stress job to the Nomad cluster.
    
    This function:
    1. Discovers which node(s) the target service is running on
    2. Gathers datacenter and resource information
    3. Deploys a stress-ng container to the same node
    4. Constrains the job to run alongside the target service
    """
    duration_int = int(duration)
    
    try:
        client = _get_nomad_client()
        
        # Smart discovery of service location
        node_info = _get_service_node_info(client, service_id)
        
        if not node_info.get("found"):
            return {
                "status": "failed",
                "service_id": service_id,
                "error": "Service not found or not running on any node"
            }
        
        node_id = node_info["node_id"]
        node_name = node_info["node_name"]
        datacenter = node_info.get("datacenter", "dc1")
        
        # Generate a unique job ID for the chaos stress job
        chaos_job_id = f"chaos-cpu-{service_id}-{int(time.time())}"[:63]  # Nomad has ID length limits
        
        # Determine CPU workers based on node resources
        node_resources = node_info.get("resources", {})
        node_cpu = node_resources.get("cpu_mhz", 0)
        
        # Use 8 CPU workers by default (aggressive stress)
        # This creates enough load to significantly impact co-located services
        cpu_workers = 8
        cpu_request = 4000  # Request 4 GHz worth of CPU
        
        console.log(f"[strategy] Using {cpu_workers} CPU workers to maximize stress impact")
        
        # Create a Nomad job specification for CPU stress
        # Using stress-ng which is a popular tool for stress testing
        stress_job = {
            "Job": {
                "ID": chaos_job_id,
                "Name": chaos_job_id,
                "Type": "batch",
                "Datacenters": [datacenter],
                "TaskGroups": [{
                    "Name": "stress",
                    "Count": 1,
                    "Tasks": [{
                        "Name": "cpu-stress",
                        "Driver": "docker",
                        "Config": {
                            "image": "polinux/stress",
                            "command": "stress",
                            "args": [
                                "--cpu", str(cpu_workers),  # Number of CPU workers
                                "--timeout", f"{duration_int}s",
                                "--verbose"
                            ]
                        },
                        "Resources": {
                            "CPU": cpu_request,  # Request significant CPU
                            "MemoryMB": 512
                        },
                        "LogConfig": {
                            "MaxFiles": 1,
                            "MaxFileSizeMB": 10
                        }
                    }],
                    "RestartPolicy": {
                        "Attempts": 0,
                        "Mode": "fail"
                    }
                }],
                # Constraint to run on the same node as the target service
                "Constraints": [{
                    "LTarget": "${node.unique.id}",
                    "RTarget": node_id,
                    "Operand": "="
                }]
            }
        }
        
        console.log(f"[deploy] Submitting chaos job: {chaos_job_id}")
        console.log(f"[deploy] Target: {service_id} on {node_name}")
        console.log(f"[deploy] Datacenter: {datacenter}, Duration: {duration_int}s")
        console.log(f"[deploy] CPU Workers: {cpu_workers}, CPU Request: {cpu_request} MHz")
        console.log(f"[deploy] Will stress CPU on node {node_id[:12]}...")
        console.log(f"[impact] Expected impact: High CPU contention, increased latency for {service_id}")
        
        # Submit the job to Nomad
        response = client.jobs.register_job(stress_job)
        eval_id = response.get("EvalID", "unknown")
        
        console.log(f"[success] ✓ Chaos job deployed successfully!")
        console.log(f"[success] ✓ Evaluation ID: {eval_id}")
        console.log(f"[success] ✓ Job will stress CPU for {duration_int}s and auto-terminate")
        
        # Wait a moment to let Nomad schedule the job
        time.sleep(3)
        
        # Try to verify the job started
        try:
            job_status = client.job.get_job(chaos_job_id)
            status = job_status.get("Status", "unknown")
            console.log(f"[verify] Job status: {status}")
            
            # Show co-located allocations to demonstrate impact
            if status == "running":
                try:
                    allocs = client.allocations.get_allocations()
                    node_allocs = [a for a in allocs if a.get("NodeID") == node_id and a.get("ClientStatus") == "running"]
                    console.log(f"[impact] Total running allocations on target node: {len(node_allocs)}")
                    console.log(f"[impact] All services on this node will compete for CPU resources")
                except Exception:
                    pass
        except Exception as e:
            console.log(f"[warning] Could not verify job status: {e}")
        
        return {
            "status": "success",
            "service_id": service_id,
            "chaos_job_id": chaos_job_id,
            "target_node": node_id,
            "target_node_name": node_name,
            "datacenter": datacenter,
            "duration": duration_int,
            "cpu_workers": cpu_workers,
            "cpu_request_mhz": cpu_request,
            "eval_id": eval_id,
            "allocations_affected": node_info.get("allocations_count", 1),
            "impact": "High CPU contention on node - services will experience degraded performance",
            "message": f"CPU stress ({cpu_workers} workers) deployed to {node_name} - will cause resource contention for {duration_int}s"
        }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to deploy CPU stress: {e}")
        import traceback
        console.log(f"[error] Traceback: {traceback.format_exc()}")
        return {
            "status": "failed",
            "service_id": service_id,
            "error": str(e)
        }


def run_memory_stress(service_id: str, duration: str | int = 60, memory_mb: str | int = 2048, **_: Any) -> Dict[str, Any]:
    """
    Intelligently deploy a memory stress job to the Nomad cluster.
    
    This function:
    1. Discovers which node(s) the target service is running on
    2. Deploys a stress container that allocates and holds memory
    3. Creates memory pressure on the node
    4. Tests service behavior under memory contention
    """
    duration_int = int(duration)
    memory_mb_int = int(memory_mb)
    
    try:
        client = _get_nomad_client()
        
        # Smart discovery of service location
        node_info = _get_service_node_info(client, service_id)
        
        if not node_info.get("found"):
            return {
                "status": "failed",
                "service_id": service_id,
                "error": "Service not found or not running on any node"
            }
        
        node_id = node_info["node_id"]
        node_name = node_info["node_name"]
        datacenter = node_info.get("datacenter", "dc1")
        
        # Generate a unique job ID
        chaos_job_id = f"chaos-mem-{service_id}-{int(time.time())}"[:63]
        
        # Determine memory workers - use 2 workers by default
        memory_workers = 2
        memory_per_worker = memory_mb_int // memory_workers
        
        console.log(f"[strategy] Using {memory_workers} memory workers, {memory_per_worker}MB each")
        console.log(f"[strategy] Total memory allocation: {memory_mb_int}MB")
        
        # Create Nomad job specification for memory stress
        stress_job = {
            "Job": {
                "ID": chaos_job_id,
                "Name": chaos_job_id,
                "Type": "batch",
                "Datacenters": [datacenter],
                "TaskGroups": [{
                    "Name": "stress",
                    "Count": 1,
                    "Tasks": [{
                        "Name": "memory-stress",
                        "Driver": "docker",
                        "Config": {
                            "image": "polinux/stress",
                            "command": "stress",
                            "args": [
                                "--vm", str(memory_workers),  # Number of memory workers
                                "--vm-bytes", f"{memory_per_worker}M",  # Memory per worker
                                "--timeout", f"{duration_int}s",
                                "--verbose"
                            ]
                        },
                        "Resources": {
                            "CPU": 500,  # Minimal CPU for memory operations
                            "MemoryMB": memory_mb_int + 256  # Request memory + overhead
                        },
                        "LogConfig": {
                            "MaxFiles": 1,
                            "MaxFileSizeMB": 10
                        }
                    }],
                    "RestartPolicy": {
                        "Attempts": 0,
                        "Mode": "fail"
                    }
                }],
                # Constraint to run on the same node as the target service
                "Constraints": [{
                    "LTarget": "${node.unique.id}",
                    "RTarget": node_id,
                    "Operand": "="
                }]
            }
        }
        
        console.log(f"[deploy] Submitting chaos job: {chaos_job_id}")
        console.log(f"[deploy] Target: {service_id} on {node_name}")
        console.log(f"[deploy] Datacenter: {datacenter}, Duration: {duration_int}s")
        console.log(f"[deploy] Memory to allocate: {memory_mb_int}MB ({memory_workers} workers)")
        console.log(f"[deploy] Will create memory pressure on node {node_id[:12]}...")
        console.log(f"[impact] Expected impact: Memory contention, potential OOM, swap usage for {service_id}")
        
        # Submit the job to Nomad
        response = client.jobs.register_job(stress_job)
        eval_id = response.get("EvalID", "unknown")
        
        console.log(f"[success] ✓ Chaos job deployed successfully!")
        console.log(f"[success] ✓ Evaluation ID: {eval_id}")
        console.log(f"[success] ✓ Job will consume {memory_mb_int}MB for {duration_int}s and auto-terminate")
        
        # Wait a moment to let Nomad schedule the job
        time.sleep(3)
        
        # Try to verify the job started
        try:
            job_status = client.job.get_job(chaos_job_id)
            status = job_status.get("Status", "unknown")
            console.log(f"[verify] Job status: {status}")
            
            # Show co-located allocations
            if status == "running":
                try:
                    allocs = client.allocations.get_allocations()
                    node_allocs = [a for a in allocs if a.get("NodeID") == node_id and a.get("ClientStatus") == "running"]
                    console.log(f"[impact] Total running allocations on target node: {len(node_allocs)}")
                    console.log(f"[impact] All services on this node will compete for {memory_mb_int}MB memory")
                except Exception:
                    pass
        except Exception as e:
            console.log(f"[warning] Could not verify job status: {e}")
        
        return {
            "status": "success",
            "service_id": service_id,
            "chaos_job_id": chaos_job_id,
            "target_node": node_id,
            "target_node_name": node_name,
            "datacenter": datacenter,
            "duration": duration_int,
            "memory_mb": memory_mb_int,
            "memory_workers": memory_workers,
            "eval_id": eval_id,
            "allocations_affected": node_info.get("allocations_count", 1),
            "impact": "High memory pressure on node - services may experience OOM or swap thrashing",
            "message": f"Memory stress ({memory_mb_int}MB) deployed to {node_name} - will cause memory contention for {duration_int}s"
        }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to deploy memory stress: {e}")
        import traceback
        console.log(f"[error] Traceback: {traceback.format_exc()}")
        return {
            "status": "failed",
            "service_id": service_id,
            "error": str(e)
        }


def run_disk_io_stress(
    service_id: str,
    duration: str | int = 60,
    io_workers: str | int = 4,
    write_size_mb: str | int = 1024,
    **_: Any
) -> Dict[str, Any]:
    """
    Deploy a disk I/O stress job to the Nomad cluster to create disk pressure.
    
    This function:
    1. Discovers which node the target service is running on
    2. Deploys stress containers that perform intensive disk I/O operations
    3. Creates read/write load to simulate disk pressure
    4. Automatically terminates after the specified duration
    
    Args:
        service_id: The Nomad job ID to target
        duration: How long to run the stress test (seconds)
        io_workers: Number of I/O worker threads
        write_size_mb: Amount of data to write per worker (MB)
    
    Returns:
        Dictionary with deployment status and details
    """
    duration_int = int(duration) if isinstance(duration, str) else duration
    io_workers_int = int(io_workers) if isinstance(io_workers, str) else io_workers
    write_size_mb_int = int(write_size_mb) if isinstance(write_size_mb, str) else write_size_mb
    
    console.log(f"[chaos] Starting disk I/O stress chaos experiment")
    console.log(f"[config] Target service: {service_id}")
    console.log(f"[config] Duration: {duration_int}s, Workers: {io_workers_int}, Write size: {write_size_mb_int}MB per worker")
    
    try:
        client = _get_nomad_client()
        
        # Discover service location
        node_info = _get_service_node_info(client, service_id)
        
        if not node_info.get("found"):
            console.log(f"[error] ✗ Service not found or not running")
            return {
                "status": "failed",
                "service_id": service_id,
                "error": "Service not found or not running on any node"
            }
        
        node_id = node_info["node_id"]
        node_name = node_info["node_name"]
        datacenter = node_info.get("datacenter", "dc1")
        
        # Calculate total I/O load
        total_write_mb = io_workers_int * write_size_mb_int
        
        console.log(f"[strategy] Deploying {io_workers_int} I/O workers to {node_name}")
        console.log(f"[strategy] Each worker will write {write_size_mb_int}MB repeatedly")
        console.log(f"[strategy] Total disk throughput target: ~{total_write_mb}MB over {duration_int}s")
        
        # Generate unique job ID
        chaos_job_id = f"chaos-io-{service_id}-{int(time.time())}"[:63]
        
        # Create Nomad job specification for disk I/O stress
        # Using stress-ng with I/O workers
        io_stress_job = {
            "Job": {
                "ID": chaos_job_id,
                "Name": chaos_job_id,
                "Type": "batch",
                "Datacenters": [datacenter],
                "Constraints": [{
                    "LTarget": "${node.unique.id}",
                    "RTarget": node_id,
                    "Operand": "="
                }],
                "TaskGroups": [{
                    "Name": "disk-io-stress",
                    "Count": 1,
                    "RestartPolicy": {
                        "Attempts": 0,
                        "Mode": "fail"
                    },
                    "Tasks": [{
                        "Name": "io-stress",
                        "Driver": "docker",
                        "Config": {
                            "image": "polinux/stress",
                            "command": "stress",
                            "args": [
                                "--io", str(io_workers_int),
                                "--hdd", str(io_workers_int),
                                "--hdd-bytes", f"{write_size_mb_int}M",
                                "--timeout", f"{duration_int}s",
                                "--verbose"
                            ]
                        },
                        "Resources": {
                            "CPU": 1000,  # 1 GHz
                            "MemoryMB": 512
                        },
                        "LogConfig": {
                            "MaxFiles": 1,
                            "MaxFileSizeMB": 10
                        }
                    }]
                }]
            }
        }
        
        console.log(f"[deploy] Submitting chaos job: {chaos_job_id}")
        console.log(f"[deploy] Target: {service_id} on node {node_name}")
        console.log(f"[deploy] I/O workers: {io_workers_int}, Write size: {write_size_mb_int}MB each")
        console.log(f"[impact] Expected: Disk I/O contention, slow file operations, potential service degradation")
        
        # Submit the job
        response = client.jobs.register_job(io_stress_job)
        eval_id = response.get("EvalID", "unknown")
        
        console.log(f"[success] ✓ Chaos job deployed successfully!")
        console.log(f"[verify] Evaluation ID: {eval_id}")
        
        # Wait briefly for job to start
        time.sleep(2)
        
        # Verify deployment
        try:
            job_status = client.job.get_job(chaos_job_id)
            status = job_status.get("Status", "unknown")
            console.log(f"[verify] Job status: {status}")
            
            # Get allocations
            job_allocations = client.job.get_allocations(chaos_job_id)
            running_allocs = [a for a in job_allocations if a.get("ClientStatus") == "running"]
            
            if running_allocs:
                console.log(f"[impact] Disk I/O stress active on {node_name}")
                console.log(f"[impact] {io_workers_int} I/O workers writing {write_size_mb_int}MB each")
                console.log(f"[impact] All I/O operations on this node will experience contention")
                console.log(f"[impact] Services with disk-intensive operations will be affected")
            else:
                console.log(f"[warning] Job submitted but not yet running (may take a few seconds)")
                
        except Exception as e:
            console.log(f"[warning] Could not verify job status: {e}")
        
        return {
            "status": "success",
            "service_id": service_id,
            "chaos_job_id": chaos_job_id,
            "target_node": node_id,
            "target_node_name": node_name,
            "datacenter": datacenter,
            "duration": duration_int,
            "io_workers": io_workers_int,
            "write_size_mb": write_size_mb_int,
            "total_write_mb": total_write_mb,
            "eval_id": eval_id,
            "allocations_affected": node_info.get("allocations_count", 1),
            "impact": "Disk I/O contention - file operations will be slow, database writes degraded",
            "message": f"Disk I/O stress ({io_workers_int} workers x {write_size_mb_int}MB) deployed to {node_name} for {duration_int}s"
        }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to deploy disk I/O stress: {e}")
        import traceback
        console.log(f"[error] Traceback: {traceback.format_exc()}")
        return {
            "status": "failed",
            "service_id": service_id,
            "error": str(e)
        }


# ==============================================================================
# VM Platform Actions (OLVM, vSphere)
# ==============================================================================

def vm_power_off(
    vm_name: str,
    platform_type: str,
    graceful: bool = True,
    timeout: int = 300,
    **platform_config: Any
) -> Dict[str, Any]:
    """
    Power off a VM on a virtualization platform.
    
    Args:
        vm_name: Name of the VM to power off
        platform_type: Platform type ('olvm' or 'vsphere')
        graceful: If True, attempt graceful shutdown; if False, force power off
        timeout: Timeout in seconds
        **platform_config: Platform-specific configuration (url, server, username, password, etc.)
    
    Returns:
        Dictionary with status and details
    """
    try:
        platform = _get_platform_client(platform_type, platform_config)
        
        console.log(f"[action] Powering off VM: {vm_name}")
        console.log(f"[platform] Type: {platform_type}")
        console.log(f"[strategy] Graceful: {graceful}")
        
        with platform:
            # Get VM info before action
            vm_info = platform.get_vm(vm_name)
            console.log(f"[discovery] Current state: {vm_info.power_state.value}")
            console.log(f"[discovery] Host: {vm_info.host}")
            
            # Power off
            success = platform.power_off(vm_name, graceful=graceful, timeout=timeout)
            
            if success:
                console.log(f"[impact] ✓ VM {vm_name} powered off")
                return {
                    "status": "success",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "action": "power_off",
                    "graceful": graceful,
                    "previous_state": vm_info.power_state.value,
                    "host": vm_info.host,
                    "message": f"VM {vm_name} powered off successfully"
                }
            else:
                return {
                    "status": "failed",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "error": "Power off operation returned False"
                }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to power off VM: {e}")
        return {
            "status": "failed",
            "vm_name": vm_name,
            "platform": platform_type,
            "error": str(e)
        }


def vm_power_on(
    vm_name: str,
    platform_type: str,
    timeout: int = 300,
    **platform_config: Any
) -> Dict[str, Any]:
    """
    Power on a VM on a virtualization platform.
    
    Args:
        vm_name: Name of the VM to power on
        platform_type: Platform type ('olvm' or 'vsphere')
        timeout: Timeout in seconds
        **platform_config: Platform-specific configuration
    
    Returns:
        Dictionary with status and details
    """
    try:
        platform = _get_platform_client(platform_type, platform_config)
        
        console.log(f"[action] Powering on VM: {vm_name}")
        console.log(f"[platform] Type: {platform_type}")
        
        with platform:
            # Get VM info before action
            vm_info = platform.get_vm(vm_name)
            console.log(f"[discovery] Current state: {vm_info.power_state.value}")
            
            # Power on
            success = platform.power_on(vm_name, timeout=timeout)
            
            if success:
                console.log(f"[impact] ✓ VM {vm_name} powered on")
                return {
                    "status": "success",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "action": "power_on",
                    "previous_state": vm_info.power_state.value,
                    "message": f"VM {vm_name} powered on successfully"
                }
            else:
                return {
                    "status": "failed",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "error": "Power on operation returned False"
                }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to power on VM: {e}")
        return {
            "status": "failed",
            "vm_name": vm_name,
            "platform": platform_type,
            "error": str(e)
        }


def vm_reboot(
    vm_name: str,
    platform_type: str,
    graceful: bool = True,
    timeout: int = 300,
    **platform_config: Any
) -> Dict[str, Any]:
    """
    Reboot a VM on a virtualization platform.
    
    Args:
        vm_name: Name of the VM to reboot
        platform_type: Platform type ('olvm' or 'vsphere')
        graceful: If True, attempt graceful reboot; if False, force hard reset
        timeout: Timeout in seconds
        **platform_config: Platform-specific configuration
    
    Returns:
        Dictionary with status and details
    """
    try:
        platform = _get_platform_client(platform_type, platform_config)
        
        console.log(f"[action] Rebooting VM: {vm_name}")
        console.log(f"[platform] Type: {platform_type}")
        console.log(f"[strategy] Graceful: {graceful}")
        
        with platform:
            # Get VM info before action
            vm_info = platform.get_vm(vm_name)
            console.log(f"[discovery] Current state: {vm_info.power_state.value}")
            
            # Reboot
            success = platform.reboot(vm_name, graceful=graceful, timeout=timeout)
            
            if success:
                console.log(f"[impact] ✓ VM {vm_name} rebooted")
                return {
                    "status": "success",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "action": "reboot",
                    "graceful": graceful,
                    "message": f"VM {vm_name} rebooted successfully"
                }
            else:
                return {
                    "status": "failed",
                    "vm_name": vm_name,
                    "platform": platform_type,
                    "error": "Reboot operation returned False"
                }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed to reboot VM: {e}")
        return {
            "status": "failed",
            "vm_name": vm_name,
            "platform": platform_type,
            "error": str(e)
        }


def vm_batch_power_off(
    vm_names: list[str],
    platform_type: str,
    graceful: bool = True,
    parallel: int = 5,
    timeout: int = 300,
    **platform_config: Any
) -> Dict[str, Any]:
    """
    Power off multiple VMs in parallel.
    
    Args:
        vm_names: List of VM names to power off
        platform_type: Platform type ('olvm' or 'vsphere')
        graceful: If True, attempt graceful shutdown
        parallel: Maximum number of parallel operations
        timeout: Timeout per VM in seconds
        **platform_config: Platform-specific configuration
    
    Returns:
        Dictionary with overall status and per-VM results
    """
    try:
        platform = _get_platform_client(platform_type, platform_config)
        
        console.log(f"[action] Batch power off: {len(vm_names)} VMs")
        console.log(f"[platform] Type: {platform_type}")
        console.log(f"[strategy] Parallel: {parallel}, Graceful: {graceful}")
        
        with platform:
            results = platform.batch_power_off(
                vm_names,
                graceful=graceful,
                parallel=parallel,
                timeout=timeout
            )
            
            success_count = sum(1 for success in results.values() if success)
            console.log(f"[impact] ✓ {success_count}/{len(vm_names)} VMs powered off successfully")
            
            return {
                "status": "success" if success_count == len(vm_names) else "partial",
                "platform": platform_type,
                "action": "batch_power_off",
                "total_vms": len(vm_names),
                "successful": success_count,
                "failed": len(vm_names) - success_count,
                "results": results,
                "message": f"Batch power off: {success_count}/{len(vm_names)} successful"
            }
    
    except Exception as e:
        console.log(f"[error] ✗ Failed batch power off: {e}")
        return {
            "status": "failed",
            "platform": platform_type,
            "error": str(e)
        }


def _get_platform_client(platform_type: str, config: Dict[str, Any]):
    """
    Get a platform client instance based on platform type.
    
    Args:
        platform_type: 'olvm' or 'vsphere'
        config: Platform-specific configuration
    
    Returns:
        Platform client instance
    
    Raises:
        ValueError: If platform type is unknown
    """
    if platform_type == "olvm":
        from chaosmonkey.platforms.olvm import OLVMPlatform
        return OLVMPlatform(
            url=config["url"],
            username=config["username"],
            password=config["password"],
            ca_file=config.get("ca_file"),
            insecure=config.get("insecure", False),
            timeout=config.get("timeout", 60)
        )
    elif platform_type == "vsphere":
        from chaosmonkey.platforms.vsphere import VSpherePlatform
        return VSpherePlatform(
            server=config["server"],
            username=config["username"],
            password=config["password"],
            port=config.get("port", 443),
            insecure=config.get("insecure", True)
        )
    else:
        raise ValueError(f"Unknown platform type: {platform_type}. Supported: olvm, vsphere")


# K6 Load Testing Actions
def run_k6_script(
    script_text: str, 
    target_url: str = "",
    options: Dict[str, Any] = None, 
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Run a K6 load testing script using our custom K6 runner.
    
    This action integrates with the chaos engineering framework to run
    K6 load tests as part of chaos experiments.
    
    Args:
        script_text: The K6 JavaScript code to execute
        target_url: The URL to test against (will replace ${target_url} in script)
        options: K6 options (stages, thresholds, etc.)
        **kwargs: Additional arguments from chaos experiment
        
    Returns:
        Dictionary with execution results compatible with chaos toolkit
    """
    try:
        # Import our custom K6 runner
        from chaosmonkey.core.k6_runner import k6_runner
        
        if not k6_runner.is_available():
            return {
                "success": False,
                "error": "K6 binary not found. Please install K6: brew install k6 or npm install -g k6",
                "status": "failed"
            }
        
        # Process script template variables
        if target_url and "${target_url}" in script_text:
            script_text = script_text.replace("${target_url}", target_url)
        
        # Handle other template variables from kwargs
        for key, value in kwargs.items():
            placeholder = f"${{{key}}}"
            if placeholder in script_text:
                script_text = script_text.replace(placeholder, str(value))
        
        console.print(f"🚀 Running K6 load test against: {target_url}", style="bold green")
        console.print(f"📊 K6 binary: {k6_runner.k6_binary}", style="dim")
        
        # Generate output JSON path for dashboard generation
        from pathlib import Path
        timestamp = int(datetime.now().timestamp())
        out_json = Path("reports") / f"k6-api-test-{timestamp}.json"
        
        # Handle options merging if script already contains options
        if options and ("export let options" in script_text or "export const options" in script_text):
            # Script already has options, merge them or replace inline
            console.print("📊 Script contains inline options, merging with provided options", style="dim")
            result = k6_runner.run_script(script_text, None, out_json=out_json)  # Don't duplicate options
        else:
            # Execute K6 script normally
            result = k6_runner.run_script(script_text, options, out_json=out_json)
        
        if result["success"]:
            console.print("✅ K6 load test completed successfully", style="bold green")
            
            # Check if HTML dashboards were generated
            html_path = Path("reports") / f"embedded-{out_json.stem}.html"
            k6_web_dashboard = result.get('k6_web_dashboard')
            custom_dashboard = result.get('custom_dashboard')
            
            if k6_web_dashboard:
                console.print(f"📊 K6 Web Dashboard: {k6_web_dashboard}", style="bold blue")
            if custom_dashboard:
                console.print(f"📊 Custom Embedded Dashboard: {custom_dashboard}", style="bold blue")
            
            return {
                "success": True,
                "status": "succeeded",
                "k6_output": result.get("stdout", ""),
                "duration": "completed",
                "json_report": str(out_json.absolute()) if out_json.exists() else None,
                "k6_web_dashboard": k6_web_dashboard,
                "html_dashboard": custom_dashboard,
            }
        else:
            console.print(f"❌ K6 load test failed: {result.get('error', 'Unknown error')}", style="bold red")
            
            # Even on failure, check if HTML dashboards were generated (for debugging)
            html_path = Path("reports") / f"embedded-{out_json.stem}.html"
            k6_web_dashboard = result.get('k6_web_dashboard')
            custom_dashboard = result.get('custom_dashboard')
            
            if k6_web_dashboard:
                console.print(f"📊 K6 Web Dashboard (with error logs): {k6_web_dashboard}", style="dim")
            if custom_dashboard:
                console.print(f"📊 Custom Dashboard (with error logs): {custom_dashboard}", style="dim")
            
            return {
                "success": False,
                "status": "failed", 
                "error": result.get("error", "K6 test failed"),
                "k6_output": result.get("stderr", ""),
                "json_report": str(out_json.absolute()) if out_json.exists() else None,
                "k6_web_dashboard": k6_web_dashboard,
                "html_dashboard": custom_dashboard,
            }
            
    except Exception as e:
        console.print(f"💥 K6 action failed: {e}", style="bold red")
        return {
            "success": False,
            "status": "failed",
            "error": f"K6 action execution failed: {e}"
        }
