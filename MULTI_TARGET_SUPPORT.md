# Multi-Target Support Implementation

## Overview
Added support for running chaos experiments on multiple targets simultaneously from the Web UI.

## Changes Made

### 1. Multi-Target Selection Support (`orchestrator.py`)

#### New Method: `_select_multiple_targets()`
```python
def _select_multiple_targets(self, target_ids: List[str], targets: List[Target]) -> List[Target]:
    """Select multiple targets by their IDs."""
    selected = []
    for target_id in target_ids:
        for candidate in targets:
            if candidate.identifier == target_id:
                selected.append(candidate)
                break
    return selected
```

#### Updated: `run_experiment()`
- Now detects comma-separated target IDs
- Splits the target_id string and processes each target
- Calls `_run_single_experiment()` for each target sequentially
- Returns consolidated result

#### New Method: `_run_single_experiment()`
- Extracted single-target experiment logic from `run_experiment()`
- Handles one target at a time
- Collects metrics (before/during/after)
- Generates report

### 2. How It Works

**Before:**
```python
target_id = "abc-123"  # Single target
run_experiment(target_id="abc-123", ...)
```

**After:**
```python
target_id = "abc-123,def-456,ghi-789"  # Multiple targets
run_experiment(target_id="abc-123,def-456,ghi-789", ...)

# Internally splits to:
# ["abc-123", "def-456", "ghi-789"]
# Runs experiment on each sequentially
```

### 3. Web UI Integration

The Web UI already sends multiple selected nodes as comma-separated values:
```javascript
// app.js (existing code)
const selectedTargets = Array.from(targetCheckboxes)
    .filter(cb => cb.checked)
    .map(cb => cb.value)
    .join(',');  // Creates: "id1,id2,id3"
```

No Web UI changes required!

## Execution Flow

```
User selects multiple nodes in UI
    ↓
UI sends: "node1-uuid,node2-uuid,node3-uuid"
    ↓
orchestrator.run_experiment() detects comma
    ↓
Splits into: ["node1-uuid", "node2-uuid", "node3-uuid"]
    ↓
Calls _select_multiple_targets()
    ↓
For each target:
    1. Print target info
    2. Run _run_single_experiment()
    3. Collect metrics (before/during/after)
    4. Generate report
    5. Store result
    ↓
Return consolidated result
```

## Current Behavior

### Sequential Execution
- Experiments run **one at a time** on each target
- Target 1 completes → Target 2 starts → Target 3 starts
- Safer approach, easier to track individual results

### Individual Reports
Each target gets:
- ✅ Separate JSON report in `reports/`
- ✅ Separate HTML report
- ✅ Individual metrics collection (before/during/after)
- ✅ Individual Prometheus graphs

### Console Output
```
🎯 Running chaos on target: 13b3c90c-bf1c-399c-0a48-f15c36537312 (hostname)
📊 Collecting baseline metrics...
💥 Executing disk I/O stress...
📊 Collecting metrics during chaos...
📊 Collecting post-chaos metrics...
✅ Chaos completed: run-abc12345

🎯 Running chaos on target: 13f8663e-c348-846d-b516-cb8531eee6fe (hostname)
📊 Collecting baseline metrics...
...
```

## Future Enhancements

### Parallel Execution (TODO)
```python
# Could use concurrent.futures for parallel execution
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(self._run_single_experiment, target, ...)
        for target in selected_targets
    ]
    results = [f.result() for f in futures]
```

### Consolidated Multi-Target Report (TODO)
- Single HTML report showing all targets
- Side-by-side metrics comparison
- Aggregate statistics
- Combined timeline view

## Testing

### Test Case 1: Single Node (backward compatibility)
```bash
# Select one node in UI
Target: msepg01p1
Result: ✅ Works as before
```

### Test Case 2: Multiple Nodes
```bash
# Select 3 nodes in UI
Targets: msepg01p1, msepg02p1, msepg03p1
Result: ✅ Runs chaos on each sequentially
```

### Test Case 3: Invalid Targets
```bash
# Mix valid and invalid IDs
Targets: valid-id-1, invalid-id, valid-id-2
Result: Only valid targets processed, no error
```

