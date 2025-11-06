# Chaos Engineering Implementation for Nomad Services

## Overview

The ChaosMonkey toolkit now **intelligently deploys chaos experiments** to Nomad cluster nodes where your services are actually running. It's not running chaos locally—it's deploying real stress jobs to the remote Nomad client machines.

## How It Works

### Architecture

```
┌─────────────────────────────────────┐
│  Your Machine (ChaosMonkey CLI)     │
│  ├─ Discovers services from Nomad   │
│  ├─ Identifies target node          │
│  └─ Deploys chaos job via API       │
└───────────────┬─────────────────────┘
                │
                ↓ Nomad API
┌─────────────────────────────────────┐
│  Nomad Cluster                      │
│  ├─ Schedules chaos job             │
│  ├─ Places on target node           │
│  └─ Executes stress container       │
└───────────────┬─────────────────────┘
                │
                ↓ Docker/Container Runtime
┌─────────────────────────────────────┐
│  Target Nomad Client Node           │
│  ├─ Your Service (being tested)     │
│  └─ Chaos Stress Job (stressing)    │
└─────────────────────────────────────┘
```

### Smart Discovery Process

When you run a chaos experiment, the system:

1. **Discovers Service Location**
   - Queries Nomad API for all allocations
   - Filters for running allocations of the target service
   - Identifies the node ID and name

2. **Gathers Node Intelligence**
   - Queries Nomad for node details
   - Extracts datacenter information
   - Retrieves resource availability (CPU, Memory)
   - Counts how many allocations are on that node

3. **Creates Targeted Chaos Job**
   - Generates unique job ID with timestamp
   - Configures appropriate datacenter
   - Sets node constraint to force co-location
   - Specifies resource requirements

4. **Deploys via Nomad API**
   - Submits job specification to Nomad
   - Receives evaluation ID
   - Verifies job scheduling
   - Reports deployment status

5. **Auto-Cleanup**
   - Job is configured as "batch" type
   - Automatically terminates after duration
   - No manual cleanup required

## Available Chaos Types

### 1. CPU Stress (`cpu-hog`) ✅ **IMPLEMENTED**

**What it does:**
- Deploys a `stress-ng` Docker container to the target node
- Stresses all available CPU cores
- Runs for configured duration (default: 120s)
- Auto-terminates and cleans up

**Technical Details:**
- **Image**: `alexeiled/stress-ng:latest-ubuntu`
- **Method**: Uses all CPU stress methods
- **Resource Request**: 3000 MHz CPU, 512 MB RAM
- **Driver**: Docker
- **Constraint**: Pinned to specific node via `${node.unique.id}`

**Example Output:**
```
[discovery] Searching for service: mobi-platform-account-service-job
[discovery] Found 1 running allocation(s)
[discovery] Target node: hostname
[discovery] Datacenter: dev1, Class: 
[deploy] Submitting chaos job: chaos-cpu-mobi-platform-account-service-job-xxx
[deploy] Target: mobi-platform-account-service-job on hostname
[success] ✓ Chaos job deployed successfully!
[success] ✓ Job will stress CPU for 120s and auto-terminate
[verify] Job status: running
```

### 2. Network Latency (`network-latency`) 🚧 **STUB**

**Planned Implementation:**
- Use `tc` (traffic control) or Toxiproxy
- Inject artificial latency to service connections
- Default: 250ms delay

### 3. Packet Loss (`packet-loss`) 🚧 **STUB**

**Planned Implementation:**
- Use `tc` with netem
- Drop packets randomly
- Default: 15% loss rate

### 4. Host Down (`host-down`) 🚧 **STUB**

**Planned Implementation:**
- Drain node allocations
- Simulate node failure
- Test service failover

## Usage

### Basic CPU Stress Test

```bash
# Stress a specific service for 120 seconds (default)
chaosmonkey execute --chaos-type cpu-hog --target-id <service-id>

# Examples:
chaosmonkey execute --chaos-type cpu-hog --target-id mobi-platform-account-service-job
chaosmonkey execute --chaos-type cpu-hog --target-id mobi-platform-api-gateway-envoy-job
```

### List Available Targets

```bash
# Show all services that can be targeted
chaosmonkey targets

# Filter by chaos type compatibility
chaosmonkey targets --chaos-type cpu-hog
```

### Discover Cluster

```bash
# See all services and their status
chaosmonkey discover

# Include allocation details
chaosmonkey discover --allocations
```

### View Reports

```bash
# List generated reports
ls -la reports/

# View a specific report
cat reports/run-<id>.md

# View JSON metadata
jq . reports/run-<id>.json
```

## Configuration

### Environment Variables

Set these in your `.env` file or shell:

```bash
NOMAD_ADDR=http://your-nomad-server:4646
NOMAD_TOKEN=your-nomad-acl-token
NOMAD_NAMESPACE=default
NOMAD_REGION=global  # optional
```

### Chaos Parameters

Modify in `src/chaosmonkey/core/experiments.py`:

```python
replacements = {
    "duration_seconds": 120,  # How long to stress
    "latency_ms": 250,        # Network latency (future)
    "packet_loss_percentage": "15%",  # Packet loss (future)
}
```

