"""Demo script to generate sample HTML metrics report."""

import json
from datetime import datetime
from pathlib import Path

# Import the HTML report generator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chaosmonkey.core.metrics_report import generate_metrics_html_report


def create_sample_metrics():
    """Create sample metrics data for demonstration."""
    
    # Sample experiment definition
    experiment = {
        "title": "CPU Stress Test",
        "description": "Stress test with CPU hogging",
        "tags": ["cpu-hog", "stress-test"],
        "configuration": {
            "target_id": "web-service-abc123",
            "duration_seconds": 60,
            "cpu_cores": 2,
        }
    }
    
    # Sample experiment result
    result = {
        "status": "completed",
        "start": datetime.utcnow().isoformat(),
        "end": datetime.utcnow().isoformat(),
        "duration": 65.42,
    }
    
    # Sample metrics comparison data
    metrics_comparison = {
        "before": {
            "timestamp": datetime.utcnow().isoformat(),
            "label": "before",
            "allocation_id": "web-service-abc123",
            "client_status": "running",
            "cpu": {
                "percent": 15.23,
                "system_mode": 1234,
                "user_mode": 5678,
            },
            "memory": {
                "usage": 512 * 1024 * 1024,  # 512 MB
                "rss": 480 * 1024 * 1024,
                "cache": 32 * 1024 * 1024,
            },
            "disk": {
                "read_bytes": 100 * 1024 * 1024,  # 100 MB
                "write_bytes": 50 * 1024 * 1024,  # 50 MB
                "total_bytes": 150 * 1024 * 1024,
                "read_ops": 1000,
                "write_ops": 500,
                "total_ops": 1500,
            },
        },
        "during": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_0",
                "cpu": {"percent": 25.5},
                "memory": {"usage": 580 * 1024 * 1024},
                "disk": {
                    "read_bytes": 120 * 1024 * 1024,
                    "write_bytes": 80 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_1",
                "cpu": {"percent": 45.2},
                "memory": {"usage": 720 * 1024 * 1024},
                "disk": {
                    "read_bytes": 180 * 1024 * 1024,
                    "write_bytes": 150 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_2",
                "cpu": {"percent": 65.8},
                "memory": {"usage": 980 * 1024 * 1024},
                "disk": {
                    "read_bytes": 250 * 1024 * 1024,
                    "write_bytes": 220 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_3",
                "cpu": {"percent": 85.1},
                "memory": {"usage": 1200 * 1024 * 1024},
                "disk": {
                    "read_bytes": 320 * 1024 * 1024,
                    "write_bytes": 300 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_4",
                "cpu": {"percent": 92.7},
                "memory": {"usage": 1450 * 1024 * 1024},
                "disk": {
                    "read_bytes": 400 * 1024 * 1024,
                    "write_bytes": 380 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_5",
                "cpu": {"percent": 98.4},  # Peak
                "memory": {"usage": 1650 * 1024 * 1024},
                "disk": {
                    "read_bytes": 480 * 1024 * 1024,  # Peak read
                    "write_bytes": 450 * 1024 * 1024,  # Peak write
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_6",
                "cpu": {"percent": 97.9},
                "memory": {"usage": 1680 * 1024 * 1024},  # Peak
                "disk": {
                    "read_bytes": 470 * 1024 * 1024,
                    "write_bytes": 460 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_7",
                "cpu": {"percent": 96.2},
                "memory": {"usage": 1620 * 1024 * 1024},
                "disk": {
                    "read_bytes": 420 * 1024 * 1024,
                    "write_bytes": 400 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_8",
                "cpu": {"percent": 92.5},
                "memory": {"usage": 1480 * 1024 * 1024},
                "disk": {
                    "read_bytes": 350 * 1024 * 1024,
                    "write_bytes": 320 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_9",
                "cpu": {"percent": 78.3},
                "memory": {"usage": 1200 * 1024 * 1024},
                "disk": {
                    "read_bytes": 270 * 1024 * 1024,
                    "write_bytes": 240 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_10",
                "cpu": {"percent": 55.6},
                "memory": {"usage": 890 * 1024 * 1024},
                "disk": {
                    "read_bytes": 180 * 1024 * 1024,
                    "write_bytes": 150 * 1024 * 1024,
                },
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "label": "during_11",
                "cpu": {"percent": 32.1},
                "memory": {"usage": 650 * 1024 * 1024},
                "disk": {
                    "read_bytes": 130 * 1024 * 1024,
                    "write_bytes": 90 * 1024 * 1024,
                },
            },
        ],
        "after": {
            "timestamp": datetime.utcnow().isoformat(),
            "label": "after",
            "allocation_id": "web-service-abc123",
            "client_status": "running",
            "cpu": {
                "percent": 16.5,
                "system_mode": 1256,
                "user_mode": 5701,
            },
            "memory": {
                "usage": 525 * 1024 * 1024,  # 525 MB
                "rss": 490 * 1024 * 1024,
                "cache": 35 * 1024 * 1024,
            },
            "disk": {
                "read_bytes": 110 * 1024 * 1024,  # Back to near baseline
                "write_bytes": 55 * 1024 * 1024,
                "total_bytes": 165 * 1024 * 1024,
                "read_ops": 1100,
                "write_ops": 550,
                "total_ops": 1650,
            },
        },
        "analysis": {
            "cpu": {
                "before_percent": 15.23,
                "peak_during_percent": 98.4,
                "after_percent": 16.5,
                "change_during": 83.17,
                "recovery": -1.27,
                "recovered": True,
            },
            "memory": {
                "before_bytes": 512 * 1024 * 1024,
                "peak_during_bytes": 1680 * 1024 * 1024,
                "after_bytes": 525 * 1024 * 1024,
                "change_during_bytes": 1168 * 1024 * 1024,
                "recovery_bytes": -13 * 1024 * 1024,
                "recovered": True,
            },
            "status": {
                "before": "running",
                "after": "running",
                "stable": True,
            },
            "disk": {
                "before_read_bytes": 100 * 1024 * 1024,
                "before_write_bytes": 50 * 1024 * 1024,
                "before_total_bytes": 150 * 1024 * 1024,
                "peak_read_bytes": 480 * 1024 * 1024,
                "peak_write_bytes": 460 * 1024 * 1024,
                "peak_total_bytes": 940 * 1024 * 1024,
                "after_read_bytes": 110 * 1024 * 1024,
                "after_write_bytes": 55 * 1024 * 1024,
                "after_total_bytes": 165 * 1024 * 1024,
                "read_increase": 380 * 1024 * 1024,
                "write_increase": 410 * 1024 * 1024,
                "total_increase": 790 * 1024 * 1024,
                "read_ops_before": 1000,
                "write_ops_before": 500,
                "read_ops_after": 1100,
                "write_ops_after": 550,
            },
        },
    }
    
    return experiment, result, metrics_comparison


def main():
    """Generate sample HTML report."""
    print("=" * 60)
    print("HTML METRICS REPORT GENERATOR")
    print("=" * 60)
    print()
    
    # Create sample data
    print("📊 Creating sample metrics data...")
    experiment, result, metrics_comparison = create_sample_metrics()
    
    # Generate HTML report
    print("🎨 Generating HTML report...")
    run_id = "run-demo-sample"
    html_content = generate_metrics_html_report(
        run_id=run_id,
        experiment=experiment,
        result=result,
        metrics_comparison=metrics_comparison,
    )
    
    # Save to file
    output_path = Path(__file__).parent.parent / "reports" / f"{run_id}.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content)
    
    print(f"✅ HTML report generated successfully!")
    print(f"   📄 Location: {output_path}")
    print(f"   📊 File size: {len(html_content):,} bytes")
    print()
    
    # Also save the raw data
    json_path = output_path.with_suffix('.json')
    json_data = {
        "experiment": experiment,
        "result": result,
        "metrics": metrics_comparison,
    }
    json_path.write_text(json.dumps(json_data, indent=2))
    print(f"   📋 JSON data: {json_path}")
    print()
    
    # Instructions
    print("=" * 60)
    print("VIEW THE REPORT")
    print("=" * 60)
    print()
    print("Option 1: Open directly")
    print(f"  open {output_path}")
    print()
    print("Option 2: Use browser")
    print(f"  file://{output_path.absolute()}")
    print()
    print("=" * 60)
    print()
    
    # Ask to open
    try:
        response = input("🌐 Open report in browser now? [y/N]: ").strip().lower()
        if response == 'y':
            import webbrowser
            webbrowser.open(f"file://{output_path.absolute()}")
            print("✅ Opening in browser...")
    except KeyboardInterrupt:
        print("\n👋 Cancelled")
    
    print()
    print("=" * 60)
    print("REPORT FEATURES")
    print("=" * 60)
    print()
    print("📈 Interactive Charts:")
    print("   • CPU Usage Over Time (line chart)")
    print("   • Memory Usage Over Time (line chart)")
    print("   • Combined Metrics View (dual-axis)")
    print()
    print("📊 Metrics Summary:")
    print("   • CPU metrics card with recovery status")
    print("   • Memory metrics card with recovery status")
    print("   • Status stability card")
    print()
    print("🎨 Design Features:")
    print("   • Modern gradient backgrounds")
    print("   • Responsive layout")
    print("   • Interactive tooltips")
    print("   • Print-ready format")
    print()
    print("=" * 60)
    print("✨ Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
