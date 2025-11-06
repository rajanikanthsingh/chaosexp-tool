#!/usr/bin/env python3
"""
Example script demonstrating metrics collection for chaos experiments.

This script shows how to:
1. Collect baseline metrics before chaos
2. Run a chaos experiment
3. Collect continuous metrics during chaos
4. Collect post-chaos metrics
5. Compare and analyze the metrics
6. Generate a comparison report
"""

import json
import time
from pathlib import Path

from chaosmonkey.config import load_settings
from chaosmonkey.core.metrics import MetricsCollector
from chaosmonkey.core.nomad import NomadClient


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def print_metrics_summary(metrics: dict, label: str):
    """Print a summary of collected metrics."""
    print(f"\n{'='*60}")
    print(f"{label.upper()} METRICS")
    print(f"{'='*60}")
    
    if "error" in metrics:
        print(f"❌ Error: {metrics['error']}")
        return
    
    print(f"Timestamp: {metrics.get('timestamp', 'N/A')}")
    print(f"Target: {metrics.get('allocation_id', metrics.get('job_id', metrics.get('node_id', 'N/A')))}")
    
    if "cpu" in metrics:
        cpu = metrics["cpu"]
        print(f"\n📊 CPU Metrics:")
        print(f"  Usage: {cpu.get('percent', 0):.2f}%")
        print(f"  System Mode: {cpu.get('system_mode', 0)} ticks")
        print(f"  User Mode: {cpu.get('user_mode', 0)} ticks")
        if cpu.get('throttled_periods', 0) > 0:
            print(f"  ⚠️  Throttled: {cpu.get('throttled_periods', 0)} periods")
    
    if "memory" in metrics:
        mem = metrics["memory"]
        print(f"\n💾 Memory Metrics:")
        print(f"  RSS: {format_bytes(mem.get('rss', 0))}")
        print(f"  Cache: {format_bytes(mem.get('cache', 0))}")
        print(f"  Usage: {format_bytes(mem.get('usage', 0))}")
        print(f"  Max Usage: {format_bytes(mem.get('max_usage', 0))}")
    
    if "tasks" in metrics:
        print(f"\n🔧 Task Metrics:")
        for task_name, task_data in metrics["tasks"].items():
            print(f"  {task_name}:")
            print(f"    CPU: {task_data.get('cpu_percent', 0):.2f}%")
            print(f"    Memory: {format_bytes(task_data.get('memory_rss', 0))}")


def print_comparison_report(comparison: dict):
    """Print a detailed comparison report."""
    print(f"\n{'='*60}")
    print("METRICS COMPARISON ANALYSIS")
    print(f"{'='*60}")
    
    analysis = comparison.get("analysis", {})
    
    # CPU Analysis
    if "cpu" in analysis:
        cpu = analysis["cpu"]
        print(f"\n📊 CPU Analysis:")
        print(f"  Before:       {cpu.get('before_percent', 0):.2f}%")
        print(f"  Peak During:  {cpu.get('peak_during_percent', 0):.2f}%")
        print(f"  After:        {cpu.get('after_percent', 0):.2f}%")
        print(f"  Change:       {cpu.get('change_during', 0):+.2f}%")
        print(f"  Recovery:     {cpu.get('recovery', 0):+.2f}%")
        
        if cpu.get('recovered', False):
            print(f"  Status:       ✅ RECOVERED (within 5%)")
        else:
            print(f"  Status:       ⚠️  NOT RECOVERED")
    
    # Memory Analysis
    if "memory" in analysis:
        mem = analysis["memory"]
        before_mb = mem.get('before_bytes', 0) / (1024 * 1024)
        peak_mb = mem.get('peak_during_bytes', 0) / (1024 * 1024)
        after_mb = mem.get('after_bytes', 0) / (1024 * 1024)
        change_mb = mem.get('change_during_bytes', 0) / (1024 * 1024)
        
        print(f"\n💾 Memory Analysis:")
        print(f"  Before:       {before_mb:.2f} MB")
        print(f"  Peak During:  {peak_mb:.2f} MB")
        print(f"  After:        {after_mb:.2f} MB")
        print(f"  Change:       {change_mb:+.2f} MB")
        
        if mem.get('recovered', False):
            print(f"  Status:       ✅ RECOVERED (within 10%)")
        else:
            print(f"  Status:       ⚠️  NOT RECOVERED")
    
    # Status Analysis
    if "status" in analysis:
        status = analysis["status"]
        print(f"\n🚦 Status Analysis:")
        print(f"  Before:  {status.get('before', 'unknown')}")
        print(f"  After:   {status.get('after', 'unknown')}")
        
        if status.get('stable', False):
            print(f"  Status:  ✅ STABLE")
        else:
            print(f"  Status:  ⚠️  CHANGED")


