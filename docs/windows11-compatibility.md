# Windows 11 Compatibility Guide

This document explains the Windows 11 compatibility issues with pyRevit configuration files and the solutions implemented.

## Problem Description

After upgrading from Windows 10 to Windows 11, users experience issues where:

1. Configuration changes are not saved
2. Personal script directories cannot be added
3. The `pyRevit_config.ini` file is not created automatically
4. Manual creation of the config file is required for pyRevit to work

## Root Cause

Windows 11 introduced enhanced security measures that affect file system operations:

1. **Enhanced UAC (User Account Control)**: Stricter permissions for file creation in system directories
2. **Controlled Folder Access**: Windows Defender may block applications from writing to certain folders
3. **AppData Protection**: Enhanced protection of the AppData folder structure
4. **File System Permissions**: More restrictive default permissions on newly created files and directories

## Solution Overview

The fix involves multiple layers of compatibility enhancements:

### 1. Enhanced C# File Creation (`CommonUtils.cs`)

**Changes Made:**
- Added explicit permission handling in `EnsureFile()` and `EnsurePath()` methods in `dev/pyRevitLabs/pyRevitLabs.Common/CommonUtils.cs`
- Implemented fallback mechanisms with Windows 11-specific error handling
- Added proper exception handling for `UnauthorizedAccessException`
- Set explicit file system permissions for created files and directories

**Key Features:**
```csharp
// Enhanced directory creation with permissions
private static void EnsurePathWithPermissions(string path)
{
    var dirInfo = Directory.CreateDirectory(path);
    var security = dirInfo.GetAccessControl();
    var currentUser = System.Security.Principal.WindowsIdentity.GetCurrent();
    var userSid = currentUser.User;
    
    var accessRule = new FileSystemAccessRule(
        userSid,
        FileSystemRights.FullControl,
        InheritanceFlags.ContainerInherit | InheritanceFlags.ObjectInherit,
        PropagationFlags.None,
        AccessControlType.Allow
    );
    
    security.SetAccessRule(accessRule);
    dirInfo.SetAccessControl(security);
}
```

### 2. Enhanced Python File Operations (`coreutils/__init__.py`)

**Changes Made:**
- Improved `touch()` function with Windows 11 compatibility
- Added `touch_with_permissions()` for explicit permission handling
- Enhanced `verify_directory()` with fallback mechanisms
- Better error messages for Windows 11-specific issues

**Key Features:**
```python
def touch_with_permissions(fname, times=None):
    """Create file with explicit permissions for Windows 11 compatibility."""
    # Create file with proper permissions
    with open(fname, 'w') as f:
        pass
    
    # Set file permissions on Windows
    if os.name == 'nt':
        import stat
        os.chmod(fname, stat.S_IWRITE | stat.S_IREAD)
```

### 3. Enhanced Configuration Setup (`PyRevitConfigs.cs`)

**Changes Made:**
- Added fallback configuration creation methods
- Implemented alternative directory locations for config files
- Enhanced error reporting with Windows 11-specific guidance
- Added minimal config content generation

**Key Features:**
- Primary location: `%APPDATA%\pyRevit\pyRevit_config.ini`
- Fallback location: `%LOCALAPPDATA%\pyRevit\pyRevit_config.ini`
- Emergency fallback: `%USERPROFILE%\.pyrevit\pyRevit_config.ini`

### 4. Enhanced Python Configuration (`userconfig.py`)

**Changes Made:**
- Added Windows 11 compatibility checks in `verify_configs()`
- Implemented multiple fallback strategies
- Enhanced error handling and user guidance
- Added alternative config file locations

## Testing and Validation

### Automated Testing

A comprehensive test script is provided: `dev/scripts/test_windows11_config.py`

**Test Coverage:**
- Windows version detection
- Directory creation with permissions
- File creation and access
- Configuration file creation
- AppData folder access

**Usage:**
```bash
python dev/scripts/test_windows11_config.py
```

### PowerShell Diagnostic Tool

A PowerShell script for diagnosis and repair: `dev/scripts/Fix-Windows11-Config.ps1`

**Features:**
- Diagnose configuration issues
- Automatically fix common problems
- Set proper file permissions
- Create fallback configuration files

**Usage:**
```powershell
# Diagnose issues
.\Fix-Windows11-Config.ps1 -Diagnose

# Fix issues automatically
.\Fix-Windows11-Config.ps1 -Fix

# Force fix with elevated permissions
.\Fix-Windows11-Config.ps1 -Fix -Force
```

## User Instructions

### For End Users

If you experience configuration issues on Windows 11:

1. **Try the automatic fix:**
   ```powershell
   .\Fix-Windows11-Config.ps1 -Fix
   ```

2. **If that fails, run as Administrator:**
   - Right-click PowerShell and select "Run as Administrator"
   - Run the fix script again

3. **Manual workaround:**
   - Create the directory: `%APPDATA%\pyRevit`
   - Create an empty file: `%APPDATA%\pyRevit\pyRevit_config.ini`
   - Restart Revit and try configuring pyRevit again

4. **Check Windows Security:**
   - Open Windows Security
   - Go to Virus & threat protection
   - Check "Controlled folder access" settings
   - Add pyRevit/Revit as allowed applications if needed

### For Developers

When developing pyRevit extensions or tools:

1. **Use the enhanced utilities:**
   ```python
   from pyrevit.coreutils import verify_directory, touch
   
   # These now handle Windows 11 compatibility automatically
   verify_directory(my_directory)
   touch(my_config_file)
   ```

2. **Handle configuration gracefully:**
   ```python
   from pyrevit.userconfig import user_config
   
   try:
       # Configuration operations
       user_config.add_section('my_section')
       user_config.save_changes()
   except Exception as ex:
       # Handle Windows 11 compatibility issues
       logger.warning('Config save failed, may be Windows 11 issue: %s', ex)
   ```

## Technical Details

### File System Permissions

The solution sets the following permissions on created files and directories:

- **Owner**: Full Control (Read, Write, Execute, Delete, Change Permissions)
- **Inheritance**: Container and Object inheritance enabled
- **Access Type**: Allow

### Error Handling Strategy

1. **Primary Method**: Standard file/directory creation
2. **Fallback Method**: Creation with explicit permissions
3. **Alternative Locations**: Try different AppData folders
4. **Graceful Degradation**: In-memory configuration if all else fails

### Compatibility Matrix

| Windows Version | Status | Notes |
|----------------|--------|-------|
| Windows 10 | ✅ Full | No changes needed |
| Windows 11 22H2 | ✅ Full | Enhanced compatibility |
| Windows 11 23H2 | ✅ Full | Enhanced compatibility |
| Windows Server 2022 | ✅ Full | Enhanced compatibility |

## Troubleshooting

### Common Issues

1. **"Access Denied" errors:**
   - Run as Administrator
   - Check Controlled Folder Access settings
   - Verify antivirus exclusions

2. **Config file not found:**
   - Use the PowerShell diagnostic tool
   - Check alternative locations
   - Manually create the file

3. **Permissions errors:**
   - Use the fix script with -Force parameter
   - Check user account permissions
   - Verify folder ownership

### Getting Help

If you continue to experience issues:

1. Run the diagnostic script and share the output
2. Check the pyRevit logs for detailed error messages
3. Report issues on the pyRevit GitHub repository
4. Include your Windows version and build number

## Future Considerations

- Monitor Windows 11 updates for additional security changes
- Consider implementing Windows Store app compatibility
- Evaluate alternative configuration storage methods
- Add telemetry for Windows 11 compatibility issues