## Technical Implementation Details

### Key Files

- **`src/chaosmonkey/stubs/actions.py`**: Chaos action implementations
  - `run_cpu_stress()`: Main CPU stress implementation
  - `_get_service_node_info()`: Smart service discovery
  - `_get_nomad_client()`: Nomad API client factory

- **`src/chaosmonkey/core/nomad.py`**: Nomad integration
  - Service discovery
  - Allocation enumeration
  - Target selection

- **`src/chaosmonkey/core/orchestrator.py`**: Experiment orchestration
  - Coordinates discovery and execution
  - Manages experiment lifecycle
  - Generates reports

- **`src/chaosmonkey/core/experiments.py`**: Template rendering
  - Variable substitution
  - Configuration injection

### Dependencies

- **`python-nomad`**: Nomad API client
- **`chaostoolkit-lib`**: Chaos Toolkit framework
- **`typer`**: CLI framework
- **`rich`**: Terminal output formatting

### Nomad Job Specification

The CPU stress job uses this structure:

```json
{
  "Job": {
    "ID": "chaos-cpu-<service>-<timestamp>",
    "Type": "batch",
    "Datacenters": ["<auto-detected>"],
    "Constraints": [{
      "LTarget": "${node.unique.id}",
      "RTarget": "<target-node-id>",
      "Operand": "="
    }],
    "TaskGroups": [{
      "Tasks": [{
        "Driver": "docker",
        "Config": {
          "image": "alexeiled/stress-ng:latest-ubuntu",
          "args": ["--cpu", "0", "--timeout", "120s"]
        }
      }]
    }]
  }
}
```

## Verification

### How to Verify It's Working

1. **Check Nomad UI**
   - Open Nomad UI: `http://your-nomad-server:4646/ui`
   - Look for jobs starting with `chaos-cpu-`
   - View allocations and logs

2. **Monitor Node CPU**
   ```bash
   # SSH to the target node
   ssh <node-name>
   
   # Watch CPU usage
   htop
   # or
   top
   ```

3. **Check Docker Containers**
   ```bash
   # On the target node
   docker ps | grep stress-ng
   
   # View logs
   docker logs <container-id>
   ```

4. **Query Nomad API**
   ```bash
   # List chaos jobs
   curl -s http://nomad-server:4646/v1/jobs | jq '.[] | select(.ID | startswith("chaos-cpu"))'
   
   # Get job status
   curl -s http://nomad-server:4646/v1/job/chaos-cpu-<job-id> | jq .
   ```

## Troubleshooting

### Job Not Deploying

**Issue**: Job submission fails

**Solutions**:
- Check Nomad ACL token has write permissions
- Verify node has Docker driver available
- Ensure datacenter name is correct
- Check if node has available resources

### Job Pending/Blocked

**Issue**: Job stuck in pending state

**Solutions**:
- Node might be at capacity
- Docker image pull might be slow
- Check constraints are satisfiable
- View allocation events in Nomad UI

### No CPU Stress Observed

**Issue**: Job runs but CPU isn't stressed

**Solutions**:
- Check if stress-ng container is actually running
- View container logs for errors
- Verify Docker driver is functioning
- Check if node has available CPU

## Future Enhancements

### Planned Features

1. **Multiple Node Targeting**
   - Stress multiple nodes simultaneously
   - Test distributed system resilience

2. **Memory Stress**
   - Add memory exhaustion experiments
   - Test OOM killer behavior

3. **Network Chaos**
   - Implement latency injection
   - Packet loss simulation
   - Network partition testing

4. **Disk I/O Stress**
   - Disk read/write saturation
   - Test storage resilience

5. **Service Draining**
   - Graceful service shutdown
   - Test failover mechanisms

6. **Custom Stress Profiles**
   - User-defined stress patterns
   - Gradual ramp-up/ramp-down
   - Spike testing

## Best Practices

1. **Start Small**: Test with short durations (10-30s) first
2. **Monitor**: Watch metrics during chaos experiments
3. **Off-Hours**: Run chaos tests during low-traffic periods initially
4. **Gradual Rollout**: Test one service at a time
5. **Document**: Record results and system behavior
6. **Alert Testing**: Verify your monitoring alerts fire correctly
7. **Cleanup**: Verify jobs auto-cleanup after completion

## Safety Features

- ✅ Jobs are `batch` type (not services)
- ✅ Auto-termination after duration
- ✅ No manual cleanup required
- ✅ Constraints prevent runaway deployments
- ✅ Resource limits prevent total exhaustion
- ✅ Detailed logging for audit trails

## Success Metrics

Your chaos engineering is working when:

1. ✅ Jobs deploy to correct nodes
2. ✅ CPU stress is visible on target nodes
3. ✅ Services show degraded performance
4. ✅ Monitoring alerts trigger appropriately
5. ✅ Services recover after chaos ends
6. ✅ No manual intervention required

---

**Status**: CPU Stress chaos is fully functional and deploying to remote Nomad nodes! 🎉
