# ChaosMonkey Web UI

A modern, intuitive web dashboard for orchestrating and monitoring chaos engineering experiments on your Nomad cluster.

## Features

### 📊 Dashboard
- Real-time cluster statistics
- Node health monitoring
- Recent experiment history
- Success rate tracking
- Quick chaos type overview

### 🖥️ Node Management
- View all Nomad client nodes
- Monitor node status, resources, and drain state
- One-click node drain/enable operations
- Resource utilization display (CPU, Memory)
- Allocation counts per node

### ⚡ Chaos Execution
- Execute chaos experiments directly from the UI
- Support for all chaos types:
  - 🔥 CPU Hog
  - 💾 Memory Hog
  - 🐌 Network Latency
  - 📦 Packet Loss
  - 💀 Host Down (Node Drain)
  - 💿 Disk I/O
- Dry-run mode for safe testing
- Real-time execution output
- Target selection

### 📈 Reports & Analytics
- View all experiment reports
- Multiple formats: JSON, Markdown, HTML
- Interactive report viewer
- Detailed experiment metadata
- Success/failure tracking
- Timeline visualization

## Installation

### 1. Install Dependencies

```bash
cd /Users/kunalsing.thakur/github/hackathon/chaosmonkey

# Install web UI dependencies
pip install flask flask-cors

# Or reinstall the entire project
pip install -e .
```

### 2. Verify Installation

```bash
chaosmonkey web --help
```

## Usage

### Starting the Web UI

```bash
# Start on default port (8080)
chaosmonkey web

# Start on custom port
chaosmonkey web --port 3000

# Start on specific host
chaosmonkey web --host 127.0.0.1 --port 8080
```

### Access the Dashboard

Once started, open your browser and navigate to:

```
http://localhost:8080
```

You should see the ChaosMonkey Dashboard with the following tabs:

## Dashboard Views

### 1. Dashboard Tab

**Statistics Cards:**
- **Total Nodes**: Total Nomad client nodes
- **Drained Nodes**: Nodes currently in drain mode
- **Total Experiments**: All chaos experiments run
- **Success Rate**: Percentage of successful experiments

**Recent Experiments:**
- Last 5 chaos experiments
- Status indicators (completed/failed/dry-run)
- Click to view full report

**Available Chaos Types:**
- Visual cards for each chaos type
- Click to navigate to execution page

### 2. Nodes Tab

**Features:**
- Tabular view of all Nomad client nodes
- Real-time status monitoring
- Resource information (CPU, Memory)
- Drain status indicators
- Action buttons:
  - **Drain**: Initiate node drain
  - **Enable**: Re-enable drained nodes

**Node Information:**
- Name and ID
- Status (ready/down)
- Datacenter
- CPU capacity
- Memory capacity
- Drain status
- Running allocations count

### 3. Execute Chaos Tab

**Execution Form:**
1. **Select Chaos Type**: Choose from dropdown
   - Displays description for selected type
2. **Target ID**: Specify service or node (optional)
   - Leave empty for automatic selection
3. **Dry Run**: Toggle for simulation mode
4. **Execute Button**: Start the chaos experiment

**Execution Output:**
- Real-time display of experiment results
- JSON-formatted output
- Error messages if execution fails

### 4. Reports Tab

**Report Cards:**
Each report displays:
- Chaos type with icon
- Run ID
- Status badge (completed/failed/dry-run)
- Target service/node
- Start and completion timestamps
- Actions:
  - **View Details**: Open report in modal
  - **HTML**: Open HTML report in new tab

**Report Modal:**
Three tabs for each report:
- **JSON**: Raw JSON data
- **Markdown**: Human-readable markdown
- **HTML**: Formatted HTML report

## API Endpoints

The web UI exposes a REST API for programmatic access:

### Discovery
- `GET /api/discover/services` - List Nomad services
- `GET /api/discover/clients` - List Nomad client nodes

### Targets
- `GET /api/targets?chaos_type={type}` - List chaos targets

### Execution
- `POST /api/execute` - Execute chaos experiment
  ```json
  {
    "chaos_type": "host-down",
    "target_id": "service-name",
    "dry_run": false
  }
  ```

### Node Operations
- `POST /api/node/drain` - Drain a node
  ```json
  {
    "node_id": "538b4367-..."
  }
  ```
- `POST /api/node/eligibility` - Enable/disable node
  ```json
  {
    "node_id": "538b4367-...",
    "enable": true
  }
  ```

### Reports
- `GET /api/reports` - List all reports
- `GET /api/reports/{run_id}?format=json|markdown|html` - Get specific report

### Chaos Types
- `GET /api/chaos-types` - List available chaos types

### Jobs
- `GET /api/chaos-jobs?status={status}` - List chaos jobs

## Screenshots

