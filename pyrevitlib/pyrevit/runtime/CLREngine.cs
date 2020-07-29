using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

using System.Reflection;
using Autodesk.Revit.UI;

// csharp
using System.CodeDom.Compiler;
using Microsoft.CSharp;
//vb
using Microsoft.VisualBasic;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;

namespace PyRevitLabs.PyRevit.Runtime {
    public class ExecParams {
        public string ExecId { get; set; }
        public string ExecTimeStamp { get; set; }
        public string ScriptPath { get; set; }
        public string ConfigScriptPath { get; set; }
        public string CommandUniqueId { get; set; }
        public string CommandControlId { get; set; }
        public string CommandName { get; set; }
        public string CommandBundle { get; set; }
        public string CommandExtension { get; set; }
        public string HelpSource { get; set; }
        public bool RefreshEngine { get; set; }
        public bool ConfigMode { get; set; }
        public bool DebugMode { get; set; }
        public bool ExecutedFromUI { get; set; }
        public Autodesk.Windows.RibbonItem UIButton { get; set; }
    }

    public class CLREngineOutputTarget : TargetWithLayout {
        public ExecParams CurrentExecParams { get; set; }

        protected override void Write(LogEventInfo logEvent) {
            try {
                var message = Layout.Render(logEvent);
                if (logEvent.Level == LogLevel.Debug) {
                    if (CurrentExecParams.DebugMode)
                        Console.WriteLine(message);
                }
                else
                    Console.WriteLine(message);
            }
            catch { }
        }
    }

    public class CLREngine : ScriptEngine {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private string scriptSig = string.Empty;
        private Assembly scriptAssm = null;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            // compile first
            // only if the signature doesn't match
            var errors = new List<string>();
            if (scriptSig == null || runtime.ScriptSourceFileSignature != scriptSig) {
                try {
                    scriptSig = runtime.ScriptSourceFileSignature;
                    scriptAssm = CompileCLRScript(ref runtime, out errors);
                    if (scriptAssm == null) {
                        if (runtime.RuntimeType == ScriptRuntimeType.ExternalCommand) {
                            runtime.OutputStream.WriteError(string.Join(Environment.NewLine, errors.ToArray()), runtime.EngineType);
                        }
                        // clear script signature
                        scriptSig = null;
                        return ScriptExecutorResultCodes.CompileException;
                    }
                }
                catch (Exception compileEx) {
                    // make sure a bad compile is not cached
                    scriptAssm = null;
                    string traceMessage = compileEx.ToString();
                    traceMessage = traceMessage.NormalizeNewLine();
                    runtime.TraceMessage = traceMessage;

                    if (runtime.RuntimeType == ScriptRuntimeType.ExternalCommand) {
                        var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                        dialog.MainInstruction = "Error compiling .NET script.";
                        dialog.ExpandedContent = string.Format("{0}\n{1}", compileEx.Message, traceMessage);
                        dialog.Show();
                    }

                    return ScriptExecutorResultCodes.CompileException;
                }
            }

            // scriptAssm must have value
            switch (runtime.RuntimeType) {
                // if is an external command
                case ScriptRuntimeType.ExternalCommand:
                    try {
                        // execute now
                        var resultCode = ExecuteExternalCommand(scriptAssm, null, ref runtime);
                        if (resultCode == ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException)
                            TaskDialog.Show(PyRevitLabsConsts.ProductName,
                                string.Format(
                                    "Can not find any type implementing IExternalCommand in assembly \"{0}\"",
                                    scriptAssm.Location
                                    ));
                        return resultCode;
                    }
                    catch (Exception execEx) {
                        string traceMessage = execEx.ToString();
                        traceMessage = traceMessage.NormalizeNewLine();
                        runtime.TraceMessage = traceMessage;

                        var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                        dialog.MainInstruction = "Error executing .NET script.";
                        dialog.ExpandedContent = string.Format("{0}\n{1}", traceMessage, execEx.StackTrace);
                        dialog.Show();

                        return ScriptExecutorResultCodes.ExecutionException;
                    }

                // if is an event hook
                case ScriptRuntimeType.EventHandler:
                    try {
                        return ExecuteEventHandler(scriptAssm, ref runtime);
                    }
                    catch (Exception execEx) {
                        string traceMessage = execEx.ToString();
                        traceMessage = traceMessage.NormalizeNewLine();
                        runtime.TraceMessage = traceMessage;

                        runtime.OutputStream.WriteError(traceMessage, runtime.EngineType);

                        return ScriptExecutorResultCodes.ExecutionException;
                    }

                default:
                    return ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException;
            }
        }

