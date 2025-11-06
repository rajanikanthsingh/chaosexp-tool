"""Enhanced HTML report generator for chaos experiments with comprehensive metrics and details."""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def generate_enhanced_html_report(run_id: str, experiment: Dict[str, Any], result: Dict[str, Any]) -> str:
    """Generate a comprehensive HTML report with all possible details from chaos experiment results."""
    
    # Extract basic information
    config = experiment.get("configuration", {})
    target = config.get("target_id", "unknown")
    chaos_type = ", ".join(experiment.get("tags", [])) or experiment.get("title", "Unknown")
    status = result.get("status", "unknown")
    reason = result.get("reason", "")
    
    # Extract experiment metadata
    title = experiment.get("title", "Chaos Experiment")
    description = experiment.get("description", "No description provided")
    hypothesis = experiment.get("steady-state-hypothesis", {})
    method = experiment.get("method", [])
    rollbacks = experiment.get("rollbacks", [])
    
    # Extract timing information
    start_time = result.get("start", "")
    end_time = result.get("end", "")
    duration = result.get("duration", 0)
    
    # Format timestamps
    start_dt = datetime.fromisoformat(start_time.replace("+00:00", "")) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace("+00:00", "")) if end_time else None
    
    # Extract system information
    platform = result.get("platform", "Unknown")
    node = result.get("node", "Unknown")
    chaoslib_version = result.get("chaoslib-version", "Unknown")
    python_version = result.get("python", "Unknown")
    
    # Extract results
    run_activities = result.get("run", [])
    steady_states = result.get("steady_states", {})
    deviated = result.get("deviated", False)
    
    # Status color mapping
    status_colors = {
        "completed": "#10b981",
        "succeeded": "#10b981",
        "failed": "#ef4444",
        "aborted": "#f59e0b",
        "interrupted": "#dc2626",
        "unknown": "#6b7280"
    }
    
    status_color = status_colors.get(status, "#6b7280")
    
    # Begin HTML generation
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chaos Report: {run_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
            color: #1f2937;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
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
            background: {status_color};
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9em;
            margin-top: 15px;
            text-transform: uppercase;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
            page-break-inside: avoid;
        }}
        
        .section-title {{
            font-size: 1.8em;
            color: #1f2937;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .info-card {{
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #667eea;
        }}
        
        .info-card .label {{
            font-size: 0.85em;
            color: #6b7280;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        
        .info-card .value {{
            font-size: 1.3em;
            color: #1f2937;
            font-weight: 600;
        }}
        
        .info-card .value code {{
            background: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            color: #667eea;
        }}
        
        .description-box {{
            background: #f9fafb;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover {{
            background: #f9fafb;
        }}
        
        .activity-card {{
            background: white;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }}
        
        .activity-card h3 {{
            color: #1f2937;
            margin-bottom: 15px;
            font-size: 1.4em;
        }}
        
        .activity-status {{
            display: inline-block;
            padding: 6px 15px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        
        .activity-status.succeeded {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .activity-status.failed {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .code-block {{
            background: #1f2937;
            color: #f3f4f6;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            line-height: 1.5;
            margin: 15px 0;
        }}
        
        .alert {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            color: #92400e;
        }}
        
        .alert-success {{
            background: #d1fae5;
            border-left-color: #10b981;
            color: #065f46;
        }}
        
        .alert-error {{
            background: #fee2e2;
            border-left-color: #ef4444;
            color: #991b1b;
        }}
        
        .alert-info {{
            background: #dbeafe;
            border-left-color: #3b82f6;
            color: #1e40af;
        }}
        
        .timeline {{
            position: relative;
            padding-left: 40px;
            margin: 20px 0;
        }}
        
        .timeline::before {{
            content: '';
            position: absolute;
            left: 10px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #e5e7eb;
        }}
        
        .timeline-item {{
            position: relative;
            margin-bottom: 30px;
        }}
        
        .timeline-item::before {{
            content: '';
            position: absolute;
            left: -34px;
            top: 5px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #667eea;
            border: 3px solid white;
            box-shadow: 0 0 0 2px #667eea;
        }}
        
        .timeline-item.failed::before {{
            background: #ef4444;
            box-shadow: 0 0 0 2px #ef4444;
        }}
        
        .timeline-content {{
            background: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}
        
        .timeline-content h4 {{
            margin-bottom: 8px;
            color: #1f2937;
        }}
        
        .timeline-meta {{
            font-size: 0.85em;
            color: #6b7280;
            margin-top: 5px;
        }}
        
        .metric-box {{
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }}
        
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        
        .metric-value {{
            font-size: 2em;
            font-weight: 700;
        }}
        
        .footer {{
            background: #f9fafb;
            padding: 30px;
            text-align: center;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
        
        .emoji {{
            font-size: 1.5em;
            margin-right: 10px;
        }}
        
        pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: white;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2.5em;
            font-weight: 700;
            color: #667eea;
        }}
        
        .stat-label {{
            color: #6b7280;
            margin-top: 8px;
            font-size: 0.9em;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 2px;
        }}
        
        .badge-success {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge-error {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .badge-warning {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .badge-info {{
            background: #dbeafe;
            color: #1e40af;
        }}
        
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
            .section {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💥 Chaos Engineering Report</h1>
            <div class="subtitle">{title}</div>
            <div class="status-badge">{status.upper()}</div>
        </div>
        
        <div class="content">
"""
    
    # Executive Summary Section
    html += f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">📊</span>
                    Executive Summary
                </h2>
                
                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-value">{duration:.2f}s</div>
                        <div class="stat-label">Total Duration</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(run_activities)}</div>
                        <div class="stat-label">Activities Executed</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{len(rollbacks)}</div>
                        <div class="stat-label">Rollback Actions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{'❌' if deviated else '✅'}</div>
                        <div class="stat-label">Steady State</div>
                    </div>
                </div>
                
                <div class="description-box">
                    <h3 style="margin-bottom: 10px;">Experiment Description</h3>
                    <p>{description}</p>
                </div>
"""
    
    if deviated:
        html += """
                <div class="alert alert-error">
                    <strong>⚠️ System Deviation Detected</strong><br>
                    The system deviated from the expected steady state during this experiment. Review the detailed findings below.
                </div>
"""
    else:
        html += """
                <div class="alert alert-success">
                    <strong>✅ System Maintained Steady State</strong><br>
                    The system remained within expected parameters throughout the experiment.
                </div>
"""
    
    if reason:
        html += f"""
                <div class="alert alert-info">
                    <strong>ℹ️ Status Reason:</strong> {reason}
                </div>
"""
    
    html += """
            </div>
"""
    
    # Experiment Configuration Section
    html += f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">📋</span>
                    Experiment Configuration
                </h2>
                
                <div class="info-grid">
                    <div class="info-card">
                        <div class="label">Run ID</div>
                        <div class="value"><code>{run_id}</code></div>
                    </div>
                    <div class="info-card">
                        <div class="label">Target Service</div>
                        <div class="value"><code>{target}</code></div>
                    </div>
                    <div class="info-card">
                        <div class="label">Chaos Type</div>
                        <div class="value">{chaos_type}</div>
                    </div>
"""
    
    if start_dt:
        html += f"""
                    <div class="info-card">
                        <div class="label">Started At</div>
                        <div class="value">{start_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
                    </div>
"""
    
    if end_dt:
        html += f"""
                    <div class="info-card">
                        <div class="label">Completed At</div>
                        <div class="value">{end_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>
                    </div>
"""
    
    html += """
                </div>
"""
    
    # Configuration Parameters Table
    if config:
        html += """
                <h3 style="margin-top: 30px; margin-bottom: 15px;">Configuration Parameters</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        param_descriptions = {
            "target_id": "Target service or resource identifier",
            "duration": "Duration of chaos injection in seconds",
            "latency_ms": "Network latency to inject in milliseconds",
            "packet_loss_percent": "Percentage of packets to drop",
            "cpu_percent": "CPU usage percentage to inject",
            "memory_mb": "Memory to consume in megabytes",
            "node_name": "Target node name for chaos injection"
        }
        
        for key, value in config.items():
            desc = param_descriptions.get(key, "Configuration parameter")
            html += f"""
                        <tr>
                            <td><strong>{key}</strong></td>
                            <td><code>{value}</code></td>
                            <td>{desc}</td>
                        </tr>
"""
        html += """
                    </tbody>
                </table>
"""
    
    html += """
            </div>
"""
    
    # Execution Timeline Section
    html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">⏱️</span>
                    Execution Timeline
                </h2>
                <div class="timeline">
"""
    
    if run_activities:
        cumulative_time = 0
        for idx, activity in enumerate(run_activities, 1):
            activity_data = activity.get("activity", {})
            activity_name = activity_data.get("name", "Unknown Activity")
            activity_type = activity_data.get("type", "action")
            activity_status = activity.get("status", "unknown")
            activity_duration = activity.get("duration", 0)
            activity_output = activity.get("output", {})
            activity_exception = activity.get("exception", None)
            
            timeline_class = "failed" if activity_status == "failed" else ""
            status_badge = "badge-success" if activity_status == "succeeded" else "badge-error"
            
            html += f"""
                    <div class="timeline-item {timeline_class}">
                        <div class="timeline-content">
                            <h4>
                                {idx}. {activity_name}
                                <span class="badge {status_badge}">{activity_status.upper()}</span>
                                <span class="badge badge-info">{activity_type.upper()}</span>
                            </h4>
                            <div class="timeline-meta">
                                ⏱️ Duration: {activity_duration:.2f}s | 
                                🕐 At: {cumulative_time:.2f}s from start
                            </div>
"""
            
            if activity_exception:
                html += f"""
                            <div class="alert alert-error" style="margin-top: 10px;">
                                <strong>❌ Exception Occurred:</strong>
                                <pre style="margin-top: 5px;">{json.dumps(activity_exception, indent=2)}</pre>
                            </div>
"""
            
            html += """
                        </div>
                    </div>
"""
            cumulative_time += activity_duration
    else:
        html += """
                    <div class="alert">No activities were executed during this experiment.</div>
"""
    
    html += """
                </div>
            </div>
"""
    
    # Detailed Activity Results Section
    html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">🎯</span>
                    Detailed Activity Results
                </h2>
"""
    
    if run_activities:
        for idx, activity in enumerate(run_activities, 1):
            activity_data = activity.get("activity", {})
            activity_name = activity_data.get("name", "Unknown Activity")
            activity_type = activity_data.get("type", "action")
            activity_status = activity.get("status", "unknown")
            activity_duration = activity.get("duration", 0)
            activity_output = activity.get("output", {})
            activity_exception = activity.get("exception", None)
            
            # Get provider information
            provider = activity_data.get("provider", {})
            provider_type = provider.get("type", "N/A")
            provider_module = provider.get("module", "N/A")
            provider_func = provider.get("func", "N/A")
            
            html += f"""
                <div class="activity-card">
                    <h3>Activity {idx}: {activity_name}</h3>
                    <div class="activity-status {activity_status}">{activity_status.upper()}</div>
                    
                    <div class="info-grid" style="margin-top: 15px;">
                        <div class="info-card">
                            <div class="label">Type</div>
                            <div class="value">{activity_type}</div>
                        </div>
                        <div class="info-card">
                            <div class="label">Duration</div>
                            <div class="value">{activity_duration:.2f}s</div>
                        </div>
                        <div class="info-card">
                            <div class="label">Provider</div>
                            <div class="value">{provider_type}</div>
                        </div>
                    </div>
                    
                    <h4 style="margin-top: 20px; color: #1f2937;">Provider Details</h4>
                    <table style="margin-top: 10px;">
                        <tbody>
                            <tr>
                                <td><strong>Module</strong></td>
                                <td><code>{provider_module}</code></td>
                            </tr>
                            <tr>
                                <td><strong>Function</strong></td>
                                <td><code>{provider_func}</code></td>
                            </tr>
                        </tbody>
                    </table>
"""
            
            # Activity Arguments
            activity_args = activity_data.get("arguments", {})
            if activity_args:
                html += """
                    <h4 style="margin-top: 20px; color: #1f2937;">Input Arguments</h4>
                    <div class="code-block">
                        <pre>""" + json.dumps(activity_args, indent=2) + """</pre>
                    </div>
"""
            
            # Activity Output
            if activity_output and isinstance(activity_output, dict):
                # Check for node-specific output
                if "node_name" in activity_output or "node_id" in activity_output:
                    html += """
                    <h4 style="margin-top: 20px; color: #1f2937;">📦 Output Details</h4>
                    <table>
                        <tbody>
"""
                    if "node_name" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>🖥️ Node Name</strong></td>
                                <td><code>{activity_output.get('node_name')}</code></td>
                            </tr>
"""
                    if "node_id" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>🆔 Node ID</strong></td>
                                <td><code>{activity_output.get('node_id', 'N/A')}</code></td>
                            </tr>
"""
                    if "datacenter" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>📍 Datacenter</strong></td>
                                <td><code>{activity_output.get('datacenter', 'N/A')}</code></td>
                            </tr>
"""
                    if "drain_deadline_seconds" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>⏱️ Drain Deadline</strong></td>
                                <td>{activity_output.get('drain_deadline_seconds', 'N/A')}s</td>
                            </tr>
"""
                    if "affected_allocations" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>📦 Affected Allocations</strong></td>
                                <td>{activity_output.get('affected_allocations', 0)}</td>
                            </tr>
"""
                    if "scheduling_eligibility" in activity_output:
                        html += f"""
                            <tr>
                                <td><strong>🚦 Scheduling Eligibility</strong></td>
                                <td>{activity_output.get('scheduling_eligibility', 'N/A')}</td>
                            </tr>
"""
                    html += """
                        </tbody>
                    </table>
"""
                    
                    message = activity_output.get('message', '')
                    if message:
                        html += f"""
                    <div class="alert alert-info" style="margin-top: 15px;">
                        ℹ️ {message}
                    </div>
"""
                    
                    recovery_cmd = activity_output.get('recovery_command', '')
                    if recovery_cmd:
                        html += f"""
                    <h4 style="margin-top: 20px; color: #1f2937;">🔧 Recovery Command</h4>
                    <div class="code-block">
                        <pre>{recovery_cmd}</pre>
                    </div>
"""
                else:
                    # Generic structured output
                    html += f"""
                    <h4 style="margin-top: 20px; color: #1f2937;">Output</h4>
                    <div class="code-block">
                        <pre>{json.dumps(activity_output, indent=2)}</pre>
                    </div>
"""
            elif activity_output:
                # Simple string output
                html += f"""
                    <h4 style="margin-top: 20px; color: #1f2937;">Output</h4>
                    <div class="code-block">
                        <pre>{str(activity_output)}</pre>
                    </div>
"""
            
            # Exception Information
            if activity_exception:
                html += """
                    <h4 style="margin-top: 20px; color: #ef4444;">❌ Exception Details</h4>
                    <div class="alert alert-error">
                        <pre>""" + json.dumps(activity_exception, indent=2) + """</pre>
                    </div>
"""
            
            html += """
                </div>
"""
    else:
        html += """
                <div class="alert">No activities were executed during this experiment.</div>
"""
    
    html += """
            </div>
"""
    
    # Steady State Hypothesis Section
    if hypothesis:
        html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">🔬</span>
                    Steady State Hypothesis
                </h2>
                
                <div class="description-box">
                    <h3 style="margin-bottom: 10px;">Hypothesis Title</h3>
                    <p>""" + hypothesis.get("title", "No title specified") + """</p>
                </div>
"""
        
        # Probes
        probes = hypothesis.get("probes", [])
        if probes:
            html += """
                <h3 style="margin-top: 20px; margin-bottom: 15px;">Hypothesis Probes</h3>
"""
            for probe_idx, probe in enumerate(probes, 1):
                probe_name = probe.get("name", "Unknown Probe")
                probe_type = probe.get("type", "probe")
                probe_provider = probe.get("provider", {})
                probe_tolerance = probe.get("tolerance", None)
                
                html += f"""
                <div class="activity-card">
                    <h4>{probe_idx}. {probe_name}</h4>
                    <div class="info-grid" style="margin-top: 10px;">
                        <div class="info-card">
                            <div class="label">Type</div>
                            <div class="value">{probe_type}</div>
                        </div>
                        <div class="info-card">
                            <div class="label">Provider</div>
                            <div class="value">{probe_provider.get('type', 'N/A')}</div>
                        </div>
                    </div>
"""
                
                if probe_tolerance:
                    html += f"""
                    <h5 style="margin-top: 15px;">Tolerance</h5>
                    <div class="code-block">
                        <pre>{json.dumps(probe_tolerance, indent=2)}</pre>
                    </div>
"""
                
                html += """
                </div>
"""
        
        html += """
            </div>
"""
    
    # Rollback Actions Section
    if rollbacks:
        html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">🔄</span>
                    Rollback Actions
                </h2>
"""
        
        for rb_idx, rollback in enumerate(rollbacks, 1):
            rb_name = rollback.get("name", "Unknown Rollback")
            rb_type = rollback.get("type", "action")
            rb_provider = rollback.get("provider", {})
            
            html += f"""
                <div class="activity-card">
                    <h4>{rb_idx}. {rb_name}</h4>
                    <span class="badge badge-warning">{rb_type.upper()}</span>
                    
                    <div class="info-grid" style="margin-top: 15px;">
                        <div class="info-card">
                            <div class="label">Provider Type</div>
                            <div class="value">{rb_provider.get('type', 'N/A')}</div>
                        </div>
                        <div class="info-card">
                            <div class="label">Module</div>
                            <div class="value"><code>{rb_provider.get('module', 'N/A')}</code></div>
                        </div>
                    </div>
"""
            
            rb_args = rollback.get("arguments", {})
            if rb_args:
                html += f"""
                    <h5 style="margin-top: 15px;">Arguments</h5>
                    <div class="code-block">
                        <pre>{json.dumps(rb_args, indent=2)}</pre>
                    </div>
"""
            
            html += """
                </div>
"""
        
        html += """
            </div>
"""
    
    # System Environment Section
    html += f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">💻</span>
                    System Environment
                </h2>
                
                <div class="info-grid">
                    <div class="info-card">
                        <div class="label">Platform</div>
                        <div class="value">{platform}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Node</div>
                        <div class="value">{node}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">ChaosLib Version</div>
                        <div class="value">{chaoslib_version}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Python Version</div>
                        <div class="value">{python_version}</div>
                    </div>
                </div>
            </div>
"""
    
    # Raw JSON Data Section (for debugging and completeness)
    html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">📄</span>
                    Raw Experiment Data
                </h2>
                
                <details>
                    <summary style="cursor: pointer; padding: 10px; background: #f3f4f6; border-radius: 8px; margin-bottom: 10px;">
                        <strong>Click to view complete experiment JSON</strong>
                    </summary>
                    <div class="code-block">
                        <pre>""" + json.dumps({"experiment": experiment, "result": result}, indent=2) + """</pre>
                    </div>
                </details>
            </div>
"""
    
    # Footer
    html += f"""
        </div>
        
        <div class="footer">
            <p><strong>🐵 Generated by ChaosMonkey CLI</strong></p>
            <p style="margin-top: 10px;">Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p style="margin-top: 5px; font-size: 0.9em;">Run ID: <code>{run_id}</code></p>
        </div>
    </div>
</body>
</html>
"""
    
    return html
