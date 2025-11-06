# ChaosMonkey Toolkit

CLI-first chaos engineering toolkit leveraging [Chaos Toolkit](https://chaostoolkit.org/) for experiment execution and HashiCorp Nomad for service discovery, scheduling, and future cluster-native fault injections. The goal is to provide a hackathon-ready baseline that can evolve into an internal reliability platform with a UI inspired by [Reliably](https://reliably.com/).

## 🚀 Quick Start (macOS)

```bash
# 1. Clone and navigate to the repository
git clone https://github.com/xperi-tmis/chaosmonkey.git
cd chaosmonkey

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install the CLI
pip install -e '.[dev]'

# 4. (Optional) Configure Nomad connection
cp .env.example .env
# Edit .env with your Nomad server details

# 5. Run discovery
chaosmonkey discover

# 6. Execute a dry-run experiment
chaosmonkey execute --dry-run
```

💡 **First time on macOS?** See the detailed [macOS Installation](#-macos-installation) section below.

## 📚 Table of Contents

- [Quick Start (macOS)](#-quick-start-macos)
- [Objectives](#-objectives)
- [Repository Layout](#-repository-layout)
- [macOS Installation](#-macos-installation)
- [Quickstart (CLI Baseline)](#-quickstart-cli-baseline)
- [Configuration](#️-configuration)
- [Testing](#-testing)
- [Go Agent Scaffold](#️-go-agent-scaffold-optional)
- [Troubleshooting (macOS)](#-troubleshooting-macos)
- [Roadmap](#️-roadmap)

## Node Operations

The toolkit provides commands for draining and recovering Nomad client nodes to simulate infrastructure failures:

### Drain Nodes

Simulate node failures by draining nodes (making them ineligible for new allocations):

```bash
# List available nodes
chaosmonkey drain-nodes

# Drain a specific node with confirmation
chaosmonkey drain-nodes --node-id <node-id>

# Drain with custom deadline and skip confirmation  
chaosmonkey drain-nodes --node-id <node-id> --deadline 600 --yes

# Dry run to see what would be drained
chaosmonkey drain-nodes --node-id <node-id> --dry-run
```

### Recover Nodes

Restore drained nodes to normal operation:

```bash
# List and recover all drained nodes
chaosmonkey recover-nodes

# Recover a specific node
chaosmonkey recover-nodes --node-id <node-id> --yes

# Dry run to see what would be recovered
chaosmonkey recover-nodes --dry-run
```

## Chaos Experiments

Run targeted chaos experiments with customizable parameters:

### Basic Execution

```bash
# Dry run (safe, generates artifacts without real chaos)
chaosmonkey execute --dry-run

# Execute network latency experiment
chaosmonkey execute --chaos-type network-latency

# Execute with custom duration and latency
chaosmonkey execute --chaos-type network-latency --duration 40 --latency-ms 300
```

### Available Chaos Types

- `network-latency`: Introduce network delays between services
- `packet-loss`: Simulate packet drop scenarios
- `host-down`: Drain nodes to simulate infrastructure failures
- `cpu-hog`: Stress CPU resources on target systems
- `memory-hog`: Consume memory to test resource limits
- `disk-io`: Generate disk I/O pressure

### Execution Options

- `--chaos-type`: Type of chaos to execute (required)
- `--duration`: Override experiment duration in seconds
- `--latency-ms`: Override network latency in milliseconds (for network experiments)
- `--dry-run`: Preview experiment without executing
- `--target`: Specify target service (auto-detected if not provided)

## Complete Node Down & Recovery Workflow

Simulate infrastructure failures and recovery:

### Step 1: List Available Nodes

```bash
# See all nodes and their current status
chaosmonkey drain-nodes
```

### Step 2: Drain Node (Simulate Failure)

```bash
# Drain a specific node with confirmation
chaosmonkey drain-nodes --node-id <node-id>

# Drain with custom deadline and skip confirmation
chaosmonkey drain-nodes --node-id <node-id> --deadline 600 --yes

# Preview what would be drained
chaosmonkey drain-nodes --node-id <node-id> --dry-run
```

### Step 3: Run Chaos Experiments

```bash
# Run experiments while node is drained to test resilience
chaosmonkey execute --chaos-type network-latency --duration 60

# Monitor application behavior with reduced capacity
chaosmonkey discover --clients
```

### Step 4: Recover Node (Restore Service)

```bash
# Recover all drained nodes
chaosmonkey recover-nodes

# Recover specific node
chaosmonkey recover-nodes --node-id <node-id> --yes

# Preview recovery operation
chaosmonkey recover-nodes --dry-run
```

### Step 5: Verify Recovery

```bash
# Confirm all nodes are healthy
chaosmonkey discover --clients

# Check specific node status
chaosmonkey drain-nodes | grep <node-name>
```

### Chaos Type Backlog

Future chaos experiment types:
- DNS failure
- Process kill
- Service kill
- Random reboot / shutdown / sleep
- Random high CPU / memory / disk I/O
- Random network latency / packet loss / DNS failure
- Random process / service kill
- Random VM down

## 📁 Repository Layout

```text
docs/
  architecture.md        # High-level component map and roadmap
src/chaosmonkey/         # Python CLI package and orchestrator core
  core/                  # Discovery, targeting, execution modules
  experiments/templates  # Chaos Toolkit experiment templates
  stubs/                 # Placeholder actions for early development
tests/                   # Pytest smoke tests for the CLI
agents/nomad/            # Go-based Nomad helper (discover/drain)
presentation/            # Hackathon slides
```

## 🍎 macOS Installation

### Prerequisites

1. **Python 3.11+** (Python 3.13+ recommended)
   ```bash
   # Check your Python version
   python3 --version
   
   # Install Python via Homebrew if needed
   brew install python@3.13
   ```

2. **Go 1.22+** (optional, only needed for the Nomad agent)
   ```bash
   # Check if Go is installed
   go version
   
   # Install Go via Homebrew if needed
   brew install go
   ```

### Setup Steps

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone https://github.com/xperi-tmis/chaosmonkey.git
   cd chaosmonkey
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the CLI in editable mode with dev dependencies**:
   ```bash
   pip install -e '.[dev]'
   ```

4. **Verify the installation**:
   ```bash
   chaosmonkey --help
   ```

### macOS-Specific Notes

- **Virtual Environment Activation**: On macOS, always activate the virtual environment before running `chaosmonkey` commands:
  ```bash
  source .venv/bin/activate
  ```

- **Homebrew**: If you don't have Homebrew installed, get it from [brew.sh](https://brew.sh/):
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- **Python Command**: On macOS, use `python3` instead of `python` to ensure you're using Python 3.

## 🚀 Quickstart (CLI Baseline)

**Prerequisites**: Ensure you have completed the installation steps above and activated your virtual environment.

1. Create a virtual environment targeting Python 3.11+ (see macOS Installation section above).

1. Install the CLI in editable mode with dev dependencies:

  ```bash
  pip install -e '.[dev]'
  ```

1. Configure Nomad connection (optional, uses defaults if not configured):

  ```bash
  # Copy the example environment file
  cp .env.example .env
  
  # Edit .env with your Nomad server details
  # NOMAD_ADDR=http://your-nomad-server:4646
  # NOMAD_TOKEN=your-nomad-token
  # NOMAD_NAMESPACE=default
  ```

1. Run discovery against stubbed Nomad data (or real data if configured):

  ```bash
  chaosmonkey discover
  ```

1. Execute a dry-run experiment to generate artifacts:

  ```bash
  chaosmonkey execute --dry-run
  ```

Generated reports land in `reports/run-*.json|md`. These will power the future UI.

## ⚙️ Configuration

ChaosMonkey supports multiple configuration methods with the following priority (highest to lowest):

1. **Configuration file** (YAML/JSON) - `chaosmonkey.yaml`, `chaosmonkey.yml`, or `chaosmonkey.json`
2. **Environment variables** - Set via `.env` file or shell environment
3. **Default values** - Built-in defaults for local development

### Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file with your favorite editor
# macOS users can use:
nano .env        # Terminal-based editor
open -e .env     # TextEdit
code .env        # VS Code (if installed)
```

Example `.env` contents:

```bash
# Nomad server address (required for real Nomad integration)
NOMAD_ADDR=http://your-nomad-server:4646

# Nomad authentication token (required if ACLs are enabled)
NOMAD_TOKEN=your-nomad-acl-token

# Optional: Nomad region
NOMAD_REGION=us-west-1

# Optional: Nomad namespace (defaults to 'default')
NOMAD_NAMESPACE=default
```

**⚠️ Security Note**: The `.env` file is already in `.gitignore` to prevent accidentally committing secrets. Never commit your actual credentials!

### Configuration File

Create a `chaosmonkey.yaml` file for more complex configuration:

```yaml
nomad:
  address: http://your-nomad-server:4646
  token: your-nomad-token
  region: us-west-1
  namespace: default

chaos:
  experiments_path: experiments
  reports_path: reports
  dry_run: false
```

Or use JSON format (`chaosmonkey.json`):

```json
{
  "nomad": {
    "address": "http://your-nomad-server:4646",
    "token": "your-nomad-token",
    "namespace": "default"
  },
  "chaos": {
    "experiments_path": "experiments",
    "reports_path": "reports"
  }
}
```

## 🧪 Testing

```bash
# Activate virtual environment first (macOS)
source .venv/bin/activate

# Run tests
pytest

# Run tests with coverage
pytest --cov=chaosmonkey --cov-report=html
```

Tests stub external dependencies, so they succeed without a live Nomad cluster or Chaos Toolkit installed.

## 🛠️ Go Agent Scaffold (Optional)

The Go module provides a lightweight Nomad helper meant to run as a Nomad job for deeper cluster integration.

### Prerequisites

Ensure Go 1.22+ is installed (see macOS Installation section above).

### Setup and Run

```bash
# Navigate to the agent directory
cd agents/nomad

# Download dependencies
go mod tidy

# Run the chaos agent
go run ./cmd/chaos-agent discover

# Run tests
go test ./...
```

### macOS-Specific Notes

- **Network Issues**: If `go mod tidy` fails with connection errors, check your network connection or try again later.
- **Go Environment**: Verify Go is properly configured:
  ```bash
  go env GOPATH
  go env GOROOT
  ```

## 🔧 Troubleshooting (macOS)

### CLI Command Not Found

If you get `command not found: chaosmonkey`, make sure:

1. You've installed the package: `pip install -e '.[dev]'`
2. Your virtual environment is activated: `source .venv/bin/activate`
3. Try running: `python -m chaosmonkey.cli --help` as an alternative

### Python Version Issues

```bash
# Check Python version (must be 3.11+)
python3 --version

# If you have multiple Python versions, specify the version:
python3.13 -m venv .venv
```

### Permission Errors

```bash
# If you encounter permission errors, don't use sudo with pip
# Instead, make sure you're in a virtual environment
source .venv/bin/activate
```

### Import Errors

```bash
# Reinstall dependencies
pip install --upgrade pip
pip install -e '.[dev]'
```

## 🗺️ Roadmap

1. **CLI Baseline (current)** – stub integrations, experiment templates, reporting artifacts.
2. **Hardening & Automation** – implement real chaos actions, CI pipelines, richer telemetry capture.
3. **UI Evolution** – expose orchestrator via API, deliver a Reliably-inspired experience for experiment design and insights.

## 🖼️ Architecture Diagram

This repository includes a draw.io (diagrams.net) XML diagram representing the ChaosMonkey architecture. The diagram file is available at `docs/architecture.drawio`.

How to open

- In the browser: go to https://app.diagrams.net/ and choose File → Open from Device, then select `architecture.drawio`.
- In VS Code: use the 'Draw.io Integration' extension and open the file.

Notes

- The diagram includes: Your Machine (CLI), Web UI, Redis, chaosmonkey CLI (subprocess), Nomad Cluster, Target Node, Service under test, and Chaos Stress Job.
- Connectors show the Web UI using Redis and optionally invoking the CLI via subprocess (dashed). The CLI executes jobs through the Nomad Cluster.

If you'd like layout tweaks or a PNG export, I can generate and attach that next.

See `docs/architecture.md` for a deeper breakdown of components and flow.
