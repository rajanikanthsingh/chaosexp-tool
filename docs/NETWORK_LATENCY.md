# Network Latency Chaos Experiment

## Overview

The **Network Latency** chaos experiment injects artificial network delays into Docker containers running on Nomad client nodes. This tests how your services behave under poor network conditions, simulating scenarios like slow networks, distant data centers, or network congestion.

## How It Works

### Architecture

```
┌─────────────────────────────────────────┐
│  Nomad Client Node                      │
│  (e.g., hostname)     │
├─────────────────────────────────────────┤
│                                         │
│  🎯 Your Service Container              │
│     └─ Responds to requests normally    │
│     └─ Network: eth0                    │
│                                         │
│  💣 Pumba Chaos Container               │
│     └─ Monitors Docker containers       │
│     └─ Injects network latency via tc   │
│     └─ Affects matching containers      │
│                                         │
│  ⚡ Network Delay Applied!              │
│     └─ Every packet delayed +250ms      │
│     └─ Affects inbound & outbound       │
│     └─ Creates realistic slow network   │
│     └─ No packets dropped (just slow)   │
└─────────────────────────────────────────┘
```

### Technology: Pumba

We use **Pumba** (https://github.com/alexei-led/pumba), a chaos testing tool for Docker:

- ✅ **No privileged mode needed** (uses Docker socket)
- ✅ **Container-level precision** (targets specific containers)
- ✅ **Built on `tc netem`** (Linux traffic control)
- ✅ **Automatic cleanup** (removes latency after duration)
- ✅ **Pattern matching** (can target multiple containers)

### What Happens

1. **Container Discovery**: Pumba scans Docker containers on the node
2. **Pattern Matching**: Finds containers matching your service name
3. **Latency Injection**: Uses `tc netem` to add delay to network interface
4. **Duration**: Maintains latency for specified duration
5. **Cleanup**: Automatically removes latency when done

## Configuration

### Default Settings

```python
latency_ms = 250           # 250ms delay per packet
duration = 120             # 120 seconds
interface = "eth0"         # Container network interface
```

### Customization

Edit `src/chaosmonkey/core/experiments.py`:

```python
replacements = {
    "latency_ms": 500,     # 500ms for more aggressive delay
    "duration_seconds": 300 # 5 minutes
}
```

Or modify the script in `src/chaosmonkey/stubs/actions.py`:

```python
# Add jitter (random variation)
pumba netem delay \
    --time {latency_ms_int} \
    --jitter 50 \  # ±50ms variation
    "re2:{service_pattern}"

# Add correlation (realistic packet delay patterns)
pumba netem delay \
    --time {latency_ms_int} \
    --correlation 25 \  # 25% correlation
    "re2:{service_pattern}"
```

## Usage

### Basic Network Latency

```bash
# Default 250ms latency for 120 seconds
chaosmonkey execute --chaos-type network-latency --target-id <service-id>

# Example
chaosmonkey execute --chaos-type network-latency --target-id mobi-platform-account-service-job
```

### List Network Chaos Jobs

```bash
# See all chaos jobs
chaosmonkey chaos-jobs

# Look for chaos-lat-* jobs
chaosmonkey chaos-jobs | grep "chaos-lat"
```

### Expected Output

```
[discovery] Searching for service: mobi-platform-account-service-job
[discovery] Found 1 running allocation(s)
[discovery] Target node: hostname
[discovery] Datacenter: dev1
[strategy] Injecting 250ms network latency
[strategy] Duration: 120s on hostname
[strategy] Using Pumba for Docker network chaos
[deploy] Submitting chaos job: chaos-lat-mobi-platform-account-service-job-xxx
[deploy] Target: mobi-platform-account-service-job on hostname
[deploy] Network latency: 250ms for 120s
[impact] Expected impact: Slow network responses, increased timeouts
[success] ✓ Chaos job deployed successfully!
[verify] Job status: running
```

## Expected Impact

### On Target Service

| Metric | Normal | With 250ms Latency | Impact |
|--------|--------|-------------------|---------|
| **API Response Time** | 50ms | 300ms | 6x slower |
| **Database Query** | 10ms | 260ms | 26x slower |
| **External API Call** | 100ms | 350ms | 3.5x slower |
| **Timeout Rate** | <0.1% | 2-5% | Timeouts increase |
| **Throughput** | 1000 req/s | 200 req/s | 80% reduction |

### System Symptoms

1. **Slow Response Times**
   - Every network call delayed by 250ms
   - Round-trip time increases by 500ms
   - Cascading delays in service chains

2. **Increased Timeouts**
   - Requests near timeout threshold fail
   - Retry logic triggers more frequently
   - Connection pool exhaustion

3. **Degraded User Experience**
   - Page load times increase
   - API calls feel sluggish
   - Real-time features lag

4. **System Backpressure**
   - Request queues build up
   - Connection pools saturate
   - Thread pools block waiting

## Verification

### 1. Check Network Latency (Inside Container)

```bash
# SSH to the node
ssh hostname

# Find your service container
docker ps | grep mobi-platform-account

# Enter the container
docker exec -it <container-id> sh

# Test latency to external service
ping -c 5 google.com

# Expected output shows ~250ms added delay:
# 64 bytes from google.com: icmp_seq=1 ttl=54 time=251.234 ms
# 64 bytes from google.com: icmp_seq=2 ttl=54 time=250.987 ms
```

### 2. Check Pumba Logs

```bash
# On the node, find Pumba container
docker ps | grep pumba

# View Pumba logs
docker logs <pumba-container-id>

# Expected output:
# ===================================
# Pumba Network Latency Chaos
# ===================================
# Target Service: mobi-platform-account-service-job
# Latency: 250ms
# Duration: 120s
```

### 3. Check tc Configuration

```bash
# Inside the target container
docker exec -it <service-container-id> sh

# Check traffic control rules (if tc is available)
tc qdisc show dev eth0

# Expected output:
# qdisc netem 8001: root refcnt 2 limit 1000 delay 250.0ms
```

### 4. Test from Another Service

```bash
# From a different container on the same node
docker exec -it <other-container> sh

# Install curl if needed
apk add --no-cache curl

# Time a request to the service
time curl http://<service-ip>:<port>/health

# Expected: ~250ms slower than normal
```

### 5. Monitor Service Metrics

```bash
# Check your service's response time metrics
# Prometheus query example:
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Grafana: Look for response time spike of ~250ms
```

### 6. Application Logs

Check for timeout errors:

```bash
# SSH to node
ssh hostname

# Check service logs
docker logs <service-container-id> | grep -i timeout

# Look for:
- "connection timeout"
- "read timeout"
- "request timeout"
- "deadline exceeded"
```

## Technical Details

### Pumba Command Breakdown

```bash
pumba netem \
    --duration 120s \      # How long to maintain latency
    --interface eth0 \     # Network interface to affect
    delay \                # Type of network chaos
    --time 250 \           # Delay in milliseconds
    "re2:service-pattern"  # Regex to match container names
```

### How tc netem Works

`tc netem` (Network Emulator) is a Linux kernel feature:

```bash
# What Pumba does under the hood:
tc qdisc add dev eth0 root netem delay 250ms

# This creates a queuing discipline that:
# 1. Intercepts every outgoing packet
# 2. Delays it by 250ms
# 3. Then sends it
#
# After duration expires:
tc qdisc del dev eth0 root
```

### Container Pattern Matching

Pumba uses RE2 regex to find containers:

```python
service_pattern = "mobi-platform-account-service"

# Matches containers like:
# - mobi-platform-account-service-xyz123
# - mobi-platform-account-service-abc456
# - mobi-platform-account-service-web-789
```

### Nomad Job Specification

```json
{
  "Job": {
    "ID": "chaos-lat-<service>-<timestamp>",
    "Type": "batch",
    "TaskGroups": [{
      "Tasks": [{
        "Driver": "docker",
        "Config": {
          "image": "gaiaadm/pumba:latest",
          "volumes": [
            "/var/run/docker.sock:/var/run/docker.sock"
          ]
        },
        "Resources": {
          "CPU": 200,
          "MemoryMB": 256
        }
      }]
    }]
  }
}
```

## Safety Considerations

### Built-in Safety

✅ **Time-limited**: Auto-removes latency after duration  
✅ **Scoped**: Only affects matched containers  
✅ **Non-destructive**: No data loss, just delay  
✅ **Reversible**: Automatic cleanup guaranteed  
✅ **Logged**: All actions logged for audit  

### Potential Risks

⚠️ **Service Timeouts**: May cause request failures  
⚠️ **Cascading Delays**: Affects downstream services  
⚠️ **Connection Pool Exhaustion**: Long-lived connections  
⚠️ **User Impact**: Noticeable performance degradation  

### Risk Mitigation

1. **Start with Small Latency**
   ```python
   latency_ms = 50  # Start with 50ms
   duration = 30    # Short duration
   ```

2. **Test During Off-Hours**
   - Low traffic periods
   - Maintenance windows
   - Development/staging first

3. **Monitor Actively**
   - Watch error rates
   - Monitor timeout metrics
   - Have rollback ready

4. **Set Reasonable Timeouts**
   ```yaml
   # In your service config
   http:
     timeout:
       connect: 5s
       read: 10s
       write: 10s
   ```

5. **Use Circuit Breakers**
   ```go
   // Example circuit breaker config
   circuitBreaker:
     threshold: 5
     timeout: 30s
   ```

## Emergency Stop

### Method 1: Stop via Nomad

```bash
# Find the chaos job
nomad job status | grep chaos-lat

# Stop it
nomad job stop chaos-lat-<service>-<timestamp>

# Latency is removed immediately
```

### Method 2: Kill Pumba Container

```bash
# On the node
docker ps | grep pumba
docker kill <pumba-container-id>

# Note: Latency may persist if not cleaned up properly
```

### Method 3: Manual Cleanup (Last Resort)

```bash
# SSH to node
ssh <node>

# Enter service container
docker exec -it <service-container> sh

# Remove tc rules (if available)
tc qdisc del dev eth0 root

# Or restart container to reset networking
docker restart <service-container>
```

## Comparison: Network Latency vs Other Chaos

| Aspect | Network Latency | CPU Hog | Memory Hog |
|--------|-----------------|---------|------------|
| **Resource** | Network | CPU | Memory |
| **Impact** | Slow responses | Slow processing | OOM errors |
| **Severity** | Medium | Medium | High |
| **Detection** | Response time | CPU metrics | Memory metrics |
| **Recovery** | Automatic | Automatic | May need restart |
| **Scope** | Network calls | All processing | Memory ops |

## Advanced Configurations

### Add Jitter (Variable Latency)

```python
# In actions.py, modify the pumba command:
latency_script = f"""
pumba netem \
    --duration {duration_int}s \
    --interface eth0 \
    delay \
    --time {latency_ms_int} \
    --jitter 50 \  # ±50ms random variation
    "re2:{service_pattern}"
"""
```

This creates realistic latency: 200ms, 230ms, 270ms, 250ms, etc.

### Add Correlation (Realistic Patterns)

```python
latency_script = f"""
pumba netem \
    --duration {duration_int}s \
    delay \
    --time {latency_ms_int} \
    --jitter 30 \
    --correlation 25 \  # 25% correlation between packets
    "re2:{service_pattern}"
"""
```

Makes consecutive packets have similar delays (more realistic).

### Target Specific Traffic

```python
# Add distribution for more realistic behavior
latency_script = f"""
pumba netem \
    --duration {duration_int}s \
    delay \
    --time {latency_ms_int} \
    --jitter 50 \
    --distribution normal \  # Normal (Gaussian) distribution
    "re2:{service_pattern}"
"""
```

### Asymmetric Latency

For different inbound/outbound delays, you'd need to:

1. Run Pumba twice with different targets
2. Use tc directly with egress/ingress filtering
3. Use more advanced tools like Toxiproxy

## Troubleshooting

### Pumba Container Fails to Start

**Symptom**: Job status "failed" immediately

**Causes**:
- Docker socket not accessible
- Insufficient permissions
- Pumba image not available

**Solution**:
```bash
# On the node, check Docker socket
ls -la /var/run/docker.sock

# Pull Pumba image manually
docker pull gaiaadm/pumba:latest
```

### No Latency Observed

**Symptom**: Service response times unchanged

**Possible Reasons**:
1. Container name pattern doesn't match
2. Latency is negligible compared to processing time
3. Service uses connection pooling (first request slow, rest cached)

**Solutions**:
```bash
# Check Pumba logs for matching containers
docker logs <pumba-container>

# Increase latency
latency_ms = 1000  # Try 1 second

# Test with simple ping
docker exec <service-container> ping -c 5 google.com
```

### Latency Persists After Job Stops

**Symptom**: Network still slow after chaos ends

**Cause**: Pumba cleanup failed

**Solution**:
```bash
# SSH to node
ssh <node>

# Find service container
docker ps | grep <service>

# Enter container and check tc rules
docker exec -it <container> tc qdisc show

# If rules exist, remove them:
docker exec -it <container> tc qdisc del dev eth0 root

# Or restart container
docker restart <container>
```

### "Device not found" Error

**Symptom**: Pumba logs show "Cannot find device eth0"

**Cause**: Container uses different network interface

**Solution**:
```python
# In actions.py, auto-detect interface:
latency_script = f"""
#!/bin/sh
INTERFACE=$(ip route | grep default | awk '{{{{print $5}}}}' | head -n1)
echo "Using interface: $INTERFACE"

pumba netem \
    --interface $INTERFACE \
    delay --time {latency_ms_int} \
    "re2:{service_pattern}"
"""
```

## Success Metrics

Network latency testing is successful when you can answer:

✅ How does the service handle slow network conditions?  
✅ Are timeout values properly configured?  
✅ Do circuit breakers engage at appropriate thresholds?  
✅ Does retry logic work correctly?  
✅ Are connection pools sized appropriately?  
✅ Do users see graceful degradation?  
✅ Are monitoring alerts triggered?  

## Real-World Scenarios

This chaos type simulates:

1. **Cross-Region Communication** (50-200ms)
   - Services in different data centers
   - Multi-region deployments

2. **Cellular Networks** (100-500ms)
   - Mobile app backends
   - Edge computing scenarios

3. **Satellite Links** (500-1000ms)
   - Remote locations
   - Maritime/aviation systems

4. **Network Congestion** (100-300ms)
   - Peak traffic periods
   - DDoS aftermath

5. **VPN Overhead** (50-150ms)
   - Remote workers
   - Secure tunnels

## Best Practices

1. **Test Progressive Latency**
   ```bash
   # Start small
   chaosmonkey execute --chaos-type network-latency  # 250ms
   
   # Gradually increase
   # 500ms, 1000ms, 2000ms
   ```

2. **Combine with Load Testing**
   - Run latency chaos during load tests
   - See how system behaves under both stress and latency

3. **Test Retry Logic**
   - Ensure services don't amplify problems
   - Validate exponential backoff

4. **Document Findings**
   - Which timeouts need adjustment?
   - Which services are most sensitive?
   - What's the user impact threshold?

5. **Automate Regular Testing**
   - Weekly chaos drills
   - Catch regressions early
   - Build confidence in system resilience

## Next Steps

1. **Establish baseline metrics** before chaos
2. **Test with different latency values** (50ms → 250ms → 1000ms)
3. **Validate timeout configurations** across services
4. **Implement circuit breakers** where needed
5. **Test retry and fallback logic**
6. **Improve monitoring and alerting**

---

**Remember**: Network latency is one of the most common real-world failures. Testing it regularly builds resilient systems! 🌐
