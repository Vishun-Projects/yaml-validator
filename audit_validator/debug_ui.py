#!/usr/bin/env python3
"""
Debug script for UI collection
"""

import sys
import os

# Add the parent directory to path to import ai_audit_gui
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    import ai_audit_gui
    print("✅ Successfully imported ai_audit_gui")
except ImportError as e:
    print(f"❌ Failed to import ai_audit_gui: {e}")
    sys.exit(1)

def debug_ui_collection():
    """Debug the UI collection function"""
    print("🔍 Debugging UI collection...")
    
    try:
        # Test the UI collection function directly
        print("\n📊 Testing collect_windows_ui_info_advanced...")
        ui_info = ai_audit_gui.collect_windows_ui_info_advanced()
        print(f"UI info type: {type(ui_info)}")
        print(f"UI info: {ui_info}")
        
        if ui_info:
            print(f"UI info keys: {list(ui_info.keys())}")
            for key, value in ui_info.items():
                print(f"  {key}: {value}")
        else:
            print("❌ UI info is empty or None")
            
    except Exception as e:
        print(f"❌ Error during UI collection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting UI debug...")
    debug_ui_collection()
