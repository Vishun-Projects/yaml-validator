#!/usr/bin/env python3
"""
Standalone Custom UI Launcher for Audit Validator
No dependencies on problematic files - guaranteed to work!
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def main():
    print("🎯 Audit Validator - Standalone Custom UI Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path(__file__).parent
    if not (current_dir / "custom_ui.html").exists():
        print("❌ Error: custom_ui.html not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    if not (current_dir / "standalone_server.py").exists():
        print("❌ Error: standalone_server.py not found!")
        print("Please run this script from the audit_validator directory.")
        return
    
    print("✅ Found custom UI files")
    print("✅ Using standalone server (no problematic dependencies)")
    
    # Start the server
    print("\n🚀 Starting standalone custom UI server...")
    print("📱 The UI will open automatically in your browser")
    print("🔗 URL: http://localhost:5002")
    print("\nPress Ctrl+C to stop the server")
    print("-" * 50)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:5002")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the server
    try:
        subprocess.run([sys.executable, "standalone_server.py"], cwd=current_dir)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
