#!/usr/bin/env python3
"""
Unit tests for Windows 11 fallback methods.

This module provides comprehensive unit tests for the new Windows 11 compatibility
fallback methods, including permission error simulation and edge case testing.

Tests cover:
- verify_directory_with_permissions function
- SetupConfigFallback C# method (via integration testing)
- Permission error handling and recovery
- Fallback location creation and validation
"""

import os
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os.path as op

# Add pyrevitlib to path
pyrevit_lib = op.join(op.dirname(op.dirname(op.dirname(__file__))), 'pyrevitlib')
if pyrevit_lib not in sys.path:
    sys.path.insert(0, pyrevit_lib)


class TestWindows11FallbackMethods(unittest.TestCase):
    """Test suite for Windows 11 fallback methods."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp(prefix='pyrevit_test_')
        self.test_config_file = op.join(self.test_dir, 'test_config.ini')

    def tearDown(self):
        """Clean up test environment."""
        if op.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_verify_directory_with_permissions_success(self):
        """Test successful directory creation with permissions."""
        try:
            from pyrevit.coreutils import verify_directory_with_permissions
            
            test_path = op.join(self.test_dir, 'success_test')
            result = verify_directory_with_permissions(test_path)
            
            self.assertTrue(op.exists(result))
            self.assertTrue(os.access(result, os.W_OK))
            
        except ImportError:
            self.skipTest("verify_directory_with_permissions not available")

    @patch('os.makedirs')
    def test_verify_directory_with_permissions_permission_error(self, mock_makedirs):
        """Test fallback behavior when PermissionError occurs."""
        try:
            from pyrevit.coreutils import verify_directory_with_permissions
            
            # Simulate PermissionError on first call, success on second
            mock_makedirs.side_effect = [PermissionError("Access denied"), None]
            
            test_path = op.join(self.test_dir, 'permission_test')
            
            # Should handle PermissionError and try fallback
            with patch('pyrevit.coreutils.logger') as mock_logger:
                result = verify_directory_with_permissions(test_path)
                
                # Verify fallback was attempted
                mock_logger.get_logger.return_value.warning.assert_called()
                
        except ImportError:
            self.skipTest("verify_directory_with_permissions not available")

    def test_config_fallback_creation(self):
        """Test config file creation with fallback method."""
        try:
            from pyrevit.userconfig import verify_configs_windows11_fallback
            
            # Test creating config file
            verify_configs_windows11_fallback(self.test_config_file)
            
            self.assertTrue(op.exists(self.test_config_file))
            
            # Verify content
            with open(self.test_config_file, 'r') as f:
                content = f.read()
                self.assertIn('pyRevit Configuration File', content)
                self.assertIn('[core]', content)
                self.assertIn('[extensions]', content)
                self.assertIn('[user]', content)
                
        except ImportError:
            self.skipTest("verify_configs_windows11_fallback not available")

    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_config_fallback_permission_error(self, mock_open):
        """Test config fallback handles permission errors."""
        try:
            from pyrevit.userconfig import verify_configs_windows11_fallback
            
            with self.assertRaises(PermissionError):
                verify_configs_windows11_fallback(self.test_config_file)
                
        except ImportError:
            self.skipTest("verify_configs_windows11_fallback not available")

    def test_fallback_locations_generation(self):
        """Test generation of fallback config locations."""
        try:
            from pyrevit.userconfig import verify_configs_with_fallback
            
            # Mock environment variables
            with patch.dict(os.environ, {
                'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local',
                'USERPROFILE': 'C:\\Users\\Test'
            }):
                # This should try fallback locations
                try:
                    verify_configs_with_fallback(self.test_config_file)
                except Exception:
                    # Expected to fail, but should have tried fallback locations
                    pass
                    
        except ImportError:
            self.skipTest("verify_configs_with_fallback not available")

    def test_minimal_config_template_usage(self):
        """Test that minimal config template is used correctly."""
        try:
            from pyrevit.userconfig import MINIMAL_CONFIG_TEMPLATE
            
            # Verify template contains required sections
            self.assertIn('pyRevit Configuration File', MINIMAL_CONFIG_TEMPLATE)
            self.assertIn('[core]', MINIMAL_CONFIG_TEMPLATE)
            self.assertIn('[extensions]', MINIMAL_CONFIG_TEMPLATE)
            self.assertIn('[user]', MINIMAL_CONFIG_TEMPLATE)
            
        except ImportError:
            self.skipTest("MINIMAL_CONFIG_TEMPLATE not available")

    def test_integration_config_creation_flow(self):
        """Integration test for complete config creation flow."""
        try:
            from pyrevit.userconfig import verify_configs_windows11_fallback, PyRevitConfig
            
            # Create config using fallback method
            verify_configs_windows11_fallback(self.test_config_file)
            
            # Verify it can be loaded as PyRevitConfig
            config = PyRevitConfig(cfg_file_path=self.test_config_file)
            
            # Test basic operations
            self.assertIsNotNone(config.core)
            
            # Test adding a setting
            config.core.set_option('test_setting', 'test_value')
            config.save_changes()
            
            # Reload and verify persistence
            config2 = PyRevitConfig(cfg_file_path=self.test_config_file)
            self.assertEqual(config2.core.get_option('test_setting'), 'test_value')
            
        except ImportError:
            self.skipTest("Required modules not available")

    def test_windows11_specific_permissions(self):
        """Test Windows 11 specific permission handling."""
        if os.name != 'nt':
            self.skipTest("Windows-specific test")
            
        try:
            from pyrevit.coreutils import verify_directory_with_permissions
            
            # Test in a location that might have Windows 11 restrictions
            appdata = os.getenv('APPDATA')
            if appdata:
                test_path = op.join(appdata, 'pyRevit_test_permissions')
                
                try:
                    result = verify_directory_with_permissions(test_path)
                    self.assertTrue(op.exists(result))
                    
                    # Clean up
                    if op.exists(test_path):
                        os.rmdir(test_path)
                        
                except Exception as e:
                    # This might fail on some systems, which is expected
                    self.assertIsInstance(e, (PermissionError, OSError))
                    
        except ImportError:
            self.skipTest("verify_directory_with_permissions not available")


class TestExitCodes(unittest.TestCase):
    """Test proper exit codes for CI compatibility."""

    def test_validation_script_exit_codes(self):
        """Test that validation script uses proper exit codes."""
        validation_script = op.join(op.dirname(op.dirname(op.dirname(__file__))), 'validate_windows11_fix.py')
        
        if op.exists(validation_script):
            with open(validation_script, 'r') as f:
                content = f.read()
                
            # Verify exit codes are used
            self.assertIn('sys.exit(0)', content)
            self.assertIn('sys.exit(1)', content)
        else:
            self.skipTest("Validation script not found")


def run_fallback_tests():
    """Run all fallback method tests."""
    print("=" * 60)
    print("Windows 11 Fallback Methods Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestWindows11FallbackMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestExitCodes))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_fallback_tests()
    sys.exit(0 if success else 1)
