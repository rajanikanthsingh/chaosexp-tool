"""Command-line interface for ChaosMonkey."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Settings, load_settings
from .core.orchestrator import ChaosOrchestrator

app = typer.Typer(help="Nomad-driven Chaos Toolkit orchestration CLI")
console = Console(color_system=None, force_terminal=False, highlight=False)

# Global state for CLI runtime overrides
_cli_overrides = {}


def _build_orchestrator(config_path: Optional[Path]) -> ChaosOrchestrator:
    settings: Settings = load_settings(config_path)
    
    # Apply CLI overrides if any
    if "prometheus_url" in _cli_overrides:
        settings.prometheus.url = _cli_overrides["prometheus_url"]
    
    return ChaosOrchestrator(settings=settings)


def _discover_nomad_clients(config_path: Optional[Path]) -> None:
    """Discover and display all Nomad client nodes."""
    import os
    from urllib.parse import urlparse
    
    try:
        import nomad
    except ImportError:
        console.print("[error] python-nomad is required but not installed")
        raise typer.Exit(1)
    
    # Get Nomad connection details from environment or config
    settings = load_settings(config_path)
    addr = settings.nomad.address
    parsed = urlparse(addr)
    
    try:
        client = nomad.Nomad(
            host=parsed.hostname,
            port=parsed.port or 4646,
            token=settings.nomad.token,
            namespace=settings.nomad.namespace
        )
        
        # Get all nodes
        nodes = client.nodes.get_nodes()
        
        if not nodes:
            console.print("[yellow]No Nomad client nodes found[/yellow]")
            return
        
        # Create a detailed table
        table = Table(title="Nomad Client Nodes", show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Datacenter", style="green")
        table.add_column("Node Class", style="yellow")
        table.add_column("CPU", style="blue", justify="right")
        table.add_column("Memory", style="blue", justify="right")
        table.add_column("Drain", style="red")
        table.add_column("Allocations", style="cyan", justify="right")
        
        for node in sorted(nodes, key=lambda x: x.get("Name", "")):
            node_id = node.get("ID", "unknown")
            node_name = node.get("Name", "unknown")
            status = node.get("Status", "unknown")
            datacenter = node.get("Datacenter", "unknown")
            node_class = node.get("NodeClass", "-")
            drain = "Yes" if node.get("Drain", False) else "No"
            
            # Get detailed node info for resources
            try:
                node_detail = client.node.get_node(node_id)
                
                # Try different resource fields
                resources = node_detail.get("Resources", {})
                node_resources = node_detail.get("NodeResources", {})
                
                # CPU from Resources or NodeResources
                cpu_mhz = resources.get("CPU", 0)
                if not cpu_mhz and node_resources:
                    cpu_info = node_resources.get("Cpu", {})
                    cpu_mhz = cpu_info.get("CpuShares", 0)
                
                # Memory from Resources or NodeResources
                memory_mb = resources.get("MemoryMB", 0)
                if not memory_mb and node_resources:
                    mem_info = node_resources.get("Memory", {})
                    memory_mb = mem_info.get("MemoryMB", 0)
                
                # Format resources nicely
                cpu_str = f"{cpu_mhz:,} MHz" if cpu_mhz else "-"
                memory_gb = memory_mb / 1024 if memory_mb else 0
                memory_str = f"{memory_gb:.1f} GB" if memory_mb else "-"
                
                # Get allocation count
                node_allocs = client.node.get_allocations(node_id)
                running_allocs = len([a for a in node_allocs if a.get("ClientStatus") == "running"])
                alloc_str = str(running_allocs)
            except Exception as e:
                console.print(f"[dim]Warning: Could not get details for {node_name}: {e}[/dim]")
                cpu_str = "-"
                memory_str = "-"
                alloc_str = "-"
            
            # Color code status
            if status == "ready":
                status_display = f"[green]{status}[/green]"
            elif status == "down":
                status_display = f"[red]{status}[/red]"
            else:
                status_display = f"[yellow]{status}[/yellow]"
            
            # Color code drain status
            drain_display = f"[red]{drain}[/red]" if drain == "Yes" else f"[green]{drain}[/green]"
            
            table.add_row(
                node_name,
                node_id[:8] + "...",  # Truncate ID for readability
                status_display,
                datacenter,
                node_class or "-",
                cpu_str,
                memory_str,
                drain_display,
                alloc_str
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(nodes)} client node(s)[/dim]")
        
        # Show summary statistics
        ready_nodes = len([n for n in nodes if n.get("Status") == "ready"])
        drained_nodes = len([n for n in nodes if n.get("Drain", False)])
        
        console.print(f"[dim]Ready: {ready_nodes} | Drained: {drained_nodes}[/dim]")
        
    except Exception as e:
        console.print(f"[error] Failed to discover Nomad clients: {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def discover(
    config: Optional[Path] = typer.Option(None, "--config", "-c", exists=True, help="Config file"),
    allocations: bool = typer.Option(
        False,
        "--allocations/--no-allocations",
        help="Include Nomad allocation details in discovery output",
    ),
    clients: bool = typer.Option(
        False,
        "--clients",
        help="Show Nomad client nodes instead of services",
    ),
    platform: Optional[str] = typer.Option(
        None,
        "--platform",
        "-p",
        help="Specify platform: 'nomad', 'kubernetes', or 'all' (default: all)",
    ),
) -> None:
    """Discover the current environment via service discovery."""
    if clients:
        _discover_nomad_clients(config)
        return
    
    orchestrator = _build_orchestrator(config)
    snapshot = orchestrator.discover_environment(include_allocations=allocations)
    console.print_json(data=snapshot)


@app.command()
def targets(
    config: Optional[Path] = typer.Option(None, "--config", "-c", exists=True, help="Config file"),
    chaos_type: Optional[str] = typer.Option(None, "--chaos-type", "-t", help="Filter by chaos type"),
    platform: Optional[str] = typer.Option(
        None,
        "--platform",
        "-p",
        help="Specify platform: 'nomad', 'kubernetes', or 'all' (default: all)",
    ),
) -> None:
    """List potential targets for chaos experiments."""
    orchestrator = _build_orchestrator(config)
    target_catalog = orchestrator.enumerate_targets(chaos_type=chaos_type)

    table = Table(title="Candidate Targets")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Attributes", style="green")

    for item in target_catalog:
        attributes = ", ".join(f"{key}={value}" for key, value in item.attributes.items())
        table.add_row(item.identifier, item.kind, attributes or "-")

    console.print(table)


@app.command()
def execute(
    config: Optional[Path] = typer.Option(None, "--config", "-c", exists=True, help="Config file"),
    experiment: Optional[Path] = typer.Option(
        None,
        "--experiment",
        "-e",
        help="Path to a Chaos Toolkit experiment file; if omitted, a template is used",
    ),
    target_id: Optional[str] = typer.Option(
        None,
        "--target-id",
        "-i",
        help="Identifier of the target to exercise",
    ),
    chaos_type: Optional[str] = typer.Option(
        None,
        "--chaos-type",
        "-t",
        help="Chaos type to execute (e.g. host-down, network-latency)",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Render but do not execute the experiment"),
    collect_metrics: bool = typer.Option(
        True,
        "--collect-metrics/--no-metrics",
        help="Collect and compare metrics before, during, and after the experiment",
    ),
    metrics_duration: int = typer.Option(
        60,
        "--metrics-duration",
        help="Duration to collect metrics during chaos (seconds)",
    ),
    metrics_interval: int = typer.Option(
        5,
        "--metrics-interval",
        help="Interval between metric collections during chaos (seconds)",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write the experiment run metadata",
    ),
    duration: Optional[int] = typer.Option(
        None,
        "--duration",
        help="Override duration_seconds for template-based experiments (seconds)",
    ),
    latency_ms: Optional[int] = typer.Option(
        None,
        "--latency-ms",
        help="Override latency_ms for network-latency experiments (milliseconds)",
    ),
    virtual_users: Optional[int] = typer.Option(
        None,
        "--virtual-users",
        "-u",
        help="Override virtual_users for k6 load testing experiments",
    ),
    target_url: Optional[str] = typer.Option(
        None,
        "--target-url",
        help="Override target_url for k6 load testing experiments",
    ),
    response_threshold: Optional[int] = typer.Option(
        None,
        "--response-threshold",
        help="Override response_time_threshold for k6 experiments (milliseconds)",
    ),
    prometheus_url: Optional[str] = typer.Option(
        None,
        "--prometheus-url",
        help="Override Prometheus URL for metrics collection (e.g., http://prometheus:9090)",
    ),
) -> None:
    """Render and execute a chaos experiment."""
    # Apply CLI overrides
    if prometheus_url:
        _cli_overrides["prometheus_url"] = prometheus_url
    
    orchestrator = _build_orchestrator(config)
    overrides = {}
    if duration is not None:
        overrides["duration_seconds"] = duration
    if latency_ms is not None:
        overrides["latency_ms"] = latency_ms
    if virtual_users is not None:
        overrides["virtual_users"] = virtual_users
    if target_url is not None:
        overrides["target_url"] = target_url
    if response_threshold is not None:
        overrides["response_time_threshold"] = response_threshold
    result = orchestrator.run_experiment(
        target_id=target_id,
        chaos_type=chaos_type,
        experiment_path=experiment,
        dry_run=dry_run,
        output_path=output_path,
        overrides=overrides or None,
        collect_metrics=collect_metrics,
        metrics_duration=metrics_duration,
        metrics_interval=metrics_interval,
    )

    console.print_json(data=result.to_dict())


@app.command()
def report(
    run_id: Optional[str] = typer.Argument(None, help="Run identifier to render a report for"),
    output_format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Report format (markdown/json/html)",
        case_sensitive=False,
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to save the rendered report",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        "-b",
        help="Open HTML report in browser (only for html format)",
    ),
) -> None:
    """Render a report for a previous chaos run."""
    orchestrator = _build_orchestrator(None)
    report_payload = orchestrator.generate_report(run_id=run_id, output_format=output_format)

    if output_format.lower() == "json":
        payload = json.dumps(report_payload, indent=2)
    else:
        payload = report_payload

    if output_path:
        output_path.write_text(payload)
        console.print(f"✅ Report written to {output_path}")
    else:
        if output_format.lower() == "html":
            report_id = run_id or orchestrator._latest_run_id()
            html_path = orchestrator._reports_path / f'{report_id}.html'
            console.print(f"✅ HTML report generated with metrics visualization!")
            console.print(f"   📊 View the report at: {html_path}")
            
            # Open in browser if requested
            if open_browser:
                import webbrowser
                webbrowser.open(f"file://{html_path.absolute()}")
                console.print(f"   🌐 Opening in browser...")
        else:
            console.print(payload)


@app.command()
def chaos_jobs(
    config: Optional[Path] = typer.Option(None, "--config", "-c", exists=True, help="Config file"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (running, dead, pending)"),
) -> None:
    """List active and recent chaos jobs in the Nomad cluster."""
    import os
    from urllib.parse import urlparse
    
    try:
        import nomad
    except ImportError:
        console.print("[error] python-nomad is required but not installed")
        raise typer.Exit(1)
    
    # Get Nomad connection details from environment
    addr = os.getenv("NOMAD_ADDR", "http://127.0.0.1:4646")
    parsed = urlparse(addr)
    
    try:
        client = nomad.Nomad(
            host=parsed.hostname,
            port=parsed.port or 4646,
            token=os.getenv("NOMAD_TOKEN"),
            namespace=os.getenv("NOMAD_NAMESPACE", "default")
        )
        
        # Get all jobs
        jobs = client.jobs.get_jobs()
        
        # Filter for chaos jobs
        chaos_jobs_list = [j for j in jobs if j.get("ID", "").startswith("chaos-")]
        
        if status:
            chaos_jobs_list = [j for j in chaos_jobs_list if j.get("Status", "").lower() == status.lower()]
        
        if not chaos_jobs_list:
            console.print(f"[yellow]No chaos jobs found{' with status: ' + status if status else ''}[/yellow]")
            return
        
        # Create a table
        table = Table(title=f"Chaos Jobs{' (' + status + ')' if status else ''}")
        table.add_column("Job ID", style="cyan", no_wrap=False)
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Submit Time", style="yellow")
        
        for job in sorted(chaos_jobs_list, key=lambda x: x.get("SubmitTime", 0), reverse=True):
            job_id = job.get("ID", "unknown")
            job_type = job_id.split("-")[1] if len(job_id.split("-")) > 1 else "unknown"
            status_str = job.get("Status", "unknown")
            
            # Format timestamp
            submit_time = job.get("SubmitTime", 0)
            if submit_time:
                from datetime import datetime
                dt = datetime.fromtimestamp(submit_time / 1e9)  # Convert nanoseconds
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "unknown"
            
            # Color code status
            if status_str == "running":
                status_display = f"[green]{status_str}[/green]"
            elif status_str == "dead":
                status_display = f"[red]{status_str}[/red]"
            else:
                status_display = status_str
            
            table.add_row(job_id, job_type, status_display, time_str)
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(chaos_jobs_list)} chaos job(s)[/dim]")
        
    except Exception as e:
        console.print(f"[error] Failed to list chaos jobs: {e}")
        raise typer.Exit(1)


@app.command("drain-nodes")
def drain_nodes_command(
    node_id: Optional[str] = typer.Option(None, "--node-id", "-n", help="Specific node ID to drain (omit to list available nodes)"),
    deadline: int = typer.Option(300, "--deadline", "-d", help="Drain deadline in seconds (default: 300)"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
) -> None:
    """Drain nodes to simulate host-down scenarios.
    
    This command marks nodes as ineligible and migrates allocations,
    simulating node failures for chaos testing.
    """
    from .core.nomad import NomadClient
    
    settings = load_settings(config_path)
    
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace
    )
    
    try:
        # If no node specified, list available nodes
        if not node_id:
            console.print("\n[yellow]Available nodes:[/yellow]\n")
            
            nodes = client.list_nodes()
            if not nodes:
                console.print("[red]No nodes found![/red]")
                return
            
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Node Name", style="cyan")
            table.add_column("Node ID", style="dim")
            table.add_column("Status", justify="center")
            table.add_column("Draining", justify="center")
            table.add_column("Eligibility", justify="center")
            
            for node in nodes:
                drain_display = "🔴 Yes" if node["Drain"] else "🟢 No"
                elig_display = "🔴 ineligible" if node["SchedulingEligibility"] == "ineligible" else "🟢 eligible"
                
                table.add_row(
                    node["Name"],
                    node["ID"][:8] + "...",
                    node["Status"],
                    drain_display,
                    elig_display
                )
            
            console.print(table)
            console.print("\n💡 [dim]Use --node-id <NODE_ID> to drain a specific node[/dim]")
            return
        
        # Get node details
        nodes = client.list_nodes()
        target_node = None
        for node in nodes:
            if node["ID"].startswith(node_id) or node["Name"] == node_id:
                target_node = node
                break
        
        if not target_node:
            console.print(f"[red]Node '{node_id}' not found![/red]")
            return
        
        # Check if already draining
        if target_node["Drain"] or target_node["SchedulingEligibility"] == "ineligible":
            console.print(f"[yellow]Node {target_node['Name']} ({target_node['ID'][:8]}...) is already draining/ineligible[/yellow]")
            return
        
        if dry_run:
            console.print(f"\n[yellow]DRY RUN MODE[/yellow] - Would drain node:")
            console.print(f"  • Name: {target_node['Name']}")
            console.print(f"  • ID: {target_node['ID']}")
            console.print(f"  • Deadline: {deadline} seconds")
            console.print("\nRun without --dry-run to actually drain the node.")
            return
        
        # Confirm drain
        if not yes and not typer.confirm(f"\n⚠️  Drain node {target_node['Name']} ({target_node['ID'][:8]}...)?"):
            console.print("Drain cancelled.")
            return
        
        # Perform drain
        console.print(f"\n[cyan]Draining node {target_node['Name']}...[/cyan]")
        
        success = client.drain_node(target_node["ID"], deadline)
        
        if success:
            console.print(f"[green]✓ Successfully drained node {target_node['Name']}[/green]")
            console.print(f"\n💡 [dim]Use 'chaosmonkey recover-nodes --node-id {target_node['ID'][:8]}' to recover[/dim]")
        else:
            console.print(f"[red]✗ Failed to drain node {target_node['Name']}[/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[error] Failed to drain nodes: {e}")
        raise typer.Exit(1)


@app.command("recover-nodes")
def recover_nodes_command(
    node_id: Optional[str] = typer.Option(None, "--node-id", "-n", help="Specific node ID to recover (omit to recover all drained nodes)"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
) -> None:
    """Recover drained nodes after host-down chaos experiments.
    
    This command re-enables nodes that were drained during chaos testing,
    making them eligible to receive allocations again.
    """
    from .core.nomad import NomadClient
    
    settings = load_settings(config_path)
    
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace
    )
    
    try:
        # Get nodes to recover
        nodes = client.list_nodes()
        
        if node_id:
            # Recover specific node
            target_node = None
            for node in nodes:
                if node["ID"].startswith(node_id) or node["Name"] == node_id:
                    target_node = node
                    break
            
            if not target_node:
                console.print(f"[red]Node '{node_id}' not found![/red]")
                return
            
            nodes_to_check = [target_node]
        else:
            # Get all nodes
            nodes_to_check = nodes
        
        # Filter for drained nodes
        drained_nodes = []
        for node in nodes_to_check:
            if node["Drain"] or node["SchedulingEligibility"] == "ineligible":
                drained_nodes.append(node)
        
        if not drained_nodes:
            console.print("✅ [green]No drained nodes found![/green] All nodes are healthy and eligible.")
            return
        
        # Display drained nodes
        console.print(f"\n[yellow]Found {len(drained_nodes)} drained/ineligible node(s):[/yellow]\n")
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Node Name", style="cyan")
        table.add_column("Node ID", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Draining", justify="center")
        table.add_column("Eligibility", justify="center")
        
        for node in drained_nodes:
            drain_display = "🔴 Yes" if node["Drain"] else "🟢 No"
            elig_display = "🔴 ineligible" if node["SchedulingEligibility"] == "ineligible" else "🟢 eligible"
            
            table.add_row(
                node["Name"],
                node["ID"][:8] + "...",
                node["Status"],
                drain_display,
                elig_display
            )
        
        console.print(table)
        
        if dry_run:
            console.print("\n[yellow]DRY RUN MODE[/yellow] - Would recover these nodes:")
            for node in drained_nodes:
                console.print(f"  • {node['Name']} ({node['ID'][:8]}...)")
            console.print("\nRun without --dry-run to actually recover nodes.")
            return
        
        # Confirm recovery
        if not yes and not typer.confirm(f"\n⚠️  Recover {len(drained_nodes)} node(s)?"):
            console.print("Recovery cancelled.")
            return
        
        # Recover each node
        console.print("\n[cyan]Recovering nodes...[/cyan]\n")
        
        success_count = 0
        failed_count = 0
        
        for node in drained_nodes:
            node_name = node["Name"]
            
            try:
                console.print(f"  Recovering {node_name}...", end=" ")
                
                success = client.recover_node(node["ID"])
                
                if success:
                    console.print("[green]✓[/green]")
                    success_count += 1
                else:
                    console.print("[red]✗[/red]")
                    failed_count += 1
                
            except Exception as e:
                console.print(f"[red]✗[/red] Error: {e}")
                failed_count += 1
        
        # Summary
        console.print("\n" + "="*50)
        if success_count > 0:
            console.print(f"[green]✓ Successfully recovered {success_count} node(s)[/green]")
        if failed_count > 0:
            console.print(f"[red]✗ Failed to recover {failed_count} node(s)[/red]")
        
        console.print("\n💡 [dim]Tip: Run 'chaosmonkey discover --clients' to verify node status[/dim]")
        
    except Exception as e:
        console.print(f"[error] Failed to recover nodes: {e}")
        raise typer.Exit(1)


@app.command()
def web(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind to"),
) -> None:
    """Start the web UI dashboard."""
    try:
        from .web.app import app as web_app
    except ImportError:
        console.print("[red]Error: Web dependencies not installed.[/red]")
        console.print("Install with: pip install flask flask-cors")
        raise typer.Exit(1)
    
    console.print(f"[green]🚀 Starting ChaosMonkey Web UI...[/green]")
    console.print(f"[cyan]📊 Dashboard: http://{host if host != '0.0.0.0' else 'localhost'}:{port}[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    web_app.run(host=host, port=port, debug=False)


# ==============================================================================
# Platform Commands (VM-based chaos)
# ==============================================================================

platforms_app = typer.Typer(help="VM platform operations (OLVM, vSphere)")
app.add_typer(platforms_app, name="platforms")


@platforms_app.command("discover-vms")
def discover_platform_vms(
    platform: str = typer.Option(..., "--platform", "-p", help="Platform type (olvm or vsphere)"),
    name_pattern: Optional[str] = typer.Option(None, "--name", "-n", help="VM name pattern"),
    datacenter: Optional[str] = typer.Option(None, "--datacenter", "-d", help="Datacenter filter"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Discover VMs on a virtualization platform."""
    from .core.platform_orchestrator import PlatformOrchestrator
    from rich.table import Table
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        vms = orchestrator.discover_vms(
            platform=platform,
            name_pattern=name_pattern,
            datacenter=datacenter
        )
        
        if not vms:
            console.print("[yellow]No VMs found matching criteria[/yellow]")
            return
        
        # Display results in a table
        table = Table(title=f"Discovered VMs on {platform.upper()}")
        table.add_column("Name", style="cyan")
        table.add_column("Power State", style="magenta")
        table.add_column("Host", style="green")
        table.add_column("Datacenter", style="blue")
        table.add_column("CPU", justify="right")
        table.add_column("Memory (GB)", justify="right")
        
        for vm in vms:
            memory_gb = f"{vm.memory_mb / 1024:.1f}" if vm.memory_mb else "N/A"
            table.add_row(
                vm.name,
                vm.power_state.value,
                vm.host or "N/A",
                vm.datacenter or "N/A",
                str(vm.cpu_count) if vm.cpu_count else "N/A",
                memory_gb
            )
        
        console.print(table)
        console.print(f"\n[green]Total: {len(vms)} VMs[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@platforms_app.command("vm-info")
def get_vm_info(
    vm_name: str = typer.Argument(..., help="VM name"),
    platform: str = typer.Option(..., "--platform", "-p", help="Platform type (olvm or vsphere)"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Get detailed information about a VM."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        vm = orchestrator.get_vm_info(platform, vm_name)
        
        console.print(f"\n[bold cyan]VM Information: {vm.name}[/bold cyan]")
        console.print(f"  Platform:     {vm.platform}")
        console.print(f"  ID:           {vm.id}")
        console.print(f"  Power State:  {vm.power_state.value}")
        console.print(f"  Host:         {vm.host or 'N/A'}")
        console.print(f"  Datacenter:   {vm.datacenter or 'N/A'}")
        console.print(f"  Cluster:      {vm.cluster or 'N/A'}")
        console.print(f"  CPUs:         {vm.cpu_count or 'N/A'}")
        console.print(f"  Memory:       {vm.memory_mb}MB" if vm.memory_mb else "  Memory:       N/A")
        console.print(f"  Guest OS:     {vm.guest_os or 'N/A'}")
        console.print(f"  Tools Status: {vm.tools_status or 'N/A'}")
        
        if vm.metadata:
            console.print("\n[bold]Metadata:[/bold]")
            for key, value in vm.metadata.items():
                console.print(f"  {key}: {value}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@platforms_app.command("power-on")
def power_on_vm(
    vm_name: str = typer.Argument(..., help="VM name"),
    platform: str = typer.Option(..., "--platform", "-p", help="Platform type (olvm or vsphere)"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Power on a VM."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        success = orchestrator.power_on_vm(platform, vm_name, timeout=timeout)
        if success:
            console.print(f"[green]✓ Successfully powered on {vm_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to power on {vm_name}[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@platforms_app.command("power-off")
def power_off_vm(
    vm_name: str = typer.Argument(..., help="VM name"),
    platform: str = typer.Option(..., "--platform", "-p", help="Platform type (olvm or vsphere)"),
    graceful: bool = typer.Option(True, "--graceful/--force", help="Graceful shutdown or force"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Power off a VM."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        success = orchestrator.power_off_vm(platform, vm_name, graceful=graceful, timeout=timeout)
        if success:
            console.print(f"[green]✓ Successfully powered off {vm_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to power off {vm_name}[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@platforms_app.command("reboot")
def reboot_vm(
    vm_name: str = typer.Argument(..., help="VM name"),
    platform: str = typer.Option(..., "--platform", "-p", help="Platform type (olvm or vsphere)"),
    graceful: bool = typer.Option(True, "--graceful/--force", help="Graceful reboot or force"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Timeout in seconds"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Reboot a VM."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        success = orchestrator.reboot_vm(platform, vm_name, graceful=graceful, timeout=timeout)
        if success:
            console.print(f"[green]✓ Successfully rebooted {vm_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to reboot {vm_name}[/red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@platforms_app.command("dora-environments")
def list_dora_environments(
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """List available Dora environments."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    environments = orchestrator.list_dora_environments()
    
    console.print("\n[bold cyan]Available Dora Environments:[/bold cyan]")
    for env in sorted(environments):
        console.print(f"  • {env}")
    console.print(f"\n[green]Total: {len(environments)} environments[/green]")


@platforms_app.command("dora-discover")
def discover_dora_environment(
    environment: str = typer.Argument(..., help="Environment name"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Dora username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Dora password"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save output to JSON file"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config file"),
) -> None:
    """Discover environment using Dora API."""
    from .core.platform_orchestrator import PlatformOrchestrator
    
    settings = load_settings(config)
    orchestrator = PlatformOrchestrator(settings)
    
    try:
        data = orchestrator.discover_dora_environment(environment, username, password)
        
        if output:
            output.write_text(json.dumps(data, indent=2))
            console.print(f"[green]✓ Saved environment data to {output}[/green]")
        else:
            console.print(json.dumps(data, indent=2))
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def main() -> None:  # pragma: no cover - thin wrapper
    app()


if __name__ == "__main__":  # pragma: no cover - direct execution guard
    main()

