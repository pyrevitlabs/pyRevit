using System;
using System.Collections.Generic;
using System.Reflection;
using System.Linq;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Bridge class to access pyRevit output window from C# using reflection and thread-safe WPF dispatcher calls
    /// </summary>
    public static class PyRevitOutputBridge
    {
        private static Assembly _runtimeAssembly;
        private static Type _scriptConsoleManagerType;
        private static Type _scriptEngineType;
        private static bool _initialized = false;

        /// <summary>
        /// Initialize the bridge by finding the pyRevit runtime assembly
        /// </summary>
        /// <returns>True if initialization was successful</returns>
        public static bool Initialize()
        {
            if (_initialized)
                return true;

            try
            {
                // Find the pyRevit runtime assembly
                foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (assembly.FullName.StartsWith("pyRevitLabs.PyRevit.Runtime."))
                    {
                        _runtimeAssembly = assembly;
                        _scriptConsoleManagerType = assembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptConsoleManager");
                        _scriptEngineType = assembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptEngineType");
                        
                        if (_scriptConsoleManagerType != null && _scriptEngineType != null)
                        {
                            _initialized = true;
                            return true;
                        }
                    }
                }
            }
            catch
            {
                // Silent failure
            }

            return false;
        }

        /// <summary>
        /// Get the first active console window
        /// </summary>
        /// <returns>Console object or null if not found</returns>
        private static object GetConsole()
        {
            if (!Initialize())
                return null;

            try
            {
                PropertyInfo activeWindowsProp = _scriptConsoleManagerType.GetProperty("ActiveOutputWindows", 
                    BindingFlags.Public | BindingFlags.Static);
                
                if (activeWindowsProp != null)
                {
                    var activeWindows = activeWindowsProp.GetValue(null) as System.Collections.IList;
                    
                    if (activeWindows != null && activeWindows.Count > 0)
                    {
                        return activeWindows[0];
                    }
                }
            }
            catch
            {
                // Silent failure
            }

            return null;
        }

        /// <summary>
        /// Invoke a function on the UI thread using WPF dispatcher
        /// </summary>
        /// <param name="consoleObj">The console object</param>
        /// <param name="action">Action to execute on UI thread</param>
        private static void InvokeOnUI(object consoleObj, Action action)
        {
            try
            {
                Type consoleType = consoleObj.GetType();
                PropertyInfo dispatcherProp = consoleType.GetProperty("Dispatcher");
                
                if (dispatcherProp != null)
                {
                    var dispatcher = dispatcherProp.GetValue(consoleObj);
                    if (dispatcher != null)
                    {
                        Type dispatcherType = dispatcher.GetType();
                        MethodInfo invokeMethod = dispatcherType.GetMethod("Invoke", new Type[] { typeof(Action) });
                        
                        if (invokeMethod != null)
                        {
                            invokeMethod.Invoke(dispatcher, new object[] { action });
                        }
                    }
                }
            }
            catch
            {
                // Silent failure
            }
        }

        /// <summary>
        /// Write HTML content to the pyRevit output window
        /// </summary>
        /// <param name="html">HTML content to write</param>
        /// <returns>True if successful</returns>
        public static bool WriteHtml(string html)
        {
            var console = GetConsole();
            if (console == null)
                return false;

            try
            {
                Type consoleType = console.GetType();
                MethodInfo appendTextMethod = consoleType.GetMethod("AppendText");
                
                if (appendTextMethod != null)
                {
                    InvokeOnUI(console, () =>
                    {
                        try
                        {
                            appendTextMethod.Invoke(console, new object[] { html, "html", true });
                        }
                        catch
                        {
                            // Silent failure in UI thread
                        }
                    });
                    return true;
                }
            }
            catch
            {
                // Silent failure
            }

            return false;
        }

        /// <summary>
        /// Write a text message to the pyRevit output window in native format
        /// </summary>
        /// <param name="message">Message to write</param>
        /// <param name="useEmoji">Whether to include emoji prefixes</param>
        /// <returns>True if successful</returns>
        public static bool WriteMessage(string message, bool useEmoji = true)
        {
            // Just write plain text without HTML formatting to match native pyRevit logs
            return WriteHtml($"{message}\n");
        }

        /// <summary>
        /// Write an error message to the pyRevit output window
        /// </summary>
        /// <param name="message">Error message to write</param>
        /// <returns>True if successful</returns>
        public static bool WriteError(string message)
        {
            var console = GetConsole();
            if (console == null)
                return false;

            try
            {
                Type consoleType = console.GetType();
                MethodInfo appendErrorMethod = consoleType.GetMethod("AppendError");
                
                if (appendErrorMethod != null && _scriptEngineType != null)
                {
                    // Get CSharp engine type
                    var csharpEngineType = Enum.Parse(_scriptEngineType, "CSharp");
                    
                    InvokeOnUI(console, () =>
                    {
                        try
                        {
                            appendErrorMethod.Invoke(console, new object[] { message, csharpEngineType });
                        }
                        catch
                        {
                            // Silent failure in UI thread
                        }
                    });
                    return true;
                }
            }
            catch
            {
                // Silent failure
            }

            return false;
        }

        /// <summary>
        /// Write an info message with emoji in native format
        /// </summary>
        /// <param name="message">Info message to write</param>
        /// <returns>True if successful</returns>
        public static bool WriteInfo(string message)
        {
            return WriteMessage($"🏭 {message}");
        }

        /// <summary>
        /// Write a success message with emoji in native format
        /// </summary>
        /// <param name="message">Success message to write</param>
        /// <returns>True if successful</returns>
        public static bool WriteSuccess(string message)
        {
            return WriteMessage($"✅ {message}");
        }

        /// <summary>
        /// Write a warning message with emoji in native format
        /// </summary>
        /// <param name="message">Warning message to write</param>
        /// <returns>True if successful</returns>
        public static bool WriteWarning(string message)
        {
            return WriteMessage($"⚠️ {message}");
        }

        /// <summary>
        /// Test the bridge by writing various message types
        /// </summary>
        /// <returns>True if test was successful</returns>
        public static bool TestBridge()
        {
            bool success = true;
            
            success &= WriteSuccess("PyRevitOutputBridge: Bridge connection successful!");
            success &= WriteInfo("PyRevitOutputBridge: Testing different message types...");
            success &= WriteWarning("PyRevitOutputBridge: This is a warning message");
            success &= WriteMessage("PyRevitOutputBridge: Plain message without emoji", false);
            
            return success;
        }
    }
}