### Dashboard
```
┌──────────────────────────────────────────────────────────┐
│  ChaosMonkey Dashboard                                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  [Total Nodes: 34]  [Drained: 0]  [Experiments: 24]     │
│                                                          │
│  Recent Experiments          Available Chaos Types       │
│  ├─ 🔥 cpu-hog              ┌──────┐ ┌──────┐          │
│  ├─ 💾 memory-hog           │ 🔥   │ │ 💾   │          │
│  └─ 💀 host-down            │ CPU  │ │ MEM  │          │
│                              └──────┘ └──────┘          │
└──────────────────────────────────────────────────────────┘
```

### Nodes View
```
┌──────────────────────────────────────────────────────────┐
│  Name         Status  Datacenter  CPU       Memory  Drain│
├──────────────────────────────────────────────────────────┤
│  msacc01p1    ready   dev1        8000 MHz  64 GB   No  │
│  msacc02p1    ready   dev1        8000 MHz  64 GB   No  │
│  msacc03p1    ready   dev1        8000 MHz  64 GB   No  │
└──────────────────────────────────────────────────────────┘
```

## Configuration

The web UI uses the same configuration as the CLI:

```bash
# Set Nomad connection
export NOMAD_ADDR=http://nomad-dev-fqdn:4646
export NOMAD_TOKEN=your-token-here
export NOMAD_NAMESPACE=default

# Start web UI
chaosmonkey web
```

## Security Considerations

⚠️ **Important Security Notes:**

1. **Authentication**: The web UI does not include built-in authentication. Use a reverse proxy (nginx, Apache) or API gateway for authentication.

2. **Network Exposure**: By default, the UI binds to `0.0.0.0` (all interfaces). For production:
   ```bash
   # Bind to localhost only
   chaosmonkey web --host 127.0.0.1
   ```

3. **Permissions**: Node drain operations require `node { policy = "write" }` ACL permissions in Nomad.

4. **CORS**: The API includes CORS support for development. Disable in production:
   - Edit `src/chaosmonkey/web/app.py`
   - Remove or configure `CORS(app)`

## Development

### File Structure

```
src/chaosmonkey/web/
├── __init__.py           # Package initialization
├── app.py                # Flask application & API routes
├── templates/
│   └── index.html        # Main dashboard HTML
└── static/
    ├── style.css         # Dashboard styles
    └── app.js            # Dashboard JavaScript
```

### Running in Development Mode

```bash
cd src/chaosmonkey/web
python app.py
```

This starts Flask in debug mode with auto-reload.

### Adding New Features

1. **New API Endpoint**: Add to `app.py`
2. **New UI Component**: Update `templates/index.html`
3. **New Styles**: Add to `static/style.css`
4. **New JavaScript**: Add to `static/app.js`

## Troubleshooting

### Web UI Won't Start

**Error**: `ModuleNotFoundError: No module named 'flask'`

**Solution**:
```bash
pip install flask flask-cors
```

### No Reports Showing

**Issue**: Reports directory is empty

**Solution**:
```bash
# Run some experiments first
chaosmonkey execute --chaos-type cpu-hog --dry-run
```

### Nodes Not Loading

**Issue**: Connection to Nomad failed

**Solution**:
```bash
# Verify Nomad connection
export NOMAD_ADDR=http://your-nomad-address:4646
export NOMAD_TOKEN=your-token

# Test connection
chaosmonkey discover --clients
```

### Permission Errors

**Issue**: "403 Permission denied" when draining nodes

**Solution**: Ensure your Nomad token has `node { policy = "write" }` permissions.

## CLI Integration

The web UI complements the CLI commands:

| CLI Command | Web UI Equivalent |
|-------------|-------------------|
| `chaosmonkey discover --clients` | Nodes Tab |
| `chaosmonkey execute --chaos-type cpu-hog` | Execute Chaos Tab |
| `chaosmonkey report run-xxx` | Reports Tab > View Details |
| `nomad node drain -enable <id>` | Nodes Tab > Drain Button |
| `nomad node eligibility -enable <id>` | Nodes Tab > Enable Button |

## Best Practices

1. **Monitor First**: Always review node status before executing chaos
2. **Start with Dry-Run**: Test experiments in dry-run mode first
3. **Check Reports**: Review experiment reports to understand impact
4. **Coordinate**: Announce chaos experiments to your team
5. **Recovery Ready**: Have recovery procedures documented

## Future Enhancements

Planned features:
- [ ] User authentication and authorization
- [ ] Scheduled chaos experiments
- [ ] Grafana integration for metrics
- [ ] Slack/Teams notifications
- [ ] Experiment templates builder
- [ ] Multi-cluster support
- [ ] Historical trend analysis
- [ ] Automated recovery workflows

## Support

For issues or questions:
- Check documentation: `docs/`
- Review examples: `reports/`
- CLI help: `chaosmonkey --help`
- Web API: http://localhost:8080/api/

## License

Apache-2.0

---

**Built with ❤️ for Chaos Engineering**
