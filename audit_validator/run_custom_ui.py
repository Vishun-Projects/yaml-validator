#!/usr/bin/env python3
"""
Custom UI Launcher for Audit Validator
This script runs the pixel-perfect custom UI that matches the image exactly.
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🎯 Audit Validator - Custom UI Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path(__file__).parent
    if not (current_dir / "custom_ui.html").exists():
        print("❌ Error: custom_ui.html not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    if not (current_dir / "custom_server.py").exists():
        print("❌ Error: custom_server.py not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    print("✅ Found custom UI files")
    
    # Check if Flask is installed
    try:
        import flask
        print("✅ Flask is installed")
    except ImportError:
        print("❌ Flask not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "flask"], check=True)
        print("✅ Flask installed successfully")
    
    # Start the server
    print("\n🚀 Starting custom UI server...")
    print("📱 The UI will open automatically in your browser")
    print("🔗 URL: http://localhost:5000")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:5000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the server
    try:
        subprocess.run([sys.executable, "custom_server.py"], cwd=current_dir)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
