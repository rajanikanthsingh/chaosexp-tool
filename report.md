{
  "experiment": {
    "version": "1.0.0",
    "title": "Memory hog template",
    "description": "Experiment that consumes memory on the target node to create memory pressure.",
    "tags": [
      "memory-hog"
    ],
    "steady-state-hypothesis": {
      "title": "Service continues operating under memory pressure",
      "probes": []
    },
    "method": [
      {
        "type": "action",
        "name": "Run memory stress job",
        "provider": {
          "type": "python",
          "module": "chaosmonkey.stubs.actions",
          "func": "run_memory_stress",
          "arguments": {
            "service_id": "${target_id}",
            "duration": "${duration_seconds}",
            "memory_mb": "${memory_mb}"
          }
        }
      }
    ],
    "rollbacks": [],
    "configuration": {
      "target_id": "mobi-platform-account-service-job",
      "target_kind": "service",
      "target_node": "unknown",
      "duration_seconds": 120,
      "latency_ms": 250,
      "packet_loss_percentage": "15%",
      "memory_mb": 2048,
      "io_workers": 4,
      "write_size_mb": 1024
    }
  },
  "result": {
    "chaoslib-version": "1.44.0",
    "platform": "macOS-15.6.1-arm64-arm-64bit-Mach-O",
    "node": "KSThakur1M-PNQ1",
    "experiment": {
      "version": "1.0.0",
      "title": "Memory hog template",
      "description": "Experiment that consumes memory on the target node to create memory pressure.",
      "tags": [
        "memory-hog"
      ],
      "steady-state-hypothesis": {
        "title": "Service continues operating under memory pressure",
        "probes": []
      },
      "method": [
        {
          "type": "action",
          "name": "Run memory stress job",
          "provider": {
            "type": "python",
            "module": "chaosmonkey.stubs.actions",
            "func": "run_memory_stress",
            "arguments": {
              "service_id": "${target_id}",
              "duration": "${duration_seconds}",
              "memory_mb": "${memory_mb}"
            }
          }
        }
      ],
      "rollbacks": [],
      "configuration": {
        "target_id": "mobi-platform-account-service-job",
        "target_kind": "service",
        "target_node": "unknown",
        "duration_seconds": 120,
        "latency_ms": 250,
        "packet_loss_percentage": "15%",
        "memory_mb": 2048,
        "io_workers": 4,
        "write_size_mb": 1024
      }
    },
    "start": "2025-10-09T12:38:04.290205+00:00",
    "status": "completed",
    "deviated": false,
    "steady_states": {
      "before": null,
      "after": null,
      "during": []
    },
    "run": [
      {
        "activity": {
          "type": "action",
          "name": "Run memory stress job",
          "provider": {
            "type": "python",
            "module": "chaosmonkey.stubs.actions",
            "func": "run_memory_stress",
            "arguments": {
              "service_id": "${target_id}",
              "duration": "${duration_seconds}",
              "memory_mb": "${memory_mb}"
            }
          }
        },
        "output": {
          "status": "success",
          "service_id": "mobi-platform-account-service-job",
          "chaos_job_id": "chaos-mem-mobi-platform-account-service-job-1760013485",
          "target_node": "538b4367-c20d-cdc7-2a73-6e59e245d5dc",
          "target_node_name": "hostname",
          "datacenter": "dev1",
          "duration": 120,
          "memory_mb": 2048,
          "memory_workers": 2,
          "eval_id": "6964af3d-590e-f085-2ba1-5c3d3611ec1c",
          "allocations_affected": 1,
          "impact": "High memory pressure on node - services may experience OOM or swap thrashing",
          "message": "Memory stress (2048MB) deployed to hostname - will cause memory contention for 120s"
        },
        "start": "2025-10-09T12:38:04.290617+00:00",
        "status": "succeeded",
        "end": "2025-10-09T12:38:10.845044+00:00",
        "duration": 6.554427
      }
    ],
    "rollbacks": [],
    "end": "2025-10-09T12:38:10.845252+00:00",
    "duration": 6.576534986495972
  }
}