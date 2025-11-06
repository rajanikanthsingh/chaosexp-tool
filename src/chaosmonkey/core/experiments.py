"""Experiment template management."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .models import Target

TEMPLATE_INDEX = {
    # Nomad-based experiments
    "network-latency": "generic_network_latency.json",
    "network_latency": "generic_network_latency.json",
    "packet-loss": "generic_packet_loss.json",
    "packet_loss": "generic_packet_loss.json",
    "cpu-hog": "generic_cpu_hog.json",
    "cpu_hog": "generic_cpu_hog.json",
    "memory-hog": "generic_memory_hog.json",
    "memory_hog": "generic_memory_hog.json",
    "disk-io": "generic_disk_io.json",
    "disk_io": "generic_disk_io.json",
    # k6 load testing experiments
    "k6-load-test": "k6_load_test.json",
    "k6_load_test": "k6_load_test.json",
    "load-test": "k6_load_test.json",
    "load_test": "k6_load_test.json",
    "k6-spike-test": "k6_spike_test.json",
    "k6_spike_test": "k6_spike_test.json",
    "spike-test": "k6_spike_test.json",
    "spike_test": "k6_spike_test.json",
    "k6-stress-test": "k6_stress_test.json",
    "k6_stress_test": "k6_stress_test.json",
    "stress-test": "k6_stress_test.json",
    "stress_test": "k6_stress_test.json",
    # Quick versions for development/testing
    "k6-quick-stress-test": "k6_quick_stress_test.json",
    "k6_quick_stress_test": "k6_quick_stress_test.json",
    "quick-stress-test": "k6_quick_stress_test.json",
    "quick_stress_test": "k6_quick_stress_test.json",
    "k6-quick-spike-test": "k6_quick_spike_test.json",
    "k6_quick_spike_test": "k6_quick_spike_test.json",
    "quick-spike-test": "k6_quick_spike_test.json",
    "quick_spike_test": "k6_quick_spike_test.json",
    # Specialized k6 templates for Nomad services
    "k6-api-test": "k6_api_load_test.json",
    "k6_api_test": "k6_api_load_test.json",
    "k6-api-load-test": "k6_api_load_test.json",
    "k6_api_load_test": "k6_api_load_test.json",
    "api-test": "k6_api_load_test.json",
    "api_test": "k6_api_load_test.json",
    "k6-database-test": "k6_database_test.json",
    "k6_database_test": "k6_database_test.json",
    "database-test": "k6_database_test.json",
    "database_test": "k6_database_test.json",
    # VM platform templates
    "olvm-vm-shutdown": "olvm_vm_shutdown.json",
    "olvm-vm-batch-shutdown": "olvm_vm_batch_shutdown.json",
}

DEFAULT_TEMPLATE = "generic_cpu_hog.json"


class ExperimentTemplateRegistry:
    """Loads and renders Chaos Toolkit experiment templates."""

    def __init__(self, base_path: Optional[Union[Path, str]] = None) -> None:
        if base_path is None:
            traversable = resources.files("chaosmonkey.experiments") / "templates"
            self._base_path = Path(str(traversable))
        else:
            self._base_path = Path(base_path)

    def available_templates(self) -> Dict[str, Path]:
        return {
            chaos_type: self._base_path / filename
            for chaos_type, filename in TEMPLATE_INDEX.items()
        }

    def render(
        self,
        chaos_type: Optional[str],
        target: Optional[Target],
        target_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        template_path = self._resolve_template(chaos_type)
        document = json.loads(template_path.read_text())

        replacements = {
            # Common variables
            "target_id": target_id if target_id else (target.identifier if target else "unknown"),
            "target_kind": target.kind if target else "unknown",
            "target_node": target.attributes.get("node", "unknown") if target else "unknown",
            "duration_seconds": 120,  # Default duration
            # Nomad-specific variables
            "latency_ms": 250,  # Default latency
            "packet_loss_percentage": "15%",  # Default packet loss
            "memory_mb": 2048,  # Default memory to consume (2GB)
            "io_workers": 4,  # Default I/O workers
            "write_size_mb": 1024,  # Default write size (1GB per worker)
            # k6 load testing variables
            "target_url": self._build_target_url(target) if target else "http://localhost:8080",
            "health_endpoint": target.attributes.get("health_endpoint", "/monitoring/health") if target else "/monitoring/health",  # Health check endpoint path
            "k6_script_path": "",  # Path to external k6 script file
            "k6_script_text": "",  # Inline k6 script text
            "virtual_users": 10,  # Default number of virtual users
            "response_time_threshold": 500,  # Default response time threshold (ms)
            "base_users": 10,  # Base load for spike tests
            "spike_users": 100,  # Peak load for spike tests
            "ramp_up_users": 50,  # Ramp-up users for stress tests
            "max_users": 200,  # Maximum users for stress tests
            "stress_response_threshold": 2000,  # Relaxed threshold for stress tests (ms)
        }

        if overrides:
            replacements.update(overrides)

        # Set configuration at the top level for Chaos Toolkit variable substitution
        document.setdefault("configuration", {})
        document["configuration"].update(replacements)

        return document

    def _resolve_template(self, chaos_type: Optional[str]) -> Path:
        filename = TEMPLATE_INDEX.get(chaos_type or "", DEFAULT_TEMPLATE)
        path = self._base_path / filename
        if not path.exists():
            raise FileNotFoundError(f"Experiment template not found: {path}")
        return path

    def _build_target_url(self, target: Target) -> str:
        """Build a target URL for load testing from target attributes."""
        if target.kind in ["service", "system"]:
            # For Nomad services and system services, try to build URL from service info
            # Priority: explicit address > node IP > localhost fallback
            # NOTE: Avoid using service_name as it's often not resolvable from local machine
            address = target.attributes.get("address", "")
            node_name = target.attributes.get("node", "localhost")
            port = target.attributes.get("port", 8080)
            
            if address and address != "unknown" and not address.startswith("nomad-"):
                # Use explicit service address (actual IP or resolvable hostname)
                return f"http://{address}:{port}"
            elif node_name and node_name != "unknown" and node_name != "localhost":
                # Use node address (should be an IP or resolvable hostname)
                return f"http://{node_name}:{port}"
            else:
                # Fallback to localhost for local testing
                return f"http://localhost:{port}"
        else:
            # Default fallback for nodes
            return "http://localhost:8080"
