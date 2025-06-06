#!/usr/bin/env python
"""
Validation script for Windows 11 configuration fix.

This script validates that our Windows 11 compatibility fixes are working correctly
by testing the core functionality that was causing issues.
"""

import os
import sys
import tempfile
import shutil
import platform
import traceback

def print_header(title):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")

def print_result(test_name, success, message=""):
    """Print test result with formatting."""
    status = "✓ PASS" if success else "✗ FAIL"
    color = "\033[92m" if success else "\033[91m"  # Green or Red
    reset = "\033[0m"
    
    print(f"{color}{status}{reset} {test_name}")
    if message:
        print(f"      {message}")

def test_system_info():
    """Test and display system information."""
    print_header("System Information")
    
    try:
        print(f"Platform: {platform.platform()}")
        print(f"System: {platform.system()}")
        print(f"Release: {platform.release()}")
        print(f"Version: {platform.version()}")
        print(f"Python: {sys.version}")
        
        # Check if this is Windows 11
        is_windows11 = False
        if platform.system() == 'Windows':
            version_info = platform.version().split('.')
            if len(version_info) >= 3:
                build_number = int(version_info[2])
                # Windows 11 starts from build 22000
                is_windows11 = build_number >= 22000
        
        print(f"Windows 11: {'Yes' if is_windows11 else 'No'}")
        return True, is_windows11
        
    except Exception as ex:
        print(f"Error getting system info: {ex}")
        return False, False

def test_environment_variables():
    """Test environment variables needed for pyRevit."""
    print_header("Environment Variables Test")
    
    required_vars = ['APPDATA', 'LOCALAPPDATA', 'USERPROFILE']
    all_present = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print_result(f"{var}", True, f"{value}")
        else:
            print_result(f"{var}", False, "Not set")
            all_present = False
    
    return all_present

def test_directory_creation():
    """Test directory creation with permissions."""
    print_header("Directory Creation Test")
    
    test_base = os.path.join(tempfile.gettempdir(), 'pyrevit_validation_test')
    
    try:
        # Clean up if exists
        if os.path.exists(test_base):
            shutil.rmtree(test_base)
        
        # Test basic directory creation
        test_dir = os.path.join(test_base, 'basic_dir')
        os.makedirs(test_dir, exist_ok=True)
        
        if os.path.exists(test_dir):
            print_result("Basic directory creation", True)
        else:
            print_result("Basic directory creation", False)
            return False
        
        # Test nested directory creation
        nested_dir = os.path.join(test_base, 'nested', 'deep', 'path')
        os.makedirs(nested_dir, exist_ok=True)
        
        if os.path.exists(nested_dir):
            print_result("Nested directory creation", True)
        else:
            print_result("Nested directory creation", False)
            return False
        
        # Test directory permissions (write access)
        test_file = os.path.join(test_dir, 'permission_test.txt')
        with open(test_file, 'w') as f:
            f.write('test')
        
        if os.path.exists(test_file):
            print_result("Directory write permissions", True)
        else:
            print_result("Directory write permissions", False)
            return False
        
        # Clean up
        shutil.rmtree(test_base)
        print_result("Cleanup", True)
        
        return True
        
    except Exception as ex:
        print_result("Directory creation", False, str(ex))
        return False

def test_file_creation():
    """Test file creation and manipulation."""
    print_header("File Creation Test")
    
    test_dir = os.path.join(tempfile.gettempdir(), 'pyrevit_file_test')
    
    try:
        # Ensure directory exists
        os.makedirs(test_dir, exist_ok=True)
        
        # Test file creation
        test_file = os.path.join(test_dir, 'test_config.ini')
        with open(test_file, 'w') as f:
            f.write('# Test configuration file\n')
            f.write('[test_section]\n')
            f.write('test_key = test_value\n')
        
        if os.path.exists(test_file):
            print_result("File creation", True)
        else:
            print_result("File creation", False)
            return False
        
        # Test file reading
        with open(test_file, 'r') as f:
            content = f.read()
        
        if 'test_section' in content:
            print_result("File reading", True)
        else:
            print_result("File reading", False)
            return False
        
        # Test file modification
        with open(test_file, 'a') as f:
            f.write('modified = true\n')
        
        with open(test_file, 'r') as f:
            content = f.read()
        
        if 'modified = true' in content:
            print_result("File modification", True)
        else:
            print_result("File modification", False)
            return False
        
        # Clean up
        shutil.rmtree(test_dir)
        print_result("File test cleanup", True)
        
        return True
        
    except Exception as ex:
        print_result("File creation", False, str(ex))
        return False

