using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class AssemblyBuilderService
    {
        private readonly ICommandTypeGenerator _typeGenerator;

        public AssemblyBuilderService(ICommandTypeGenerator typeGenerator)
        {
            _typeGenerator = typeGenerator;
        }

        public ExtensionAssemblyInfo BuildExtensionAssembly(IExtension extension)
        {
            string fileId = $"{extension.GetHash()}_{extension.Name}";
            string outputDir =   Path.Combine(Path.GetTempPath(), "pyRevit", "assemblies");
            Directory.CreateDirectory(outputDir);

            string outputPath = Path.Combine(outputDir, fileId + ".dll");

            var asmName = new AssemblyName(extension.Name)
            {
                Version = new Version(1, 0, 0, 0)
            };

            string fileName = Path.GetFileNameWithoutExtension(outputPath);
            string fileNameWithExt = Path.GetFileName(outputPath);

#if NETFRAMEWORK
            var domain = AppDomain.CurrentDomain;
            var asmBuilder = domain.DefineDynamicAssembly(asmName, AssemblyBuilderAccess.RunAndSave, outputDir);
            var moduleBuilder = asmBuilder.DefineDynamicModule(fileName, fileNameWithExt);
#else
            var asmBuilder = AssemblyBuilder.DefineDynamicAssembly(asmName, AssemblyBuilderAccess.Run);
            var moduleBuilder = asmBuilder.DefineDynamicModule(fileName);
#endif

            foreach (var cmd in extension.GetAllCommands())
            {
                _typeGenerator.DefineCommandType(extension, cmd, moduleBuilder);
            }

#if NETFRAMEWORK
            asmBuilder.Save(fileNameWithExt);
#else
            var generator = new Lokad.ILPack.AssemblyGenerator();
            generator.GenerateAssembly(asmBuilder, outputPath);
#endif

            return new ExtensionAssemblyInfo(
                name: extension.Name,
                location: outputPath,
                isReloading: CheckIfExtensionAlreadyLoaded(extension.Name)
            );
        }

        private bool CheckIfExtensionAlreadyLoaded(string extensionName)
        {
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (asm.GetName().Name == extensionName)
                    return true;
            }
            return false;
        }
    }
}
