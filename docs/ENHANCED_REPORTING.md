# Enhanced Chaos Engineering Report System

## Overview
This document describes the comprehensive chaos experiment reporting system that has been implemented for the ChaosMonkey CLI tool.

## Features Implemented

### 1. **Enhanced HTML Reports** ✅
   - **Comprehensive Executive Summary**
     - Visual statistics cards showing duration, activities, rollback count, and steady state status
     - Experiment description and system deviation alerts
     - Status-specific color coding and badges
   
   - **Detailed Configuration Section**
     - All experiment parameters with descriptions
     - Target service and chaos type information
     - Timing information (start/end timestamps)
   
   - **Execution Timeline**
     - Visual timeline showing all activities in chronological order
     - Cumulative time tracking
     - Activity status indicators (succeeded/failed)
     - Duration and timing for each step
   
   - **Activity Results**
     - Provider details (module, function, type)
     - Input arguments for each activity
     - Structured output display
     - Special handling for node-specific operations (drains, recoveries)
     - Recovery command display
     - Exception and error tracking
   
   - **Steady State Hypothesis**
     - Hypothesis title and probes
     - Tolerance specifications
     - Provider information for each probe
   
   - **Rollback Actions**
     - All defined rollback operations
     - Arguments and provider details
   
   - **System Environment**
     - Platform and node information
     - ChaosLib and Python versions
   
   - **Raw Data**
     - Collapsible section with complete JSON experiment and result data
   
   - **Professional Styling**
     - Gradient backgrounds
     - Responsive design
     - Print-optimized CSS
     - Color-coded status indicators
     - Clean, modern UI with proper spacing

### 2. **PDF Generation Capability** ✅
   - **WeasyPrint Integration**
     - Added `weasyprint>=60.0,<62.0` to dependencies
     - Created `report_pdf.py` module for PDF generation
     - HTML-to-PDF conversion with proper styling
     - A4 page formatting
     - Automatic margin handling
   
   - **Features**
     - Generate PDF from enhanced HTML reports
     - Optional file saving or byte stream return
     - Graceful handling when WeasyPrint not installed
     - Error handling and informative messages

### 3. **Web UI Enhancements** ✅
   - **New API Endpoints**
     - `GET /api/reports/<run_id>/html` - Get/generate enhanced HTML report
     - `GET /api/reports/<run_id>/download?format=html` - Download HTML report
     - `GET /api/reports/<run_id>/download?format=pdf` - Download PDF report
   
   - **Report Modal Enhancements**
     - Added download button group in modal header
     - "View Full Report" button - opens HTML in new tab
     - "Download HTML" button - downloads HTML file
     - "Download PDF" button - downloads PDF file
     - All buttons with appropriate icons
   
   - **JavaScript Functions**
     - `downloadReport(format)` - Handles HTML/PDF downloads
     - `viewFullHTMLReport()` - Opens full report in new window
     - Automatic notification on download start
     - Session storage of current report ID

### 4. **Report Architecture**

```
src/chaosmonkey/core/
├── report_html.py              # Main HTML report generator (delegates to enhanced)
├── report_html_enhanced.py     # Comprehensive HTML report generator
└── report_pdf.py               # PDF generation module

src/chaosmonkey/web/
├── app.py                      # Enhanced with new report endpoints
├── templates/
│   └── index.html              # Updated with download buttons
└── static/
    └── app.js                  # Added download/view functions
```

## Report Content Details

### Executive Summary Section
- **Statistics Cards**: Duration, Activities count, Rollback count, Steady state status
- **Description Box**: Experiment description
- **Status Alerts**: System deviation warnings or success messages
- **Reason Display**: Shows status reason if available

### Configuration Parameters
- **Target Service**: The service/resource being tested
- **Chaos Type**: Type of chaos injection
- **Timestamps**: Exact start and completion times
- **Parameter Table**: All configuration parameters with descriptions including:
  - Duration of chaos injection
  - Latency settings
  - Packet loss percentages
  - CPU/Memory targets
  - Node names

### Execution Timeline
- **Visual Timeline**: CSS-based timeline with connecting lines
- **Time Markers**: Cumulative time from start for each activity
- **Status Indicators**: Color-coded success/failure markers
- **Duration Display**: Per-activity execution time
- **Exception Highlighting**: Failed activities clearly marked

### Activity Results
Each activity includes:
- **Activity Name and Type**: Clear identification
- **Status Badge**: Visual success/failure indicator
- **Duration**: Exact execution time
- **Provider Details**: Module, function, and provider type
- **Input Arguments**: JSON formatted arguments
- **Output Details**: Structured or raw output
  - For node operations: Node name, ID, datacenter, drain deadline, affected allocations, scheduling eligibility
  - Recovery commands with copy-friendly formatting
  - Messages and notifications
