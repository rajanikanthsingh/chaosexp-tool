"""HTML report generator for chaos experiments."""
# Import the enhanced report generator
from .report_html_enhanced import generate_enhanced_html_report


def generate_html_report(run_id: str, experiment: dict, result: dict) -> str:
    """Generate a comprehensive HTML report for chaos experiment results with detailed metrics.
    
    This function now delegates to the enhanced report generator for comprehensive reporting.
    """
    return generate_enhanced_html_report(run_id, experiment, result)


# Keep old implementation for backward compatibility if needed
def generate_basic_html_report(run_id: str, experiment: dict, result: dict) -> str:
    """Generate a basic HTML report (legacy version)."""
    import json
    from datetime import datetime
    from typing import Any, Dict
    
    config = experiment.get("configuration", {})
    target = config.get("target_id", "unknown")
    chaos_type = ", ".join(experiment.get("tags", [])) or experiment.get("title", "Unknown")
    status = result.get("status", "unknown")
    reason = result.get("reason", "")
    
    # Get primary chaos type
    primary_type = experiment.get("tags", ["unknown"])[0] if experiment.get("tags") else "unknown"
    
    # Calculate duration
    start_time = result.get("start", "")
    end_time = result.get("end", "")
    duration = result.get("duration", 0)
    
    # Format timestamps
    start_dt = datetime.fromisoformat(start_time.replace("+00:00", "")) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace("+00:00", "")) if end_time else None
    
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
        }}
        
        .container {{
            max-width: 1200px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💥 Chaos Engineering Report</h1>
            <div class="subtitle">{chaos_type}</div>
            <div class="status-badge">{status.upper()}</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">📋</span>
                    Experiment Information
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
                        <div class="value">{primary_type}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Duration</div>
                        <div class="value">{duration:.2f}s</div>
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
            </div>
"""
    
    # Configuration section
    if config:
        html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">⚙️</span>
                    Configuration Parameters
                </h2>
                <table>
                    <thead>
                        <tr>
                            <th>Parameter</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for key, value in config.items():
            if key != "target_id":  # Already shown above
                html += f"""
                        <tr>
                            <td><code>{key}</code></td>
                            <td><code>{value}</code></td>
                        </tr>
"""
        html += """
                    </tbody>
                </table>
            </div>
"""
    
    # Execution results section
    html += """
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">🎯</span>
                    Execution Results
                </h2>
"""
    
    run_activities = result.get("run", [])
    if run_activities:
        for idx, activity in enumerate(run_activities, 1):
            activity_name = activity.get("activity", {}).get("name", "Unknown Activity")
            activity_status = activity.get("status", "unknown")
            activity_duration = activity.get("duration", 0)
            activity_output = activity.get("output", {})
            
            html += f"""
                <div class="activity-card">
                    <h3>Activity {idx}: {activity_name}</h3>
                    <div class="activity-status {activity_status}">{activity_status.upper()}</div>
                    <p><strong>Duration:</strong> {activity_duration:.2f}s</p>
"""
            
            if activity_output and isinstance(activity_output, dict):
                # Check for node drain specific output
                if "node_name" in activity_output:
                    html += """
                    <h4 style="margin-top: 20px; color: #1f2937;">Output Details</h4>
                    <table>
                        <tbody>
"""
                    html += f"""
                            <tr>
                                <td><strong>🖥️ Node Name</strong></td>
                                <td><code>{activity_output.get('node_name')}</code></td>
                            </tr>
                            <tr>
                                <td><strong>🆔 Node ID</strong></td>
                                <td><code>{activity_output.get('node_id', 'N/A')}</code></td>
                            </tr>
                            <tr>
                                <td><strong>📍 Datacenter</strong></td>
                                <td><code>{activity_output.get('datacenter', 'N/A')}</code></td>
                            </tr>
                            <tr>
                                <td><strong>⏱️ Drain Deadline</strong></td>
                                <td>{activity_output.get('drain_deadline_seconds', 'N/A')}s</td>
                            </tr>
                            <tr>
                                <td><strong>📦 Affected Allocations</strong></td>
                                <td>{activity_output.get('affected_allocations', 0)}</td>
                            </tr>
                            <tr>
                                <td><strong>🚦 Scheduling</strong></td>
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
                    <div class="alert">
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
                    # Generic output
                    html += f"""
                    <h4 style="margin-top: 20px; color: #1f2937;">Output</h4>
                    <div class="code-block">
                        <pre>{json.dumps(activity_output, indent=2)}</pre>
                    </div>
"""
            
            html += """
                </div>
"""
    else:
        html += """
                <div class="alert">No activities executed</div>
"""
    
    html += """
            </div>
"""
    
    # Summary section
    deviated = result.get("deviated", False)
    alert_class = "alert" if deviated else "alert alert-success"
    alert_icon = "⚠️" if deviated else "✅"
    alert_message = "System deviated from steady state during experiment" if deviated else "System remained within expected steady state"
    
    html += f"""
            <div class="section">
                <h2 class="section-title">
                    <span class="emoji">📝</span>
                    Summary
                </h2>
                <div class="{alert_class}">
                    {alert_icon} <strong>{alert_message}</strong>
                </div>
                
                <div class="info-grid" style="margin-top: 20px;">
                    <div class="info-card">
                        <div class="label">Platform</div>
                        <div class="value">{result.get('platform', 'Unknown')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">Node</div>
                        <div class="value">{result.get('node', 'Unknown')}</div>
                    </div>
                    <div class="info-card">
                        <div class="label">ChaosLib Version</div>
                        <div class="value">{result.get('chaoslib-version', 'Unknown')}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Generated by ChaosMonkey CLI</strong></p>
            <p style="margin-top: 10px;">Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html
