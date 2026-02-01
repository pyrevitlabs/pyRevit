using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Context object passed to __selfinit__ function.
    /// Provides access to the button and component data with Python-friendly naming.
    /// </summary>
    public class SmartButtonContext
    {
        private readonly PushButton _pushButton;
        private readonly ParsedComponent _component;
        private readonly UIApplication _uiApp;
        private readonly bool _isDarkTheme;

        public SmartButtonContext(PushButton pushButton, ParsedComponent component, UIApplication uiApp, bool isDarkTheme = false)
        {
            _pushButton = pushButton;
            _component = component;
            _uiApp = uiApp;
            _isDarkTheme = isDarkTheme;
        }

        /// <summary>Gets the component's bundle directory.</summary>
        public string directory => _component?.Directory ?? string.Empty;

        /// <summary>Gets the component name.</summary>
        public string name => _component?.Name ?? string.Empty;

        /// <summary>Gets the component unique name.</summary>
        public string unique_name => _component?.UniqueId ?? string.Empty;

        /// <summary>Gets the raw Revit PushButton API object.</summary>
        public PushButton ui_button => _pushButton;

        /// <summary>Gets the Revit UIApplication instance.</summary>
        public UIApplication uiapp => _uiApp;

        /// <summary>Gets the script file path.</summary>
        public string script_file => _component?.ScriptPath ?? string.Empty;

        /// <summary>Gets the on icon path (theme-aware).</summary>
        public string on_icon_path => _isDarkTheme && !string.IsNullOrEmpty(_component?.OnIconDarkPath) 
            ? _component.OnIconDarkPath : _component?.OnIconPath ?? string.Empty;

        /// <summary>Gets the off icon path (theme-aware).</summary>
        public string off_icon_path => _isDarkTheme && !string.IsNullOrEmpty(_component?.OffIconDarkPath) 
            ? _component.OffIconDarkPath : _component?.OffIconPath ?? string.Empty;

        /// <summary>Whether the current theme is dark.</summary>
        public bool is_dark_theme => _isDarkTheme;

        /// <summary>
        /// Sets the button icon from a file path.
        /// Uses Python-style parameter naming for compatibility.
        /// Matches pythonic loader behavior: ICON_SMALL=16, ICON_MEDIUM=24, ICON_LARGE=32
        /// </summary>
        public void set_icon(string icon_path, int icon_size = UIManagerConstants.ICON_MEDIUM)
        {
            if (_pushButton == null || string.IsNullOrEmpty(icon_path) || !File.Exists(icon_path))
                return;

            try
            {
                // Always create small bitmap (16px) for Image property
                var smallBitmap = CreateBitmap(icon_path, UIManagerConstants.ICON_SMALL);
                if (smallBitmap != null)
                    _pushButton.Image = smallBitmap;

                // Create large bitmap based on icon_size parameter
                // If icon_size is ICON_LARGE (32), use large; otherwise use medium (24)
                int largeIconSize = (icon_size >= UIManagerConstants.ICON_LARGE) ? UIManagerConstants.ICON_LARGE : UIManagerConstants.ICON_MEDIUM;
                var largeBitmap = CreateBitmap(icon_path, largeIconSize);
                if (largeBitmap != null)
                    _pushButton.LargeImage = largeBitmap;
            }
            catch
            {
                // Ignore icon setting errors
            }
        }

        /// <summary>
        /// Creates a bitmap from file path with specified size.
        /// Matches the pythonic loader's ButtonIcons.create_bitmap behavior:
        /// - Doubles icon size and DPI for proper HiDPI rendering
        /// - Applies screen scale factor for proper display on scaled monitors
        /// </summary>
        private System.Windows.Media.Imaging.BitmapSource CreateBitmap(string iconPath, int iconSize)
        {
            try
            {
                // Match pythonic loader: double size and DPI
                int adjustedIconSize = iconSize * 2;
                double adjustedDpi = UIManagerConstants.DEFAULT_DPI * 2;
                
                // Get screen scale factor (matches HOST_APP.proc_screen_scalefactor)
                double screenScaling = GetScreenScaleFactor();
                
                // Read file bytes to avoid file locking issues
                var fileBytes = File.ReadAllBytes(iconPath);
                using (var memoryStream = new MemoryStream(fileBytes))
                {
                    // Decode at adjusted size with screen scaling
                    var baseImage = new System.Windows.Media.Imaging.BitmapImage();
                    baseImage.BeginInit();
                    baseImage.StreamSource = memoryStream;
                    baseImage.DecodePixelHeight = (int)(adjustedIconSize * screenScaling);
                    baseImage.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                    baseImage.EndInit();
                    baseImage.Freeze();
                    
                    // Get image data for creating properly DPI-scaled bitmap
                    int imageSize = baseImage.PixelWidth;
                    var imageFormat = baseImage.Format;
                    int bytesPerPixel = (baseImage.Format.BitsPerPixel + 7) / 8;
                    int stride = imageSize * bytesPerPixel;
                    int arraySize = stride * imageSize;
                    
                    byte[] imageData = new byte[arraySize];
                    baseImage.CopyPixels(imageData, stride, 0);
                    
                    // Create bitmap with proper DPI (matches pythonic loader)
                    int scaledSize = (int)(adjustedIconSize * screenScaling);
                    double scaledDpi = adjustedDpi * screenScaling;
                    
                    var bitmapSource = System.Windows.Media.Imaging.BitmapSource.Create(
                        scaledSize,
                        scaledSize,
                        scaledDpi,
                        scaledDpi,
                        imageFormat,
                        baseImage.Palette,
                        imageData,
                        stride
                    );
                    bitmapSource.Freeze();
                    return bitmapSource;
                }
            }
            catch
            {
                return null;
            }
        }
        
        /// <summary>
        /// Gets the screen scale factor for the current process.
        /// Matches HOST_APP.proc_screen_scalefactor in the pythonic loader.
        /// Uses WPF DPI detection to avoid System.Windows.Forms dependency.
        /// </summary>
        private double GetScreenScaleFactor()
        {
            try
            {
                // Get system DPI using WPF
                var dpiXProperty = typeof(System.Windows.SystemParameters).GetProperty("DpiX", 
                    BindingFlags.NonPublic | BindingFlags.Static);
                
                if (dpiXProperty != null)
                {
                    int dpiX = (int)dpiXProperty.GetValue(null, null);
                    return dpiX / UIManagerConstants.DEFAULT_DPI;
                }
                
                return 1.0;
            }
            catch
            {
                return 1.0;
            }
        }

        /// <summary>
        /// Toggles between on and off icons based on the state.
        /// </summary>
        public void toggle_icon(bool is_on, int icon_size = UIManagerConstants.ICON_MEDIUM)
        {
            var iconPath = is_on ? on_icon_path : off_icon_path;
            if (!string.IsNullOrEmpty(iconPath))
            {
                set_icon(iconPath, icon_size);
            }
        }

        /// <summary>
        /// Sets the button to enabled or disabled state.
        /// </summary>
        public void set_enabled(bool enabled)
        {
            if (_pushButton != null)
                _pushButton.Enabled = enabled;
        }

        /// <summary>
        /// Gets a bundle file path by name or validates an absolute path.
        /// If fileName is already an absolute path, validates it exists.
        /// </summary>
        public string get_bundle_file(string fileName)
        {
            if (string.IsNullOrEmpty(fileName))
                return null;
            
            // If it's already an absolute path (result of ui.resolve_icon_file), just validate it
            if (Path.IsPathRooted(fileName))
            {
                return File.Exists(fileName) ? fileName : null;
            }

            if (string.IsNullOrEmpty(_component?.Directory))
                return null;

            // If looking for an icon file and dark theme is active, try dark variant first
            if (_isDarkTheme && IsPotentialIconFile(fileName))
            {
                var darkFileName = GetDarkVariant(fileName);
                var darkPath = Path.Combine(_component.Directory, darkFileName);
                if (File.Exists(darkPath))
                    return darkPath;
            }

            var fullPath = Path.Combine(_component.Directory, fileName);
            return File.Exists(fullPath) ? fullPath : null;
        }

        private bool IsPotentialIconFile(string fileName)
        {
            var ext = Path.GetExtension(fileName)?.ToLowerInvariant();
            return ext == ".png" || ext == ".ico" || ext == ".jpg" || ext == ".jpeg";
        }

        private string GetDarkVariant(string fileName)
        {
            var ext = Path.GetExtension(fileName);
            var name = Path.GetFileNameWithoutExtension(fileName);
            return $"{name}.dark{ext}";
        }
    }

    /// <summary>
    /// Handles execution of SmartButton __selfinit__ scripts.
    /// Delegates to PyRevitLoader.SmartButtonExecutor for actual execution.
    /// </summary>
    public class SmartButtonScriptInitializer
    {
        private readonly ILogger _logger;
        private readonly UIApplication _uiApp;
        private readonly RevitThemeDetector _themeDetector;
        private static Assembly _pyRevitLoaderAssembly;
        private static Type _executorType;
        private static bool _staticInitialized;
        private static bool _staticInitializationFailed;
        private static readonly object _staticLock = new object();
        private object _executor;
        private MethodInfo _executeMethod;
        private bool _instanceInitialized;
        private bool _instanceInitializationFailed;

        public SmartButtonScriptInitializer(UIApplication uiApp, ILogger logger)
        {
            _uiApp = uiApp;
            _logger = logger;
            _themeDetector = new RevitThemeDetector(logger);
            
            // Do static initialization once
            EnsureStaticInitialized();
        }
        
        /// <summary>
        /// One-time static initialization to find assemblies and types (expensive operations).
        /// </summary>
        private void EnsureStaticInitialized()
        {
            if (_staticInitialized || _staticInitializationFailed)
                return;
                
            lock (_staticLock)
            {
                if (_staticInitialized || _staticInitializationFailed)
                    return;
                    
                try
                {
                    // Use AssemblyCache instead of scanning AppDomain directly
                    _pyRevitLoaderAssembly = SessionManager.AssemblyCache.GetByPrefix("pyRevitLoader");

                    if (_pyRevitLoaderAssembly == null)
                    {
                        _staticInitializationFailed = true;
                        return;
                    }

                    // Get SmartButtonExecutor type - do this ONCE
                    _executorType = _pyRevitLoaderAssembly.GetType("PyRevitLoader.SmartButtonExecutor");
                    if (_executorType == null)
                    {
                        _staticInitializationFailed = true;
                        return;
                    }

                    _staticInitialized = true;
                }
                catch
                {
                    _staticInitializationFailed = true;
                }
            }
        }

        /// <summary>
        /// Per-instance initialization to create executor with UIApp.
        /// </summary>
        private void EnsureInstanceInitialized()
        {
            if (_instanceInitialized || _instanceInitializationFailed)
                return;

            if (_staticInitializationFailed || _executorType == null)
            {
                _logger.Warning("PyRevitLoader assembly or SmartButtonExecutor type not found");
                _instanceInitializationFailed = true;
                return;
            }

            try
            {
                // Create executor instance with logger
                Action<string> logAction = msg => _logger.Debug(msg);
                _executor = Activator.CreateInstance(_executorType, _uiApp, logAction);

                // Get ExecuteSelfInit method
                _executeMethod = _executorType.GetMethod("ExecuteSelfInit");

                _instanceInitialized = true;
                _logger.Debug("SmartButtonScriptInitializer initialized successfully");
            }
            catch (Exception ex)
            {
                _logger.Error($"Failed to initialize SmartButtonScriptInitializer: {ex.Message}");
                _instanceInitializationFailed = true;
            }
        }

        /// <summary>
        /// Executes the __selfinit__ function for a SmartButton.
        /// </summary>
        public bool ExecuteSelfInit(ParsedComponent component, PushButton pushButton)
        {
            EnsureInstanceInitialized();

            if (_instanceInitializationFailed || _executor == null || _executeMethod == null)
            {
                _logger.Debug("SmartButtonScriptInitializer not available");
                return true;
            }

            var scriptPath = component?.ScriptPath;
            if (string.IsNullOrEmpty(scriptPath) || !File.Exists(scriptPath))
            {
                return true;
            }

            // Only process Python scripts
            if (!scriptPath.EndsWith(".py", StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }

            // Determine dark theme
            bool isDarkTheme = false;
            try { isDarkTheme = _themeDetector.IsDarkTheme(); } catch { }

            // Create context
            var context = new SmartButtonContext(pushButton, component, _uiApp, isDarkTheme);

            // Collect additional search paths from extension hierarchy
            var additionalPaths = new List<string>();
            if (!string.IsNullOrEmpty(component?.Directory))
            {
                var current = new DirectoryInfo(component.Directory);
                while (current != null)
                {
                    var libPath = Path.Combine(current.FullName, "lib");
                    if (Directory.Exists(libPath) && !additionalPaths.Contains(libPath))
                        additionalPaths.Add(libPath);

                    if (current.Name.EndsWith(".extension", StringComparison.OrdinalIgnoreCase))
                        break;
                    current = current.Parent;
                }
            }

            try
            {
                // Call SmartButtonExecutor.ExecuteSelfInit(scriptPath, context, additionalPaths)
                var result = _executeMethod.Invoke(_executor, new object[] { scriptPath, context, additionalPaths });
                return result is bool boolResult ? boolResult : true;
            }
            catch (TargetInvocationException ex)
            {
                _logger.Error($"Error executing __selfinit__: {ex.InnerException?.Message ?? ex.Message}");
                return true;
            }
            catch (Exception ex)
            {
                _logger.Error($"Error executing __selfinit__: {ex.Message}");
                return true;
            }
        }
    }
}