def main():
    """Main example function."""
    print("=" * 60)
    print("CHAOS METRICS COLLECTION EXAMPLE")
    print("=" * 60)
    
    # Load settings and initialize clients
    print("\n🔧 Initializing clients...")
    settings = load_settings(None)
    
    nomad_client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    metrics_collector = MetricsCollector(nomad_client=nomad_client)
    
    # Example 1: Single allocation metrics
    print("\n" + "="*60)
    print("EXAMPLE 1: Allocation Metrics Collection")
    print("="*60)
    
    # Get first allocation from Nomad
    allocations = nomad_client.list_allocations()
    if not allocations:
        print("❌ No allocations found. Please deploy some jobs to Nomad first.")
        return
    
    target_alloc = allocations[0]
    alloc_id = target_alloc["ID"]
    alloc_name = target_alloc.get("Name", "unknown")
    
    print(f"\n🎯 Target: {alloc_name} ({alloc_id})")
    
    # Collect before metrics
    print("\n📊 Collecting BEFORE metrics...")
    before = metrics_collector.collect_nomad_allocation_metrics(
        allocation_id=alloc_id,
        label="before"
    )
    print_metrics_summary(before, "before")
    
    # Simulate chaos (in real scenario, this would be the chaos experiment)
    print("\n⚡ Simulating chaos experiment (10 seconds)...")
    print("   In real usage, this is where your chaos experiment runs")
    
    # Collect continuous metrics
    print("\n📊 Collecting DURING metrics (5 samples, 2s interval)...")
    during = metrics_collector.collect_continuous_metrics(
        target_type="allocation",
        target_id=alloc_id,
        duration_seconds=10,
        interval_seconds=2,
        label="during"
    )
    
    print(f"\n   Collected {len(during)} snapshots")
    for i, snapshot in enumerate(during):
        if "cpu" in snapshot:
            cpu_pct = snapshot["cpu"].get("percent", 0)
            print(f"   Snapshot {i+1}: CPU = {cpu_pct:.2f}%")
    
    # Collect after metrics
    print("\n📊 Collecting AFTER metrics...")
    after = metrics_collector.collect_nomad_allocation_metrics(
        allocation_id=alloc_id,
        label="after"
    )
    print_metrics_summary(after, "after")
    
    # Compare metrics
    print("\n📈 Generating comparison report...")
    comparison = metrics_collector.compare_metrics(
        before=before,
        during=during,
        after=after
    )
    
    print_comparison_report(comparison)
    
    # Save report to file
    report_path = Path("metrics_comparison_example.json")
    report_path.write_text(json.dumps(comparison, indent=2))
    print(f"\n💾 Full report saved to: {report_path}")
    
    # Example 2: Job-level metrics
    print("\n" + "="*60)
    print("EXAMPLE 2: Job-Level Metrics Collection")
    print("="*60)
    
    job_id = target_alloc.get("JobID")
    if job_id:
        print(f"\n🎯 Target: Job {job_id}")
        
        print("\n📊 Collecting job metrics...")
        job_metrics = metrics_collector.collect_nomad_job_metrics(
            job_id=job_id,
            label="job_snapshot"
        )
        
        print(f"\nJob: {job_metrics.get('job_id', 'N/A')}")
        print(f"Allocations: {job_metrics.get('allocation_count', 0)}")
        
        if "aggregate" in job_metrics:
            agg = job_metrics["aggregate"]
            print(f"\n📊 Aggregate Metrics:")
            print(f"  Total CPU: {agg.get('total_cpu_percent', 0):.2f}%")
            print(f"  Average CPU: {agg.get('average_cpu_percent', 0):.2f}%")
            print(f"  Total Memory: {format_bytes(agg.get('total_memory_bytes', 0))}")
            print(f"  Running Allocations: {agg.get('running_allocations', 0)}")
    
    print("\n" + "="*60)
    print("✅ Example completed successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Review the metrics_comparison_example.json file")
    print("2. Try running actual chaos experiments with --collect-metrics")
    print("3. Customize metrics_duration and metrics_interval for your needs")
    print("4. View the full documentation: docs/METRICS_COLLECTION.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
