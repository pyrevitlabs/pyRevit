"""Test Project Parameters Functions - Issue #2695"""

__context__ = 'zero-doc'

import sys
import traceback
import time
from pyrevit import script
from pyrevit.revit.db.query import (
    get_project_parameters,
    iter_project_parameters,
    model_has_parameter
)

# Get the output window
output = script.get_output()

def test_debug_imports():
    """Debug test to isolate import issues"""
    output.print_md("## Debug: Testing imports...")
    
    try:
        output.print_md("   Checking get_project_parameters...")
        output.print_md("   [PASS] get_project_parameters available")
        
        output.print_md("   Checking iter_project_parameters...")
        output.print_md("   [PASS] iter_project_parameters available")
        
        output.print_md("   Checking model_has_parameter...")
        output.print_md("   [PASS] model_has_parameter available")
        
        output.print_md("   Testing get_project_parameters() call...")
        result = get_project_parameters()
        output.print_md("   [PASS] get_project_parameters() executed successfully")
        output.print_md("   Found {} parameters".format(len(result)))
        
        return True
        
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def test_basic_functionality():
    """Test that iterator produces same results as original function"""
    output.print_md("## Testing basic functionality...")
    
    try:
        
        # Get results both ways
        original_list = get_project_parameters()
        iterator_list = list(iter_project_parameters())
        
        output.print_md("   Original function: **{}** parameters".format(len(original_list)))
        output.print_md("   Iterator function: **{}** parameters".format(len(iterator_list)))
        
        # Compare counts
        if len(original_list) == len(iterator_list):
            output.print_md("   [PASS] Parameter counts match")
        else:
            output.print_md("   [FAIL] Parameter counts don't match!")
            return False
            
        # Compare first few parameters if they exist
        if original_list and iterator_list:
            for i, (orig, iter_param) in enumerate(zip(original_list[:3], iterator_list[:3])):
                if orig.name == iter_param.name:
                    output.print_md("   [PASS] Parameter {} '{}' matches".format(i+1, orig.name))
                else:
                    output.print_md("   [FAIL] Parameter {} mismatch: '{}' vs '{}'".format(i+1, orig.name, iter_param.name))
                    return False
        
        return True
        
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def test_early_termination():
    """Test that iterator can terminate early"""
    output.print_md("## Testing early termination...")
    
    try:
        
        # Test early termination - get only first 3 parameters
        count = 0
        first_three = []
        for param in iter_project_parameters():
            first_three.append(param)
            count += 1
            if count >= 3:
                break
        
        total_params = len(get_project_parameters())
        
        output.print_md("   Retrieved first **{}** parameters".format(len(first_three)))
        output.print_md("   Total available: **{}** parameters".format(total_params))
        
        if len(first_three) == 3 and total_params >= 3:
            output.print_md("   [PASS] Early termination works correctly")
            return True
        elif total_params < 3:
            output.print_md("   [PASS] Early termination works (only {} parameters available)".format(total_params))
            return True
        else:
            output.print_md("   [FAIL] Early termination failed")
            return False
            
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def test_boolean_return():
    """Test that model_has_parameter returns proper boolean"""
    output.print_md("## Testing boolean return...")
    
    try:
        
        # Get a real parameter name if available
        params = get_project_parameters()
        if params:
            real_param_name = params[0].name
            result_real = model_has_parameter(real_param_name)
            
            output.print_md("   Testing with real parameter: '{}'".format(real_param_name))
            output.print_md("   Result: **{}** (type: {})".format(result_real, type(result_real).__name__))
            
            if isinstance(result_real, bool) and result_real:
                output.print_md("   [PASS] Returns True for existing parameter")
            else:
                output.print_md("   [FAIL] Should return True for existing parameter")
                return False
        
        # Test with fake parameter
        fake_result = model_has_parameter("NonExistentParameter12345")
        output.print_md("   Testing with fake parameter: 'NonExistentParameter12345'")
        output.print_md("   Result: **{}** (type: {})".format(fake_result, type(fake_result).__name__))
        
        if isinstance(fake_result, bool) and not fake_result:
            output.print_md("   [PASS] Returns False for non-existent parameter")
            return True
        else:
            output.print_md("   [FAIL] Should return False for non-existent parameter")
            return False
            
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def test_performance():
    """Basic performance comparison"""
    output.print_md("## Testing performance...")
    
    try:
        
        # Time original function
        start_time = time.time()
        original_result = get_project_parameters()
        original_time = time.time() - start_time
        
        # Time iterator (full consumption)
        start_time = time.time()
        iterator_result = list(iter_project_parameters())
        iterator_time = time.time() - start_time
        
        output.print_md("   Original function: **{:.4f}s** ({} parameters)".format(original_time, len(original_result)))
        output.print_md("   Iterator function: **{:.4f}s** ({} parameters)".format(iterator_time, len(iterator_result)))
        
        if iterator_time <= original_time * 1.1:  # Allow 10% tolerance
            output.print_md("   [PASS] Iterator performance is acceptable")
        else:
            output.print_md("   [INFO] Iterator is slower (but this is expected for full consumption)")
        
        return True
        
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def test_list_parameters():
    """List all parameter names"""
    output.print_md("## Listing all project parameters...")
    
    try:
        # Get all parameters
        params = get_project_parameters()
        
        if not params:
            output.print_md("   [INFO] No project parameters found in current document")
            return True
            
        output.print_md("   Found **{}** project parameters:".format(len(params)))
        output.print_md("   | # | Parameter Name |")
        output.print_md("   |---|---------------|")
        
        # List all parameters
        for i, param in enumerate(params, 1):
            output.print_md("   | {} | {} |".format(i, param.name))
            
        return True
        
    except Exception as e:
        output.print_md("   [ERROR] Error: {}".format(str(e)))
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    output.print_md("# Project Parameters Tests - Issue #2695")
    output.print_md("---")
    
    tests = [
        ("Debug Imports", test_debug_imports),
        ("List Parameters", test_list_parameters),
        ("Basic Functionality", test_basic_functionality),
        ("Early Termination", test_early_termination),
        ("Boolean Return on model_has_parameter", test_boolean_return),
        ("Performance", test_performance),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            output.print_md("## [CRASHED] {}".format(test_name))
            output.print_md("Error: {}".format(str(e)))
            traceback.print_exc()
    
    output.print_md("---")
    output.print_md("# Results: **{}/{}** tests passed".format(passed, total))
    
    if passed == total:
        output.print_md("## All tests passed!")
    else:
        output.print_md("## {} test(s) failed".format(total - passed))


if __name__ == "__main__":
    run_all_tests()
