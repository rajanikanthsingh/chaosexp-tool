"""Metrics visualization for chaos experiments."""

from __future__ import annotations

import base64
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    Figure = None


class MetricsVisualizer:
    """
    Generate visualizations for chaos experiment metrics.
    
    Creates time-series graphs showing CPU, memory, and other metrics
    before, during, and after chaos experiments.
    """
    
    def __init__(self):
        """Initialize the visualizer."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError(
                "matplotlib is required for metrics visualization. "
                "Install it with: pip install matplotlib"
            )
    
    def generate_timeline_graph(
        self,
        before: Dict[str, Any],
        during: List[Dict[str, Any]],
        after: Dict[str, Any],
        output_path: Optional[Path] = None,
        title: str = "Chaos Experiment Metrics Timeline"
    ) -> Optional[str]:
        """
        Generate a comprehensive timeline graph showing all metrics.
        
        Args:
            before: Before metrics snapshot
            during: List of during metrics snapshots
            after: After metrics snapshot
            output_path: Path to save the graph (PNG)
            title: Graph title
            
        Returns:
            Base64-encoded PNG image if output_path is None, else None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        # Create figure with subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Extract timestamps and convert to datetime objects
        timestamps = []
        cpu_values = []
        memory_values = []
        status_values = []
        
        # Add before snapshot
        if before and 'timestamp' in before:
            try:
                ts = datetime.fromisoformat(before['timestamp'].replace('Z', '+00:00'))
                timestamps.append(ts)
                cpu_values.append(before.get('cpu', {}).get('percent', 0))
                memory_mb = before.get('memory', {}).get('usage', 0) / (1024 * 1024)
                memory_values.append(memory_mb)
                status = before.get('client_status', 'unknown')
                status_values.append(1 if status == 'running' else 0)
            except (ValueError, AttributeError):
                pass
        
        # Add during snapshots
        for snapshot in during:
            if 'timestamp' in snapshot:
                try:
                    ts = datetime.fromisoformat(snapshot['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(ts)
                    cpu_values.append(snapshot.get('cpu', {}).get('percent', 0))
                    memory_mb = snapshot.get('memory', {}).get('usage', 0) / (1024 * 1024)
                    memory_values.append(memory_mb)
                    status = snapshot.get('client_status', 'unknown')
                    status_values.append(1 if status == 'running' else 0)
                except (ValueError, AttributeError):
                    pass
        
        # Add after snapshot
        if after and 'timestamp' in after:
            try:
                ts = datetime.fromisoformat(after['timestamp'].replace('Z', '+00:00'))
                timestamps.append(ts)
                cpu_values.append(after.get('cpu', {}).get('percent', 0))
                memory_mb = after.get('memory', {}).get('usage', 0) / (1024 * 1024)
                memory_values.append(memory_mb)
                status = after.get('client_status', 'unknown')
                status_values.append(1 if status == 'running' else 0)
            except (ValueError, AttributeError):
                pass
        
        if not timestamps:
            plt.close(fig)
            return None
        
        # Plot 1: CPU Usage
        ax1.plot(timestamps, cpu_values, 'o-', linewidth=2, markersize=6, 
                color='#e74c3c', label='CPU Usage')
        ax1.fill_between(timestamps, cpu_values, alpha=0.3, color='#e74c3c')
        ax1.set_ylabel('CPU Usage (%)', fontsize=12, fontweight='bold')
        ax1.set_title('CPU Usage Over Time', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, max(cpu_values) * 1.1 if cpu_values else 100)
        
        # Add horizontal lines for before/after
        if len(cpu_values) > 0:
            ax1.axhline(y=cpu_values[0], color='green', linestyle='--', 
                       alpha=0.5, label=f'Baseline: {cpu_values[0]:.1f}%')
            if len(cpu_values) > 1:
                ax1.axhline(y=cpu_values[-1], color='blue', linestyle='--', 
                           alpha=0.5, label=f'Final: {cpu_values[-1]:.1f}%')
        ax1.legend(loc='upper left')
        
        # Plot 2: Memory Usage
        ax2.plot(timestamps, memory_values, 'o-', linewidth=2, markersize=6,
                color='#3498db', label='Memory Usage')
        ax2.fill_between(timestamps, memory_values, alpha=0.3, color='#3498db')
        ax2.set_ylabel('Memory Usage (MB)', fontsize=12, fontweight='bold')
        ax2.set_title('Memory Usage Over Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, max(memory_values) * 1.1 if memory_values else 1000)
        
        # Add horizontal lines for before/after
        if len(memory_values) > 0:
            ax2.axhline(y=memory_values[0], color='green', linestyle='--',
                       alpha=0.5, label=f'Baseline: {memory_values[0]:.1f} MB')
            if len(memory_values) > 1:
                ax2.axhline(y=memory_values[-1], color='blue', linestyle='--',
                           alpha=0.5, label=f'Final: {memory_values[-1]:.1f} MB')
        ax2.legend(loc='upper left')
        
        # Plot 3: Status Timeline
        ax3.plot(timestamps, status_values, 'o-', linewidth=2, markersize=8,
                color='#2ecc71', label='Status')
        ax3.fill_between(timestamps, status_values, alpha=0.3, color='#2ecc71')
        ax3.set_ylabel('Status', fontsize=12, fontweight='bold')
        ax3.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax3.set_title('System Status Over Time', fontsize=12)
        ax3.set_yticks([0, 1])
        ax3.set_yticklabels(['Down', 'Running'])
        ax3.grid(True, alpha=0.3)
        ax3.set_ylim(-0.1, 1.1)
        
        # Mark chaos phases
        if len(timestamps) > 2:
            # Before phase (first point)
            ax1.axvspan(timestamps[0], timestamps[1], alpha=0.1, color='green', label='Before')
            ax2.axvspan(timestamps[0], timestamps[1], alpha=0.1, color='green')
            ax3.axvspan(timestamps[0], timestamps[1], alpha=0.1, color='green')
            
            # During phase (middle points)
            ax1.axvspan(timestamps[1], timestamps[-2], alpha=0.1, color='red', label='During Chaos')
            ax2.axvspan(timestamps[1], timestamps[-2], alpha=0.1, color='red')
            ax3.axvspan(timestamps[1], timestamps[-2], alpha=0.1, color='red')
            
            # After phase (last point)
            ax1.axvspan(timestamps[-2], timestamps[-1], alpha=0.1, color='blue', label='After')
            ax2.axvspan(timestamps[-2], timestamps[-1], alpha=0.1, color='blue')
            ax3.axvspan(timestamps[-2], timestamps[-1], alpha=0.1, color='blue')
        
        # Format x-axis
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save or return base64
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            # Return base64-encoded image
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            return image_base64
    
    def generate_comparison_bars(
        self,
        comparison: Dict[str, Any],
        output_path: Optional[Path] = None,
        title: str = "Before vs After Comparison"
    ) -> Optional[str]:
        """
        Generate bar chart comparing before and after metrics.
        
        Args:
            comparison: Metrics comparison data
            output_path: Path to save the graph (PNG)
            title: Graph title
            
        Returns:
            Base64-encoded PNG image if output_path is None, else None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        analysis = comparison.get('analysis', {})
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # CPU comparison
        if 'cpu' in analysis:
            cpu = analysis['cpu']
            categories = ['Before', 'Peak', 'After']
            values = [
                cpu.get('before_percent', 0),
                cpu.get('peak_during_percent', 0),
                cpu.get('after_percent', 0)
            ]
            colors = ['#2ecc71', '#e74c3c', '#3498db']
            
            bars1 = ax1.bar(categories, values, color=colors, alpha=0.7, edgecolor='black')
            ax1.set_ylabel('CPU Usage (%)', fontsize=12, fontweight='bold')
            ax1.set_title('CPU Usage Comparison', fontsize=12)
            ax1.set_ylim(0, max(values) * 1.2 if values else 100)
            ax1.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar, value in zip(bars1, values):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.1f}%',
                        ha='center', va='bottom', fontweight='bold')
            
            # Add recovery status
            recovered = cpu.get('recovered', False)
            status_text = '✅ Recovered' if recovered else '⚠️ Not Recovered'
            ax1.text(0.5, 0.95, status_text, transform=ax1.transAxes,
                    ha='center', va='top', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # Memory comparison
        if 'memory' in analysis:
            mem = analysis['memory']
            categories = ['Before', 'Peak', 'After']
            values_bytes = [
                mem.get('before_bytes', 0),
                mem.get('peak_during_bytes', 0),
                mem.get('after_bytes', 0)
            ]
            # Convert to MB
            values = [v / (1024 * 1024) for v in values_bytes]
            colors = ['#2ecc71', '#e74c3c', '#3498db']
            
            bars2 = ax2.bar(categories, values, color=colors, alpha=0.7, edgecolor='black')
            ax2.set_ylabel('Memory Usage (MB)', fontsize=12, fontweight='bold')
            ax2.set_title('Memory Usage Comparison', fontsize=12)
            ax2.set_ylim(0, max(values) * 1.2 if values else 1000)
            ax2.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar, value in zip(bars2, values):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{value:.1f}',
                        ha='center', va='bottom', fontweight='bold')
            
            # Add recovery status
            recovered = mem.get('recovered', False)
            status_text = '✅ Recovered' if recovered else '⚠️ Not Recovered'
            ax2.text(0.5, 0.95, status_text, transform=ax2.transAxes,
                    ha='center', va='top', fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Save or return base64
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return None
        else:
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            return image_base64
    
    def generate_all_graphs(
        self,
        comparison: Dict[str, Any],
        output_dir: Path,
        run_id: str
    ) -> Dict[str, Path]:
        """
        Generate all graphs for a metrics comparison.
        
        Args:
            comparison: Full metrics comparison data
            output_dir: Directory to save graphs
            run_id: Run identifier for filenames
            
        Returns:
            Dictionary mapping graph type to file path
        """
        if not MATPLOTLIB_AVAILABLE:
            return {}
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        graphs = {}
        
        # Timeline graph
        timeline_path = output_dir / f"{run_id}_timeline.png"
        self.generate_timeline_graph(
            before=comparison.get('before', {}),
            during=comparison.get('during', []),
            after=comparison.get('after', {}),
            output_path=timeline_path,
            title=f"Metrics Timeline - {run_id}"
        )
        graphs['timeline'] = timeline_path
        
        # Comparison bars
        comparison_path = output_dir / f"{run_id}_comparison.png"
        self.generate_comparison_bars(
            comparison=comparison,
            output_path=comparison_path,
            title=f"Before vs After - {run_id}"
        )
        graphs['comparison'] = comparison_path
        
        return graphs