- **Exception Details**: Full error traces when failures occur

### System Information
- Platform details
- Node information
- Tool versions (ChaosLib, Python)
- Execution environment

## Usage

### From Web UI
1. Navigate to the Reports tab
2. Click on any report to view details
3. In the modal, use the new buttons:
   - **View Full Report**: Opens complete HTML in new tab
   - **Download HTML**: Saves HTML file locally
   - **Download PDF**: Generates and saves PDF (requires WeasyPrint)

### From CLI
```bash
# Generate HTML report
chaosmonkey report run-XXXXX --format html

# The enhanced report is automatically generated with all details
```

### From API
```bash
# View HTML report in browser
curl http://localhost:8081/api/reports/run-XXXXX/html

# Download HTML report
curl -O http://localhost:8081/api/reports/run-XXXXX/download?format=html

# Download PDF report
curl -O http://localhost:8081/api/reports/run-XXXXX/download?format=pdf
```

## Installation

### Install WeasyPrint for PDF Support
```bash
# Reinstall package with PDF support
cd /path/to/chaosmonkey
source .venv/bin/activate
pip install -e '.[dev]'
```

### System Dependencies (for WeasyPrint)
```bash
# On Ubuntu/Debian
sudo apt-get install python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

# On macOS
brew install cairo pango gdk-pixbuf libffi
```

## Benefits

1. **Comprehensive Documentation**: Every aspect of the chaos experiment is captured
2. **Professional Presentation**: Clean, modern HTML reports suitable for stakeholders
3. **Portability**: HTML and PDF formats for easy sharing
4. **Debugging**: Complete activity logs, exceptions, and timing information
5. **Audit Trail**: Full raw data included for compliance and verification
6. **User-Friendly**: Easy access from web UI with one-click downloads
7. **Print-Ready**: PDF format perfect for archival and reporting
8. **Responsive**: Works on all devices and screen sizes

## Future Enhancements (Not Yet Implemented)

### 4. Enhanced Metric Collection (Recommended)
- **Node Metrics**: CPU, Memory, Disk usage before/after chaos
- **Nomad Metrics**: Allocation states, job health scores
- **Network Metrics**: Latency measurements, packet loss verification
- **Resource Metrics**: Actual vs expected resource consumption
- **Time-series Data**: Metrics collected at intervals during chaos

To implement this, the orchestrator would need to be updated to:
1. Query Nomad metrics API before/during/after chaos
2. Collect system metrics from target nodes
3. Store time-series data in the report JSON
4. Display charts and graphs in the HTML report

## Technical Details

### Dependencies Added
```toml
"weasyprint>=60.0,<62.0"
```

### New Files Created
- `src/chaosmonkey/core/report_html_enhanced.py` (565 lines)
- `src/chaosmonkey/core/report_pdf.py` (60 lines)

### Files Modified
- `src/chaosmonkey/core/report_html.py` - Delegates to enhanced generator
- `src/chaosmonkey/web/app.py` - Added 3 new endpoints (~120 lines)
- `src/chaosmonkey/web/templates/index.html` - Added download buttons
- `src/chaosmonkey/web/static/app.js` - Added download functions (~30 lines)
- `pyproject.toml` - Added WeasyPrint dependency

### API Endpoints
1. `GET /api/reports/<run_id>/html` - Serve or generate enhanced HTML
2. `GET /api/reports/<run_id>/download?format=html` - Download HTML
3. `GET /api/reports/<run_id>/download?format=pdf` - Download PDF

## Testing

To test the complete workflow:

1. **Run a chaos experiment**:
   ```bash
   chaosmonkey run drain-nodes --target nomad-dev-fqdn --duration 60 --dry-run
   ```

2. **Generate and view report via CLI**:
   ```bash
   chaosmonkey report --format html
   ```

3. **View in Web UI**:
   - Open http://localhost:8081
   - Go to Reports tab
   - Click on the latest report
   - Try all download buttons

4. **Test PDF generation**:
   - Click "Download PDF" in the web UI
   - Or use: `curl -O http://localhost:8081/api/reports/run-XXXXX/download?format=pdf`

## Summary

The enhanced reporting system provides comprehensive, professional-grade reports for chaos experiments with:
- ✅ Detailed HTML reports with complete metrics and timeline
- ✅ PDF export capability
- ✅ Web UI integration with download buttons
- ✅ Professional styling and responsive design
- ✅ Complete activity tracking and error reporting
- ✅ Easy sharing and archival

The system is ready for production use and provides all the detailed information needed for chaos engineering analysis, debugging, and stakeholder reporting.