        public static IEnumerable<Type> GetTypesSafely(Assembly assembly) {
            try {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex) {
                return ex.Types.Where(x => x != null);
            }
        }

        public static Assembly CompileCLRScript(ref ScriptRuntime runtime, out List<string> errors) {
            // https://stackoverflow.com/a/3188953
            // read the script
            var scriptContents = File.ReadAllText(runtime.ScriptSourceFile);

            // read the referenced dlls from env vars
            // pyrevit sets this when loading
            string[] refFiles;
            var envDic = new EnvDictionary();
            if (envDic.ReferencedAssemblies.Length == 0) {
                var refs = AppDomain.CurrentDomain.GetAssemblies();
                refFiles = refs.Select(a => a.Location).ToArray();
            }
            else {
                refFiles = envDic.ReferencedAssemblies;
            }

            // create compiler parameters
            var compileParams = new CompilerParameters(refFiles);
            compileParams.OutputAssembly = Path.Combine(
                UserEnv.UserTemp,
                string.Format("{0}_{1}.dll", runtime.ScriptData.CommandName, runtime.ScriptSourceFileSignature)
                );
            compileParams.CompilerOptions = string.Format("/optimize /define:REVIT{0}", runtime.App.VersionNumber);
            compileParams.GenerateInMemory = true;
            compileParams.GenerateExecutable = false;
            compileParams.TreatWarningsAsErrors = false;
            compileParams.ReferencedAssemblies.Add(typeof(ScriptExecutor).Assembly.Location);

            // determine which code provider to use
            CodeDomProvider compiler;
            var compConfig = new Dictionary<string, string>() { { "CompilerVersion", "v4.0" } };
            switch (runtime.EngineType) {
                case ScriptEngineType.CSharp:
                    compiler = new CSharpCodeProvider(compConfig);
                    break;
                case ScriptEngineType.VisualBasic:
                    compiler = new VBCodeProvider(compConfig);
                    break;
                default:
                    throw new PyRevitException("Specified language does not have a compiler.");
            }

            // compile code first
            var res = compiler.CompileAssemblyFromFile(
                options: compileParams,
                fileNames: new string[] { runtime.ScriptSourceFile }
            );

            // return nothing if errors occured
            errors = new List<string> { };
            if(res.Errors.HasErrors) {
                foreach (var err in res.Errors)
                    errors.Add(err.ToString());
                return null;
            }

            // otherwise return compiled assm
            return res.CompiledAssembly;
        }

        public static int ExecuteExternalCommand(Assembly assmObj, string className, ref ScriptRuntime runtime) {
            foreach (Type assmType in GetTypesSafely(assmObj)) {
                if (assmType.IsClass) {
                    // find the appropriate type and execute
                    if (className != null) {
                        if (assmType.Name == className)
                            return ExecuteExternalCommandType(assmType, ref runtime);
                        else
                            continue;
                    }
                    else if (assmType.GetInterfaces().Contains(typeof(IExternalCommand)))
                        return ExecuteExternalCommandType(assmType, ref runtime);
                }
            }

            return ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException;
        }

