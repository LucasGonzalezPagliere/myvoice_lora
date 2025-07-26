#!/usr/bin/env python3
"""
Test script to verify the iMessage data processing setup.
"""

import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import sqlite3
        print("✅ sqlite3 imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import sqlite3: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ pandas imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pandas: {e}")
        return False
    
    try:
        from imessage_processor import iMessageProcessor
        print("✅ iMessageProcessor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import iMessageProcessor: {e}")
        return False
    
    return True

def test_database_access():
    """Test if the iMessage database is accessible."""
    print("\nTesting database access...")
    
    # Check if database file exists
    home = Path.home()
    db_path = home / "Library" / "Messages" / "chat.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Make sure you have Full Disk Access permission enabled")
        return False
    
    print(f"✅ Database file found at {db_path}")
    
    # Try to connect to database
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"✅ Successfully connected to database")
        print(f"   Found {len(tables)} tables")
        
        # Check for key tables
        table_names = [table[0] for table in tables]
        required_tables = ['message', 'chat', 'handle']
        
        for table in required_tables:
            if table in table_names:
                print(f"   ✅ Found table: {table}")
            else:
                print(f"   ❌ Missing table: {table}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        print("   This might be a permission issue. Check Full Disk Access settings.")
        return False

def test_processor():
    """Test the iMessage processor."""
    print("\nTesting iMessage processor...")
    
    try:
        from imessage_processor import iMessageProcessor
        
        processor = iMessageProcessor()
        
        # Test database connection
        if processor.connect_to_database():
            print("✅ Processor can connect to database")
            
            # Test getting chats
            chats = processor.get_all_chats()
            print(f"✅ Found {len(chats)} conversations")
            
            processor.close_connection()
            return True
        else:
            print("❌ Processor cannot connect to database")
            return False
            
    except Exception as e:
        print(f"❌ Error testing processor: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing MyVoice LoRA iMessage Processing Setup\n")
    
    tests = [
        ("Import Test", test_imports),
        ("Database Access Test", test_database_access),
        ("Processor Test", test_processor)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run: python imessage_processor.py")
        print("2. Check the generated training_data.csv file")
        print("3. Review the data quality and statistics")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        print("\nCommon solutions:")
        print("1. Install missing dependencies: pip install -r requirements.txt")
        print("2. Enable Full Disk Access for your terminal in System Preferences")
        print("3. Restart your terminal after changing permissions")

if __name__ == "__main__":
    main() 