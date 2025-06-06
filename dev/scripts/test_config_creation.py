#!/usr/bin/env python
"""
Simple test script to verify configuration file creation works.
This tests the core functionality without complex dependencies.
"""

import os
import sys
import tempfile
import shutil
import platform

def test_basic_file_creation():
    """Test basic file creation in temp directory."""
    print("=== Basic File Creation Test ===")
    
    test_dir = os.path.join(tempfile.gettempdir(), 'pyrevit_basic_test')
    test_file = os.path.join(test_dir, 'test_config.ini')
    
    try:
        # Clean up if exists
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        
        # Create directory
        os.makedirs(test_dir, exist_ok=True)
        print(f"✓ Created directory: {test_dir}")
        
        # Create file
        with open(test_file, 'w') as f:
            f.write("# Test configuration file\n")
            f.write("[test]\n")
            f.write("setting = value\n")
        
        print(f"✓ Created file: {test_file}")
        
        # Verify file exists and is readable
        if os.path.exists(test_file):
            with open(test_file, 'r') as f:
                content = f.read()
                if "Test configuration file" in content:
                    print("✓ File is readable and contains expected content")
                else:
                    print("✗ File content is incorrect")
        else:
            print("✗ File was not created")
        
        # Clean up
        shutil.rmtree(test_dir)
        print("✓ Cleanup successful")
        
        return True
        
    except Exception as ex:
        print(f"✗ Basic file creation failed: {ex}")
        return False


def test_appdata_access():
    """Test access to AppData directories."""
    print("\n=== AppData Access Test ===")
    
    appdata_vars = ['APPDATA', 'LOCALAPPDATA', 'USERPROFILE']
    results = {}
    
    for var_name in appdata_vars:
        path = os.getenv(var_name)
        if path:
            print(f"{var_name}: {path}")
            
            # Test if directory exists
            if os.path.exists(path):
                print(f"  ✓ Directory exists")
                
                # Test if we can create a test subdirectory
                test_subdir = os.path.join(path, 'pyrevit_access_test')
                try:
                    os.makedirs(test_subdir, exist_ok=True)
                    
                    # Test if we can create a file
                    test_file = os.path.join(test_subdir, 'test.txt')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    
                    print(f"  ✓ Can create files and directories")
                    results[var_name] = True
                    
                    # Clean up
                    os.remove(test_file)
                    os.rmdir(test_subdir)
                    
                except Exception as ex:
                    print(f"  ✗ Cannot create files: {ex}")
                    results[var_name] = False
            else:
                print(f"  ✗ Directory does not exist")
                results[var_name] = False
        else:
            print(f"{var_name}: Not set")
            results[var_name] = False
    
    return results


def test_pyrevit_config_location():
    """Test pyRevit configuration file location."""
    print("\n=== pyRevit Config Location Test ===")
    
    appdata = os.getenv('APPDATA')
    if not appdata:
        print("✗ APPDATA environment variable not set")
        return False
    
    pyrevit_dir = os.path.join(appdata, 'pyRevit')
    config_file = os.path.join(pyrevit_dir, 'pyRevit_config.ini')
    
    print(f"Expected pyRevit directory: {pyrevit_dir}")
    print(f"Expected config file: {config_file}")
    
    # Check if pyRevit directory exists
    if os.path.exists(pyrevit_dir):
        print("✓ pyRevit directory exists")
        
        # Check if config file exists
        if os.path.exists(config_file):
            print("✓ Config file exists")
            
            # Try to read it
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    print(f"✓ Config file is readable ({len(content)} characters)")
                    return True
            except Exception as ex:
                print(f"✗ Cannot read config file: {ex}")
                return False
        else:
            print("⚠ Config file does not exist")
            
            # Try to create it
            try:
                with open(config_file, 'w') as f:
                    f.write("# pyRevit Configuration File\n")
                    f.write("# Created by test script\n\n")
                    f.write("[core]\n")
                    f.write("# Core settings\n\n")
                
                print("✓ Successfully created config file")
                return True
                
            except Exception as ex:
                print(f"✗ Cannot create config file: {ex}")
                return False
    else:
        print("⚠ pyRevit directory does not exist")
        
        # Try to create it
        try:
            os.makedirs(pyrevit_dir, exist_ok=True)
            print("✓ Successfully created pyRevit directory")
            
            # Now try to create config file
            with open(config_file, 'w') as f:
                f.write("# pyRevit Configuration File\n")
                f.write("# Created by test script\n\n")
                f.write("[core]\n")
                f.write("# Core settings\n\n")
            
            print("✓ Successfully created config file")
            return True
            
        except Exception as ex:
            print(f"✗ Cannot create pyRevit directory or config file: {ex}")
            return False


def main():
    """Run all tests."""
    print("pyRevit Configuration Creation Test")
    print("=" * 50)
    
    # Show system info
    print(f"Platform: {platform.platform()}")
    print(f"Python: {sys.version}")
    
    # Run tests
    test1_result = test_basic_file_creation()
    appdata_results = test_appdata_access()
    test3_result = test_pyrevit_config_location()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Basic file creation: {'✓ PASS' if test1_result else '✗ FAIL'}")
    print(f"AppData access: {'✓ PASS' if any(appdata_results.values()) else '✗ FAIL'}")
    print(f"pyRevit config: {'✓ PASS' if test3_result else '✗ FAIL'}")
    
    if test1_result and any(appdata_results.values()) and test3_result:
        print("\n✓ All tests passed! Configuration creation should work.")
    else:
        print("\n⚠ Some tests failed. There may be Windows 11 compatibility issues.")
        print("\nTroubleshooting suggestions:")
        print("1. Run as Administrator")
        print("2. Check Windows Security settings")
        print("3. Verify folder permissions")
        print("4. Check antivirus exclusions")


if __name__ == '__main__':
    main()
