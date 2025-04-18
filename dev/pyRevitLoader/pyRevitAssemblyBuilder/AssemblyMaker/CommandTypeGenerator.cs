using System;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class CommandTypeGenerator
    {
        private static Type _scriptCommandBaseType;

        public CommandTypeGenerator()
        {
            var runtimeAssembly = AppDomain.CurrentDomain.GetAssemblies()
                .FirstOrDefault(a => a.FullName.StartsWith("pyRevitLabs.PyRevit.Runtime"));

            if (runtimeAssembly == null)
                throw new InvalidOperationException("ScriptCommand base types could not be resolved. Ensure PyRevitLabs.PyRevit.Runtime is loaded.");

            _scriptCommandBaseType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.ScriptCommand")
                ?? throw new InvalidOperationException("ScriptCommand type not found in runtime assembly.");
        }

        public void DefineCommandType(WrappedExtension extension, FileCommandComponent command, ModuleBuilder moduleBuilder)
        {
            // TODO: try to build assemblies in the isolated context with referencies
            //var typeBuilder = moduleBuilder.DefineType(
            //    fullTypeName,
            //    TypeAttributes.Public | TypeAttributes.Class,
            //    _scriptCommandBaseType
            //);

            var typeBuilder = moduleBuilder.DefineType(
                command.UniqueId,
                TypeAttributes.Public | TypeAttributes.Class
            );
            // Add Description attribute
            var descAttrCtor = typeof(DescriptionAttribute).GetConstructor(new[] { typeof(string) });
            var descAttr = new CustomAttributeBuilder(descAttrCtor, new object[] { command.Tooltip ?? "" });
            typeBuilder.SetCustomAttribute(descAttr);

            var ctorParams = Enumerable.Repeat(typeof(string), 13).ToArray();

            var baseCtor = _scriptCommandBaseType.GetConstructor(
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null, ctorParams, null
            );

            if (baseCtor == null)
                throw new InvalidOperationException("Could not find ScriptCommand base constructor.");

            var ctorBuilder = typeBuilder.DefineConstructor(
                MethodAttributes.Public,
                CallingConventions.Standard,
                Type.EmptyTypes
            );

            var il = ctorBuilder.GetILGenerator();

            // Setup constructor arguments
            string scriptPath = command.ScriptPath;
            string configScriptPath = null;
            string searchPaths = string.Join(";", new[]
            {
                Path.GetDirectoryName(command.ScriptPath),
                Path.Combine(extension.Directory, "lib"),
                Path.Combine(extension.Directory, "..", "..", "pyrevitlib"),
                Path.Combine(extension.Directory, "..", "..", "site-packages")
            });
            string args = "";
            string help = "";
            string tooltip = command.Tooltip ?? "";
            string name = command.Name;
            string bundle = Path.GetFileName(Path.GetDirectoryName(command.ScriptPath));
            string extName = extension.Name;
            string uniqueName = command.UniqueId;
            string ctrlId = $"CustomCtrl_%{extName}%{bundle}%{name}";
            string context = "(zero-doc)";
            string engineCfgs = "{\"clean\": false, \"persistent\": false, \"full_frame\": false}";

            foreach (var arg in new[]
            {
                scriptPath, configScriptPath, searchPaths, args, help,
                tooltip, name, bundle, extName, uniqueName, ctrlId, context, engineCfgs
            })
            {
                il.Emit(OpCodes.Ldstr, arg ?? string.Empty);
            }

            il.Emit(OpCodes.Call, baseCtor);
            il.Emit(OpCodes.Ret);

            typeBuilder.CreateType();
        }
    }
}