        public static int ExecuteExternalCommandType(Type extCommandType, ref ScriptRuntime runtime) {
            // create instance
            object extCommandInstance = Activator.CreateInstance(extCommandType);

            // set properties if available
            // set ExecParams
            var execParams = new ExecParams {
                ExecId = runtime.ExecId,
                ExecTimeStamp = runtime.ExecTimestamp,
                ScriptPath = runtime.ScriptData.ScriptPath,
                ConfigScriptPath = runtime.ScriptData.ConfigScriptPath,
                CommandUniqueId = runtime.ScriptData.CommandUniqueId,
                CommandControlId = runtime.ScriptData.CommandControlId,
                CommandName = runtime.ScriptData.CommandName,
                CommandBundle = runtime.ScriptData.CommandBundle,
                CommandExtension = runtime.ScriptData.CommandExtension,
                HelpSource = runtime.ScriptData.HelpSource,
                RefreshEngine = runtime.ScriptRuntimeConfigs.RefreshEngine,
                ConfigMode = runtime.ScriptRuntimeConfigs.ConfigMode,
                DebugMode = runtime.ScriptRuntimeConfigs.DebugMode,
                ExecutedFromUI = runtime.ScriptRuntimeConfigs.ExecutedFromUI,
                UIButton = runtime.UIControl
            };

            FieldInfo execParamField = null;
            foreach (var fieldInfo in extCommandType.GetFields())
                if (fieldInfo.FieldType == typeof(ExecParams))
                    execParamField = fieldInfo;

            if (execParamField != null)
                execParamField.SetValue(extCommandInstance, execParams);

            // reroute console output to runtime stream
            var existingOutStream = Console.Out;
            StreamWriter runtimeOutputStream = new StreamWriter(runtime.OutputStream);
            runtimeOutputStream.AutoFlush = true;
            Console.SetOut(runtimeOutputStream);

            // setup logger
            var prevLoggerCfg = LogManager.Configuration;
            var newLoggerCfg = new LoggingConfiguration();
            var target = new CLREngineOutputTarget();
            target.CurrentExecParams = execParams;
            target.Name = logger.Name;
            target.Layout = "${level:uppercase=true}: [${logger}] ${message}";
            newLoggerCfg.AddTarget(target.Name, target);
            newLoggerCfg.AddRuleForAllLevels(target);
            LogManager.Configuration = newLoggerCfg;

            // execute
            string commandMessage = string.Empty;
            extCommandType.InvokeMember(
                "Execute",
                BindingFlags.Default | BindingFlags.InvokeMethod,
                null,
                extCommandInstance,
                new object[] {
                    runtime.ScriptRuntimeConfigs.CommandData,
                    commandMessage,
                    runtime.ScriptRuntimeConfigs.SelectedElements}
                );

            // revert logger back to previous
            LogManager.Configuration = prevLoggerCfg;

            // cleanup reference to exec params
            target.CurrentExecParams = null;
            if (execParamField != null)
                execParamField.SetValue(extCommandInstance, null);

            // reroute console output back to original
            Console.SetOut(existingOutStream);
            runtimeOutputStream = null;

            return ScriptExecutorResultCodes.Succeeded;
        }

        public static int ExecuteEventHandler(Assembly assmObj, ref ScriptRuntime runtime) {
            var argsType = runtime.ScriptRuntimeConfigs.EventArgs.GetType();
            foreach (Type assmType in GetTypesSafely(assmObj))
                foreach (MethodInfo methodInfo in assmType.GetMethods()) {
                    var methodParams = methodInfo.GetParameters();
                    if (methodParams.Count() == 2
                            && methodParams[0].Name == "sender"
                            && (methodParams[1].Name == "e" || methodParams[1].Name == "args")
                            && methodParams[1].ParameterType == argsType) {
                        object extEventInstance = Activator.CreateInstance(assmType);
                        assmType.InvokeMember(
                            methodInfo.Name,
                            BindingFlags.Default | BindingFlags.InvokeMethod,
                            null,
                            extEventInstance,
                            new object[] {
                                    runtime.ScriptRuntimeConfigs.EventSender,
                                    runtime.ScriptRuntimeConfigs.EventArgs
                                }
                            );
                        return ScriptExecutorResultCodes.Succeeded;
                    }
                }

            return ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException;
        }
    }
}
