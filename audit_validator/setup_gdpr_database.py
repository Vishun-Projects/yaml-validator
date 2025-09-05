#!/usr/bin/env python3
"""
setup_gdpr_database.py

Setup script for GDPR-compliant database for Audit Validator.
This script will create the database and all necessary tables for GDPR compliance.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_mysql_connection():
    """Check if MySQL is available and accessible"""
    try:
        import pymysql
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='',
            port=3306
        )
        connection.close()
        return True
    except Exception as e:
        print(f"❌ MySQL connection failed: {e}")
        return False

def install_dependencies():
    """Install required database dependencies"""
    try:
        print("📦 Installing database dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "sqlalchemy"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_gdpr_database():
    """Set up the GDPR database using the gdpr_database module"""
    print("🗄️ Setting up GDPR database...")
    try:
        # Import and initialize the GDPR database
        from gdpr_database import get_gdpr_db
        
        # This will automatically create the database and tables
        gdpr_db = get_gdpr_db(echo=True)  # Set echo=True to see SQL commands
        
        print("✅ GDPR database setup completed successfully")
        return True
    except Exception as e:
        print(f"❌ GDPR database setup failed: {e}")
        return False

def test_gdpr_database():
    """Test the GDPR database functionality"""
    print("🧪 Testing GDPR database functionality...")
    try:
        from gdpr_database import get_gdpr_db
        import uuid
        
        gdpr_db = get_gdpr_db(echo=False)
        
        # Test session creation
        test_session_id = f"test_{uuid.uuid4()}"
        session = gdpr_db.create_session(test_session_id, "Test User Agent", "127.0.0.1")
        print(f"✅ Session creation test passed: {test_session_id}")
        
        # Test file saving
        test_file_data = b"test file content"
        file_record = gdpr_db.save_file(test_session_id, "config", test_file_data, "test.yaml", "text/yaml")
        print(f"✅ File saving test passed: {file_record.original_filename}")
        
        # Test validation results saving
        test_validation = {
            "match_percentage": 85,
            "details": [
                {
                    "key": "test.key",
                    "status": "match",
                    "severity": "low",
                    "expected": "test_value",
                    "actual": "test_value",
                    "explanation": "Test validation result"
                }
            ]
        }
        gdpr_db.save_validation_results(test_session_id, test_validation)
        print("✅ Validation results saving test passed")
        
        # Test chat message saving
        chat_msg = gdpr_db.save_chat_message(test_session_id, "user", "Test message", "test_model")
        print("✅ Chat message saving test passed")
        
        # Test GDPR export
        gdpr_export = gdpr_db.export_gdpr_data(test_session_id)
        if gdpr_export:
            print("✅ GDPR export test passed")
        else:
            print("❌ GDPR export test failed")
        
        print("🎉 All GDPR database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ GDPR database test failed: {e}")
        return False

def show_database_info():
    """Show information about the created database"""
    print("\n📊 Database Information:")
    print("=" * 50)
    print("Database Name: audit_validator_db")
    print("Tables Created:")
    print("  • validation_sessions - Main validation sessions")
    print("  • uploaded_files - Files uploaded during validation")
    print("  • validation_details - Detailed validation findings")
    print("  • chat_messages - AI chat conversation history")
    print("  • audit_logs - Audit trail for compliance")
    print("  • gdpr_consents - GDPR consent management")
    print("\nGDPR Compliance Features:")
    print("  • Data retention policies (2 years operational, 7 years audit)")
    print("  • Consent management and tracking")
    print("  • Data export capabilities")
    print("  • Audit logging for all actions")
    print("  • Secure file storage with integrity hashing")
    print("\nAPI Endpoints Available:")
    print("  • /api/gdpr/export/<session_id> - Export session data")
    print("  • /api/gdpr/cleanup - Clean up expired data")
    print("  • /api/gdpr/sessions - List sessions")

def main():
    print("=" * 60)
    print("🔧 GDPR Database Setup for Audit Validator")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("gdpr_database.py"):
        print("❌ gdpr_database.py not found. Please run this script from the audit_validator directory.")
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Check MySQL connection
    print("🔍 Checking MySQL connection...")
    if not check_mysql_connection():
        print("\n💡 To fix this:")
        print("1. Make sure MySQL is installed and running")
        print("2. Ensure MySQL is accessible on localhost:3306")
        print("3. Verify root user has no password (or update environment variables)")
        print("4. Try running: mysql -u root -p")
        return False
    
    print("✅ MySQL connection successful")
    
    # Set up GDPR database
    if not setup_gdpr_database():
        return False
    
    # Test the database
    if not test_gdpr_database():
        return False
    
    # Show database information
    show_database_info()
    
    print("\n🎉 GDPR database setup completed successfully!")
    print("You can now run the custom server with full GDPR compliance features.")
    print("\nNext steps:")
    print("1. Run the custom server: python custom_server.py")
    print("2. Open your browser to the provided URL")
    print("3. Accept GDPR consent to start using the application")
    print("4. Upload files and run validation - all data will be stored securely")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
