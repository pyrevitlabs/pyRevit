import pytest
from unittest.mock import MagicMock, patch
from pyrevit import DB, HOST_APP

# Import the functions to test
from extensions.pyRevitTools.extension.pyRevit.tab.Project.panel.ptools.stack.Family.pulldown.Export_Family_Config.pushbutton.script import read_configs
from extensions.pyRevitTools.extension.pyRevit.tab.Project.panel.ptools.stack.Family.pulldown.Import_Family_Config.pushbutton.script import get_param_config

def test_read_configs_revit2023():
    """Test parameter export in Revit 2023+"""
    # Mock Revit objects
    mock_param = MagicMock()
    mock_param.Definition.Name = "TestParam"
    mock_param.IsInstance = True
    mock_param.IsReporting = False
    mock_param.Formula = None
    mock_param.IsShared = False
    
    # Mock ForgeTypeId for Revit 2023+
    mock_type_id = MagicMock()
    mock_type_id.TypeId = "autodesk.spec.aec:length-1.0.0"
    mock_group_id = MagicMock()
    mock_group_id.TypeId = "autodesk.spec.aec:construction-1.0.0"
    
    mock_param.Definition.GetDataType.return_value = mock_type_id
    mock_param.Definition.GetGroupTypeId.return_value = mock_group_id
    
    # Mock HOST_APP
    with patch('pyrevit.HOST_APP') as mock_host:
        mock_host.is_newer_than.return_value = True
        
        # Call function
        configs, _ = read_configs([mock_param.Definition.Name], include_types=False)
        
        # Verify results
        param_config = configs['parameters']['TestParam']
        assert param_config['type'] == "autodesk.spec.aec:length-1.0.0"
        assert param_config['group'] == "autodesk.spec.aec:construction-1.0.0"
        assert param_config['instance'] == True
        assert param_config['reporting'] == False

def test_get_param_config_revit2023():
    """Test parameter import in Revit 2023+"""
    param_opts = {
        'type': 'autodesk.spec.aec:length-1.0.0',
        'group': 'autodesk.spec.aec:construction-1.0.0',
        'instance': 'true',
        'reporting': 'false'
    }
    
    # Mock HOST_APP
    with patch('pyrevit.HOST_APP') as mock_host:
        mock_host.is_newer_than.return_value = True
        
        # Mock ForgeTypeId
        with patch('pyrevit.DB.ForgeTypeId') as mock_forge_type:
            # Call function
            param_config = get_param_config("TestParam", param_opts)
            
            # Verify ForgeTypeId was created with correct values
            mock_forge_type.assert_any_call('autodesk.spec.aec:length-1.0.0')
            mock_forge_type.assert_any_call('autodesk.spec.aec:construction-1.0.0')
            
            # Verify param config
            assert param_config.name == "TestParam"
            assert param_config.isinst == True
            assert param_config.isreport == False

def test_get_param_config_revit2023_with_category():
    """Test category parameter import in Revit 2023+"""
    param_opts = {
        'type': 'autodesk.revit.category.family:doors-1.0.0',
        'group': 'autodesk.spec.aec:construction-1.0.0',
        'instance': 'true',
        'reporting': 'false',
        'category': 'Doors'
    }
    
    # Mock HOST_APP and category query
    with patch('pyrevit.HOST_APP') as mock_host, \
         patch('pyrevit.query.get_category') as mock_get_cat:
        mock_host.is_newer_than.return_value = True
        mock_get_cat.return_value = MagicMock()
        
        # Call function
        param_config = get_param_config("TestParam", param_opts)
        
        # Verify category was queried
        mock_get_cat.assert_called_once_with('Doors')
        
        # Verify param config has category
        assert param_config.famcat is not None

def test_get_param_config_revit2023_error_handling():
    """Test error handling during parameter import in Revit 2023+"""
    param_opts = {
        'type': 'invalid:type-id',
        'group': 'invalid:group-id',
        'instance': 'true',
        'reporting': 'false'
    }
    
    # Mock HOST_APP
    with patch('pyrevit.HOST_APP') as mock_host, \
         patch('pyrevit.script.get_logger') as mock_logger:
        mock_host.is_newer_than.return_value = True
        
        # Mock ForgeTypeId to raise exception
        with patch('pyrevit.DB.ForgeTypeId', side_effect=Exception("Invalid TypeId")):
            # Call function
            param_config = get_param_config("TestParam", param_opts)
            
            # Verify error was logged
            mock_logger.return_value.error.assert_called_once()
            
            # Verify fallback to defaults
            assert param_config is not None  # Should not return None