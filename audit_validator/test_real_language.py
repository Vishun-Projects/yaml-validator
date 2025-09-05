#!/usr/bin/env python3
"""
Test script to check REAL current Windows language settings
"""

import subprocess
import json
import os

def run_powershell_command(command):
    """Run a PowerShell command and return the result"""
    try:
        ps_cmd = ["powershell", "-NoProfile", "-Command", command]
        result = subprocess.check_output(ps_cmd, stderr=subprocess.DEVNULL, timeout=30)
        return result.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"Error: {str(e)}"

def check_windows_language_settings():
    """Check various Windows language settings"""
    print("🔍 Checking REAL Windows Language Settings...")
    print("=" * 50)
    
    # 1. Check current user's display language
    print("\n1️⃣ Current User Display Language:")
    display_lang = run_powershell_command("Get-WinUserLanguageList | ConvertTo-Json")
    print(f"   Result: {display_lang}")
    
    # 2. Check system locale
    print("\n2️⃣ System Locale:")
    system_locale = run_powershell_command("Get-WinSystemLocale | ConvertTo-Json")
    print(f"   Result: {system_locale}")
    
    # 3. Check UI language
    print("\n3️⃣ UI Language:")
    ui_lang = run_powershell_command("Get-WinUILanguageOverride | ConvertTo-Json")
    print(f"   Result: {ui_lang}")
    
    # 4. Check keyboard layout
    print("\n4️⃣ Current Keyboard Layout:")
    keyboard = run_powershell_command("Get-WinDefaultInputMethodOverride | ConvertTo-Json")
    print(f"   Result: {keyboard}")
    
    # 5. Check registry for language settings
    print("\n5️⃣ Registry Language Settings:")
    reg_lang = run_powershell_command("Get-ItemProperty -Path 'HKCU:\\Control Panel\\International' -Name 'LocaleName' | ConvertTo-Json")
    print(f"   Result: {reg_lang}")
    
    # 6. Check MUI language packs
    print("\n6️⃣ MUI Language Packs:")
    mui_langs = run_powershell_command("Get-WinLanguageBarOption | ConvertTo-Json")
    print(f"   Result: {mui_langs}")
    
    # 7. Check what the user actually sees
    print("\n7️⃣ What User Actually Sees (Current Culture):")
    culture = run_powershell_command("[System.Globalization.CultureInfo]::CurrentUICulture | ConvertTo-Json")
    print(f"   Result: {culture}")
    
    # 8. Check environment variables
    print("\n8️⃣ Environment Variables:")
    env_vars = {
        'LANG': os.environ.get('LANG'),
        'LANGUAGE': os.environ.get('LANGUAGE'),
        'LC_ALL': os.environ.get('LC_ALL'),
        'USERPROFILE': os.environ.get('USERPROFILE')
    }
    print(f"   LANG: {env_vars['LANG']}")
    print(f"   LANGUAGE: {env_vars['LANGUAGE']}")
    print(f"   LC_ALL: {env_vars['LC_ALL']}")
    print(f"   USERPROFILE: {env_vars['USERPROFILE']}")

def check_what_should_be_detected():
    """Check what the validation tool should be detecting"""
    print("\n🔍 What Validation Tool Should Detect:")
    print("=" * 50)
    
    # Check the specific fields that the validation tool looks for
    print("\n1️⃣ OsLanguage (from Get-ComputerInfo):")
    os_lang = run_powershell_command("(Get-ComputerInfo).OsLanguage")
    print(f"   OsLanguage: {os_lang}")
    
    print("\n2️⃣ OsMuiLanguages (from Get-ComputerInfo):")
    os_mui = run_powershell_command("(Get-ComputerInfo).OsMuiLanguages | ConvertTo-Json")
    print(f"   OsMuiLanguages: {os_mui}")
    
    print("\n3️⃣ KeyboardLayout (from Get-ComputerInfo):")
    kb_layout = run_powershell_command("(Get-ComputerInfo).KeyboardLayout")
    print(f"   KeyboardLayout: {kb_layout}")
    
    print("\n4️⃣ OsLocale (from Get-ComputerInfo):")
    os_locale = run_powershell_command("(Get-ComputerInfo).OsLocale")
    print(f"   OsLocale: {os_locale}")

def check_user_interface_language():
    """Check the actual user interface language"""
    print("\n🔍 User Interface Language Check:")
    print("=" * 50)
    
    # Check if Japanese is actually the current display language
    print("\n1️⃣ Current UI Language (what user sees):")
    current_ui = run_powershell_command("[System.Globalization.CultureInfo]::CurrentUICulture.Name")
    print(f"   Current UI Culture: {current_ui}")
    
    print("\n2️⃣ Current Culture (system default):")
    current_culture = run_powershell_command("[System.Globalization.CultureInfo]::CurrentCulture.Name")
    print(f"   Current Culture: {current_culture}")
    
    print("\n3️⃣ Installed UI Languages:")
    installed_ui = run_powershell_command("Get-WinUserLanguageList | Select-Object LanguageTag, LocalizedName | ConvertTo-Json")
    print(f"   Installed UI Languages: {installed_ui}")

if __name__ == "__main__":
    print("🚀 Starting REAL Language Settings Check...")
    
    check_windows_language_settings()
    check_what_should_be_detected()
    check_user_interface_language()
    
    print("\n" + "=" * 50)
    print("✅ Language check completed!")
    print("\n💡 If you changed your language to Japanese, check if:")
    print("   - The change was applied to the current user account")
    print("   - You need to restart applications or log out/in")
    print("   - The language pack is properly installed")
