"""Core orchestration logic for chaos experiments."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

try:
    from chaoslib.experiment import run_experiment
except ImportError:  # pragma: no cover - optional dependency
    run_experiment = None  # type: ignore[misc,assignment]

from ..config import Settings
from .experiments import ExperimentTemplateRegistry
from .metrics import MetricsCollector
from .prometheus_metrics import PrometheusMetricsCollector
from .metrics_report import generate_metrics_html_report
from .models import ExperimentRun, Target
from .nomad import NomadClient
from .report_html import generate_html_report

try:
    from .kubernetes import KubernetesClient
except ImportError:
    KubernetesClient = None  # type: ignore[misc,assignment]


class ChaosOrchestrator:
    """Coordinates discovery, execution, and reporting."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._nomad = NomadClient(
            address=settings.nomad.address,
            region=settings.nomad.region,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace,
        )
        
        # Initialize Kubernetes client if available
        self._kubernetes = None
        if KubernetesClient is not None:
            try:
                self._kubernetes = KubernetesClient(
                    config_file=settings.kubernetes.config_file,
                    context=settings.kubernetes.context,
                    namespace=settings.kubernetes.namespace,
                    verify_ssl=settings.kubernetes.verify_ssl,
                )
            except Exception as e:
                print(f"Warning: Could not initialize Kubernetes client: {e}")
        
        # Initialize Prometheus metrics collector
        try:
            self._prometheus_metrics = PrometheusMetricsCollector(
                prometheus_url=settings.prometheus.url,
                timeout=settings.prometheus.timeout,
            )
        except Exception as e:
            print(f"Warning: Could not initialize Prometheus metrics collector: {e}")
            self._prometheus_metrics = None
        
        # Keep old metrics collector for backward compatibility (deprecated)
        nomad_client_for_metrics = self._nomad._client if self._nomad else None
        self._metrics = MetricsCollector(
            nomad_client=nomad_client_for_metrics,
            kubernetes_client=self._kubernetes,
        )
        
        self._templates = ExperimentTemplateRegistry(
            base_path=self._resolve_experiments_path(settings.chaos.experiments_path)
        )
        self._reports_path = (
            settings.chaos.reports_path
            if settings.chaos.reports_path.is_absolute()
            else Path.cwd() / settings.chaos.reports_path
        )
        self._reports_path.mkdir(parents=True, exist_ok=True)

    # Discovery -----------------------------------------------------------------
    def discover_environment(self, include_allocations: bool = False) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {"generated_at": datetime.now(UTC).isoformat()}
        
        # Discover Nomad services
        try:
            nomad_services = self._nomad.discover_services()
            snapshot["nomad"] = {"services": nomad_services}
            if include_allocations:
                snapshot["nomad"]["allocations"] = self._nomad.list_allocations()
        except Exception as e:
            snapshot["nomad"] = {"error": str(e)}
        
        # Discover Kubernetes resources
        if self._kubernetes:
            try:
                k8s_services = self._kubernetes.discover_services()
                k8s_deployments = self._kubernetes.discover_deployments()  
                k8s_pods = self._kubernetes.discover_pods()
                snapshot["kubernetes"] = {
                    "services": k8s_services,
                    "deployments": k8s_deployments,
                    "pods": k8s_pods,
                }
            except Exception as e:
                snapshot["kubernetes"] = {"error": str(e)}
        
        # Maintain backward compatibility
        snapshot["services"] = snapshot.get("nomad", {}).get("services", [])
        
        return snapshot

    # Targeting -----------------------------------------------------------------
    def enumerate_targets(self, chaos_type: Optional[str] = None) -> List[Target]:
        targets = []
        
        # Get Nomad targets
        try:
            nomad_targets = self._nomad.enumerate_targets()
            targets.extend(nomad_targets)
        except Exception as e:
            print(f"Warning: Could not get Nomad targets: {e}")
        
        # Get Kubernetes targets
        if self._kubernetes:
            try:
                k8s_targets = self._kubernetes.list_targets()
                targets.extend(k8s_targets)
            except Exception as e:
                print(f"Warning: Could not get Kubernetes targets: {e}")
        
        if chaos_type:
            # Normalize chaos_type to use underscores for comparison
            normalized_chaos_type = chaos_type.replace("-", "_")
            
            # Filter targets by chaos type compatibility
            filtered = [
                target
                for target in targets
                if normalized_chaos_type in [ct.replace("-", "_") for ct in self._suggested_chaos_types(target)]
            ]
            return filtered
        
        return targets

    def _suggested_chaos_types(self, target: Target) -> Iterable[str]:
        # Determine chaos types based on target kind and platform
        kind = target.kind.lower()
        
        # Check if this is a Kubernetes target (has namespace attribute)
        is_k8s_target = "namespace" in target.attributes
        
        if is_k8s_target:
            # Kubernetes-specific chaos types
            if kind == "service":
                return ["k8s_pod_failure", "k8s_network_partition", "k8s_resource_starvation"]
            elif kind == "deployment":
                return ["k8s_pod_failure", "k8s_scale_down", "k8s_resource_starvation"]
            elif kind == "pod":
                return ["k8s_pod_failure", "k8s_resource_starvation"]
        else:
            # Nomad-specific chaos types
            if kind == "service":
                return [
                    "host_down", "network_latency", "packet_loss", "cpu_hog", "memory_hog", "disk_io",
                    # K6 load testing chaos types
                    "k6_load_test", "k6_spike_test", "k6_stress_test", "k6_quick_stress_test", "k6_quick_spike_test", "k6_api_load_test", "k6_database_test"
                ]
            elif kind == "node":
                return [
                    "host_down", "network_latency", "packet_loss", "cpu_hog", "memory_hog", "disk_io",
                    # K6 load testing chaos types also work on nodes
                    "k6_load_test", "k6_spike_test", "k6_stress_test", "k6_quick_stress_test", "k6_quick_spike_test", "k6_api_load_test", "k6_database_test"
                ]
        
        return ["host_down"]

    # Execution -----------------------------------------------------------------
    def run_experiment(
        self,
        target_id: Optional[str],
        chaos_type: Optional[str],
        experiment_path: Optional[Path],
        dry_run: bool,
        output_path: Optional[Path],
        overrides: Optional[Dict[str, Any]] = None,
        collect_metrics: bool = True,
        metrics_duration: int = 60,
        metrics_interval: int = 5,
    ) -> ExperimentRun:
        targets = self.enumerate_targets(chaos_type=chaos_type)
        
        # Handle multiple targets (comma-separated)
        if target_id and "," in target_id:
            target_ids = [tid.strip() for tid in target_id.split(",")]
            selected_targets = self._select_multiple_targets(target_ids, targets)
            if not selected_targets:
                raise ValueError(f"None of the specified targets found: {target_id}")
            
            # Run experiment for each target (sequentially for now)
            results = []
            for target in selected_targets:
                print(f"\n🎯 Running chaos on target: {target.identifier} ({target.attributes.get('name', 'unknown')})")
                result = self._run_single_experiment(
                    target=target,
                    chaos_type=chaos_type,
                    experiment_path=experiment_path,
                    dry_run=dry_run,
                    output_path=None,  # Don't write individual outputs
                    overrides=overrides,
                    collect_metrics=collect_metrics,
                    metrics_duration=metrics_duration,
                    metrics_interval=metrics_interval,
                )
                results.append(result)
            
            # Return a consolidated result (use first one for now)
            # TODO: Enhance to create a multi-target report
            if output_path and results:
                output_path.write_text(json.dumps(results[0].to_dict(), indent=2))
            return results[0]
        
        else:
            target = self._select_target(target_id, targets)
            return self._run_single_experiment(
                target=target,
                chaos_type=chaos_type,
                experiment_path=experiment_path,
                dry_run=dry_run,
                output_path=output_path,
                overrides=overrides,
                collect_metrics=collect_metrics,
                metrics_duration=metrics_duration,
                metrics_interval=metrics_interval,
            )

    def _run_single_experiment(
        self,
        target: Optional[Target],
        chaos_type: Optional[str],
        experiment_path: Optional[Path],
        dry_run: bool,
        output_path: Optional[Path],
        overrides: Optional[Dict[str, Any]],
        collect_metrics: bool,
        metrics_duration: int,
        metrics_interval: int,
    ) -> ExperimentRun:
        run_id = f"run-{uuid4().hex[:8]}"
        started_at = datetime.now(UTC)

        if experiment_path:
            experiment_doc = json.loads(Path(experiment_path).read_text())
        else:
            experiment_doc = self._templates.render(
                chaos_type=chaos_type,
                target=target,
                overrides=overrides,
            )

        # Collect metrics before experiment
        before_metrics = None
        during_metrics = []
        after_metrics = None
        metrics_comparison = None
        
        if collect_metrics and not dry_run and target:
            print(f"📊 Collecting baseline metrics for {target.identifier}...")
            before_metrics = self._collect_target_metrics(target, label="before")
        
        # Execute experiment
        output = self._execute_experiment_document(experiment_doc, dry_run=dry_run)
        
        # Collect metrics during experiment (if still running)
        if collect_metrics and not dry_run and target:
            print(f"📊 Collecting metrics during chaos (duration: {metrics_duration}s, interval: {metrics_interval}s)...")
            
            # Use Prometheus for node targets, otherwise use old collector
            target_kind = target.kind.lower()
            if target_kind == "node" and self._prometheus_metrics:
                # Collect continuous metrics from Prometheus for nodes
                during_metrics = []
                iterations = metrics_duration // metrics_interval
                node_name = target.attributes.get('name', target.identifier)
                
                # Extract short hostname if FQDN
                if "." in node_name:
                    node_name = node_name.split(".")[0]
                
                for i in range(iterations):
                    snapshot = self._prometheus_metrics.collect_node_metrics(node_name=node_name)
                    snapshot["label"] = f"during_{i}"
                    during_metrics.append(snapshot)
                    
                    if i < iterations - 1:  # Don't sleep after last iteration
                        import time
                        time.sleep(metrics_interval)
            else:
                # Fall back to old collector for other target types
                during_metrics = self._metrics.collect_continuous_metrics(
                    target_type=target.kind.lower(),
                    target_id=target.identifier,
                    duration_seconds=metrics_duration,
                    interval_seconds=metrics_interval,
                    label="during"
                )
        
        # Collect metrics after experiment
        if collect_metrics and not dry_run and target:
            print(f"📊 Collecting post-chaos metrics for {target.identifier}...")
            after_metrics = self._collect_target_metrics(target, label="after")
            
            # Compare metrics
            if before_metrics and after_metrics:
                metrics_comparison = self._metrics.compare_metrics(
                    before=before_metrics,
                    during=during_metrics,
                    after=after_metrics
                )

        completed_at = datetime.now(UTC)
        status = "dry-run" if dry_run else output.get("status", "completed")

        report_record = ExperimentRun(
            run_id=run_id,
            chaos_type=chaos_type or "unspecified",
            target_id=target.identifier if target else None,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            report_path=self._write_run_artifacts(
                run_id, 
                experiment_doc, 
                output, 
                metrics_comparison
            ),
            metadata={
                "dry_run": str(dry_run).lower(),
                "metrics_collected": str(collect_metrics).lower(),
            },
        )

        if output_path:
            output_path.write_text(json.dumps(report_record.to_dict(), indent=2))

        return report_record
    
    def _collect_target_metrics(self, target: Target, label: str) -> Optional[Dict[str, Any]]:
        """Collect metrics for a target based on its kind."""
        try:
            target_kind = target.kind.lower()
            
            # Use Prometheus for node metrics if available
            if target_kind == "node" and self._prometheus_metrics:
                # Get node name from target
                node_name = target.attributes.get('name', target.identifier)
                
                # Extract short hostname if FQDN
                if "." in node_name:
                    node_name = node_name.split(".")[0]
                
                print(f"📊 Collecting {label} metrics from Prometheus for node: {node_name}")
                metrics = self._prometheus_metrics.collect_node_metrics(node_name=node_name)
                
                # Add label and return
                metrics["label"] = label
                return metrics
            
            # Fall back to old Nomad-based metrics collector for other types
            if target_kind == "allocation":
                return self._metrics.collect_nomad_allocation_metrics(
                    allocation_id=target.identifier,
                    label=label
                )
            elif target_kind == "job":
                return self._metrics.collect_nomad_job_metrics(
                    job_id=target.identifier,
                    label=label
                )
            elif target_kind == "node":
                # Fallback to Nomad metrics if Prometheus not available
                return self._metrics.collect_node_metrics(
                    node_id=target.identifier,
                    label=label
                )
            elif target_kind == "service":
                # For services, try to get the allocation from attributes
                # Services may have allocation_id in attributes
                if "allocation_id" in target.attributes:
                    return self._metrics.collect_nomad_allocation_metrics(
                        allocation_id=target.attributes["allocation_id"],
                        label=label
                    )
                else:
                    print(f"⚠️  Service target {target.identifier} has no allocation_id, skipping metrics")
                    return None
            else:
                print(f"⚠️  Unknown target kind {target_kind}, skipping metrics collection")
                return None
                
        except Exception as e:
            print(f"⚠️  Failed to collect {label} metrics: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _select_target(self, target_id: Optional[str], targets: List[Target]) -> Optional[Target]:
        if target_id:
            for candidate in targets:
                if candidate.identifier == target_id:
                    return candidate
                # Also match by name attribute (hostname for nodes)
                if candidate.attributes.get('name') == target_id:
                    return candidate
            raise ValueError(f"Target {target_id} not found in catalog")
        return targets[0] if targets else None

    def _select_multiple_targets(self, target_ids: List[str], targets: List[Target]) -> List[Target]:
        """Select multiple targets by their IDs."""
        selected = []
        for target_id in target_ids:
            for candidate in targets:
                if candidate.identifier == target_id:
                    selected.append(candidate)
                    break
        return selected

    def _execute_experiment_document(
        self,
        experiment: Dict[str, Any],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        if dry_run or run_experiment is None:
            return {"status": "skipped", "reason": "dry-run or chaoslib unavailable"}

        result = run_experiment(experiment)
        return result  # type: ignore[return-value]

    # Reporting -----------------------------------------------------------------
    def _write_run_artifacts(
        self,
        run_id: str,
        experiment_doc: Dict[str, Any],
        output: Dict[str, Any],
        metrics_comparison: Optional[Dict[str, Any]] = None,
    ) -> Path:
        # Write main report with experiment and result
        report_data = {
            "experiment": experiment_doc,
            "result": output,
        }
        
        # Add metrics if available
        if metrics_comparison:
            report_data["metrics"] = metrics_comparison
        
        metadata_path = self._reports_path / f"{run_id}.json"
        metadata_path.write_text(json.dumps(report_data, indent=2))
        
        # Generate markdown summary
        markdown_path = self._reports_path / f"{run_id}.md"
        markdown_path.write_text(
            _render_markdown_summary(run_id, experiment_doc, output, metrics_comparison)
        )
        
        # Generate HTML report with metrics visualization
        html_path = self._reports_path / f"{run_id}.html"
        if metrics_comparison:
            html_content = generate_metrics_html_report(
                run_id, experiment_doc, output, metrics_comparison
            )
        else:
            html_content = generate_html_report(run_id, experiment_doc, output)
        html_path.write_text(html_content)
        
        print(f"📄 Reports generated:")
        print(f"   - JSON: {metadata_path}")
        print(f"   - Markdown: {markdown_path}")
        print(f"   - HTML: {html_path}")
        
        return markdown_path

    def generate_report(self, run_id: Optional[str], output_format: str = "markdown") -> Any:
        run_id = run_id or self._latest_run_id()
        if run_id is None:
            raise FileNotFoundError("No experiment runs found. Execute an experiment first.")

        json_path = self._reports_path / f"{run_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Run metadata not found for {run_id}")

        payload = json.loads(json_path.read_text())
        experiment = payload.get("experiment", {})
        result = payload.get("result", {})
        metrics = payload.get("metrics")
        
        if output_format.lower() == "json":
            return payload
        
        if output_format.lower() == "html":
            html_path = self._reports_path / f"{run_id}.html"
            
            # Generate HTML with metrics if available
            if metrics:
                html_content = generate_metrics_html_report(run_id, experiment, result, metrics)
            else:
                html_content = generate_html_report(run_id, experiment, result)
            
            html_path.write_text(html_content)
            return html_content

        markdown_path = self._reports_path / f"{run_id}.md"
        if markdown_path.exists():
            return markdown_path.read_text()

        markdown_content = _render_markdown_summary(run_id, experiment, result, metrics)
        markdown_path.write_text(markdown_content)
        return markdown_content

    def _latest_run_id(self) -> Optional[str]:
        candidates = sorted(self._reports_path.glob("run-*.json"), reverse=True)
        if not candidates:
            return None
        return candidates[0].stem

    def _resolve_experiments_path(self, base_path: Path) -> Optional[Path]:
        if base_path.is_absolute():
            return base_path

        candidate = Path.cwd() / base_path
        if candidate.exists():
            return candidate

        return None


def _render_markdown_summary(
    run_id: str, 
    experiment: Dict[str, Any], 
    result: Dict[str, Any],
    metrics_comparison: Optional[Dict[str, Any]] = None
) -> str:
    config = experiment.get("configuration", {})
    target = config.get("target_id", "unknown")
    chaos_type = ", ".join(experiment.get("tags", [])) or experiment.get("title", "Unknown")
    status = result.get("status", "unknown")
    reason = result.get("reason", "")
    
    # Status emoji mapping
    status_emoji = {
        "completed": "✅",
        "succeeded": "✅",
        "failed": "❌",
        "aborted": "⚠️",
        "interrupted": "🛑",
        "unknown": "❓"
    }
    
    # Chaos type emoji mapping
    chaos_emoji = {
        "cpu-hog": "🔥",
        "memory-hog": "💾",
        "network-latency": "🌐",
        "packet-loss": "📡",
        "disk-io": "💿",
        "host-down": "💥",
        "node-drain": "🔌"
    }
    
    # Get primary chaos type for emoji
    primary_type = experiment.get("tags", ["unknown"])[0] if experiment.get("tags") else "unknown"
    type_emoji = chaos_emoji.get(primary_type, "⚡")
    stat_emoji = status_emoji.get(status, "❓")
    
    # Calculate duration
    start_time = result.get("start", "")
    end_time = result.get("end", "")
    duration = result.get("duration", 0)
    
    # Format timestamps
    from datetime import datetime
    start_dt = datetime.fromisoformat(start_time.replace("+00:00", "")) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace("+00:00", "")) if end_time else None
    
    lines = [
        f"# {type_emoji} Chaos Engineering Report",
        "",
        f"## 📋 Experiment Information",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| **Run ID** | `{run_id}` |",
        f"| **Chaos Type** | {chaos_type} |",
        f"| **Target** | `{target}` |",
        f"| **Status** | {stat_emoji} **{status.upper()}** |",
    ]
    
    if start_dt:
        lines.append(f"| **Started** | {start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} |")
    if end_dt:
        lines.append(f"| **Completed** | {end_dt.strftime('%Y-%m-%d %H:%M:%S UTC')} |")
    if duration:
        lines.append(f"| **Duration** | {duration:.2f}s |")
    
    if reason:
        lines.append(f"| **Details** | {reason} |")
    
    # Configuration section
    lines.extend([
        "",
        "## ⚙️ Configuration Parameters",
        "",
    ])
    
    if config:
        lines.append("| Parameter | Value |")
        lines.append("|-----------|-------|")
        for key, value in config.items():
            if key not in ["target_id"]:  # Already shown above
                lines.append(f"| `{key}` | `{value}` |")
    
    # Execution details
    lines.extend([
        "",
        "## 🎯 Execution Results",
        "",
    ])
    
    run_activities = result.get("run", [])
    if run_activities:
        for idx, activity in enumerate(run_activities, 1):
            activity_name = activity.get("activity", {}).get("name", "Unknown Activity")
            activity_status = activity.get("status", "unknown")
            activity_duration = activity.get("duration", 0)
            activity_output = activity.get("output", {})
            activity_emoji = status_emoji.get(activity_status, "❓")
            
            lines.extend([
                f"### Activity {idx}: {activity_name}",
                "",
                f"**Status:** {activity_emoji} {activity_status}",
                "",
                f"**Duration:** {activity_duration:.2f}s",
                "",
            ])
            
            if activity_output:
                lines.append("**Output:**")
                lines.append("")
                
                # Pretty print key information
                if isinstance(activity_output, dict):
                    # Check for node drain specific output
                    if "node_name" in activity_output:
                        lines.extend([
                            "| Property | Value |",
                            "|----------|-------|",
                            f"| 🖥️ **Node Name** | `{activity_output.get('node_name')}` |",
                            f"| 🆔 **Node ID** | `{activity_output.get('node_id', 'N/A')}` |",
                            f"| 📍 **Datacenter** | `{activity_output.get('datacenter', 'N/A')}` |",
                            f"| ⏱️ **Drain Deadline** | {activity_output.get('drain_deadline_seconds', 'N/A')}s |",
                            f"| 📦 **Affected Allocations** | {activity_output.get('affected_allocations', 0)} |",
                            f"| 🚦 **Scheduling** | {activity_output.get('scheduling_eligibility', 'N/A')} |",
                            "",
                        ])
                        
                        message = activity_output.get('message', '')
                        if message:
                            lines.append(f"> ℹ️ {message}")
                            lines.append("")
                        
                        recovery_cmd = activity_output.get('recovery_command', '')
                        if recovery_cmd:
                            lines.extend([
                                "**🔧 Recovery Command:**",
                                "",
                                "```bash",
                                recovery_cmd,
                                "```",
                                "",
                            ])
                    else:
                        # Generic output formatting
                        lines.append("```json")
                        lines.append(json.dumps(activity_output, indent=2))
                        lines.append("```")
                        lines.append("")
                else:
                    lines.append(f"`{activity_output}`")
                    lines.append("")
    else:
        lines.append("*No activities executed*")
        lines.append("")
    
    # Rollbacks section
    rollbacks = result.get("rollbacks", [])
    if rollbacks:
        lines.extend([
            "",
            "## 🔄 Rollback Actions",
            "",
        ])
        for idx, rollback in enumerate(rollbacks, 1):
            lines.append(f"### Rollback {idx}")
            lines.append("```json")
            lines.append(json.dumps(rollback, indent=2))
            lines.append("```")
            lines.append("")
    
    # Steady state section
    steady_states = result.get("steady_states", {})
    if steady_states and (steady_states.get("before") or steady_states.get("after")):
        lines.extend([
            "",
            "## 📊 Steady State Validation",
            "",
        ])
        
        if steady_states.get("before"):
            lines.extend([
                "### Before Experiment",
                "```json",
                json.dumps(steady_states["before"], indent=2),
                "```",
                "",
            ])
        
        if steady_states.get("after"):
            lines.extend([
                "### After Experiment",
                "```json",
                json.dumps(steady_states["after"], indent=2),
                "```",
                "",
            ])
    
    # Metrics comparison section
    if metrics_comparison:
        lines.extend([
            "",
            "## 📈 Metrics Comparison Report",
            "",
        ])
        
        analysis = metrics_comparison.get("analysis", {})
        
        # CPU Analysis
        if "cpu" in analysis:
            cpu = analysis["cpu"]
            lines.extend([
                "### CPU Usage",
                "",
                "| Phase | CPU % |",
                "|-------|-------|",
                f"| **Before Chaos** | {cpu.get('before_percent', 0):.2f}% |",
                f"| **Peak During Chaos** | {cpu.get('peak_during_percent', 0):.2f}% |",
                f"| **After Chaos** | {cpu.get('after_percent', 0):.2f}% |",
                "",
                f"**Change During Chaos:** {cpu.get('change_during', 0):+.2f}%",
                "",
                f"**Recovery Status:** {'✅ Recovered' if cpu.get('recovered', False) else '⚠️ Not fully recovered'}",
                "",
            ])
        
        # Memory Analysis
        if "memory" in analysis:
            mem = analysis["memory"]
            before_mb = mem.get('before_bytes', 0) / (1024 * 1024)
            peak_mb = mem.get('peak_during_bytes', 0) / (1024 * 1024)
            after_mb = mem.get('after_bytes', 0) / (1024 * 1024)
            change_mb = mem.get('change_during_bytes', 0) / (1024 * 1024)
            
            lines.extend([
                "### Memory Usage",
                "",
                "| Phase | Memory (MB) |",
                "|-------|-------------|",
                f"| **Before Chaos** | {before_mb:.2f} MB |",
                f"| **Peak During Chaos** | {peak_mb:.2f} MB |",
                f"| **After Chaos** | {after_mb:.2f} MB |",
                "",
                f"**Change During Chaos:** {change_mb:+.2f} MB",
                "",
                f"**Recovery Status:** {'✅ Recovered' if mem.get('recovered', False) else '⚠️ Not fully recovered'}",
                "",
            ])
        
        # Status Analysis
        if "status" in analysis:
            status_info = analysis["status"]
            lines.extend([
                "### Status Stability",
                "",
                f"**Before:** {status_info.get('before', 'unknown')}",
                "",
                f"**After:** {status_info.get('after', 'unknown')}",
                "",
                f"**Stable:** {'✅ Yes' if status_info.get('stable', False) else '⚠️ No'}",
                "",
            ])
        
        # Timeline visualization
        during_snapshots = metrics_comparison.get("during", [])
        if during_snapshots and len(during_snapshots) > 1:
            lines.extend([
                "### Metrics Timeline",
                "",
                "```",
            ])
            
            # Create simple ASCII chart for CPU
            has_cpu = any("cpu" in s for s in during_snapshots)
            if has_cpu:
                lines.append("CPU Usage During Chaos:")
                for i, snapshot in enumerate(during_snapshots):
                    if "cpu" in snapshot:
                        cpu_pct = snapshot["cpu"].get("percent", 0)
                        bar_len = int(cpu_pct / 2)  # Scale to 50 chars max
                        bar = "█" * bar_len
                        lines.append(f"  {i*5:3d}s: {bar} {cpu_pct:.1f}%")
            
            lines.extend([
                "```",
                "",
            ])
    
    # Summary section
    lines.extend([
        "",
        "---",
        "",
        "## 📝 Summary",
        "",
    ])
    
    deviated = result.get("deviated", False)
    if deviated:
        lines.append("⚠️ **System deviated from steady state during experiment**")
    else:
        lines.append("✅ **System remained within expected steady state**")
    
    lines.extend([
        "",
        f"Platform: `{result.get('platform', 'Unknown')}`",
        f"Node: `{result.get('node', 'Unknown')}`",
        f"ChaosLib Version: `{result.get('chaoslib-version', 'Unknown')}`",
        "",
        "---",
        "",
        "*Generated by ChaosMonkey CLI*",
    ])

    return "\n".join(lines)
