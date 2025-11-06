"""HTML report generation with metrics visualization."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_metrics_html_report(
    run_id: str,
    experiment: Dict[str, Any],
    result: Dict[str, Any],
    metrics_comparison: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate an HTML report with interactive metrics charts.
    
    Args:
        run_id: Unique run identifier
        experiment: Experiment definition
        result: Experiment execution results
        metrics_comparison: Metrics comparison data with before/during/after
        
    Returns:
        HTML string with embedded charts
    """
    config = experiment.get("configuration", {})
    target = config.get("target_id", "unknown")
    chaos_type = ", ".join(experiment.get("tags", [])) or experiment.get("title", "Unknown")
    status = result.get("status", "unknown")
    
    # Extract metrics data
    has_metrics = metrics_comparison is not None
    metrics_data = {}
    
    if has_metrics:
        before = metrics_comparison.get("before", {})
        during = metrics_comparison.get("during", [])
        after = metrics_comparison.get("after", {})
        analysis = metrics_comparison.get("analysis", {})
        
        # Prepare timeline data
        metrics_data = _prepare_metrics_timeline(before, during, after)
        
        # Prepare summary data
        metrics_data["summary"] = {
            "cpu": analysis.get("cpu", {}),
            "memory": analysis.get("memory", {}),
            "disk": analysis.get("disk", {}),
            "status": analysis.get("status", {}),
        }
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaos Experiment Report - {run_id}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            margin-top: 15px;
            text-transform: uppercase;
            font-size: 0.9em;
        }}
        
        .status-completed {{ background: #10b981; }}
        .status-failed {{ background: #ef4444; }}
        .status-aborted {{ background: #f59e0b; }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            font-weight: 600;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .info-card {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }}
        
        .info-card .label {{
            font-size: 0.85em;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .info-card .value {{
            font-size: 1.3em;
            color: #1e293b;
            font-weight: 600;
        }}
        
        .chart-container {{
            background: #f8fafc;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.3em;
            color: #334155;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        .chart-wrapper {{
            position: relative;
            height: 400px;
        }}
        
        .metrics-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-top: 4px solid #667eea;
        }}
        
        .metric-card h3 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.2em;
        }}
        
        .metric-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .metric-row:last-child {{
            border-bottom: none;
        }}
        
        .metric-label {{
            color: #64748b;
            font-weight: 500;
        }}
        
        .metric-value {{
            color: #1e293b;
            font-weight: 600;
        }}
        
        .metric-value.positive {{
            color: #10b981;
        }}
        
        .metric-value.negative {{
            color: #ef4444;
        }}
        
        .recovery-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }}
        
        .recovery-success {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .recovery-warning {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .no-metrics {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 20px;
            border-radius: 8px;
            color: #92400e;
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            background: #f8fafc;
            color: #64748b;
            font-size: 0.9em;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Chaos Engineering Report</h1>
            <div class="subtitle">{chaos_type}</div>
            <div class="status-badge status-{status}">{status.upper()}</div>
        </div>
        
        <div class="content">
            <!-- Experiment Information -->
            <div class="section">
                <h2 class="section-title">📋 Experiment Information</h2>
                <div class="info-grid">
                    <div class="info-card">
                        <div class="label">Run ID</div>
                        <div class="value">{run_id}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Target</div>
                        <div class="value">{target}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Chaos Type</div>
                        <div class="value">{chaos_type}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Status</div>
                        <div class="value">{status.upper()}</div>
                    </div>
                </div>
            </div>
"""

    # Add metrics visualization if available
    if has_metrics and metrics_data.get("timeline"):
        html += """
            <!-- Metrics Visualization -->
            <div class="section">
                <h2 class="section-title">📈 Metrics Timeline</h2>
"""
        
        # CPU Chart
        if metrics_data["timeline"].get("cpu"):
            cpu_data = metrics_data["timeline"]["cpu"]
            html += f"""
                <div class="chart-container">
                    <div class="chart-title">CPU Usage Over Time</div>
                    <div class="chart-wrapper">
                        <canvas id="cpuChart"></canvas>
                    </div>
                </div>
                <script>
                    const cpuCtx = document.getElementById('cpuChart').getContext('2d');
                    const cpuChart = new Chart(cpuCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(cpu_data["labels"])},
                            datasets: [{{
                                label: 'CPU Usage (%)',
                                data: {json.dumps(cpu_data["values"])},
                                borderColor: 'rgb(239, 68, 68)',
                                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                pointBackgroundColor: 'rgb(239, 68, 68)',
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top',
                                    labels: {{
                                        font: {{
                                            size: 14,
                                            weight: '600'
                                        }},
                                        padding: 15
                                    }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                    titleFont: {{
                                        size: 14,
                                        weight: 'bold'
                                    }},
                                    bodyFont: {{
                                        size: 13
                                    }},
                                    callbacks: {{
                                        label: function(context) {{
                                            return 'CPU: ' + context.parsed.y.toFixed(2) + '%';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    max: 100,
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 12
                                        }},
                                        callback: function(value) {{
                                            return value + '%';
                                        }}
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 11
                                        }},
                                        maxRotation: 45,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});
                </script>
"""
        
        # Memory Chart
        if metrics_data["timeline"].get("memory"):
            mem_data = metrics_data["timeline"]["memory"]
            html += f"""
                <div class="chart-container">
                    <div class="chart-title">Memory Usage Over Time</div>
                    <div class="chart-wrapper">
                        <canvas id="memoryChart"></canvas>
                    </div>
                </div>
                <script>
                    const memCtx = document.getElementById('memoryChart').getContext('2d');
                    const memChart = new Chart(memCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(mem_data["labels"])},
                            datasets: [{{
                                label: 'Memory Usage (MB)',
                                data: {json.dumps(mem_data["values"])},
                                borderColor: 'rgb(59, 130, 246)',
                                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.4,
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                pointBackgroundColor: 'rgb(59, 130, 246)',
                                pointBorderColor: '#fff',
                                pointBorderWidth: 2,
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top',
                                    labels: {{
                                        font: {{
                                            size: 14,
                                            weight: '600'
                                        }},
                                        padding: 15
                                    }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                    titleFont: {{
                                        size: 14,
                                        weight: 'bold'
                                    }},
                                    bodyFont: {{
                                        size: 13
                                    }},
                                    callbacks: {{
                                        label: function(context) {{
                                            return 'Memory: ' + context.parsed.y.toFixed(2) + ' MB';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 12
                                        }},
                                        callback: function(value) {{
                                            return value.toFixed(0) + ' MB';
                                        }}
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 11
                                        }},
                                        maxRotation: 45,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});
                </script>
"""
        
        # Disk I/O Chart
        if metrics_data["timeline"].get("disk"):
            disk_data = metrics_data["timeline"]["disk"]
            html += f"""
                <div class="chart-container">
                    <div class="chart-title">Disk I/O Over Time</div>
                    <div class="chart-wrapper">
                        <canvas id="diskChart"></canvas>
                    </div>
                </div>
                <script>
                    const diskCtx = document.getElementById('diskChart').getContext('2d');
                    const diskChart = new Chart(diskCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(disk_data["labels"])},
                            datasets: [
                                {{
                                    label: 'Read (MB)',
                                    data: {json.dumps(disk_data["read_values"])},
                                    borderColor: 'rgb(16, 185, 129)',
                                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                    borderWidth: 3,
                                    fill: true,
                                    tension: 0.4,
                                    pointRadius: 4,
                                    pointHoverRadius: 6,
                                    pointBackgroundColor: 'rgb(16, 185, 129)',
                                    pointBorderColor: '#fff',
                                    pointBorderWidth: 2,
                                }},
                                {{
                                    label: 'Write (MB)',
                                    data: {json.dumps(disk_data["write_values"])},
                                    borderColor: 'rgb(245, 158, 11)',
                                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                    borderWidth: 3,
                                    fill: true,
                                    tension: 0.4,
                                    pointRadius: 4,
                                    pointHoverRadius: 6,
                                    pointBackgroundColor: 'rgb(245, 158, 11)',
                                    pointBorderColor: '#fff',
                                    pointBorderWidth: 2,
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top',
                                    labels: {{
                                        font: {{
                                            size: 14,
                                            weight: '600'
                                        }},
                                        padding: 15
                                    }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                    titleFont: {{
                                        size: 14,
                                        weight: 'bold'
                                    }},
                                    bodyFont: {{
                                        size: 13
                                    }},
                                    callbacks: {{
                                        label: function(context) {{
                                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' MB';
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 12
                                        }},
                                        callback: function(value) {{
                                            return value.toFixed(0) + ' MB';
                                        }}
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        font: {{
                                            size: 11
                                        }},
                                        maxRotation: 45,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});
                </script>
"""
        
        # Combined Chart
        if metrics_data["timeline"].get("cpu") and metrics_data["timeline"].get("memory"):
            cpu_data = metrics_data["timeline"]["cpu"]
            mem_data = metrics_data["timeline"]["memory"]
            html += f"""
                <div class="chart-container">
                    <div class="chart-title">Combined Metrics View</div>
                    <div class="chart-wrapper">
                        <canvas id="combinedChart"></canvas>
                    </div>
                </div>
                <script>
                    const combinedCtx = document.getElementById('combinedChart').getContext('2d');
                    const combinedChart = new Chart(combinedCtx, {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(cpu_data["labels"])},
                            datasets: [
                                {{
                                    label: 'CPU Usage (%)',
                                    data: {json.dumps(cpu_data["values"])},
                                    borderColor: 'rgb(239, 68, 68)',
                                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                                    borderWidth: 2,
                                    yAxisID: 'y',
                                    tension: 0.4,
                                }},
                                {{
                                    label: 'Memory Usage (MB)',
                                    data: {json.dumps(mem_data["values"])},
                                    borderColor: 'rgb(59, 130, 246)',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    borderWidth: 2,
                                    yAxisID: 'y1',
                                    tension: 0.4,
                                }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {{
                                mode: 'index',
                                intersect: false,
                            }},
                            plugins: {{
                                legend: {{
                                    display: true,
                                    position: 'top',
                                    labels: {{
                                        font: {{
                                            size: 14,
                                            weight: '600'
                                        }},
                                        padding: 15
                                    }}
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    padding: 12,
                                }}
                            }},
                            scales: {{
                                y: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    beginAtZero: true,
                                    max: 100,
                                    grid: {{
                                        color: 'rgba(239, 68, 68, 0.1)'
                                    }},
                                    ticks: {{
                                        callback: function(value) {{
                                            return value + '%';
                                        }}
                                    }},
                                    title: {{
                                        display: true,
                                        text: 'CPU Usage (%)',
                                        color: 'rgb(239, 68, 68)',
                                        font: {{
                                            size: 14,
                                            weight: 'bold'
                                        }}
                                    }}
                                }},
                                y1: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    beginAtZero: true,
                                    grid: {{
                                        drawOnChartArea: false,
                                    }},
                                    ticks: {{
                                        callback: function(value) {{
                                            return value.toFixed(0) + ' MB';
                                        }}
                                    }},
                                    title: {{
                                        display: true,
                                        text: 'Memory Usage (MB)',
                                        color: 'rgb(59, 130, 246)',
                                        font: {{
                                            size: 14,
                                            weight: 'bold'
                                        }}
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }},
                                    ticks: {{
                                        maxRotation: 45,
                                        minRotation: 45
                                    }}
                                }}
                            }}
                        }}
                    }});
                </script>
"""
        
        html += """
            </div>
"""
        
        # Metrics Summary Cards
        if metrics_data.get("summary"):
            summary = metrics_data["summary"]
            html += """
            <div class="section">
                <h2 class="section-title">📊 Metrics Analysis</h2>
                <div class="metrics-summary">
"""
            
            # CPU Summary
            if summary.get("cpu"):
                cpu = summary["cpu"]
                cpu_recovered = cpu.get("recovered", False)
                html += f"""
                    <div class="metric-card">
                        <h3>🔥 CPU Metrics</h3>
                        <div class="metric-row">
                            <span class="metric-label">Before Chaos</span>
                            <span class="metric-value">{cpu.get('before_percent', 0):.2f}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Peak During Chaos</span>
                            <span class="metric-value negative">{cpu.get('peak_during_percent', 0):.2f}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">After Chaos</span>
                            <span class="metric-value">{cpu.get('after_percent', 0):.2f}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Change During</span>
                            <span class="metric-value {'positive' if cpu.get('change_during', 0) < 0 else 'negative'}">{cpu.get('change_during', 0):+.2f}%</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Recovery Status</span>
                            <span class="metric-value">
                                <span class="recovery-badge recovery-{'success' if cpu_recovered else 'warning'}">
                                    {'✅ Recovered' if cpu_recovered else '⚠️ Not Fully Recovered'}
                                </span>
                            </span>
                        </div>
                    </div>
"""
            
            # Memory Summary
            if summary.get("memory"):
                mem = summary["memory"]
                mem_recovered = mem.get("recovered", False)
                before_mb = mem.get('before_bytes', 0) / (1024 * 1024)
                peak_mb = mem.get('peak_during_bytes', 0) / (1024 * 1024)
                after_mb = mem.get('after_bytes', 0) / (1024 * 1024)
                change_mb = mem.get('change_during_bytes', 0) / (1024 * 1024)
                
                html += f"""
                    <div class="metric-card">
                        <h3>💾 Memory Metrics</h3>
                        <div class="metric-row">
                            <span class="metric-label">Before Chaos</span>
                            <span class="metric-value">{before_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Peak During Chaos</span>
                            <span class="metric-value negative">{peak_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">After Chaos</span>
                            <span class="metric-value">{after_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Change During</span>
                            <span class="metric-value {'positive' if change_mb < 0 else 'negative'}">{change_mb:+.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Recovery Status</span>
                            <span class="metric-value">
                                <span class="recovery-badge recovery-{'success' if mem_recovered else 'warning'}">
                                    {'✅ Recovered' if mem_recovered else '⚠️ Not Fully Recovered'}
                                </span>
                            </span>
                        </div>
                    </div>
"""
            
            # Status Summary
            if summary.get("status"):
                status_info = summary["status"]
                status_stable = status_info.get("stable", False)
                html += f"""
                    <div class="metric-card">
                        <h3>🚦 Status Stability</h3>
                        <div class="metric-row">
                            <span class="metric-label">Before Status</span>
                            <span class="metric-value">{status_info.get('before', 'unknown')}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">After Status</span>
                            <span class="metric-value">{status_info.get('after', 'unknown')}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Stability</span>
                            <span class="metric-value">
                                <span class="recovery-badge recovery-{'success' if status_stable else 'warning'}">
                                    {'✅ Stable' if status_stable else '⚠️ Changed'}
                                </span>
                            </span>
                        </div>
                    </div>
"""
            
            # Disk I/O Summary
            if summary.get("disk"):
                disk = summary["disk"]
                before_read_mb = disk.get('before_read_bytes', 0) / (1024 * 1024)
                peak_read_mb = disk.get('peak_read_bytes', 0) / (1024 * 1024)
                after_read_mb = disk.get('after_read_bytes', 0) / (1024 * 1024)
                
                before_write_mb = disk.get('before_write_bytes', 0) / (1024 * 1024)
                peak_write_mb = disk.get('peak_write_bytes', 0) / (1024 * 1024)
                after_write_mb = disk.get('after_write_bytes', 0) / (1024 * 1024)
                
                total_increase_mb = disk.get('total_increase', 0) / (1024 * 1024)
                
                html += f"""
                    <div class="metric-card">
                        <h3>💿 Disk I/O Metrics</h3>
                        <div class="metric-row">
                            <span class="metric-label">Before Read</span>
                            <span class="metric-value">{before_read_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Peak Read</span>
                            <span class="metric-value negative">{peak_read_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Before Write</span>
                            <span class="metric-value">{before_write_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Peak Write</span>
                            <span class="metric-value negative">{peak_write_mb:.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Total I/O Increase</span>
                            <span class="metric-value {'positive' if total_increase_mb < 0 else 'negative'}">{total_increase_mb:+.2f} MB</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Read Ops</span>
                            <span class="metric-value">{disk.get('read_ops_before', 0)} → {disk.get('read_ops_after', 0)}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Write Ops</span>
                            <span class="metric-value">{disk.get('write_ops_before', 0)} → {disk.get('write_ops_after', 0)}</span>
                        </div>
                    </div>
"""
            
            html += """
                </div>
            </div>
"""
    else:
        html += """
            <div class="section">
                <div class="no-metrics">
                    ⚠️ No metrics data available for this experiment. Metrics collection may have been disabled.
                </div>
            </div>
"""
    
    # Footer
    html += f"""
        </div>
        
        <div class="footer">
            <p>Generated by ChaosMonkey Toolkit • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Run ID: {run_id}</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html


def _prepare_metrics_timeline(
    before: Dict[str, Any],
    during: List[Dict[str, Any]],
    after: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Prepare timeline data for charts.
    
    Args:
        before: Before metrics snapshot
        during: List of during metrics snapshots
        after: After metrics snapshot
        
    Returns:
        Dictionary with timeline data for CPU, memory, and disk I/O
    """
    timeline = {
        "cpu": {"labels": [], "values": []},
        "memory": {"labels": [], "values": []},
        "disk": {"labels": [], "read_values": [], "write_values": []},
    }
    
    # Add before point
    if "cpu" in before:
        timeline["cpu"]["labels"].append("Before")
        timeline["cpu"]["values"].append(before["cpu"].get("percent", 0))
    
    if "memory" in before:
        timeline["memory"]["labels"].append("Before")
        timeline["memory"]["values"].append(before["memory"].get("usage", 0) / (1024 * 1024))
    
    if "disk" in before:
        timeline["disk"]["labels"].append("Before")
        timeline["disk"]["read_values"].append(before["disk"].get("read_bytes", 0) / (1024 * 1024))
        timeline["disk"]["write_values"].append(before["disk"].get("write_bytes", 0) / (1024 * 1024))
    
    # Add during points
    for i, snapshot in enumerate(during):
        label = snapshot.get("label", f"During {i}")
        
        # Extract time from label if available (e.g., "during_0" -> "0s")
        if label.startswith("during_"):
            time_index = label.split("_")[-1]
            if time_index.isdigit():
                # Assuming 5-second intervals by default
                label = f"{int(time_index) * 5}s"
        
        if "cpu" in snapshot:
            timeline["cpu"]["labels"].append(label)
            timeline["cpu"]["values"].append(snapshot["cpu"].get("percent", 0))
        
        if "memory" in snapshot:
            timeline["memory"]["labels"].append(label)
            timeline["memory"]["values"].append(snapshot["memory"].get("usage", 0) / (1024 * 1024))
        
        if "disk" in snapshot:
            timeline["disk"]["labels"].append(label)
            timeline["disk"]["read_values"].append(snapshot["disk"].get("read_bytes", 0) / (1024 * 1024))
            timeline["disk"]["write_values"].append(snapshot["disk"].get("write_bytes", 0) / (1024 * 1024))
    
    # Add after point
    if "cpu" in after:
        timeline["cpu"]["labels"].append("After")
        timeline["cpu"]["values"].append(after["cpu"].get("percent", 0))
    
    if "memory" in after:
        timeline["memory"]["labels"].append("After")
        timeline["memory"]["values"].append(after["memory"].get("usage", 0) / (1024 * 1024))
    
    if "disk" in after:
        timeline["disk"]["labels"].append("After")
        timeline["disk"]["read_values"].append(after["disk"].get("read_bytes", 0) / (1024 * 1024))
        timeline["disk"]["write_values"].append(after["disk"].get("write_bytes", 0) / (1024 * 1024))
    
    return {"timeline": timeline}
