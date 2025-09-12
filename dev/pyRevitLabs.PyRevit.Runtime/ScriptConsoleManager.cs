using System;
using System.Collections.Generic;
using System.Reflection;


namespace PyRevitLabs.PyRevit.Runtime {
    public static class ScriptConsoleManager
    {
        public static FieldInfo GetField(Object outputWindow, string fieldName)
        {
            return outputWindow.GetType().GetField(fieldName);
        }

        public static MethodInfo GetMethod(Object outputWindow, string methodName)
        {
            return outputWindow.GetType().GetMethod(methodName);
        }

        public static string GetOutputWindowId(Object outputWindow, string defaultId = "")
        {
            var outputIdProp = GetField(outputWindow, "OutputId");
            if (outputIdProp != null)
            {
                var outputId = outputIdProp.GetValue(outputWindow);
                if (outputId != null)
                    return (string)outputId;
            }

            return defaultId;
        }

        public static string GetOutputWindowUniqueId(Object outputWindow, string defaultId = "")
        {
            var uniqueIdProp = GetField(outputWindow, "OutputUniqueId");
            if (uniqueIdProp != null)
            {
                var uniqueId = uniqueIdProp.GetValue(outputWindow);
                if (uniqueId != null)
                    return (string)uniqueId;
            }

            return defaultId;
        }

        public static void CallCloseMethod(Object outputObj)
        {
            var closeMethod = GetMethod(outputObj, "Close");

            if (closeMethod != null)
            {
                closeMethod.Invoke(outputObj, null);
            }
        }

        public static List<Object> ActiveOutputWindows
        {
            get
            {
                var outputWindowList = (List<Object>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.OutputWindowsDictKey);
                if (outputWindowList == null)
                {
                    var newOutputWindowList = new List<Object>();
                    AppDomain.CurrentDomain.SetData(DomainStorageKeys.OutputWindowsDictKey, newOutputWindowList);
                    return newOutputWindowList;
                }
                else
                    return outputWindowList;
            }

            set
            {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.OutputWindowsDictKey, value);
            }
        }

        public static List<Object> GetAllActiveOutputWindows(string outputWindowId = null)
        {
            if (outputWindowId != null)
            {
                var newOutputWindowList = new List<Object>();
                foreach (Object activeScriptOutput in ActiveOutputWindows)
                    if (GetOutputWindowId(activeScriptOutput) == outputWindowId)
                        newOutputWindowList.Add(activeScriptOutput);
                return newOutputWindowList;
            }
            else
                return ActiveOutputWindows;
        }

        public static void AppendToOutputWindowList(Object outputWindow)
        {
            ActiveOutputWindows.Add(outputWindow);
        }

        public static void RemoveFromOutputList(Object outputWindow)
        {
            var newOutputWindowList = new List<Object>();
            foreach (Object activeOutputWindow in ActiveOutputWindows)
            {
                if (GetOutputWindowUniqueId(activeOutputWindow) != GetOutputWindowUniqueId(outputWindow))
                    newOutputWindowList.Add(activeOutputWindow);
            }

            ActiveOutputWindows = newOutputWindowList;
        }

        public static void CloseActiveOutputWindows(Object excludeOutputWindow = null, string filterOutputWindowId = null)
        {
            if (excludeOutputWindow != null)
            {
                foreach (Object activeOutputWindow in GetAllActiveOutputWindows(filterOutputWindowId))
                    if (GetOutputWindowUniqueId(excludeOutputWindow) != GetOutputWindowUniqueId(activeOutputWindow))
                        CallCloseMethod(activeOutputWindow);
            }
            else
            {
                foreach (Object activeOutputWindow in GetAllActiveOutputWindows())
                    CallCloseMethod(activeOutputWindow);

                ActiveOutputWindows = null;
            }
        }
    }
}
