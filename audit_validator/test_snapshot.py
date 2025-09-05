#!/usr/bin/env python3
"""
Test script to get raw system snapshot data
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

def test_snapshot_collection():
    """Test the snapshot collection functions"""
    print("🔍 Testing system snapshot collection...")
    
    try:
        # Test Windows full dump
        print("\n📊 Testing Windows full dump...")
        windows_dump = ai_audit_gui.collect_windows_full_dump()
        print(f"Windows dump keys: {list(windows_dump.keys()) if isinstance(windows_dump, dict) else 'Not a dict'}")
        
        # Test Windows UI info (includes language and keyboard)
        print("\n🖥️ Testing Windows UI info...")
        ui_info = ai_audit_gui.collect_windows_ui_info_advanced()
        print(f"UI info keys: {list(ui_info.keys()) if isinstance(ui_info, dict) else 'Not a dict'}")
        
        # Test full snapshot
        print("\n📸 Testing full snapshot...")
        full_snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=True, collect_apps_flag=False)
        print(f"Full snapshot keys: {list(full_snapshot.keys()) if isinstance(full_snapshot, dict) else 'Not a dict'}")
        
        # Look for language and keyboard related fields
        print("\n🔍 Searching for language and keyboard fields...")
        language_fields = []
        keyboard_fields = []
        
        if isinstance(full_snapshot, dict):
            for key, value in full_snapshot.items():
                key_lower = str(key).lower()
                if any(term in key_lower for term in ['language', 'locale', 'lang']):
                    language_fields.append((key, value))
                if any(term in key_lower for term in ['keyboard', 'input', 'layout']):
                    keyboard_fields.append((key, value))
        
        print(f"Language-related fields found: {len(language_fields)}")
        for key, value in language_fields:
            print(f"  {key}: {value}")
            
        print(f"Keyboard-related fields found: {len(keyboard_fields)}")
        for key, value in keyboard_fields:
            print(f"  {key}: {value}")
        
        # Save full snapshot to file for inspection
        import json
        with open('raw_snapshot_debug.json', 'w', encoding='utf-8') as f:
            json.dump(full_snapshot, f, indent=2, default=str)
        print(f"\n💾 Full snapshot saved to 'raw_snapshot_debug.json'")
        
        return full_snapshot
        
    except Exception as e:
        print(f"❌ Error during snapshot collection: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🚀 Starting snapshot test...")
    result = test_snapshot_collection()
    
    if result:
        print("\n✅ Snapshot collection completed successfully!")
        print(f"📊 Total fields collected: {len(result) if isinstance(result, dict) else 'Unknown'}")
    else:
        print("\n❌ Snapshot collection failed!")
