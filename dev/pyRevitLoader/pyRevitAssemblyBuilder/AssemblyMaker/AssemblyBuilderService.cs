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
        private static readonly string _executingAssemblyLocation = Assembly.GetExecutingAssembly().Location;
        private static readonly string _baseDir = Path.GetDirectoryName(_executingAssemblyLocation);
        private static readonly string _appDataPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);

        public AssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy)
        {
            _revitVersion = revitVersion ?? throw new ArgumentNullException(nameof(revitVersion));
            _buildStrategy = buildStrategy;

#if !NETFRAMEWORK
            if (_buildStrategy == AssemblyBuildStrategy.ILPack)
            {
                // On .NET Core, hook into AssemblyLoadContext to resolve Lokad.ILPack two folders up
                var baseDir = _baseDir;
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
                var baseDir = _baseDir;
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

        public ExtensionAssemblyInfo BuildExtensionAssembly(ParsedExtension extension, IEnumerable<ParsedExtension> libraryExtensions = null)
        {
            if (extension == null)
                throw new ArgumentNullException(nameof(extension));

            // Pre-load module DLLs before building the assembly
            // This matches the pythonic loader's approach: collect modules and load them
            // so they're available in the AppDomain for CLREngine to reference
            LoadExtensionModules(extension);

            // Use build strategy as seed to differentiate DLLs built with different strategies
            // This ensures DLLs are only regenerated when extension structure changes or build strategy changes
            string strategySeed = _buildStrategy == AssemblyBuildStrategy.ILPack ? "ILPack" : "Roslyn";
            string hash = GetStableHash(extension.GetHash(strategySeed) + _revitVersion).Substring(0, 16);
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
                catch (Exception)
                {
                    // If file is corrupted or invalid, delete it and rebuild
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
                    BuildWithRoslyn(extension, outputPath, libraryExtensions);
                else
                    BuildWithILPack(extension, outputPath, libraryExtensions);

                return new ExtensionAssemblyInfo(extension.Name, outputPath, isReloading: false);
            }
            catch
            {
                throw; // Re-throw the original exception
            }
        }

        /// <summary>
        /// Pre-loads module DLLs for all commands in the extension.
        /// Mimics the pythonic loader's approach: assmutils.load_asm_files(ui_ext_modules)
        /// This makes the modules available in the AppDomain for CLREngine to reference.
        /// </summary>
        private void LoadExtensionModules(ParsedExtension extension)
        {
            var loadedModules = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            // Collect all module DLLs from all commands
            foreach (var cmd in extension.CollectCommandComponents())
            {
                if (cmd.Modules == null || cmd.Modules.Count == 0)
                    continue;

                foreach (var moduleName in cmd.Modules)
                {
                    // Find the module DLL using binary paths
                    var modulePath = extension.FindModuleDll(moduleName, cmd);
                    
                    if (string.IsNullOrEmpty(modulePath))
                    {
                        continue;
                    }

                    // Skip if already loaded
                    if (loadedModules.Contains(modulePath))
                        continue;

                    try
                    {
                        // Load the module DLL into the AppDomain
                        Assembly.LoadFrom(modulePath);
                        loadedModules.Add(modulePath);
                    }
                    catch (Exception)
                    {
                        // Silently ignore module load failures
                    }
                }
            }

            // Update the environment dictionary with loaded module paths
            // This matches pythonic loader's sessioninfo.update_loaded_pyrevit_referenced_modules()
            if (loadedModules.Count > 0)
            {
                UpdateReferencedAssemblies(loadedModules);
            }
        }

        /// <summary>
        /// Updates the AppDomain's environment dictionary with referenced assemblies.
        /// Mimics pythonic loader's sessioninfo.update_loaded_pyrevit_referenced_modules()
        /// </summary>
        private void UpdateReferencedAssemblies(HashSet<string> newModulePaths)
        {
            try
            {
                // Get the environment dictionary from AppDomain
                const string envDictKey = "PYREVITEnvVarsDict";
                const string refedAssmsKey = "PYREVIT_REFEDASSMS";
                
                var envDict = AppDomain.CurrentDomain.GetData(envDictKey);
                if (envDict == null)
                {
                    return;
                }

                // Use reflection to access the dictionary
                var dictType = envDict.GetType();
                var containsMethod = dictType.GetMethod("Contains", new[] { typeof(object) });
                var getItemMethod = dictType.GetMethod("get_Item", new[] { typeof(object) });
                var setItemMethod = dictType.GetMethod("set_Item", new[] { typeof(object), typeof(object) });

                if (containsMethod == null || getItemMethod == null || setItemMethod == null)
                {
                    return;
                }

                // Get existing referenced assemblies
                var existingAssemblies = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                if ((bool)containsMethod.Invoke(envDict, new object[] { refedAssmsKey }))
                {
                    var existingValue = (string)getItemMethod.Invoke(envDict, new object[] { refedAssmsKey });
                    if (!string.IsNullOrEmpty(existingValue))
                    {
                        foreach (var path in existingValue.Split(Path.PathSeparator))
                        {
                            if (!string.IsNullOrWhiteSpace(path))
                                existingAssemblies.Add(path);
                        }
                    }
                }

                // Add new module paths
                existingAssemblies.UnionWith(newModulePaths);

                // Update the environment dictionary
                var updatedValue = string.Join(Path.PathSeparator.ToString(), existingAssemblies);
                setItemMethod.Invoke(envDict, new object[] { refedAssmsKey, updatedValue });
            }
            catch (Exception)
            {
                // Silently ignore environment dictionary update failures
            }
        }

        private void BuildWithRoslyn(ParsedExtension extension, string outputPath, IEnumerable<ParsedExtension> libraryExtensions)
        {
            var generator = new RoslynCommandTypeGenerator();
            string code = generator.GenerateExtensionCode(extension, _revitVersion, libraryExtensions);
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

        private void BuildWithILPack(ParsedExtension extension, string outputPath, IEnumerable<ParsedExtension> libraryExtensions)
        {
            // Load runtime for dependecy (Probably temparary due to future implementation of env loader in C#)
            var loaderDir = _baseDir;
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
                generator.DefineCommandType(extension, cmd, moduleBuilder, libraryExtensions, _revitVersion);

#if NETFRAMEWORK
            asmBuilder.Save(Path.GetFileName(outputPath));
#else
            new AssemblyGenerator().GenerateAssembly(asmBuilder, outputPath);
#endif
        }

        private List<MetadataReference> ResolveRoslynReferences()
        {
            string baseDir = _baseDir;
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
