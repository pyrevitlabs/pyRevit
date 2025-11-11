using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
#if !NETFRAMEWORK
using System.Runtime.Loader;
#endif
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Lokad.ILPack;
using System.Text;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public enum AssemblyBuildStrategy
    {
        Roslyn,
        ILPack
    }

    public class AssemblyBuilderService
    {
        private readonly string _revitVersion;
        private readonly AssemblyBuildStrategy _buildStrategy;

        public AssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy)
        {
            _revitVersion = revitVersion ?? throw new ArgumentNullException(nameof(revitVersion));
            _buildStrategy = buildStrategy;

#if !NETFRAMEWORK
            if (_buildStrategy == AssemblyBuildStrategy.ILPack)
            {
                // On .NET Core, hook into AssemblyLoadContext to resolve Lokad.ILPack two folders up
                var baseDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var ilPackPath = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "Lokad.ILPack.dll"));
                AssemblyLoadContext.Default.Resolving += (context, name) =>
                {
                    if (string.Equals(name.Name, "Lokad.ILPack", StringComparison.OrdinalIgnoreCase)
                        && File.Exists(ilPackPath))
                    {
                        return context.LoadFromAssemblyPath(ilPackPath);
                    }
                    return null;
                };
            }
#else
            if (_buildStrategy == AssemblyBuildStrategy.ILPack)
            {
                // On .NET Framework, hook into AppDomain to resolve Lokad.ILPack two folders up
                var baseDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                var ilPackPath = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "Lokad.ILPack.dll"));
                AppDomain.CurrentDomain.AssemblyResolve += (sender, args) =>
                {
                    var name = new AssemblyName(args.Name).Name;
                    if (string.Equals(name, "Lokad.ILPack", StringComparison.OrdinalIgnoreCase)
                        && File.Exists(ilPackPath))
                    {
                        return Assembly.LoadFrom(ilPackPath);
                    }
                    return null;
                };
            }