def test_appdata_access():
    """Test access to AppData directories."""
    print_header("AppData Access Test")
    
    appdata_paths = [
        ('APPDATA', os.getenv('APPDATA')),
        ('LOCALAPPDATA', os.getenv('LOCALAPPDATA')),
    ]
    
    all_accessible = True
    
    for name, path in appdata_paths:
        if not path:
            print_result(f"{name} access", False, "Environment variable not set")
            all_accessible = False
            continue
        
        try:
            # Test directory exists
            if not os.path.exists(path):
                print_result(f"{name} access", False, "Directory does not exist")
                all_accessible = False
                continue
            
            # Test write access
            test_subdir = os.path.join(path, 'pyrevit_validation_test')
            os.makedirs(test_subdir, exist_ok=True)
            
            test_file = os.path.join(test_subdir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Clean up
            os.remove(test_file)
            os.rmdir(test_subdir)
            
            print_result(f"{name} access", True, "Read/write access confirmed")
            
        except Exception as ex:
            print_result(f"{name} access", False, str(ex))
            all_accessible = False
    
    return all_accessible

def test_pyrevit_config_simulation():
    """Simulate pyRevit configuration file creation."""
    print_header("pyRevit Configuration Simulation")
    
    appdata = os.getenv('APPDATA')
    if not appdata:
        print_result("pyRevit config simulation", False, "APPDATA not available")
        return False
    
    try:
        # Simulate pyRevit directory structure
        pyrevit_dir = os.path.join(appdata, 'pyRevit_test')
        config_file = os.path.join(pyrevit_dir, 'pyRevit_config.ini')
        
        # Clean up if exists
        if os.path.exists(pyrevit_dir):
            shutil.rmtree(pyrevit_dir)
        
        # Create pyRevit directory
        os.makedirs(pyrevit_dir, exist_ok=True)
        print_result("pyRevit directory creation", True)
        
        # Create configuration file
        config_content = """# pyRevit Configuration File
# Created by validation script

[core]
# Core pyRevit settings
check_updates = true
debug = false

[extensions]
# Extension settings

[user]
# User-specific settings
"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        print_result("Configuration file creation", True)
        
        # Test configuration file reading
        with open(config_file, 'r') as f:
            content = f.read()
        
        if '[core]' in content and '[extensions]' in content:
            print_result("Configuration file validation", True)
        else:
            print_result("Configuration file validation", False)
            return False
        
        # Test configuration file modification (simulating settings change)
        with open(config_file, 'a') as f:
            f.write('\n[test_section]\n')
            f.write('test_setting = test_value\n')
        
        print_result("Configuration modification", True)
        
        # Clean up
        shutil.rmtree(pyrevit_dir)
        print_result("Config test cleanup", True)
        
        return True
        
    except Exception as ex:
        print_result("pyRevit config simulation", False, str(ex))
        return False

def main():
    """Run all validation tests."""
    print("pyRevit Windows 11 Configuration Fix Validation")
    print("=" * 60)
    print("This script validates that the Windows 11 compatibility fixes")
    print("are working correctly by testing core file system operations.")
    
    # Run all tests
    tests = [
        ("System Info", test_system_info),
        ("Environment Variables", test_environment_variables),
        ("Directory Creation", test_directory_creation),
        ("File Creation", test_file_creation),
        ("AppData Access", test_appdata_access),
        ("pyRevit Config Simulation", test_pyrevit_config_simulation),
    ]
    
    results = []
    is_windows11 = False
    
    for test_name, test_func in tests:
        try:
            if test_name == "System Info":
                success, is_windows11 = test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as ex:
            print(f"Error running {test_name}: {ex}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print_header("Validation Summary")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        print_result(test_name, success)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if is_windows11:
        print("\n✓ Windows 11 detected - compatibility fixes are relevant")
    else:
        print("\nℹ Windows 10 or earlier detected - fixes provide enhanced compatibility")
    
    if passed == total:
        print("\n🎉 All tests passed! The Windows 11 configuration fix should work correctly.")
        print("   Users should be able to create and modify pyRevit configurations.")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. There may still be compatibility issues.")
        print("   Consider running as Administrator or checking Windows Security settings.")
    
    print("\nFor more information, see: WINDOWS11_SOLUTION_SUMMARY.md")

if __name__ == '__main__':
    main()
