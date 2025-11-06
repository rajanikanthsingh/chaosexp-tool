# Chaos Monkey Toolkit Architecture

## Overview

The project targets a hackathon-ready chaos engineering platform that can mature into an organizational tool. The initial milestone prioritizes a CLI-first workflow with a future UI inspired by Reliably. HashiCorp Nomad is the primary scheduler and service discovery layer, while Chaos Toolkit provides a Python-first experimentation framework. Go is used for Nomad-native helpers and agents.

## Components

1. **Python Orchestrator (`src/chaosmonkey`)**
   - Wraps Chaos Toolkit experiment execution.
   - Provides subcommands for environment discovery, target selection, chaos execution, and report generation.
   - Produces structured output (JSON + markdown summaries) for both CLI consumption and future UI ingestion.

2. **Experiment Library (`src/chaosmonkey/experiments`)**
   - Parameterized Chaos Toolkit experiment templates.
   - Organized by chaos type (host down, network latency, etc.).
   - Supports templating to mix deterministic and random target selection.

3. **Nomad Integration Layer**
   - Python-side Nomad client wrapper (using `python-nomad`) for discovery and scheduling chaos jobs.
   - Go helper/agent (`agents/nomad`) packaged as a Nomad task for tighter cluster integration and future extensibility.

4. **Reporting & Telemetry (`reports/`)**
   - Collects run artifacts, telemetry snapshots, and diff reports.
   - Exposes metadata for a future UI backend.

## Execution Flow (CLI-first milestone)

1. **Discover**
   - Fetch topology and services from Nomad.
   - Cache environment snapshot.

2. **Target**
   - Allow explicit selection or weighted random selection.
   - Map chaos types to compatible targets (e.g., process kill → Nomad allocations).

3. **Execute**
   - Render experiment template with selected target.
   - Invoke Chaos Toolkit runner.
   - Optionally schedule Go helper jobs through Nomad for host-level faults.

4. **Report**
   - Gather Chaos Toolkit outputs, Nomad job logs, and system metrics.
   - Emit JSON for automation and Markdown for humans.

## Roadmap Phases

1. **Baseline CLI (current work)**
   - Provide scaffolding for commands, configuration, and experiment templates.
   - Stub integrations with Nomad and Chaos Toolkit for iterative development.

2. **Hardening & Automation**
   - Flesh out chaos actions, add validation tests, and integrate CI.
   - Add richer reporting and persistence.

3. **UI Layer**
   - Serve CLI artifacts through an API.
   - Develop web UI inspired by Reliably for experiment orchestration and observability.

## Technology Choices

- **Python 3.11+** with Typer (or Click) for CLI ergonomics and Chaos Toolkit integration.
- **Go 1.22+** for Nomad-native plugins and statically compiled helpers.
- **HashiCorp Nomad** for service discovery, scheduling chaos jobs, and coordinating distributed actions.
- **Chaos Toolkit** for experiment definition, execution, and validation of steady states.

This document will evolve as concrete integrations and features land in the repository.
