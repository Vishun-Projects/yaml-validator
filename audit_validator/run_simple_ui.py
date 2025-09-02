#!/usr/bin/env python3
"""
Simple Custom UI Launcher for Audit Validator
Uses Python's built-in modules - no additional installations required!
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🎯 Audit Validator - Simple Custom UI Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path(__file__).parent
    if not (current_dir / "custom_ui.html").exists():
        print("❌ Error: custom_ui.html not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    if not (current_dir / "simple_server.py").exists():
        print("❌ Error: simple_server.py not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    print("✅ Found custom UI files")
    print("✅ Using Python's built-in modules (no Flask required)")
    
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
        subprocess.run([sys.executable, "simple_server.py"], cwd=current_dir)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
