using System;
using System.Collections.Generic;


namespace PyRevitBaseClasses
{
    public static class ScriptOutputManager
    {
        public static List<ScriptOutput> ActiveScriptOutputs
        {
            get
            {
                var scriptOutputList = (List<ScriptOutput>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitScriptOutputsDictKey);
                if (scriptOutputList == null)
                {
                    var newScriptOutputList = new List<ScriptOutput>();
                    AppDomain.CurrentDomain.SetData(DomainStorageKeys.pyRevitScriptOutputsDictKey, newScriptOutputList);
                    return newScriptOutputList;
                }
                else
                    return scriptOutputList;
            }

            set
            {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.pyRevitScriptOutputsDictKey, value);
            }
        }

        public static List<ScriptOutput> GetAllActiveOutputWindows(String scriptOutputId = null)
        {
            if (scriptOutputId != null)
            {
                var newScriptOutputList = new List<ScriptOutput>();
                foreach (ScriptOutput activeScriptOutput in ActiveScriptOutputs)
                    if (activeScriptOutput.OutputId == scriptOutputId)
                        newScriptOutputList.Add(activeScriptOutput);
                return newScriptOutputList;
            }
            else
                return ActiveScriptOutputs;
        }

        public static void AppendToOutputList(ScriptOutput scriptOutput)
        {
            ActiveScriptOutputs.Add(scriptOutput);
        }

        public static void RemoveFromOutputList(ScriptOutput scriptOutput)
        {
            var newScriptOutputList = new List<ScriptOutput>();
            foreach (ScriptOutput activeScriptOutput in ActiveScriptOutputs)
            {
                if (activeScriptOutput != scriptOutput)
                    newScriptOutputList.Add(activeScriptOutput);
            }

            ActiveScriptOutputs = newScriptOutputList;
        }

        public static void CloseActiveScriptOutputs(ScriptOutput excludeScriptOutput, String scriptOutputId = null)
        {
            if (excludeScriptOutput != null)
            {
                foreach (ScriptOutput activeScriptOutput in GetAllActiveOutputWindows(scriptOutputId))
                    if (excludeScriptOutput != activeScriptOutput)
                        activeScriptOutput.Close();
            }
            else
            {
                foreach (ScriptOutput activeScriptOutput in GetAllActiveOutputWindows(scriptOutputId))
                    activeScriptOutput.Close();
            }

            ActiveScriptOutputs = null;
        }
    }
}