#endif
        }

        public ExtensionAssemblyInfo BuildExtensionAssembly(ParsedExtension extension)
        {
            if (extension == null)
                throw new ArgumentNullException(nameof(extension));

            string hash = GetStableHash(extension.GetHash() + _revitVersion).Substring(0, 16);
            string fileName = $"pyRevit_{_revitVersion}_{hash}_{extension.Name}.dll";

            string outputDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                _revitVersion);
            Directory.CreateDirectory(outputDir);

            string outputPath = Path.Combine(outputDir, fileName);

            // Check if assembly file already exists (hash-based caching)
            if (File.Exists(outputPath))
            {
                try
                {
                    // Verify the assembly is valid by reading its name
                    var assemblyName = AssemblyName.GetAssemblyName(outputPath);
                    
                    return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading: false);
                }
                catch (Exception ex)
                {
                    // If file is corrupted or invalid, delete it and rebuild
                    Console.WriteLine($"Warning: Existing assembly is invalid, rebuilding: {ex.Message}");
                    try
                    {
                        File.Delete(outputPath);
                    }
                    catch
                    {
                        // Ignore delete errors, build will overwrite
                    }
                }
            }

            try
            {
                if (_buildStrategy == AssemblyBuildStrategy.Roslyn)
                    BuildWithRoslyn(extension, outputPath);
                else
                    BuildWithILPack(extension, outputPath);

                return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading: false);
            }
            catch
            {
                throw; // Re-throw the original exception
            }
        }

        private void BuildWithRoslyn(ParsedExtension extension, string outputPath)
        {
            var generator = new RoslynCommandTypeGenerator();
            string code = generator.GenerateExtensionCode(extension);
            File.WriteAllText(Path.Combine(Path.GetDirectoryName(outputPath), $"{extension.Name}.cs"), code);

            var tree = CSharpSyntaxTree.ParseText(code);
            var compilation = CSharpCompilation.Create(
                Path.GetFileNameWithoutExtension(outputPath),
                new[] { tree },
                ResolveRoslynReferences(),
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, optimizationLevel: OptimizationLevel.Release));

            using var fs = new FileStream(outputPath, FileMode.Create);
            var result = compilation.Emit(fs);
            
            if (!result.Success)
            {
                HandleCompilationErrors(result.Diagnostics);
                throw new Exception("Roslyn compilation failed.");
            }
        }

        private void BuildWithILPack(ParsedExtension extension, string outputPath)
        {
            // Load runtime for dependecy (Probably temparary due to future implementation of env loader in C#)
            var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var twoUp = Path.GetFullPath(Path.Combine(loaderDir, "..", ".."));
            var runtimeName = $"PyRevitLabs.PyRevit.Runtime.{_revitVersion}.dll";
            var runtimePath = Directory
                .EnumerateFiles(loaderDir, runtimeName, SearchOption.TopDirectoryOnly)
                .FirstOrDefault();

            if (runtimePath != null)
            {
                Assembly.LoadFrom(runtimePath);

            }
            var generator = new ReflectionEmitCommandTypeGenerator();
            var asmName = new AssemblyName(extension.Name) { Version = new Version(1, 0, 0, 0) };
            string moduleName = Path.GetFileNameWithoutExtension(outputPath);

#if NETFRAMEWORK
            var asmBuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(
                asmName, AssemblyBuilderAccess.RunAndSave, Path.GetDirectoryName(outputPath));
            var moduleBuilder = asmBuilder.DefineDynamicModule(moduleName, Path.GetFileName(outputPath));
#else
            var asmBuilder = AssemblyBuilder.DefineDynamicAssembly(asmName, AssemblyBuilderAccess.Run);
            var moduleBuilder = asmBuilder.DefineDynamicModule(moduleName);
#endif

            foreach (var cmd in extension.CollectCommandComponents())
                generator.DefineCommandType(extension, cmd, moduleBuilder);

#if NETFRAMEWORK
            asmBuilder.Save(Path.GetFileName(outputPath));
#else
            new AssemblyGenerator().GenerateAssembly(asmBuilder, outputPath);
#endif
        }

        private List<MetadataReference> ResolveRoslynReferences()
        {
            string baseDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var refs = new List<MetadataReference>
            {
                MetadataReference.CreateFromFile(typeof(object).Assembly.Location),
                MetadataReference.CreateFromFile(typeof(Console).Assembly.Location),
                MetadataReference.CreateFromFile(Path.Combine(AppContext.BaseDirectory, "RevitAPI.dll")),
                MetadataReference.CreateFromFile(Path.Combine(AppContext.BaseDirectory, "RevitAPIUI.dll")),
                MetadataReference.CreateFromFile(Path.Combine(baseDir, $"PyRevitLabs.PyRevit.Runtime.{_revitVersion}.dll"))
            };
            string sys = Path.Combine(Path.GetDirectoryName(typeof(object).Assembly.Location), "System.Runtime.dll");
            if (File.Exists(sys)) refs.Add(MetadataReference.CreateFromFile(sys));
            return refs;
        }

        private static void HandleCompilationErrors(IEnumerable<Diagnostic> diagnostics)
        {
            // Compilation errors will be handled by the calling method
            // This method is kept for potential future error handling
        }

        // TODO: Implement a proper hashing module
        private static string GetStableHash(string input)
        {
            using var sha1 = System.Security.Cryptography.SHA1.Create();
            var hash = sha1.ComputeHash(Encoding.UTF8.GetBytes(input));
            return BitConverter.ToString(hash).Replace("-", string.Empty).ToLowerInvariant();
        }

        public void LoadAssembly(ExtensionAssemblyInfo info)
        {
            if (!File.Exists(info.Location))
                throw new FileNotFoundException("Assembly not found", info.Location);
                
            try
            {
                Assembly.LoadFrom(info.Location);
            }
            catch
            {
                throw;
            }
        }
    }
}