## Error Handling

### No Targets Found
```python
if not selected_targets:
    raise ValueError(f"None of the specified targets found: {target_id}")
```

### Partial Success
- If Target 1 succeeds but Target 2 fails
- Target 1 report is saved
- Error logged for Target 2
- Execution continues with Target 3

## Steady State Hypothesis

### Status: Already Implemented ✅

The steady state hypothesis was **never removed** - it's already in the report generation code and appears in reports **when there's data to display**.

### How It Works

1. **Experiment Templates** (`src/chaosmonkey/experiments/templates/*.json`)
   - All templates have `steady-state-hypothesis` section
   - Currently have empty `probes` arrays
   - Example:
   ```json
   {
     "steady-state-hypothesis": {
       "title": "Service I/O performance remains acceptable",
       "probes": []
     }
   }
   ```

2. **Experiment Execution**
   - Chaos Toolkit runs steady state probes before and after experiment
   - Results stored in `output["steady_states"]`:
     ```json
     {
       "steady_states": {
         "before": null,
         "after": null,
         "during": []
       }
     }
     ```

3. **Report Generation** (`orchestrator.py` lines 643-668)
   ```python
   # Steady state section
   steady_states = result.get("steady_states", {})
   if steady_states and (steady_states.get("before") or steady_states.get("after")):
       lines.extend([
           "",
           "## 📊 Steady State Validation",
           "",
       ])
       
       if steady_states.get("before"):
           lines.extend([
               "### Before Experiment",
               "```json",
               json.dumps(steady_states["before"], indent=2),
               "```",
           ])
       
       if steady_states.get("after"):
           lines.extend([
               "### After Experiment", 
               "```json",
               json.dumps(steady_states["after"], indent=2),
               "```",
           ])
   ```

### Why You Don't See It

The steady state section **only appears when probes return data**. Currently:
- ❌ Templates have `"probes": []` (empty)
- ❌ No actual validation happens
- ❌ `before` and `after` are `null`
- ❌ Report generation skips the section

### To Enable Steady State Validation

Add probes to experiment templates. Example for disk I/O:

```json
{
  "steady-state-hypothesis": {
    "title": "Node disk I/O performance remains acceptable",
    "probes": [
      {
        "type": "probe",
        "name": "Check node is ready",
        "tolerance": {
          "type": "probe",
          "name": "node-is-ready"
        },
        "provider": {
          "type": "python",
          "module": "chaosmonkey.stubs.probes",
          "func": "check_node_status",
          "arguments": {
            "node_id": "${target_id}"
          }
        }
      },
      {
        "type": "probe",
        "name": "Check disk I/O latency",
        "tolerance": {
          "type": "range",
          "range": [0, 100],
          "target": "stdout"
        },
        "provider": {
          "type": "python",
          "module": "chaosmonkey.stubs.probes",
          "func": "check_disk_latency",
          "arguments": {
            "node_id": "${target_id}",
            "max_latency_ms": 100
          }
        }
      }
    ]
  }
}
```

Then implement the probe functions in `src/chaosmonkey/stubs/probes.py`:

```python
def check_node_status(node_id: str) -> dict:
    """Check if node is in ready state."""
    # Query Nomad API
    # Return {"status": "ready"}
    pass

def check_disk_latency(node_id: str, max_latency_ms: int) -> int:
    """Check disk I/O latency in milliseconds."""
    # Query metrics from Prometheus
    # Return latency value
    pass
```

### Summary

- ✅ Report code **already supports** steady state hypothesis
- ✅ Templates **already have** steady state hypothesis section
- ❌ Templates have **empty probe arrays**
- ℹ️ Add probes to templates if you want validation
- ℹ️ Report will **automatically display** results when probes exist

No code changes needed - this is a **configuration/template** enhancement, not a bug fix.

## Files Modified

- `src/chaosmonkey/core/orchestrator.py`
  - Added `_select_multiple_targets()`
  - Added `_run_single_experiment()`
  - Updated `run_experiment()`

## Backward Compatibility

✅ **Fully backward compatible**
- Single target selection still works
- Existing scripts/tests unchanged
- Only new: comma-separated multi-target support

## Date
October 10, 2025
