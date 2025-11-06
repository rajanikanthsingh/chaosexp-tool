#!/usr/bin/env python3
"""
Quick launcher for ChaosMonkey Web UI
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from chaosmonkey.web.app import app
from chaosmonkey.config import load_settings
import argparse


def main():
    # Prefer explicit CLI flags, then environment variables, then default.
    parser = argparse.ArgumentParser(description="Quick launcher for ChaosMonkey Web UI")
    env_port = os.getenv('PORT') or os.getenv('WEB_UI_PORT')
    default_port = int(env_port) if env_port and env_port.isdigit() else 8081
    parser.add_argument('-p', '--port', type=int, default=default_port,
                        help=f'Port to bind the web UI (default: {default_port})')
    parser.add_argument('-H', '--host', default=os.getenv('HOST') or '0.0.0.0',
                        help='Host/IP to bind to (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', default=(os.getenv('DEBUG', '').lower() in ('1','true')),
                        help='Enable Flask debug mode')

    args = parser.parse_args()

    settings = load_settings(None)
    print(f"🔍 Effective OLVM URL: {settings.platforms.olvm.url}")

    print("🚀 Starting ChaosMonkey Web UI...")
    print(f"📊 Dashboard: http://{args.host}:{args.port}")
    print("🔑 Make sure NOMAD_ADDR and NOMAD_TOKEN are set in your environment")
    print("⏹️  Press Ctrl+C to stop\n")

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    import os
    main()
