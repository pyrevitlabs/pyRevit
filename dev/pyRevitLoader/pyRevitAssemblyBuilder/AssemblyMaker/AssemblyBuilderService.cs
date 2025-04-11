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
        private readonly string _revitVersion;

        public AssemblyBuilderService(ICommandTypeGenerator typeGenerator, string revitVersion)
        {
            _typeGenerator = typeGenerator;
            _revitVersion = revitVersion ?? throw new ArgumentNullException(nameof(revitVersion));
        }

        public ExtensionAssemblyInfo BuildExtensionAssembly(IExtension extension)
        {
            string extensionHash = GetStableHash(extension.GetHash() + _revitVersion).Substring(0, 16);
            string fileName = $"pyRevit_{_revitVersion}_{extensionHash}_{extension.Name}.dll";

            string outputDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                _revitVersion
            );
            Directory.CreateDirectory(outputDir);

            string outputPath = Path.Combine(outputDir, fileName);

            var asmName = new AssemblyName(extension.Name)
            {
                Version = new Version(1, 0, 0, 0)
            };

            string fileNameWithoutExt = Path.GetFileNameWithoutExtension(outputPath);

#if NETFRAMEWORK
            var domain = AppDomain.CurrentDomain;
            var asmBuilder = domain.DefineDynamicAssembly(asmName, AssemblyBuilderAccess.RunAndSave, outputDir);
            var moduleBuilder = asmBuilder.DefineDynamicModule(fileNameWithoutExt, fileName);
#else
            var asmBuilder = AssemblyBuilder.DefineDynamicAssembly(asmName, AssemblyBuilderAccess.Run);
            var moduleBuilder = asmBuilder.DefineDynamicModule(fileNameWithoutExt);
#endif

            foreach (var cmd in extension.GetAllCommands())
            {
                _typeGenerator.DefineCommandType(extension, cmd, moduleBuilder);
            }

#if NETFRAMEWORK
            asmBuilder.Save(fileName);
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

        private static string GetStableHash(string input)
        {
            using (var sha1 = System.Security.Cryptography.SHA1.Create())
            {
                var hash = sha1.ComputeHash(System.Text.Encoding.UTF8.GetBytes(input));
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
        }
    }
}
