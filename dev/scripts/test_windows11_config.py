#!/usr/bin/env python
"""
Test script for Windows 11 configuration compatibility.

This script tests the enhanced configuration file creation and management
for Windows 11 compatibility issues.
"""

import os
import sys
import tempfile
import shutil
import platform
from pathlib import Path

# Add pyrevitlib to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pyrevitlib'))

def test_windows_version():
    """Test Windows version detection."""
    print("=== Windows Version Test ===")
    print(f"Platform: {platform.platform()}")
    print(f"System: {platform.system()}")
    print(f"Release: {platform.release()}")
    print(f"Version: {platform.version()}")
    
    # Check if this is Windows 11
    is_windows11 = False
    if platform.system() == 'Windows':
        version_info = platform.version().split('.')
        if len(version_info) >= 3:
            build_number = int(version_info[2])
            # Windows 11 starts from build 22000
            is_windows11 = build_number >= 22000
    
    print(f"Is Windows 11: {is_windows11}")
    return is_windows11


def test_directory_creation():
    """Test enhanced directory creation with permissions."""
    print("\n=== Directory Creation Test ===")
    
    try:
        from pyrevit.coreutils import verify_directory
        
        # Test in temp directory
        test_dir = os.path.join(tempfile.gettempdir(), 'pyrevit_test_dir')
        
        # Clean up if exists
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        print(f"Creating test directory: {test_dir}")
        result_dir = verify_directory(test_dir)
        
        if os.path.exists(result_dir):
            print("✓ Directory creation successful")
            
            # Test nested directory
            nested_dir = os.path.join(test_dir, 'nested', 'deep', 'path')
            nested_result = verify_directory(nested_dir)
            
            if os.path.exists(nested_result):
                print("✓ Nested directory creation successful")
            else:
                print("✗ Nested directory creation failed")
                
            # Clean up
            shutil.rmtree(test_dir)
            print("✓ Cleanup successful")
            
        else:
            print("✗ Directory creation failed")
            
    except Exception as ex:
        print(f"✗ Directory creation test failed: {ex}")


def test_file_creation():
    """Test enhanced file creation with permissions."""
    print("\n=== File Creation Test ===")
    
    try:
        from pyrevit.coreutils import touch
        
        # Test in temp directory
        test_file = os.path.join(tempfile.gettempdir(), 'pyrevit_test_file.txt')
        
        # Clean up if exists
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print(f"Creating test file: {test_file}")
        touch(test_file)
        
        if os.path.exists(test_file):
            print("✓ File creation successful")
            
            # Test file is writable
            try:
                with open(test_file, 'w') as f:
                    f.write("Test content")
                print("✓ File is writable")
                
                # Test file is readable
                with open(test_file, 'r') as f:
                    content = f.read()
                    if content == "Test content":
                        print("✓ File is readable")
                    else:
                        print("✗ File content mismatch")
                        
            except Exception as rw_ex:
                print(f"✗ File read/write test failed: {rw_ex}")
            
            # Clean up
            os.remove(test_file)
            print("✓ Cleanup successful")
            
        else:
            print("✗ File creation failed")
            
    except Exception as ex:
        print(f"✗ File creation test failed: {ex}")


def test_config_creation():
    """Test pyRevit configuration file creation."""
    print("\n=== Config Creation Test ===")
    
    try:
        from pyrevit.userconfig import verify_configs
        
        # Test config creation in temp directory
        test_config_dir = os.path.join(tempfile.gettempdir(), 'pyrevit_config_test')
        test_config_file = os.path.join(test_config_dir, 'pyRevit_config.ini')
        
        # Clean up if exists
        if os.path.exists(test_config_dir):
            shutil.rmtree(test_config_dir)
        
        print(f"Creating test config: {test_config_file}")
        config = verify_configs(test_config_file)
        
        if config:
            print("✓ Config object creation successful")
            
            # Test config file exists
            if os.path.exists(test_config_file):
                print("✓ Config file created successfully")
                
                # Test config is usable
                try:
                    config.add_section('test_section')
                    config.test_section.test_property = 'test_value'
                    config.save_changes()
                    print("✓ Config is functional")
                    
                except Exception as config_ex:
                    print(f"✗ Config functionality test failed: {config_ex}")
                    
            else:
                print("✗ Config file not created (may be in-memory)")
            
            # Clean up
            if os.path.exists(test_config_dir):
                shutil.rmtree(test_config_dir)
                print("✓ Cleanup successful")
                
        else:
            print("✗ Config object creation failed")
            
    except Exception as ex:
        print(f"✗ Config creation test failed: {ex}")


def test_appdata_access():
    """Test access to AppData directories."""
    print("\n=== AppData Access Test ===")
    
    appdata_paths = [
        ('APPDATA', os.getenv('APPDATA')),
        ('LOCALAPPDATA', os.getenv('LOCALAPPDATA')),
        ('USERPROFILE', os.getenv('USERPROFILE')),
    ]
    
    for name, path in appdata_paths:
        if path:
            print(f"{name}: {path}")
            
            # Test if directory exists and is accessible
            if os.path.exists(path):
                print(f"  ✓ Directory exists")
                
                # Test if we can create a subdirectory
                test_subdir = os.path.join(path, 'pyrevit_test_access')
                try:
                    os.makedirs(test_subdir, exist_ok=True)
                    print(f"  ✓ Can create subdirectories")
                    
                    # Test if we can create a file
                    test_file = os.path.join(test_subdir, 'test.txt')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    print(f"  ✓ Can create files")
                    
                    # Clean up
                    os.remove(test_file)
                    os.rmdir(test_subdir)
                    print(f"  ✓ Cleanup successful")
                    
                except Exception as access_ex:
                    print(f"  ✗ Access test failed: {access_ex}")
            else:
                print(f"  ✗ Directory does not exist")
        else:
            print(f"{name}: Not set")


def main():
    """Run all tests."""
    print("pyRevit Windows 11 Configuration Compatibility Test")
    print("=" * 50)
    
    is_windows11 = test_windows_version()
    
    if not is_windows11:
        print("\nNote: This is not Windows 11, but tests will still run for compatibility.")
    
    test_appdata_access()
    test_directory_creation()
    test_file_creation()
    test_config_creation()
    
    print("\n" + "=" * 50)
    print("Test completed. Check results above for any failures.")
    print("\nIf you see failures on Windows 11:")
    print("1. Try running as administrator")
    print("2. Check Windows Security settings")
    print("3. Verify folder permissions in AppData")


if __name__ == '__main__':
    main()
