using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using pyRevitAssemblyBuilder.SessionManager;
using System.Reflection;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class AssemblyBuilderService
    {
        private readonly CommandTypeGenerator _typeGenerator;
        private readonly string _revitVersion;

        public AssemblyBuilderService(CommandTypeGenerator typeGenerator, string revitVersion)
        {
            _typeGenerator = typeGenerator;
            _revitVersion = revitVersion ?? throw new ArgumentNullException(nameof(revitVersion));
        }

        public ExtensionAssemblyInfo BuildExtensionAssembly(WrappedExtension extension)
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
            string code = _typeGenerator.GenerateExtensionCode(extension);

            File.WriteAllText(Path.Combine(outputDir, $"{extension.Name}_Generated.cs"), code);

            var syntaxTree = CSharpSyntaxTree.ParseText(code);

            var references = new List<MetadataReference>
            {
                MetadataReference.CreateFromFile(typeof(object).Assembly.Location),
                MetadataReference.CreateFromFile(typeof(Console).Assembly.Location),
                MetadataReference.CreateFromFile(@"C:\Program Files\Autodesk\Revit 2025\RevitAPI.dll"),
                MetadataReference.CreateFromFile(@"C:\Program Files\Autodesk\Revit 2025\RevitAPIUI.dll"),
                MetadataReference.CreateFromFile(@"C:\Users\Equipo\dev\romangolev\pyRevit\bin\netcore\engines\IPY342\pyRevitLabs.PyRevit.Runtime.2025.dll")
            };

            string runtimePath = Path.Combine(Path.GetDirectoryName(typeof(object).Assembly.Location), "System.Runtime.dll");
            if (File.Exists(runtimePath))
                references.Add(MetadataReference.CreateFromFile(runtimePath));

            var compilation = CSharpCompilation.Create(
                Path.GetFileNameWithoutExtension(outputPath),
                syntaxTrees: new[] { syntaxTree },
                references: references,
                options: new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, optimizationLevel: OptimizationLevel.Release));

            using (var dllStream = new FileStream(outputPath, FileMode.Create))
            {
                var result = compilation.Emit(dllStream);
                if (!result.Success)
                {
                    Console.WriteLine("=== Roslyn Compilation Errors ===");
                    foreach (var diagnostic in result.Diagnostics)
                    {
                        if (diagnostic.Severity == DiagnosticSeverity.Error)
                        {
                            Console.WriteLine($"ERROR {diagnostic.Id}: {diagnostic.GetMessage()}");
                            Console.WriteLine($"Location: {diagnostic.Location.GetLineSpan()}");
                        }
                        else if (diagnostic.Severity == DiagnosticSeverity.Warning)
                        {
                            Console.WriteLine($"WARNING {diagnostic.Id}: {diagnostic.GetMessage()}");
                        }
                    }
                    Console.WriteLine("=================================");
                    throw new Exception("Assembly compilation failed");
                }
            }

            return new ExtensionAssemblyInfo(
                name: extension.Name,
                location: outputPath,
                isReloading: false
            );
        }

        private static string GetStableHash(string input)
        {
            using (var sha1 = System.Security.Cryptography.SHA1.Create())
            {
                var hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(input));
                return BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();
            }
        }
        public void LoadAssembly(ExtensionAssemblyInfo assemblyInfo)
        {
            if (!File.Exists(assemblyInfo.Location))
                throw new FileNotFoundException("Assembly file not found", assemblyInfo.Location);

            Assembly.LoadFrom(assemblyInfo.Location);
        }
    }
}
