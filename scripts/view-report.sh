#!/bin/bash

# ChaosMonkey Report Viewer
# Opens HTML chaos reports in your default browser

REPORTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )/reports"

if [ -z "$1" ]; then
    echo "📊 ChaosMonkey Report Viewer"
    echo ""
    echo "Usage: ./view-report.sh <run-id> [format]"
    echo ""
    echo "Formats:"
    echo "  html     - Open beautiful HTML report in browser (default)"
    echo "  markdown - Display markdown report in terminal"
    echo "  json     - Display raw JSON data"
    echo ""
    echo "Examples:"
    echo "  ./view-report.sh run-026dc6aa"
    echo "  ./view-report.sh run-026dc6aa markdown"
    echo "  ./view-report.sh latest html"
    echo ""
    echo "Available reports:"
    cd "$REPORTS_DIR"
    ls -1 *.json 2>/dev/null | sed 's/.json$//' | while read run_id; do
        status=$(jq -r '.result.status // "unknown"' "${run_id}.json" 2>/dev/null)
        chaos_type=$(jq -r '.experiment.tags[0] // "unknown"' "${run_id}.json" 2>/dev/null)
        case "$status" in
            completed|succeeded) icon="✅" ;;
            failed) icon="❌" ;;
            *) icon="❓" ;;
        esac
        echo "  $icon $run_id ($chaos_type - $status)"
    done
    exit 0
fi

RUN_ID="$1"
FORMAT="${2:-html}"

# Handle "latest" keyword
if [ "$RUN_ID" = "latest" ]; then
    RUN_ID=$(ls -1 "$REPORTS_DIR"/run-*.json 2>/dev/null | sort -r | head -1 | xargs basename | sed 's/.json$//')
    if [ -z "$RUN_ID" ]; then
        echo "❌ No reports found"
        exit 1
    fi
    echo "📄 Using latest report: $RUN_ID"
fi

# Generate report if needed
if [ "$FORMAT" = "html" ] && [ ! -f "$REPORTS_DIR/${RUN_ID}.html" ]; then
    echo "🔄 Generating HTML report..."
    chaosmonkey report "$RUN_ID" --format html > /dev/null 2>&1
fi

if [ "$FORMAT" = "markdown" ] && [ ! -f "$REPORTS_DIR/${RUN_ID}.md" ]; then
    echo "🔄 Generating Markdown report..."
    chaosmonkey report "$RUN_ID" --format markdown > /dev/null 2>&1
fi

# View report
case "$FORMAT" in
    html)
        REPORT_FILE="$REPORTS_DIR/${RUN_ID}.html"
        if [ ! -f "$REPORT_FILE" ]; then
            echo "❌ HTML report not found: $REPORT_FILE"
            exit 1
        fi
        echo "🌐 Opening HTML report in browser..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "$REPORT_FILE"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open "$REPORT_FILE"
        else
            echo "Please open this file in your browser:"
            echo "$REPORT_FILE"
        fi
        echo "✅ Report opened: $REPORT_FILE"
        ;;
    
    markdown|md)
        REPORT_FILE="$REPORTS_DIR/${RUN_ID}.md"
        if [ ! -f "$REPORT_FILE" ]; then
            echo "❌ Markdown report not found: $REPORT_FILE"
            exit 1
        fi
        if command -v glow &> /dev/null; then
            glow "$REPORT_FILE"
        elif command -v bat &> /dev/null; then
            bat "$REPORT_FILE"
        else
            cat "$REPORT_FILE"
        fi
        ;;
    
    json)
        REPORT_FILE="$REPORTS_DIR/${RUN_ID}.json"
        if [ ! -f "$REPORT_FILE" ]; then
            echo "❌ JSON report not found: $REPORT_FILE"
            exit 1
        fi
        if command -v jq &> /dev/null; then
            jq . "$REPORT_FILE"
        else
            cat "$REPORT_FILE"
        fi
        ;;
    
    *)
        echo "❌ Unknown format: $FORMAT"
        echo "Valid formats: html, markdown, json"
        exit 1
        ;;
esac
