using System;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;


namespace PyRevitBaseClasses
{
    public class EngineManager
    {
        private readonly UIApplication _revit;

        public EngineManager(UIApplication revit)
        {
            _revit = revit;

            // cleanup engines for douments that are no longer loaded
            CleanupOrphanedEngines();
        }


        public ScriptEngine GetEngine()
        {
            var engineDocId = GetActiveDocumentId();
            var existingEngineDict = GetEngineDict();
            if (existingEngineDict != null)
            {
                if (existingEngineDict.ContainsKey(engineDocId))
                {
                    return existingEngineDict[engineDocId];
                }
                else
                {
                    var newEngine = CreateNewEngine();
                    existingEngineDict[engineDocId] = newEngine;
                    return newEngine;
                }
            }
            else
            {
                var newEngineDict = RegisterEngineDict();
                var newEngine = CreateNewEngine();
                newEngineDict[engineDocId] = newEngine;
                return newEngine;
            }
        }


        private int GetDocumentId(Document doc)
        {
            return doc.GetHashCode();
        }


        private int GetActiveDocumentId()
        {
            var activeUIDoc = _revit.ActiveUIDocument;
            if (activeUIDoc != null)
            {
                return GetDocumentId(activeUIDoc.Document);
            }
            else
            {
                return 0;
            }
        }


        private void CleanupOrphanedEngines()
        {

            var openDocuments = _revit.Application.Documents;
            var openDocumentsList = new List<int>();
            openDocumentsList.Add(0);
            foreach (Document doc in openDocuments)
            {
                openDocumentsList.Add(GetDocumentId(doc));
            }

            var existingEngineDict = GetEngineDict();
            if (existingEngineDict != null)
            {
                foreach (int docId in existingEngineDict.Keys)
                {
                    if (!openDocumentsList.Contains(docId))
                    {
                        ScriptEngine docEng = existingEngineDict[docId];
                        existingEngineDict.Remove(docId);
                    }
                }
            }
        }


        private Dictionary<int, ScriptEngine> RegisterEngineDict()
        {
            var engineDict = new Dictionary<int, ScriptEngine>();
            AppDomain.CurrentDomain.SetData(EnvDictionaryKeys.docEngineDict, engineDict);
            return engineDict;
        }


        private Dictionary<int, ScriptEngine> GetEngineDict()
        {
            return (Dictionary<int, ScriptEngine>)AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.docEngineDict);
        }


        private ScriptEngine CreateNewEngine()
        {
            var engine = IronPython.Hosting.Python.CreateEngine(new Dictionary<string, object>()
            {{ "Frames", true },
             { "FullFrames", true },
             { "LightweightScopes", true }
             // Tried these options together and made the runtime much slower
             //  { "GCStress", 0 },
             //  { "MaxRecursion", 0 },
            });

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // also, allow access to the RPL internals
            engine.Runtime.LoadAssembly(typeof(PyRevitBaseClasses.ScriptExecutor).Assembly);

            return engine;
        }
    }
}
