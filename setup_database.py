#!/usr/bin/env python3
"""
Simple database setup script for Audit Validator
This script will set up the MySQL database and create necessary tables.
"""

import os
import sys
import subprocess

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
    print("📦 Installing database dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pymysql", "sqlalchemy"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_database():
    """Set up the database using db_setup.py"""
    print("🗄️ Setting up database...")
    try:
        subprocess.check_call([sys.executable, "db_setup.py"])
        print("✅ Database setup completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Database setup failed: {e}")
        return False

def main():
    print("=" * 50)
    print("🔧 Audit Validator Database Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("db_setup.py"):
        print("❌ db_setup.py not found. Please run this script from the project root directory.")
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
        print("3. Verify root user has no password (or update db_setup.py)")
        print("4. Try running: mysql -u root -p")
        return False
    
    print("✅ MySQL connection successful")
    
    # Set up database
    if not setup_database():
        return False
    
    print("\n🎉 Database setup completed!")
    print("You can now run the Streamlit app with full database features.")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Setup failed. The app will still work in demo mode.")
    input("\nPress Enter to continue...")
