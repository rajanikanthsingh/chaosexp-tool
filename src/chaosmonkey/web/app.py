"""Flask web application for ChaosMonkey UI."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from .cache import get_cache, invalidate_cache

app = Flask(__name__, 
            template_folder=str(Path(__file__).parent / "templates"),
            static_folder=str(Path(__file__).parent / "static"))
CORS(app)

# Get the workspace root
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent  # Fixed: 4 parents, not 5
REPORTS_DIR = WORKSPACE_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Node operations tracking
NODE_OPS_DIR = WORKSPACE_ROOT / "node_operations"
NODE_OPS_DIR.mkdir(parents=True, exist_ok=True)

# Initialize cache
cache = get_cache()

# Dora status cache / updater settings
DORA_VMS_STATUS_KEY_PREFIX = "dora:vms-status:env:"
DORA_VMS_STATUS_TTL = 60  # seconds - how long cached status is considered valid
DORA_STATUS_UPDATE_INTERVAL = 15  # seconds - background refresh frequency per environment

# Updater thread guard
_dora_updater_thread = None
_dora_updater_running = False
_dora_updater_initialised = False


# Background job keys prefix
JOB_KEY_PREFIX = "dora:vms-status:job:"


def _store_job(job_id: str, payload: Dict[str, Any], ttl: int = 3600) -> None:
    """Store job metadata/result in cache."""
    if cache.enabled:
        cache.set(f"{JOB_KEY_PREFIX}{job_id}", payload, ttl=ttl)


def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if not cache.enabled:
        return None
    return cache.get(f"{JOB_KEY_PREFIX}{job_id}")


def _dora_cache_key_for_env(environment: str) -> str:
    return f"{DORA_VMS_STATUS_KEY_PREFIX}{environment}"


def probe_and_cache_dora_env(environment: str, settings) -> None:
    """Probe OLVM for all VMs in a Dora environment and cache results in Redis."""
    if not cache.enabled:
        return

    try:
        from chaosmonkey.platforms.dora import DoraClient
        from chaosmonkey.platforms.olvm import OLVMPlatform

        dora_client = DoraClient(
            dora_host=settings.platforms.dora.host,
            api_port=settings.platforms.dora.api_port,
            auth_port=settings.platforms.dora.auth_port
        )

        env_data = dora_client.get_environment_data(environment=environment, username=settings.platforms.dora.username, password=settings.platforms.dora.password)
        vms_data = env_data.get('vms', {})
        if isinstance(vms_data, dict) and 'items' in vms_data:
            vms = vms_data['items']
        elif isinstance(vms_data, list):
            vms = vms_data
        else:
            vms = []

        entries = []
        for vm in vms:
            if isinstance(vm, dict):
                entries.append({'name': vm.get('name'), 'dora': vm})
            else:
                entries.append({'name': str(vm), 'dora': {}})

        results = []
        if not (hasattr(settings, 'platforms') and hasattr(settings.platforms, 'olvm') and settings.platforms.olvm.url):
            # OLVM not configured: store Dora-only information
            for e in entries:
                d = e['dora']
                results.append({'vm_name': e['name'], 'dora_status': d.get('state') if isinstance(d, dict) else None, 'probe_status': None, 'probe_source': None, 'host': d.get('host') if isinstance(d, dict) else None})
            cache.set(_dora_cache_key_for_env(environment), {'environment': environment, 'vms': results}, ttl=DORA_VMS_STATUS_TTL)
            return

        # OLVM configured: probe in parallel
        with OLVMPlatform(
            url=settings.platforms.olvm.url,
            username=settings.platforms.olvm.username,
            password=settings.platforms.olvm.password,
            ca_file=getattr(settings.platforms.olvm, 'ca_file', None),
            insecure=getattr(settings.platforms.olvm, 'insecure', False)
        ) as olvm_client:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def probe(e):
                name = e['name']
                dora = e['dora']
                try:
                    vm_info = olvm_client.get_vm(name)
                    st = getattr(vm_info, 'power_state', None)
                    # Extract CPU, memory and guest OS from vm_info if available.
                    # vm_info may be an object or dict depending on platform client.
                    def _get_attr(obj, *names):
                        for n in names:
                            try:
                                if isinstance(obj, dict) and n in obj:
                                    return obj.get(n)
                                if hasattr(obj, n):
                                    return getattr(obj, n)
                            except Exception:
                                continue
                        return None

                    cpu_val = _get_attr(vm_info, 'cpu_count', 'cpus', 'cpu', 'num_cpus', 'vcpus', 'numVcpus', 'vcpu_count')
                    mem_val = _get_attr(vm_info, 'memory_mb', 'memMb', 'memory_mb', 'mem', 'memory')
                    guest = _get_attr(vm_info, 'guest_os', 'guestOS', 'guest')
                    # Normalize memory to a human readable string if numeric
                    try:
                        if isinstance(mem_val, (int, float)) and mem_val > 0:
                            memory_str = f"{mem_val / 1024:.1f} GB"
                        else:
                            memory_str = str(mem_val) if mem_val is not None else None
                    except Exception:
                        memory_str = None

                    # Normalize cpu to a string for UI; prefer integer count if available
                    cpu_str = None
                    try:
                        if isinstance(cpu_val, (int, float)):
                            cpu_str = str(int(cpu_val))
                        elif isinstance(cpu_val, str) and cpu_val.strip():
                            cpu_str = cpu_val.strip()
                    except Exception:
                        cpu_str = None

                    results.append({'vm_name': name, 'dora_status': (dora.get('state') if isinstance(dora, dict) else None), 'probe_status': st, 'probe_source': 'olvm', 'host': dora.get('host') if isinstance(dora, dict) else None, 'cpu': cpu_str, 'memory': memory_str, 'guest_os': guest})
                except Exception as ex:
                    results.append({'vm_name': name, 'dora_status': (dora.get('state') if isinstance(dora, dict) else None), 'probe_status': None, 'probe_source': 'olvm', 'host': dora.get('host') if isinstance(dora, dict) else None, 'probe_error': str(ex)})

            with ThreadPoolExecutor(max_workers=10) as exe:
                futures = [exe.submit(probe, e) for e in entries]
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception:
                        pass

        # Store cache
        cache.set(_dora_cache_key_for_env(environment), {'environment': environment, 'vms': results}, ttl=DORA_VMS_STATUS_TTL)
    except Exception as ex:
        print(f"Error probing and caching Dora env {environment}: {ex}")


def _start_dora_background_updater(settings):
    """Start a background thread that periodically refreshes Dora VM statuses for environments configured in Dora."""
    global _dora_updater_thread, _dora_updater_running
    if not cache.enabled:
        print("Redis cache disabled; background Dora updater will not start")
        return

    if _dora_updater_running:
        return

    # Mark running before thread start so the thread can observe the flag and exit when cleared
    _dora_updater_running = True

    def updater():
        nonlocal settings
        global _dora_updater_running
        try:
            # Determine environments from Dora or fallback to ['Dev']
            try:
                from chaosmonkey.platforms.dora import DoraClient
                dora_client = DoraClient(
                    dora_host=settings.platforms.dora.host,
                    api_port=settings.platforms.dora.api_port,
                    auth_port=settings.platforms.dora.auth_port
                )
                envs = DoraClient.list_environments() if hasattr(DoraClient, 'list_environments') else ['Dev']
            except Exception:
                envs = ['Dev']

            import time
            # Run while the running flag is True so external callers can stop the updater
            while _dora_updater_running:
                for env in envs:
                    if not _dora_updater_running:
                        break
                    try:
                        probe_and_cache_dora_env(env, settings)
                    except Exception as e:
                        print(f"Background updater error for env {env}: {e}")
                # Sleep with small increments to respond promptly to stop requests
                slept = 0
                while _dora_updater_running and slept < DORA_STATUS_UPDATE_INTERVAL:
                    time.sleep(1)
                    slept += 1
        finally:
            # Ensure running flag is cleared when thread exits
            try:
                _dora_updater_running = False
            except Exception:
                pass

    from threading import Thread
    _dora_updater_thread = Thread(target=updater, daemon=True)
    _dora_updater_thread.start()


def _stop_dora_background_updater(timeout: int = 5) -> None:
    """Stop the Dora background updater thread if running.

    This sets the running flag to False and waits up to `timeout` seconds for the
    thread to exit. It's safe to call even if the updater is not running.
    """
    global _dora_updater_thread, _dora_updater_running
    if not _dora_updater_thread:
        _dora_updater_running = False
        return

    _dora_updater_running = False
    try:
        _dora_updater_thread.join(timeout=timeout)
    except Exception:
        pass
    if _dora_updater_thread and _dora_updater_thread.is_alive():
        print('Warning: Dora updater thread did not stop within timeout')
    _dora_updater_thread = None


def log_node_operation(operation_type: str, node_id: str, node_name: str, details: Dict[str, Any] = None, batch_id: str = None) -> str:
    """Log a node operation (drain/recover) for reporting."""
    from datetime import datetime, UTC
    import uuid
    
    operation_id = f"node-op-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(UTC).isoformat()
    
    operation_data = {
        "operation_id": operation_id,
        "type": operation_type,  # 'drain' or 'recover'
        "node_id": node_id,
        "node_name": node_name,
        "timestamp": timestamp,
        "details": details or {},
        "success": details.get("success", True) if details else True,
        "batch_id": batch_id  # Link to batch operation if this is part of a batch
    }
    
    # Save to file
    operation_file = NODE_OPS_DIR / f"{operation_id}.json"
    with open(operation_file, 'w') as f:
        json.dump(operation_data, f, indent=2)
    
    return operation_id


def log_batch_node_operation(operation_type: str, nodes: List[Dict[str, Any]], details: Dict[str, Any] = None) -> str:
    """Log a batch node operation (multiple nodes drained/recovered together)."""
    from datetime import datetime, UTC
    import uuid
    
    batch_id = f"batch-op-{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now(UTC).isoformat()
    
    batch_data = {
        "operation_id": batch_id,
        "type": operation_type,  # 'drain' or 'recover'
        "is_batch": True,
        "node_count": len(nodes),
        "nodes": nodes,  # List of {node_id, node_name, success}
        "timestamp": timestamp,
        "details": details or {},
        "success": all(n.get("success", True) for n in nodes),
        "success_count": sum(1 for n in nodes if n.get("success", True)),
        "failed_count": sum(1 for n in nodes if not n.get("success", True))
    }
    
    # Save to file
    operation_file = NODE_OPS_DIR / f"{batch_id}.json"
    with open(operation_file, 'w') as f:
        json.dump(batch_data, f, indent=2)
    
    return batch_id


def get_node_operations(operation_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Get logged node operations, optionally filtered by type."""
    operations = []
    
    for op_file in sorted(NODE_OPS_DIR.glob("node-op-*.json"), reverse=True):
        try:
            with open(op_file, 'r') as f:
                op_data = json.load(f)
                if operation_type is None or op_data.get("type") == operation_type:
                    operations.append(op_data)
                if len(operations) >= limit:
                    break
        except Exception as e:
            print(f"Error loading operation file {op_file}: {e}")
    
    return operations


