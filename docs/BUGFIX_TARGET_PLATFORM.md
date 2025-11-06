# Bug Fix: Target Platform Attribute Error

## Issue

When executing chaos experiments, the system was crashing with:
```
AttributeError: 'Target' object has no attribute 'platform'
```

## Root Cause

The `orchestrator.py` was trying to access `target.platform` attribute which doesn't exist in the `Target` dataclass. The correct attribute is `target.kind`.

### Target Model Structure
```python
@dataclass(slots=True)
class Target:
    identifier: str
    kind: str  # ← This is the correct attribute (not 'platform')
    attributes: Dict[str, str] = field(default_factory=dict)
```

## Affected Code Locations

### 1. `orchestrator.py` Line 212
**Before:**
```python
during_metrics = self._metrics.collect_continuous_metrics(
    target_type=target.platform.lower(),  # ❌ Wrong
    target_id=target.identifier,
    duration_seconds=metrics_duration,
    interval_seconds=metrics_interval,
    label="during"
)
```

**After:**
```python
during_metrics = self._metrics.collect_continuous_metrics(
    target_type=target.kind.lower(),  # ✅ Correct
    target_id=target.identifier,
    duration_seconds=metrics_duration,
    interval_seconds=metrics_interval,
    label="during"
)
```

### 2. `orchestrator.py` Line 262 (_collect_target_metrics method)
**Before:**
```python
def _collect_target_metrics(self, target: Target, label: str) -> Optional[Dict[str, Any]]:
    """Collect metrics for a target based on its platform."""
    try:
        platform = target.platform.lower()  # ❌ Wrong
        
        if platform == "allocation":
            ...
        elif platform == "job":
            ...
        elif platform == "node":
            ...
        else:
            print(f"⚠️  Unknown platform {platform}, skipping metrics collection")
```

**After:**
```python
def _collect_target_metrics(self, target: Target, label: str) -> Optional[Dict[str, Any]]:
    """Collect metrics for a target based on its kind."""
    try:
        target_kind = target.kind.lower()  # ✅ Correct
        
        if target_kind == "allocation":
            return self._metrics.collect_nomad_allocation_metrics(
                allocation_id=target.identifier,
                label=label
            )
        elif target_kind == "job":
            return self._metrics.collect_nomad_job_metrics(
                job_id=target.identifier,
                label=label
            )
        elif target_kind == "node":
            return self._metrics.collect_node_metrics(
                node_id=target.identifier,
                label=label
            )
        elif target_kind == "service":
            # For services, try to get the allocation from attributes
            if "allocation_id" in target.attributes:
                return self._metrics.collect_nomad_allocation_metrics(
                    allocation_id=target.attributes["allocation_id"],
                    label=label
                )
            else:
                print(f"⚠️  Service target {target.identifier} has no allocation_id, skipping metrics")
                return None
        else:
            print(f"⚠️  Unknown target kind {target_kind}, skipping metrics collection")
            return None
```

## Target Kinds

The system supports these target kinds:

| Kind | Description | Metrics Collection Method |
|------|-------------|---------------------------|
| `allocation` | Nomad allocation | `collect_nomad_allocation_metrics()` |
| `job` | Nomad job | `collect_nomad_job_metrics()` |
| `node` | Nomad node | `collect_node_metrics()` |
| `service` | Nomad service | Uses `allocation_id` from attributes |

## Example Target Objects

### Node Target (Your Case)
```python
Target(
    identifier='09555425-9f96-1555-abf9-bdad45e8231a',
    kind='node',  # ← This is what we should use
    attributes={
        'name': 'hostname',
        'status': 'ready',
        'drain': False,
        'scheduling_eligibility': 'eligible'
    }
)
```

### Allocation Target
```python
Target(
    identifier='abc123-allocation-id',
    kind='allocation',
    attributes={
        'name': 'web-service.task[0]',
        'job_id': 'web-service',
        'status': 'running'
    }
)
```

### Service Target
```python
Target(
    identifier='web-service',
    kind='service',
    attributes={
        'name': 'web-service',
        'node': 'some-node-id',
        'status': 'running',
        'allocation_id': 'abc123-allocation-id',  # Used for metrics
        'address': '10.0.0.1',
        'port': 8080
    }
)
```

## Testing

### Before Fix
```bash
$ chaosmonkey execute --chaos-type memory-hog --target-id 09555425-9f96-1555-abf9-bdad45e8231a

# Result: AttributeError: 'Target' object has no attribute 'platform'
```

### After Fix
```bash
$ chaosmonkey execute --chaos-type memory-hog --target-id 09555425-9f96-1555-abf9-bdad45e8231a

# Expected output:
# 📊 Collecting baseline metrics for 09555425-9f96-1555-abf9-bdad45e8231a...
# 🔥 Executing chaos experiment...
# 📊 Collecting metrics during chaos (duration: 60s, interval: 5s)...
# 📊 Collecting post-chaos metrics for 09555425-9f96-1555-abf9-bdad45e8231a...
# ✅ Experiment completed successfully!
```

## Impact

✅ **Fixed:** Metrics collection now works for all target types (allocation, job, node, service)  
✅ **Enhanced:** Added proper handling for service targets with allocation_id lookup  
✅ **Improved:** Better error messages for unsupported target kinds

## Files Modified

1. **`src/chaosmonkey/core/orchestrator.py`**
   - Line 212: Changed `target.platform` → `target.kind`
   - Lines 260-295: Refactored `_collect_target_metrics()` method
   - Added service target support with allocation_id fallback

## Related Documentation

- [METRICS_COLLECTION.md](METRICS_COLLECTION.md) - Full metrics guide
- [METRICS_QUICKSTART.md](METRICS_QUICKSTART.md) - Quick start guide
- [models.py](../src/chaosmonkey/core/models.py) - Target dataclass definition

---

*Fixed: October 10, 2025*  
*Bug ID: target-platform-attribute-error*  
*Severity: Critical*  
*Status: Resolved* ✅
