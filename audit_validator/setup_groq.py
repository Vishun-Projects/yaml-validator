#!/usr/bin/env python3
"""
Setup script for Groq API integration
"""

import os
import sys

def setup_groq_api():
    """Interactive setup for Groq API key"""
    print("🔧 Groq API Setup for Audit Validator")
    print("=" * 50)
    
    # Check if config.py exists
    config_path = "config.py"
    if not os.path.exists(config_path):
        print("❌ config.py not found. Please ensure you're in the audit_validator directory.")
        return False
    
    # Get current API key
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        if 'gsk_your_actual_api_key_here' in content:
            print("⚠️  Default API key detected in config.py")
        elif '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' in content:
            print("⚠️  Demo API key detected in config.py")
        else:
            print("✅ Custom API key already configured")
            return True
            
    except Exception as e:
        print(f"❌ Error reading config.py: {e}")
        return False
    
    print("\n📋 To get your Groq API key:")
    print("1. Go to: https://console.groq.com/")
    print("2. Sign up/Login to your account")
    print("3. Navigate to API Keys section")
    print("4. Create a new API key")
    print("5. Copy the key (starts with 'gsk_')")
    
    print("\n🔑 Enter your Groq API key (or press Enter to skip):")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("⏭️  Skipping API key setup. Using demo key for now.")
        return False
    
    if not api_key.startswith('gsk_'):
        print("❌ Invalid API key format. Groq API keys start with 'gsk_'")
        return False
    
    # Update config.py
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Replace the default key
        if 'gsk_UpuDFxHOWF4k9op21LwoWGdyb8kyIpLWO5a6Xh6avAeeHkNW' in content:
            content = content.replace(
                'GROQ_API_KEY = os.environ.get(\'GROQ_API_KEY\') or "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"',
                f'GROQ_API_KEY = os.environ.get(\'GROQ_API_KEY\') or "{api_key}"'
            )
        elif 'gsk_your_actual_api_key_here' in content:
            content = content.replace(
                'GROQ_API_KEY = "gsk_your_actual_api_key_here"',
                f'GROQ_API_KEY = "{api_key}"'
            )
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        print("✅ API key successfully updated in config.py!")
        print("🚀 You can now run the server with real Groq AI integration")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config.py: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = ['flask', 'requests', 'pandas', 'pyyaml', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("✅ All required packages are installed")
        return True

def main():
    """Main setup function"""
    print("🚀 Audit Validator - Groq AI Integration Setup")
    print("=" * 60)
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Setup API key
    api_ok = setup_groq_api()
    
    print("\n" + "=" * 60)
    if deps_ok and api_ok:
        print("🎉 Setup completed successfully!")
        print("💡 You can now run: python custom_server.py")
    elif deps_ok:
        print("⚠️  Setup partially completed. API key not configured.")
        print("💡 You can still run the server, but AI chat will use fallback responses.")
    else:
        print("❌ Setup failed. Please install missing dependencies first.")
    
    print("\n📚 For more help, check the README.md file")

if __name__ == "__main__":
    main()
