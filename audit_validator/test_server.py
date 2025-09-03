#!/usr/bin/env python3
"""
Test script to verify the custom server can start and imports work correctly
"""

import sys
import os

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

print("Testing imports...")

try:
    print("1. Testing basic imports...")
    import json
    import yaml
    import pandas as pd
    print("   ✓ Basic imports successful")
except Exception as e:
    print(f"   ✗ Basic imports failed: {e}")

try:
    print("2. Testing ai_audit_gui import...")
    import ai_audit_gui
    print("   ✓ ai_audit_gui import successful")
    
    # Test basic functions
    print("3. Testing ai_audit_gui functions...")
    snapshot = ai_audit_gui.collect_full_snapshot(interactive_ui=False, collect_apps_flag=False)
    print(f"   ✓ collect_full_snapshot successful: {len(snapshot) if snapshot else 0} keys")
    
    # Test validation with sample data
    test_config = "test_key: test_value"
    result = ai_audit_gui.validate_against_yaml(test_config, snapshot)
    print(f"   ✓ validate_against_yaml successful: {result.get('match_percentage', 'N/A')}% match")
    
except Exception as e:
    print(f"   ✗ ai_audit_gui import/functions failed: {e}")

try:
    print("4. Testing Flask app creation...")
    from custom_server import app
    print("   ✓ Flask app creation successful")
except Exception as e:
    print(f"   ✗ Flask app creation failed: {e}")

print("\nImport test completed!")
print("\nTo start the server, run:")
print("python custom_server.py")
print("\nThen open your browser to: http://localhost:5000")