# Ensure background services are started once when the app begins handling requests.
@app.before_request
def _on_app_first_request():
    global _dora_updater_initialised
    if _dora_updater_initialised:
        return
    _dora_updater_initialised = True
    try:
        from chaosmonkey.config import load_settings
        settings = load_settings(None)
        # Start the Dora background updater (will be a no-op if cache disabled or already running)
        try:
            _start_dora_background_updater(settings)
            print("Dora background updater started (or already running)")
        except Exception as e:
            print(f"Failed to start Dora background updater: {e}")
    except Exception as e:
        # Loading settings failed; do not prevent the app from running.
        print(f"App startup: failed to load settings, background updaters not started: {e}")


def run_cli_command(command: List[str]) -> Dict[str, Any]:
    """Execute a chaosmonkey CLI command and return the result."""
    try:
        # Replace 'chaosmonkey' with full path to ensure it's found
        if command and command[0] == 'chaosmonkey':
            command = [str(WORKSPACE_ROOT / '.venv' / 'bin' / 'chaosmonkey')] + command[1:]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=WORKSPACE_ROOT,
            timeout=300  # 5 minute timeout
        )
        
        # Try to parse JSON output
        # The CLI may print warnings before the JSON, so find where JSON starts
        output_data = {}
        if result.stdout.strip():
            try:
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Try to find JSON in the output (look for first '{' or '[')
                stdout = result.stdout.strip()
                json_start = -1
                for i, char in enumerate(stdout):
                    if char in ('{', '['):
                        json_start = i
                        break
                
                if json_start >= 0:
                    try:
                        output_data = json.loads(stdout[json_start:])
                    except json.JSONDecodeError:
                        output_data = {"raw_output": result.stdout}
                else:
                    output_data = {"raw_output": result.stdout}
        
        return {
            "success": result.returncode == 0,
            "output": output_data,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Command timed out after 5 minutes"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.route("/")
def index():
    """Render the main dashboard."""
    return render_template("index.html")


@app.route("/api/discover/services")
def discover_services():
    """Discover Nomad services."""
    result = run_cli_command(["chaosmonkey", "discover"])
    
    # Flatten the response structure for frontend compatibility
    # The CLI returns: {"output": {"nomad": {"services": [...]}}}
    # Frontend expects: {"output": {"targets": [...], "services": [...]}}
    if result.get("success") and result.get("output"):
        output = result["output"]
        
        # Extract services from nested structure
        services = []
        if isinstance(output, dict):
            # Check for nomad.services path
            if "nomad" in output and isinstance(output["nomad"], dict):
                services = output["nomad"].get("services", [])
            # Check for direct services path
            elif "services" in output:
                services = output["services"]
        
        # Add both 'targets' and 'services' keys for compatibility
        result["output"] = {
            "targets": services,
            "services": services,
            "nomad": output.get("nomad", {}) if isinstance(output, dict) else {}
        }
    
    return jsonify(result)


@app.route("/api/discover/clients")
def discover_clients():
    """Discover Nomad client nodes using Nomad API with Redis caching."""
    import os
    from urllib.parse import urlparse
    
    
    # Check source parameter (nomad or dora)
    source = request.args.get('source', 'nomad').lower()
    
    # If source is dora, delegate to Dora endpoint
    if source == 'dora':
        return discover_dora()
    
    # Otherwise, continue with Nomad discovery
    # Check for refresh flag
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    # Try to get from cache first (unless force refresh)
    cache_key = "nomad:clients:all"
    if not force_refresh and cache.enabled:
        cached_data = cache.get(cache_key)
        if cached_data:
            print("✅ Returning cached Nomad clients")
            return jsonify({
                "success": True,
                "output": {"clients": cached_data},
                "cached": True
            })
    
    try:
        import nomad
    except ImportError:
        return jsonify({
            "success": False,
            "error": "python-nomad library not installed"
        })
    
    try:
        # Get Nomad connection from environment
        addr = os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646")
        token = os.getenv("NOMAD_TOKEN", "")
        parsed = urlparse(addr)
        
        client = nomad.Nomad(
            host=parsed.hostname,
            port=parsed.port or 4646,
            token=token,
            namespace=os.getenv("NOMAD_NAMESPACE", "default")
        )
        
        # Get all nodes
        nodes = client.nodes.get_nodes()
        
        # If we have cached data and not forcing refresh, do incremental update
        existing_clients = {}
        if not force_refresh and cache.enabled:
            cached_hash = cache.get_all_hash("nomad:clients:hash")
            if cached_hash:
                existing_clients = cached_hash
                print(f"📦 Found {len(existing_clients)} cached clients, doing incremental update")
        
        clients = []
        updated_count = 0
        new_count = 0
        
        for node in nodes:
            node_id = node.get("ID", "")
            node_name = node.get("Name", "unknown")
            status = node.get("Status", "unknown")
            datacenter = node.get("Datacenter", "unknown")
            node_class = node.get("NodeClass", "-")
            drain = node.get("Drain", False)
            drain_strategy = node.get("DrainStrategy")
            scheduling_eligibility = node.get("SchedulingEligibility", "eligible")
            
            # Determine drain display status
            if drain_strategy:
                drain_display = "Draining..."
            elif drain or scheduling_eligibility == "ineligible":
                drain_display = "Yes"
            else:
                drain_display = "No"
            
            # Check if we have this node cached and if basic info hasn't changed
            cached_node = existing_clients.get(node_id)
            if cached_node and not force_refresh:
                # Check if status or drain changed (critical fields)
                if (cached_node.get("status") == status and 
                    cached_node.get("drain") == drain_display):
                    # Use cached version
                    clients.append(cached_node)
                    continue
            
            # Need to fetch detailed info (new node or changed status)
            try:
                node_detail = client.node.get_node(node_id)
                resources = node_detail.get("Resources", {})
                node_resources = node_detail.get("NodeResources", {})
                
                cpu_mhz = resources.get("CPU", 0)
                if not cpu_mhz and node_resources:
                    cpu_info = node_resources.get("Cpu", {})
                    cpu_mhz = cpu_info.get("CpuShares", 0)
                
                memory_mb = resources.get("MemoryMB", 0)
                if not memory_mb and node_resources:
                    mem_info = node_resources.get("Memory", {})
                    memory_mb = mem_info.get("MemoryMB", 0)
                
                cpu_str = f"{cpu_mhz:,} MHz" if cpu_mhz else "-"
                memory_gb = memory_mb / 1024 if memory_mb else 0
                memory_str = f"{memory_gb:.1f} GB" if memory_mb else "-"
                
                node_allocs = client.node.get_allocations(node_id)
                running_allocs = len([a for a in node_allocs if a.get("ClientStatus") == "running"])
                
                if cached_node:
                    updated_count += 1
                else:
                    new_count += 1
                    
            except Exception as e:
                print(f"⚠️  Error fetching details for node {node_id}: {e}")
                # Use cached data if available, otherwise use defaults
                if cached_node:
                    clients.append(cached_node)
                    continue
                cpu_str = "-"
                memory_str = "-"
                running_allocs = 0
            
            node_data = {
                "name": node_name,
                "id": node_id,
                "status": status,
                "datacenter": datacenter,
                "node_class": node_class or "-",
                "cpu": cpu_str,
                "memory": memory_str,
                "drain": drain_display,
                "allocations": str(running_allocs)
            }
            
            clients.append(node_data)
            
            # Update hash cache for this node
            if cache.enabled:
                cache.set_hash("nomad:clients:hash", node_id, node_data)
        
        # Cache the full result for 60 seconds (fast queries)
        if cache.enabled:
            cache.set(cache_key, clients, ttl=60)
            # Keep the hash cache for 5 minutes (for incremental updates)
            cache.expire("nomad:clients:hash", 300)
            
            print(f"💾 Cached {len(clients)} clients (new: {new_count}, updated: {updated_count})")
        
        return jsonify({
            "success": True,
            "output": {
                "clients": clients,
                "stats": {
                    "total": len(clients),
                    "new": new_count,
                    "updated": updated_count,
                    "cached": len(clients) - new_count - updated_count
                }
            },
            "cached": False
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })


@app.route("/api/discover/dora")
def discover_dora():
    """Discover VMs from Dora API."""
    try:
        from chaosmonkey.platforms.dora import DoraClient
        from chaosmonkey.config import load_settings
        
        environment = request.args.get('environment', 'Dev')
        debug = request.args.get('debug', 'false').lower() == 'true'
        
        # Load settings
        settings = load_settings(None)

        # If cache has a recent value for this environment, return it immediately
        try:
            if cache.enabled:
                cached = cache.get(_dora_cache_key_for_env(environment))
                if cached:
                    # Ensure background updater is running so cache stays fresh
                    try:
                        _start_dora_background_updater(settings)
                    except Exception:
                        pass
                    # Return a consistent response shape expected by the frontend
                    # (frontend expects output.clients). The cache may contain
                    # probe results produced by probe_and_cache_dora_env which
                    # use the key 'vm_name' and different field names. Normalize
                    # those entries into the UI-friendly client shape so the
                    # Nodes page shows name, hypervisor, cpu, memory and guest OS.
                    raw_clients = cached.get('vms', [])
                    clients = []
                    for entry in raw_clients:
                        # probe entries usually have: vm_name, dora_status, probe_status, probe_source, host
                        name = entry.get('name') or entry.get('vm_name') or entry.get('vm')
                        # Use vm_name as id when managed reference isn't available
                        vm_id = entry.get('id') or entry.get('managedObjRef') or entry.get('vm_name') or name
                        # Determine power state preference: probe_status (live) else dora_status
                        power_state = None
                        if entry.get('probe_status'):
                            power_state = entry.get('probe_status')
                        elif entry.get('dora_status'):
                            power_state = entry.get('dora_status')
                        else:
                            power_state = entry.get('power_state') if isinstance(entry.get('power_state'), str) else None

                        # Coerce cpu/memory values to printable strings to ensure UI shows them
                        # Robust CPU extraction: check common keys and nested structures
                        def _find_cpu(src):
                            candidates = []
                            if isinstance(src, dict):
                                candidates.extend([src.get(k) for k in ('cpu', 'cpus', 'cpu_count', 'num_cpus', 'vcpus', 'numVcpus', 'vcpu_count')])
                                # metadata or vm_info may contain cpu info
                                md = src.get('metadata') or src.get('vm_info') or src.get('vm')
                                if isinstance(md, dict):
                                    candidates.extend([md.get(k) for k in ('cpu', 'cpus', 'cpu_count', 'num_cpus', 'vcpus')])
                            else:
                                # src might be a primitive
                                candidates.append(src)
                            # Filter out None and empty
                            for c in candidates:
                                if c is None:
                                    continue
                                if isinstance(c, (int, float)):
                                    return c
                                if isinstance(c, str) and c.strip():
                                    # Try to coerce numeric strings
                                    try:
                                        return int(c)
                                    except Exception:
                                        return c.strip()
                            return None

                        cpu_val_raw = _find_cpu(entry)
                        cpu_val = None
                        try:
                            if isinstance(cpu_val_raw, (int, float)):
                                cpu_val = str(int(cpu_val_raw))
                            elif isinstance(cpu_val_raw, str):
                                cpu_val = cpu_val_raw
                            else:
                                cpu_val = '-'
                        except Exception:
                            cpu_val = '-'
                        mem_raw = entry.get('memory') if entry.get('memory') is not None else entry.get('mem') if entry.get('mem') is not None else entry.get('memMb')
                        memory_val = None
                        try:
                            if isinstance(mem_raw, (int, float)):
                                memory_val = f"{mem_raw / 1024:.1f} GB"
                            else:
                                memory_val = str(mem_raw) if mem_raw is not None else '-'
                        except Exception:
                            memory_val = '-'

                        clients.append({
                            "name": name or 'Unknown',
                            "id": vm_id or (name or 'unknown'),
                            "power_state": power_state or 'unknown',
                            "status": power_state or 'unknown',
                            "probe_status": entry.get('probe_status'),
                            "probe_source": entry.get('probe_source'),
                            "hypervisor": entry.get('host') or entry.get('hypervisor') or 'N/A',
                            "datacenter": environment,
                            "cpu": cpu_val,
                            "memory": memory_val,
                            "guest_os": entry.get('guest_os') or entry.get('guestOS') or entry.get('guest') or '-',
                            "guestOS": entry.get('guestOS') or entry.get('guest_os') or entry.get('guest') or '-'
                        })

                    return jsonify({
                        "success": True,
                        "output": {"clients": clients, "environment": environment, "total": len(clients)},
                        "cached": True
                    })
        except Exception:
            # Any cache errors should not prevent normal operation
            pass
        
        # Create Dora client
        client = DoraClient(
            dora_host=settings.platforms.dora.host,
            api_port=settings.platforms.dora.api_port,
            auth_port=settings.platforms.dora.auth_port
        )
        
        # Get credentials
        username = settings.platforms.dora.username
        password = settings.platforms.dora.password
        
        # Fetch environment data
        data = client.get_environment_data(
            environment=environment,
            username=username,
            password=password
        )
        
        # Debug mode: return raw data
        if debug:
            return jsonify({
                "success": True,
                "debug": True,
                "raw_data": data,
                "data_type": str(type(data)),
                "vms_type": str(type(data.get('vms'))) if isinstance(data, dict) else "N/A"
            })
        
        # Extract VMs from response
        # Data structure: {"environment": str, "hypervisors": {"items": [...]}, "vms": {"items": [...]}}
        vms_data = data.get('vms', {})
        
        # VMs are in an 'items' array
        if isinstance(vms_data, dict) and 'items' in vms_data:
            vm_list = vms_data['items']
        elif isinstance(vms_data, list):
            vm_list = vms_data
        else:
            vm_list = []
        
        # Transform to UI-friendly format
        vms = []
        for vm in vm_list:
            if isinstance(vm, dict):
                # Extract host name from path
                host_path = vm.get("host", "N/A")
                host_name = host_path.split('/')[-1] if '/' in host_path else host_path
                
                # Get memory in GB
                mem_mb = vm.get('memMb', 0)
                memory_str = f"{mem_mb / 1024:.1f} GB" if mem_mb else "N/A"
                
                vms.append({
                    "name": vm.get("name", "N/A"),
                    "id": vm.get("managedObjRef", vm.get("name", "N/A")),
                    "power_state": vm.get("state", "unknown"),
                    "hypervisor": host_name,
                    "cpu": str(vm.get("cpus", 0)),
                    "memory": memory_str,
                    "guest_os": vm.get("os", "N/A"),
                    "datacenter": environment
                })
        
        # Don't perform synchronous OLVM enrichment here: it makes initial page loads slow
        # Instead, return Dora-only (fast) and spawn a background probe to populate Redis
        # so subsequent requests or the frontend poller can get live probe data from cache.
        olvm_configured = False
        try:
            olvm_configured = bool(settings.platforms.olvm.url)
        except Exception:
            olvm_configured = False

        # Prepare Dora-only client entries (UI-friendly format)
        clients = []
        for vm in vms:
                if isinstance(vm, dict):
                    host_path = vm.get("host", "N/A")
                    host_name = host_path.split('/')[-1] if '/' in host_path else host_path
                    # Normalize cpu/memory into printable strings
                    # Robust CPU extraction for Dora-only VM entries
                    def _find_cpu_vm(src):
                        candidates = []
                        if isinstance(src, dict):
                            candidates.extend([src.get(k) for k in ('cpu', 'cpus', 'cpu_count', 'num_cpus', 'vcpus', 'numVcpus', 'vcpu_count')])
                            md = src.get('metadata') or src.get('vm_info') or src.get('vm')
                            if isinstance(md, dict):
                                candidates.extend([md.get(k) for k in ('cpu', 'cpus', 'cpu_count', 'num_cpus', 'vcpus')])
                        else:
                            candidates.append(src)
                        for c in candidates:
                            if c is None:
                                continue
                            if isinstance(c, (int, float)):
                                return c
                            if isinstance(c, str) and c.strip():
                                try:
                                    return int(c)
                                except Exception:
                                    return c.strip()
                        return None

                    cpu_raw = _find_cpu_vm(vm)
                    try:
                        cpu_str = str(int(cpu_raw)) if isinstance(cpu_raw, (int, float)) else (str(cpu_raw) if cpu_raw is not None else '-')
                    except Exception:
                        cpu_str = '-'
                    mem_mb = vm.get('memMb') if vm.get('memMb') is not None else vm.get('memory')
                    try:
                        memory_str = f"{mem_mb / 1024:.1f} GB" if isinstance(mem_mb, (int, float)) and mem_mb > 0 else (str(mem_mb) if mem_mb is not None else 'N/A')
                    except Exception:
                        memory_str = 'N/A'
                    clients.append({
                        "name": vm.get("name", "N/A"),
                        "id": vm.get("managedObjRef", vm.get("name", "N/A")),
                        "power_state": vm.get("state", "unknown"),
                        "hypervisor": host_name,
                        # The UI expects 'datacenter' to display the hypervisor column
                        "datacenter": host_name,
                        "cpu": cpu_str,
                        "memory": memory_str,
                        "guest_os": vm.get("os", "N/A"),
                        "guestOS": vm.get("os", "N/A"),
                        "datacenter": host_name,
                        "environment": environment
                    })

        # If OLVM is configured and cache is available, spawn background probe to warm cache
        if olvm_configured and cache.enabled:
            try:
                from threading import Thread
                Thread(target=probe_and_cache_dora_env, args=(environment, settings), daemon=True).start()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "output": {
                "clients": clients,
                "environment": environment,
                "total": len(clients)
            },
            "cached": False
        })
        
    except ImportError as e:
        return jsonify({
            "success": False,
            "error": f"Dora platform not available: {str(e)}"
        }), 500
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": f"Invalid environment: {str(e)}"
        }), 400
    except RuntimeError as e:
        return jsonify({
            "success": False,
            "error": f"Dora API error: {str(e)}"
        }), 500
    except Exception as e:
        import traceback
        print(f"Error in discover_dora: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500


@app.route("/api/dora/environments")
def list_dora_environments():
    """List available Dora environments."""
    try:
        from chaosmonkey.platforms.dora import DoraClient
        
        environments = DoraClient.list_environments()
        return jsonify({
            "success": True,
            "environments": environments
        })
    except ImportError:
        return jsonify({
            "success": False,
            "error": "Dora platform not available"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/dora/vm-power", methods=["POST"])
def dora_vm_power_action():
    """
    Handle VM power actions for Dora-managed VMs.
    
    This endpoint receives power action requests from the UI and forwards them
    to the appropriate vSphere/OLVM backend since Dora is a read-only inventory system.
    
    Note: This requires proper vSphere/OLVM credentials to be configured in chaosmonkey.yaml
    """
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.vsphere import VSpherePlatform
        from chaosmonkey.platforms.olvm import OLVMPlatform
        
        data = request.json
        vm_name = data.get("vm_name")
        action = data.get("action")  # 'start', 'reboot', 'stop'
        environment = data.get("environment", "Dev1")
        
        if not vm_name or not action:
            return jsonify({
                "success": False, 
                "error": "vm_name and action are required"
            }), 400
        
        if action not in ['start', 'reboot', 'stop']:
            return jsonify({
                "success": False,
                "error": f"Invalid action: {action}. Must be 'start', 'reboot', or 'stop'"
            }), 400
        
        settings = load_settings(None)
        errors = []
        
        # Map action to platform method
        action_map = {
            'start': 'power_on',
            'stop': 'power_off',
            'reboot': 'reboot'
        }
        platform_action = action_map[action]
        
        # Check if vSphere is configured
        vsphere_configured = (
            hasattr(settings.platforms, 'vsphere') and 
            settings.platforms.vsphere.server and
            settings.platforms.vsphere.username and
            settings.platforms.vsphere.password
        )
        
        # Check if OLVM is configured
        olvm_configured = (
            hasattr(settings.platforms, 'olvm') and 
            settings.platforms.olvm.url and
            settings.platforms.olvm.username and
            settings.platforms.olvm.password
        )
        
        if not vsphere_configured and not olvm_configured:
            return jsonify({
                "success": False,
                "error": "No virtualization platform configured. Please configure vSphere or OLVM credentials in chaosmonkey.yaml"
            }), 500
        
        # Try vSphere first if configured
        if vsphere_configured:
            try:
                with VSpherePlatform(
                    server=settings.platforms.vsphere.server,
                    username=settings.platforms.vsphere.username,
                    password=settings.platforms.vsphere.password,
                    insecure=settings.platforms.vsphere.insecure
                ) as platform:
                    method = getattr(platform, platform_action)
                    if platform_action == 'reboot':
                        method(vm_name, graceful=True, timeout=300)
                    else:
                        method(vm_name, timeout=300)
                    
                    return jsonify({
                        "success": True,
                        "message": f"VM '{vm_name}' {action} successful via vSphere",
                        "platform": "vsphere",
                        "vm_name": vm_name,
                        "action": action,
                        "note": "Note: VM status in Dora may take 30-60 seconds to reflect the change"
                    })
            except Exception as e:
                error_msg = str(e)
                errors.append(f"vSphere: {error_msg}")
                print(f"vSphere {action} failed for {vm_name}: {error_msg}")
        
        # Try OLVM if vSphere failed or not configured
        if olvm_configured:
            try:
                with OLVMPlatform(
                    url=settings.platforms.olvm.url,
                    username=settings.platforms.olvm.username,
                    password=settings.platforms.olvm.password,
                    insecure=settings.platforms.olvm.insecure
                ) as platform:
                    method = getattr(platform, platform_action)
                    if platform_action == 'reboot':
                        method(vm_name, graceful=True, timeout=300)
                    else:
                        method(vm_name, timeout=300)
                    
                    return jsonify({
                        "success": True,
                        "message": f"VM '{vm_name}' {action} successful via OLVM",
                        "platform": "olvm",
                        "vm_name": vm_name,
                        "action": action,
                        "note": "Note: VM status in Dora may take 30-60 seconds to reflect the change"
                    })
            except Exception as e:
                error_msg = str(e)
                errors.append(f"OLVM: {error_msg}")
                print(f"OLVM {action} failed for {vm_name}: {error_msg}")
        
        # All attempts failed
        return jsonify({
            "success": False,
            "error": f"Failed to {action} VM on all platforms. Errors: {'; '.join(errors)}"
        }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500


@app.route("/api/dora/vm-status", methods=["POST"])
def get_dora_vm_status():
    """Get real-time VM status by consulting Dora first to detect platform, then querying the appropriate platform API.

    Decision order:
      1. Query Dora to find VM metadata (provider/hypervisor).
      2. If Dora indicates OLVM and OLVM is configured -> query OLVM.
      3. If Dora indicates vSphere and vSphere is configured -> query vSphere.
      4. Otherwise try vSphere then OLVM as fallbacks if configured.
      5. If all platform checks fail, return Dora's reported state (if present).
    """
    try:
        # Use absolute imports so this function works whether the package is
        # imported as a module or run from a script that adjusted sys.path.
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.dora import DoraClient

        data = request.get_json()
        vm_name = data.get("vm_name")
        environment = data.get("environment", "Dev")

        if not vm_name:
            return jsonify({"success": False, "error": "vm_name is required"}), 400

        settings = load_settings(None)

        # Prepare platform availability flags
        vsphere_configured = (
            hasattr(settings, 'platforms') and
            hasattr(settings.platforms, 'vsphere') and
            settings.platforms.vsphere.server
        )
        olvm_configured = (
            hasattr(settings, 'platforms') and
            hasattr(settings.platforms, 'olvm') and
            settings.platforms.olvm.url
        )

        # Fetch Dora environment data to detect VM provider and get Dora-reported state
        try:
            dora_username = settings.platforms.dora.username
            dora_password = settings.platforms.dora.password
            dora_client = DoraClient(
                dora_host=settings.platforms.dora.host,
                api_port=settings.platforms.dora.api_port,
                auth_port=settings.platforms.dora.auth_port
            )

            env_data = dora_client.get_environment_data(
                environment=environment,
                username=dora_username,
                password=dora_password
            )

            vms_data = env_data.get('vms', {})
            if isinstance(vms_data, dict) and 'items' in vms_data:
                vms = vms_data['items']
            elif isinstance(vms_data, list):
                vms = vms_data
            else:
                vms = []

            vm_data = next((vm for vm in vms if vm.get('name') == vm_name), None)
        except Exception as dora_err:
            print(f"Dora query failed: {dora_err}")
            vm_data = None

        # Determine provider_text if Dora provided metadata
        provider_text = ''
        if vm_data:
            provider_fields = [
                vm_data.get('provider', ''),
                vm_data.get('hypervisor', ''),
                vm_data.get('engine', ''),
                vm_data.get('platform', ''),
                vm_data.get('type', ''),
            ]
            provider_text = ' '.join([str(p).lower() for p in provider_fields if p])

        # Helper to normalize platform VMInfo power_state to UI string.
        # Accept a wide range of inputs from platform SDKs (enums, strings,
        # bools) and Dora's reported state.
        def normalize_vminfo_power(vm_info_or_state):
            # Accept either an object with attribute `power_state` or a raw value
            if hasattr(vm_info_or_state, 'power_state'):
                raw = getattr(vm_info_or_state, 'power_state')
            else:
                raw = vm_info_or_state

            if raw is None:
                return 'unknown'

            rs = str(raw).strip().lower()

            # Common positive indicators
            if any(x in rs for x in ('poweredon', 'powered on', 'on', 'up', 'running', 'true')):
                return 'poweredOn'

            # Common negative indicators
            if any(x in rs for x in ('poweredoff', 'powered off', 'off', 'down', 'stopped', 'false')):
                return 'poweredOff'

            # Suspended/paused
            if any(x in rs for x in ('suspend', 'suspended', 'paused')):
                return 'suspended'

            return 'unknown'

        # If Dora indicates OLVM/ovirt and OLVM is configured, check OLVM first
        # Normalize Dora's reported state for later inclusion
        dora_reported_state = None
        if vm_data:
            dora_reported_state = normalize_vminfo_power(vm_data.get('state'))
        if vm_data and olvm_configured and any(k in provider_text for k in ('ovirt', 'olvm', 'ovirt-engine')):
            try:
                from chaosmonkey.platforms.olvm import OLVMPlatform
                with OLVMPlatform(
                    url=settings.platforms.olvm.url,
                    username=settings.platforms.olvm.username,
                    password=settings.platforms.olvm.password,
                    ca_file=settings.platforms.olvm.ca_file,
                    insecure=settings.platforms.olvm.insecure
                ) as olvm_client:
                    try:
                        vm_info = olvm_client.get_vm(vm_name)
                        status = normalize_vminfo_power(vm_info)
                        return jsonify({
                            "success": True,
                            "vm_name": vm_name,
                            "status": status,
                            "source": "olvm",
                            "probe_status": status,
                            "probe_source": "olvm",
                            "dora_status": dora_reported_state
                        })
                    except ValueError:
                        print(f"OLVM: VM '{vm_name}' not found in OLVM; falling back")
            except Exception as e:
                print(f"OLVM probe failed for {vm_name}: {e}")

        # If Dora says vSphere (or we didn't detect OLVM), try vSphere if configured
        if vm_data and vsphere_configured and any(k in provider_text for k in ('vcenter', 'vsphere', 'vc')):
            try:
                from chaosmonkey.platforms.vsphere import VSpherePlatform
                with VSpherePlatform(
                    server=settings.platforms.vsphere.server,
                    username=settings.platforms.vsphere.username,
                    password=settings.platforms.vsphere.password,
                    insecure=settings.platforms.vsphere.insecure
                ) as vs_client:
                    try:
                        vm_info = vs_client.get_vm(vm_name)
                        status = normalize_vminfo_power(vm_info)
                        return jsonify({
                            "success": True,
                            "vm_name": vm_name,
                            "status": status,
                            "source": "vsphere",
                            "probe_status": status,
                            "probe_source": "vsphere",
                            "dora_status": dora_reported_state
                        })
                    except ValueError:
                        print(f"vSphere: VM '{vm_name}' not found in vSphere; falling back")
            except Exception as e:
                print(f"vSphere probe failed for {vm_name}: {e}")

        # If Dora didn't indicate platform or platform-specific probes failed, try best-effort probes
        # Try vSphere then OLVM as fallbacks
        if vsphere_configured:
            try:
                from chaosmonkey.platforms.vsphere import VSpherePlatform
                with VSpherePlatform(
                    server=settings.platforms.vsphere.server,
                    username=settings.platforms.vsphere.username,
                    password=settings.platforms.vsphere.password,
                    insecure=settings.platforms.vsphere.insecure
                ) as vs_client:
                    try:
                        vm_info = vs_client.get_vm(vm_name)
                        status = normalize_vminfo_power(vm_info)
                        return jsonify({
                            "success": True,
                            "vm_name": vm_name,
                            "status": status,
                            "source": "vsphere",
                            "probe_status": status,
                            "probe_source": "vsphere",
                            "dora_status": dora_reported_state
                        })
                    except ValueError:
                        pass
            except Exception as e:
                print(f"vSphere fallback probe failed for {vm_name}: {e}")

        if olvm_configured:
            try:
                from chaosmonkey.platforms.olvm import OLVMPlatform
                with OLVMPlatform(
                    url=settings.platforms.olvm.url,
                    username=settings.platforms.olvm.username,
                    password=settings.platforms.olvm.password,
                    ca_file=settings.platforms.olvm.ca_file,
                    insecure=settings.platforms.olvm.insecure
                ) as olvm_client:
                    try:
                        vm_info = olvm_client.get_vm(vm_name)
                        status = normalize_vminfo_power(vm_info)
                        return jsonify({
                            "success": True,
                            "vm_name": vm_name,
                            "status": status,
                            "source": "olvm",
                            "probe_status": status,
                            "probe_source": "olvm",
                            "dora_status": dora_reported_state
                        })
                    except ValueError:
                        pass
            except Exception as e:
                print(f"OLVM fallback probe failed for {vm_name}: {e}")

        # As a last resort, return Dora's reported state if available (normalized)
        if vm_data:
            raw_state = vm_data.get('state', None)
            status = normalize_vminfo_power(raw_state)
            return jsonify({"success": True, "vm_name": vm_name, "status": status, "source": "dora", "olvm_checked": olvm_configured})

        return jsonify({"success": False, "error": f"VM '{vm_name}' not found in Dora environment '{environment}'"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"Unexpected error: {str(e)}"}), 500


@app.route("/api/dora/vms-status", methods=["POST", "GET"])
def get_dora_vms_status():
    """Fetch Dora VM list for an environment and probe OLVM for real-time statuses.

    Returns a list of VMs with Dora's reported state and (when available) a live probe
    status from OLVM. Probes are executed in parallel to reduce latency.
    """
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.dora import DoraClient

        # Accept env either via JSON body or query param
        if request.method == 'POST':
            data = request.get_json() or {}
            environment = data.get('environment', 'Dev')
        else:
            environment = request.args.get('environment', 'Dev')

        settings = load_settings(None)

        olvm_configured = (
            hasattr(settings, 'platforms') and
            hasattr(settings.platforms, 'olvm') and
            bool(settings.platforms.olvm.url)
        )

        # Fetch Dora environment data
        dora_username = settings.platforms.dora.username
        dora_password = settings.platforms.dora.password
        dora_client = DoraClient(
            dora_host=settings.platforms.dora.host,
            api_port=settings.platforms.dora.api_port,
            auth_port=settings.platforms.dora.auth_port
        )

        env_data = dora_client.get_environment_data(
            environment=environment,
            username=dora_username,
            password=dora_password
        )

        vms_data = env_data.get('vms', {})
        if isinstance(vms_data, dict) and 'items' in vms_data:
            vms = vms_data['items']
        elif isinstance(vms_data, list):
            vms = vms_data
        else:
            vms = []

        # Helper to normalize power state strings/enums
        def normalize_power(raw):
            if raw is None:
                return 'unknown'
            rs = str(raw).strip().lower()
            if any(x in rs for x in ('poweredon', 'powered on', 'on', 'up', 'running', 'true')):
                return 'poweredOn'
            if any(x in rs for x in ('poweredoff', 'powered off', 'off', 'down', 'stopped', 'false')):
                return 'poweredOff'
            if any(x in rs for x in ('suspend', 'suspended', 'paused')):
                return 'suspended'
            return 'unknown'

        results = []

        # Build Dora-only normalized entries (used for fast responses)
        dora_only_results = []
        for vm in vms:
            name = vm.get('name') if isinstance(vm, dict) else str(vm)
            dora_only_results.append({
                'vm_name': name,
                'dora_status': normalize_power(vm.get('state') if isinstance(vm, dict) else None),
                'probe_status': None,
                'probe_source': None,
                'host': vm.get('host') if isinstance(vm, dict) else None
            })

        # If OLVM not configured, return Dora states only (normalized)
        if not olvm_configured:
            return jsonify({"success": True, "environment": environment, "count": len(dora_only_results), "vms": dora_only_results, "cached": False})

        # OLVM is configured. If Redis cache is enabled and empty, spawn background probe
        # to populate cache and return Dora-only results quickly instead of performing
        # synchronous OLVM probes on the request path.
        try:
            if cache.enabled:
                cached = cache.get(_dora_cache_key_for_env(environment))
                if cached:
                    # Ensure background updater is running
                    try:
                        _start_dora_background_updater(settings)
                    except Exception:
                        pass
                    return jsonify({"success": True, "environment": environment, "count": len(cached.get('vms', [])), "vms": cached.get('vms', [])})
                else:
                    # Spawn background worker to probe and cache results
                    try:
                        from threading import Thread
                        Thread(target=probe_and_cache_dora_env, args=(environment, settings), daemon=True).start()
                    except Exception:
                        pass
                    # Return Dora-only info quickly
                    return jsonify({"success": True, "environment": environment, "count": len(dora_only_results), "vms": dora_only_results, "cached": False})
        except Exception:
            # On any cache error, fall back to synchronous probing below
            pass

        # OLVM configured: probe VMs in parallel
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from chaosmonkey.platforms.olvm import OLVMPlatform

        # Build list of vm names and original Dora entries
        vm_entries = []
        for vm in vms:
            if isinstance(vm, dict):
                vm_entries.append({'name': vm.get('name'), 'dora': vm})
            else:
                vm_entries.append({'name': str(vm), 'dora': {}})

        # Use a single OLVM client for all probes (connect once)
        with OLVMPlatform(
            url=settings.platforms.olvm.url,
            username=settings.platforms.olvm.username,
            password=settings.platforms.olvm.password,
            ca_file=settings.platforms.olvm.ca_file,
            insecure=settings.platforms.olvm.insecure
        ) as olvm_client:

            def probe_entry(entry):
                name = entry['name']
                dora = entry['dora']
                try:
                    vm_info = olvm_client.get_vm(name)
                    status = normalize_power(getattr(vm_info, 'power_state', None))
                    # Extract additional fields for UI
                    def _get_attr(obj, *names):
                        for n in names:
                            try:
                                if isinstance(obj, dict) and n in obj:
                                    return obj.get(n)
                                if hasattr(obj, n):
                                    return getattr(obj, n)
                            except Exception:
                                continue
                        return None

                    cpu_val = _get_attr(vm_info, 'cpu_count', 'cpus', 'cpu', 'num_cpus', 'vcpus', 'numVcpus', 'vcpu_count')
                    mem_val = _get_attr(vm_info, 'memory_mb', 'memMb', 'memory_mb', 'mem', 'memory')
                    guest = _get_attr(vm_info, 'guest_os', 'guestOS', 'guest')
                    try:
                        if isinstance(mem_val, (int, float)) and mem_val > 0:
                            memory_str = f"{mem_val / 1024:.1f} GB"
                        else:
                            memory_str = str(mem_val) if mem_val is not None else None
                    except Exception:
                        memory_str = None

                    cpu_str = None
                    try:
                        if isinstance(cpu_val, (int, float)):
                            cpu_str = str(int(cpu_val))
                        elif isinstance(cpu_val, str) and cpu_val.strip():
                            cpu_str = cpu_val.strip()
                    except Exception:
                        cpu_str = None

                    return {'vm_name': name, 'dora_status': normalize_power(dora.get('state') if isinstance(dora, dict) else None), 'probe_status': status, 'probe_source': 'olvm', 'host': dora.get('host'), 'cpu': cpu_str, 'memory': memory_str, 'guest_os': guest}
                except Exception as e:
                    # Probe failed: return Dora state and probe error note
                    return {'vm_name': name, 'dora_status': normalize_power(dora.get('state') if isinstance(dora, dict) else None), 'probe_status': None, 'probe_source': 'olvm', 'host': dora.get('host'), 'probe_error': str(e)}

            with ThreadPoolExecutor(max_workers=10) as exe:
                futures = {exe.submit(probe_entry, e): e for e in vm_entries}
                for fut in as_completed(futures):
                    results.append(fut.result())

        return jsonify({"success": True, "environment": environment, "count": len(results), "vms": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dora/vms-status/job/start", methods=["POST"])
def start_vms_status_job():
    """Start a background job that probes OLVM for Dora VMs' statuses (OLVM only).

    Returns a job_id which can be polled for results.
    """
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.dora import DoraClient
        from chaosmonkey.platforms.olvm import OLVMPlatform

        data = request.get_json() or {}
        environment = data.get('environment', 'Dev')

        settings = load_settings(None)

        if not settings.platforms.olvm.url:
            return jsonify({"success": False, "error": "OLVM not configured"}), 400

        # Create job id and initial record
        job_id = uuid.uuid4().hex[:12]
        job_key = f"{JOB_KEY_PREFIX}{job_id}"
        _store_job(job_id, {"status": "pending", "created": datetime.utcnow().isoformat(), "environment": environment})

        # Start background worker thread (non-blocking)
        def worker():
            try:
                # Fetch Dora data
                dora_client = DoraClient(
                    dora_host=settings.platforms.dora.host,
                    api_port=settings.platforms.dora.api_port,
                    auth_port=settings.platforms.dora.auth_port
                )
                env_data = dora_client.get_environment_data(environment=environment, username=settings.platforms.dora.username, password=settings.platforms.dora.password)
                vms_data = env_data.get('vms', {})
                if isinstance(vms_data, dict) and 'items' in vms_data:
                    vms = vms_data['items']
                elif isinstance(vms_data, list):
                    vms = vms_data
                else:
                    vms = []

                # Prepare entries
                entries = []
                for vm in vms:
                    if isinstance(vm, dict):
                        entries.append({'name': vm.get('name'), 'dora': vm})
                    else:
                        entries.append({'name': str(vm), 'dora': {}})

                # Probe OLVM in parallel
                from concurrent.futures import ThreadPoolExecutor, as_completed
                with OLVMPlatform(
                    url=settings.platforms.olvm.url,
                    username=settings.platforms.olvm.username,
                    password=settings.platforms.olvm.password,
                    ca_file=settings.platforms.olvm.ca_file,
                    insecure=settings.platforms.olvm.insecure
                ) as olvm_client:

                    def probe(e):
                        name = e['name']
                        dora = e['dora']
                        try:
                            vm_info = olvm_client.get_vm(name)
                            st = 'poweredOn' if getattr(vm_info, 'power_state', None) and 'on' in str(getattr(vm_info, 'power_state')).lower() else 'poweredOff'
                            return {"vm_name": name, "dora_status": (dora.get('state') if isinstance(dora, dict) else None), "probe_status": st, "probe_source": "olvm", "host": dora.get('host')}
                        except Exception as e:
                            return {"vm_name": name, "dora_status": (dora.get('state') if isinstance(dora, dict) else None), "probe_status": None, "probe_source": "olvm", "host": dora.get('host'), "probe_error": str(e)}

                    results = []
                    with ThreadPoolExecutor(max_workers=10) as exe:
                        futures = {exe.submit(probe, e): e for e in entries}
                        for fut in as_completed(futures):
                            results.append(fut.result())

                # Store final job result
                _store_job(job_id, {"status": "finished", "finished": datetime.utcnow().isoformat(), "environment": environment, "count": len(results), "vms": results})
            except Exception as ex:
                _store_job(job_id, {"status": "error", "error": str(ex), "environment": environment})

        # Kick off worker in background
        from threading import Thread
        t = Thread(target=worker, daemon=True)
        t.start()

        return jsonify({"success": True, "job_id": job_id}), 202
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/dora/vms-status/job/<job_id>", methods=["GET"])
def get_vms_status_job(job_id: str):
    job = _get_job(job_id)
    if job is None:
        return jsonify({"success": False, "error": "job not found or cache disabled"}), 404
    return jsonify({"success": True, "job": job})


@app.route("/api/vm/power-on", methods=["POST"])
def vm_power_on():
    """Power on a VM using available platforms."""
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.vsphere import VSpherePlatform
        from chaosmonkey.platforms.olvm import OLVMPlatform
        
        data = request.json
        vm_name = data.get("vm_name")
        timeout = data.get("timeout", 300)
        
        if not vm_name:
            return jsonify({"success": False, "error": "vm_name required"}), 400
        
        settings = load_settings(None)
        errors = []
        
        # Try vSphere first
        try:
            with VSpherePlatform(
                server=settings.platforms.vsphere.server,
                username=settings.platforms.vsphere.username,
                password=settings.platforms.vsphere.password,
                insecure=settings.platforms.vsphere.insecure
            ) as platform:
                platform.power_on(vm_name, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' powered on via vSphere",
                    "platform": "vsphere"
                })
        except Exception as e:
            errors.append(f"vSphere: {str(e)}")
        
        # Try OLVM if vSphere failed
        try:
            with OLVMPlatform(
                url=settings.platforms.olvm.url,
                username=settings.platforms.olvm.username,
                password=settings.platforms.olvm.password,
                insecure=settings.platforms.olvm.insecure
            ) as platform:
                platform.power_on(vm_name, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' powered on via OLVM",
                    "platform": "olvm"
                })
        except Exception as e:
            errors.append(f"OLVM: {str(e)}")
        
        # Both failed
        return jsonify({
            "success": False,
            "error": f"Failed to power on VM on all platforms. Errors: {'; '.join(errors)}"
        }), 500
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/vm/power-off", methods=["POST"])
def vm_power_off():
    """Power off a VM using available platforms."""
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.vsphere import VSpherePlatform
        from chaosmonkey.platforms.olvm import OLVMPlatform
        
        data = request.json
        vm_name = data.get("vm_name")
        graceful = data.get("graceful", True)
        timeout = data.get("timeout", 300)
        
        if not vm_name:
            return jsonify({"success": False, "error": "vm_name required"}), 400
        
        settings = load_settings(None)
        errors = []
        
        # Try vSphere first
        try:
            with VSpherePlatform(
                server=settings.platforms.vsphere.server,
                username=settings.platforms.vsphere.username,
                password=settings.platforms.vsphere.password,
                insecure=settings.platforms.vsphere.insecure
            ) as platform:
                platform.power_off(vm_name, graceful=graceful, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' powered off via vSphere (graceful={graceful})",
                    "platform": "vsphere"
                })
        except Exception as e:
            errors.append(f"vSphere: {str(e)}")
        
        # Try OLVM if vSphere failed
        try:
            with OLVMPlatform(
                url=settings.platforms.olvm.url,
                username=settings.platforms.olvm.username,
                password=settings.platforms.olvm.password,
                insecure=settings.platforms.olvm.insecure
            ) as platform:
                platform.power_off(vm_name, graceful=graceful, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' powered off via OLVM (graceful={graceful})",
                    "platform": "olvm"
                })
        except Exception as e:
            errors.append(f"OLVM: {str(e)}")
        
        # Both failed
        return jsonify({
            "success": False,
            "error": f"Failed to power off VM on all platforms. Errors: {'; '.join(errors)}"
        }), 500
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/vm/reboot", methods=["POST"])
def vm_reboot():
    """Reboot a VM using available platforms."""
    try:
        from chaosmonkey.config import load_settings
        from chaosmonkey.platforms.vsphere import VSpherePlatform
        from chaosmonkey.platforms.olvm import OLVMPlatform
        
        data = request.json
        vm_name = data.get("vm_name")
        graceful = data.get("graceful", True)
        timeout = data.get("timeout", 300)
        
        if not vm_name:
            return jsonify({"success": False, "error": "vm_name required"}), 400
        
        settings = load_settings(None)
        errors = []
        
        # Try vSphere first
        try:
            with VSpherePlatform(
                server=settings.platforms.vsphere.server,
                username=settings.platforms.vsphere.username,
                password=settings.platforms.vsphere.password,
                insecure=settings.platforms.vsphere.insecure
            ) as platform:
                platform.reboot(vm_name, graceful=graceful, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' rebooted via vSphere (graceful={graceful})",
                    "platform": "vsphere"
                })
        except Exception as e:
            errors.append(f"vSphere: {str(e)}")
        
        # Try OLVM if vSphere failed
        try:
            with OLVMPlatform(
                url=settings.platforms.olvm.url,
                username=settings.platforms.olvm.username,
                password=settings.platforms.olvm.password,
                insecure=settings.platforms.olvm.insecure
            ) as platform:
                platform.reboot(vm_name, graceful=graceful, timeout=timeout)
                return jsonify({
                    "success": True,
                    "message": f"VM '{vm_name}' rebooted via OLVM (graceful={graceful})",
                    "platform": "olvm"
                })
        except Exception as e:
            errors.append(f"OLVM: {str(e)}")
        
        # Both failed
        return jsonify({
            "success": False,
            "error": f"Failed to reboot VM on all platforms. Errors: {'; '.join(errors)}"
        }), 500
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/targets")
def list_targets():
    """List chaos experiment targets."""
    chaos_type = request.args.get("chaos_type")
    
    try:
        # Import here to avoid circular imports
        from chaosmonkey.core.orchestrator import ChaosOrchestrator
        from chaosmonkey.config import load_settings
        
        config = load_settings(None)
        orchestrator = ChaosOrchestrator(config)
        
        # Get targets
        targets = orchestrator.enumerate_targets(chaos_type=chaos_type)
        
        # Convert to dict format with health endpoint information
        targets_list = [
            {
                "id": target.identifier,
                "name": target.attributes.get("name", target.identifier),
                "kind": target.kind,
                "node": target.attributes.get("node", "unknown"),
                "status": target.attributes.get("status", "unknown"),
                "address": target.attributes.get("address"),
                "port": target.attributes.get("port"),
                "health_endpoint": target.attributes.get("health_endpoint"),
            }
            for target in targets
        ]
        
        return jsonify({
            "success": True,
            "targets": targets_list,
            "count": len(targets_list)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/api/chaos-jobs")
def list_chaos_jobs():
    """List active chaos jobs."""
    status_filter = request.args.get("status")
    cmd = ["chaosmonkey", "chaos-jobs"]
    if status_filter:
        cmd.extend(["--status", status_filter])
    
    result = run_cli_command(cmd)
    return jsonify(result)


@app.route("/api/execute", methods=["POST"])
def execute_chaos():
    """Execute a chaos experiment."""
    data = request.json
    
    cmd = ["chaosmonkey", "execute"]
    
    if data.get("target_id"):
        cmd.extend(["--target-id", data["target_id"]])
    
    if data.get("chaos_type"):
        cmd.extend(["--chaos-type", data["chaos_type"]])
    
    if data.get("dry_run"):
        cmd.append("--dry-run")
    
    # Support for duration override
    if data.get("duration"):
        cmd.extend(["--duration", str(data["duration"])])
    
    # Support for network latency experiments
    if data.get("latency_ms"):
        cmd.extend(["--latency-ms", str(data["latency_ms"])])
    
    # Support for k6 load testing parameters
    if data.get("virtual_users"):
        cmd.extend(["--virtual-users", str(data["virtual_users"])])
    
    if data.get("target_url"):
        cmd.extend(["--target-url", data["target_url"]])
    
    if data.get("response_threshold"):
        cmd.extend(["--response-threshold", str(data["response_threshold"])])
    
    # Metrics collection support (enabled by default unless explicitly disabled)
    if data.get("collect_metrics") is False:
        cmd.append("--no-metrics")
    
    # Allow customizing metrics collection parameters
    if data.get("metrics_duration"):
        cmd.extend(["--metrics-duration", str(data["metrics_duration"])])
    
    if data.get("metrics_interval"):
        cmd.extend(["--metrics-interval", str(data["metrics_interval"])])
    
    # Debug: Log the command being executed
    print(f"🔍 Executing command: {' '.join(cmd)}")
    print(f"📊 Metrics settings: collect={data.get('collect_metrics', 'not set')}, duration={data.get('metrics_duration', 'default')}, interval={data.get('metrics_interval', 'default')}")
    
    result = run_cli_command(cmd)
    return jsonify(result)


@app.route("/api/node-operations")
def list_node_operations():
    """List all node drain/recover operations."""
    operation_type = request.args.get("type")  # Optional filter: 'drain' or 'recover'
    limit = int(request.args.get("limit", 100))
    
    operations = get_node_operations(operation_type, limit)
    return jsonify({
        "success": True,
        "operations": operations,
        "count": len(operations)
    })


@app.route("/api/reports")
def list_reports():
    """List all available reports."""
    reports = []
    
    for report_file in REPORTS_DIR.glob("run-*.json"):
        try:
            with open(report_file) as f:
                report_data = json.load(f)
                
                # Extract run_id from filename
                run_id = report_file.stem
                
                # Extract data from nested structure
                experiment = report_data.get("experiment", {})
                result = report_data.get("result", {})
                configuration = experiment.get("configuration", {})
                
                # Get chaos type from tags
                tags = experiment.get("tags", [])
                chaos_type = tags[0] if tags else "unknown"
                
                # Check for K6 web dashboard in activity outputs
                k6_dashboard = None
                run_activities = result.get("run", [])
                if run_activities:
                    for activity in run_activities:
                        activity_output = activity.get("output", {})
                        if activity_output.get("k6_web_dashboard"):
                            # Extract just the filename from the full path
                            dashboard_path = activity_output.get("k6_web_dashboard")
                            k6_dashboard = Path(dashboard_path).name if dashboard_path else None
                            break
                
                reports.append({
                    "run_id": run_id,
                    "chaos_type": chaos_type,
                    "status": result.get("status", "unknown"),
                    "started_at": result.get("start"),
                    "completed_at": result.get("end"),
                    "target_id": configuration.get("target_id"),
                    "has_markdown": (REPORTS_DIR / f"{report_file.stem}.md").exists(),
                    "has_html": (REPORTS_DIR / f"{report_file.stem}.html").exists(),
                    "k6_dashboard": k6_dashboard
                })
        except Exception as e:
            print(f"Error reading report {report_file}: {e}")
    
    # Sort reports by started_at timestamp, latest first (descending order)
    # Handle None values by putting them at the end
    reports.sort(
        key=lambda r: r.get("started_at") or "", 
        reverse=True
    )
    
    return jsonify({"reports": reports})


@app.route("/api/reports/<run_id>")
def get_report(run_id):
    """Get a specific report."""
    report_format = request.args.get("format", "json")
    
    if report_format == "json":
        report_file = REPORTS_DIR / f"{run_id}.json"
        if report_file.exists():
            with open(report_file) as f:
                return jsonify(json.load(f))
    elif report_format == "markdown":
        report_file = REPORTS_DIR / f"{run_id}.md"
        if report_file.exists():
            with open(report_file) as f:
                return jsonify({"content": f.read()})
    elif report_format == "html":
        report_file = REPORTS_DIR / f"{run_id}.html"
        if report_file.exists():
            with open(report_file) as f:
                return jsonify({"content": f.read()})
    
    return jsonify({"error": "Report not found"}), 404


@app.route("/api/chaos-types")
def list_chaos_types():
    """List available chaos types."""
    # Get templates directory relative to this file
    templates_dir = Path(__file__).parent.parent / "experiments" / "templates"
    chaos_types = []
    
    if not templates_dir.exists():
        return jsonify({"chaos_types": [], "error": f"Templates directory not found: {templates_dir}"})
    
    # Process all template files
    for template_file in templates_dir.glob("*.json"):
        if template_file.stem.startswith("generic_"):
            chaos_type = template_file.stem.replace("generic_", "")
        elif template_file.stem.startswith("k6_"):
            chaos_type = template_file.stem
        elif template_file.stem.startswith("olvm_") or template_file.stem.startswith("vsphere_"):
            chaos_type = template_file.stem
        else:
            chaos_type = template_file.stem
        
        # Read template to get description
        try:
            with open(template_file) as f:
                template_data = json.load(f)
                description = template_data.get("description", "")
        except Exception as e:
            description = f"Error reading template: {e}"
        
        chaos_types.append({
            "name": chaos_type,
            "display_name": chaos_type.replace("_", " ").title(),
            "description": description,
            "icon": get_chaos_icon(chaos_type)
        })
    
    return jsonify({"chaos_types": chaos_types})


def get_chaos_icon(chaos_type: str) -> str:
    """Get emoji icon for chaos type."""
    icons = {
        "cpu_hog": "🔥",
        "memory_hog": "💾",
        "network_latency": "🐌",
        "packet_loss": "📦",
        "host_down": "💀",
        "disk_io": "💿",
        "k6_load_test": "📈",
        "k6_spike_test": "⚡",
        "k6_stress_test": "💥",
        "k6_api_load_test": "🔗",
        "k6_database_test": "🗄️",
        "quick_stress_test": "⚡🚀",
        "quick_spike_test": "⚡💨",
        "olvm_vm_shutdown": "🔴",
        "olvm_vm_batch_shutdown": "🔴🔴",
        "vsphere_vm_poweroff": "🖥️",
        "vsphere_vm_reboot": "🔄"
    }
    return icons.get(chaos_type, "⚡")


@app.route("/api/node/drain", methods=["POST"])
def drain_node_endpoint():
    """Drain a Nomad node using NomadClient."""
    from ..core.nomad import NomadClient
    from ..config import load_settings
    
    data = request.json
    node_id = data.get("node_id")
    deadline = data.get("deadline", 300)  # Default 300 seconds
    
    if not node_id:
        return jsonify({"error": "node_id is required"}), 400
    
    try:
        # Load settings and initialize NomadClient
        settings = load_settings(None)
        client = NomadClient(
            address=settings.nomad.address,
            region=settings.nomad.region,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace
        )
        
        # Clean the node_id (remove "..." if present)
        clean_node_id = node_id.split("...")[0] if "..." in node_id else node_id
        
        # Use NomadClient's drain_node method
        success = client.drain_node(clean_node_id, deadline_seconds=deadline)
        
        if success:
            # Log the operation
            node_name = data.get("node_name", clean_node_id[:8])
            log_node_operation("drain", clean_node_id, node_name, {
                "success": True,
                "deadline_seconds": deadline
            })
            
            # Invalidate cache after draining
            invalidate_cache("nomad:clients:all")
            
            return jsonify({
                "success": True,
                "message": f"Node {clean_node_id} drain initiated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to drain node"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/node/batch-drain", methods=["POST"])
def batch_drain_nodes_endpoint():
    """Drain multiple Nomad nodes as a single batch operation."""
    from ..core.nomad import NomadClient
    from ..config import load_settings
    
    data = request.json
    node_ids = data.get("node_ids", [])
    deadline = data.get("deadline", 300)
    
    if not node_ids or not isinstance(node_ids, list):
        return jsonify({"error": "node_ids array is required"}), 400
    
    try:
        settings = load_settings(None)
        client = NomadClient(
            address=settings.nomad.address,
            region=settings.nomad.region,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace
        )
        
        results = []
        for node_info in node_ids:
            node_id = node_info.get("id")
            node_name = node_info.get("name", node_id[:8] if node_id else "unknown")
            clean_node_id = node_id.split("...")[0] if "..." in node_id else node_id
            
            try:
                success = client.drain_node(clean_node_id, deadline_seconds=deadline)
                results.append({
                    "node_id": clean_node_id,
                    "node_name": node_name,
                    "success": success
                })
            except Exception as e:
                results.append({
                    "node_id": clean_node_id,
                    "node_name": node_name,
                    "success": False,
                    "error": str(e)
                })
        
        # Log as a single batch operation
        log_batch_node_operation("drain", results, {
            "deadline_seconds": deadline,
            "total_nodes": len(node_ids)
        })
        
        invalidate_cache("nomad:clients:all")
        
        success_count = sum(1 for r in results if r["success"])
        return jsonify({
            "success": True,
            "message": f"Batch drain completed: {success_count}/{len(results)} successful",
            "results": results,
            "success_count": success_count,
            "total_count": len(results)
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/node/batch-recover", methods=["POST"])
def batch_recover_nodes_endpoint():
    """Recover multiple Nomad nodes as a single batch operation."""
    from ..core.nomad import NomadClient
    from ..config import load_settings
    
    data = request.json
    node_ids = data.get("node_ids", [])
    
    if not node_ids or not isinstance(node_ids, list):
        return jsonify({"error": "node_ids array is required"}), 400
    
    try:
        settings = load_settings(None)
        client = NomadClient(
            address=settings.nomad.address,
            region=settings.nomad.region,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace
        )
        
        results = []
        for node_info in node_ids:
            node_id = node_info.get("id")
            node_name = node_info.get("name", node_id[:8] if node_id else "unknown")
            clean_node_id = node_id.split("...")[0] if "..." in node_id else node_id
            
            try:
                success = client.recover_node(clean_node_id)
                results.append({
                    "node_id": clean_node_id,
                    "node_name": node_name,
                    "success": success
                })
            except Exception as e:
                results.append({
                    "node_id": clean_node_id,
                    "node_name": node_name,
                    "success": False,
                    "error": str(e)
                })
        
        # Log as a single batch operation
        log_batch_node_operation("recover", results, {
            "total_nodes": len(node_ids)
        })
        
        invalidate_cache("nomad:clients:all")
        
        success_count = sum(1 for r in results if r["success"])
        return jsonify({
            "success": True,
            "message": f"Batch recover completed: {success_count}/{len(results)} successful",
            "results": results,
            "success_count": success_count,
            "total_count": len(results)
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/node/eligibility", methods=["POST"])
def set_node_eligibility():
    """Enable or disable node eligibility using NomadClient."""
    from ..core.nomad import NomadClient
    from ..config import load_settings
    
    data = request.json
    node_id = data.get("node_id")
    enable = data.get("enable", True)
    
    if not node_id:
        return jsonify({"error": "node_id is required"}), 400
    
    try:
        # Load settings and initialize NomadClient
        settings = load_settings(None)
        client = NomadClient(
            address=settings.nomad.address,
            region=settings.nomad.region,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace
        )
        
        # Clean the node_id (remove "..." if present)
        clean_node_id = node_id.split("...")[0] if "..." in node_id else node_id
        
        if enable:
            # Use NomadClient's recover_node method to enable the node
            success = client.recover_node(clean_node_id)
            action = "enabled"
        else:
            # For disabling, we would need a new method or use drain
            # For now, just return an error as the UI only uses enable=True
            return jsonify({
                "success": False,
                "error": "Disabling nodes is not supported. Use drain instead."
            }), 400
        
        if success:
            # Log the operation
            node_name = data.get("node_name", clean_node_id[:8])
            log_node_operation("recover", clean_node_id, node_name, {
                "success": True
            })
            
            # Invalidate cache after recovery
            invalidate_cache("nomad:clients:all")
            
            return jsonify({
                "success": True,
                "message": f"Node {clean_node_id} {action} successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to {action} node"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/reports/<run_id>/html")
def get_html_report(run_id):
    """Get or generate HTML report for a specific run."""
    from ..core.report_html import generate_html_report
    
    # Check if HTML report already exists
    html_file = REPORTS_DIR / f"{run_id}.html"
    if html_file.exists():
        return send_from_directory(REPORTS_DIR, f"{run_id}.html", mimetype='text/html')
    
    # Generate HTML report from JSON data
    json_file = REPORTS_DIR / f"{run_id}.json"
    if not json_file.exists():
        return jsonify({"error": "Report not found"}), 404
    
    try:
        with open(json_file) as f:
            report_data = json.load(f)
        
        experiment = report_data.get("experiment", {})
        result = report_data.get("result", {})
        
        # Generate enhanced HTML report
        html_content = generate_html_report(run_id, experiment, result)
        
        # Save for future use
        html_file.write_text(html_content)
        
        # Return HTML directly
        from flask import Response
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        return jsonify({"error": f"Failed to generate HTML report: {str(e)}"}), 500


@app.route("/api/reports/<run_id>/download")
def download_report(run_id):
    """Download report in specified format (html or pdf)."""
    format_type = request.args.get("format", "html").lower()
    
    if format_type == "html":
        html_file = REPORTS_DIR / f"{run_id}.html"
        
        # Generate if doesn't exist
        if not html_file.exists():
            from ..core.report_html import generate_html_report
            json_file = REPORTS_DIR / f"{run_id}.json"
            
            if not json_file.exists():
                return jsonify({"error": "Report not found"}), 404
            
            try:
                with open(json_file) as f:
                    report_data = json.load(f)
                
                experiment = report_data.get("experiment", {})
                result = report_data.get("result", {})
                html_content = generate_html_report(run_id, experiment, result)
                html_file.write_text(html_content)
            except Exception as e:
                return jsonify({"error": f"Failed to generate HTML: {str(e)}"}), 500
        
        return send_from_directory(
            REPORTS_DIR, 
            f"{run_id}.html",
            as_attachment=True,
            download_name=f"chaos-report-{run_id}.html"
        )
    
    elif format_type == "pdf":
        from ..core.report_pdf import is_pdf_generation_available, generate_pdf_from_html
        from flask import Response
        
        if not is_pdf_generation_available():
            return jsonify({
                "error": "PDF generation not available. WeasyPrint is not installed."
            }), 503
        
        # Get or generate HTML first
        html_file = REPORTS_DIR / f"{run_id}.html"
        
        if not html_file.exists():
            from ..core.report_html import generate_html_report
            json_file = REPORTS_DIR / f"{run_id}.json"
            
            if not json_file.exists():
                return jsonify({"error": "Report not found"}), 404
            
            try:
                with open(json_file) as f:
                    report_data = json.load(f)
                
                experiment = report_data.get("experiment", {})
                result = report_data.get("result", {})
                html_content = generate_html_report(run_id, experiment, result)
                html_file.write_text(html_content)
            except Exception as e:
                return jsonify({"error": f"Failed to generate HTML: {str(e)}"}), 500
        
        try:
            # Generate PDF from HTML
            html_content = html_file.read_text()
            pdf_bytes = generate_pdf_from_html(html_content)
            
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': f'attachment; filename=chaos-report-{run_id}.pdf'
                }
            )
        except Exception as e:
            return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500
    
    else:
        return jsonify({"error": "Invalid format. Use 'html' or 'pdf'"}), 400


@app.route("/reports/<path:filename>")
def serve_report(filename):
    """Serve report files directly."""
    return send_from_directory(REPORTS_DIR, filename)


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """Clear Redis cache."""
    pattern = request.json.get("pattern", "*") if request.json else "*"
    
    if not cache.enabled:
        return jsonify({
            "success": False,
            "message": "Cache is not enabled"
        })
    
    count = invalidate_cache(pattern)
    return jsonify({
        "success": True,
        "message": f"Cleared {count} cache entries",
        "count": count
    })


@app.route("/api/cache/stats")
def cache_stats():
    """Get cache statistics."""
    if not cache.enabled:
        return jsonify({
            "enabled": False,
            "message": "Cache is not enabled"
        })
    
    try:
        # Get cache info
        info = cache._client.info("stats")
        keyspace = cache._client.info("keyspace")
        
        return jsonify({
            "enabled": True,
            "stats": {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "keys": keyspace
            }
        })
    except Exception as e:
        return jsonify({
            "enabled": True,
            "error": str(e)
        })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
