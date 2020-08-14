using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

using Microsoft.CodeAnalysis;
using CS = Microsoft.CodeAnalysis.CSharp;
using VB = Microsoft.CodeAnalysis.VisualBasic;
using Microsoft.CodeAnalysis.Emit;


namespace pyRevitLabs.Common {
    public static class CodeCompiler {
        #region CSharp Compilation

        private static readonly CS.LanguageVersion MaxCSharpLanguageVersion =
            Enum.GetValues(typeof(CS.LanguageVersion))
                .Cast<CS.LanguageVersion>()
                .Max();

        public static bool CompileCSharp(
            IEnumerable<string> sourceFiles,
            string outputPath,
            IEnumerable<string> references,
            IEnumerable<string> defines,
            out List<string> messages
            ) {
            CS.CSharpCompilation compilation =
                CreateCSharpCompilation(
                    sourceFiles,
                    Path.GetFileName(outputPath),
                    references,
                    defines,
                    out messages
                );

            // compile and write results
            var result = compilation.Emit(outputPath);
            foreach (var diag in result.Diagnostics)
                messages.Add(diag.ToString());

            return result.Success;
        }

        public static Assembly CompileCSharpToAssembly(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            IEnumerable<string> defines,
            out List<string> messages
            ) {
            var compilation = CreateCSharpCompilation(
                sourceFiles,
                assemblyName,
                references,
                defines,
                out messages
                );
            // compile and write results
            var emitOpts = new EmitOptions();
            using (var assmData = new MemoryStream())
            using (var assmPdbData = new MemoryStream()) {
                var result =
                    compilation.Emit(
                        peStream: assmData,
                        pdbStream: assmPdbData,
                        options: emitOpts
                        );
                foreach (var diag in result.Diagnostics)
                    messages.Add(diag.ToString());

                // load assembly from memory stream
                assmData.Seek(0, SeekOrigin.Begin);
                if (assmData.Length > 0)
                    return Assembly.Load(
                        assmData.ToArray(),
                        assmPdbData.ToArray()
                        );
            }
            return null;
        }

        // TODO: implement resources https://stackoverflow.com/a/26853131/2350244
        private static CS.CSharpCompilation CreateCSharpCompilation(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            IEnumerable<string> defines,
            out List<string> messages
            ) {
            // parse the source files
            var parseOpts =
                CS.CSharpParseOptions.Default
                .WithLanguageVersion(MaxCSharpLanguageVersion)
                .WithPreprocessorSymbols(defines);

            // and build syntax tree
            List<SyntaxTree> syntaxTrees = new List<SyntaxTree>();
            foreach (var sourceFile in sourceFiles)
                syntaxTrees.Add(
                    CS.CSharpSyntaxTree.ParseText(
                        text: File.ReadAllText(sourceFile),
                        options: parseOpts,
                        path: sourceFile,
                        encoding: Encoding.UTF8
                        )
                    );

            // collect references
            var refs = new List<string>();
            // add mscorelib
            refs.Add(typeof(object).Assembly.Location);
            foreach (var refFile in references)
                refs.Add(refFile);

            messages = new List<string>();
            messages.Add($"Define: {string.Join(";", defines)}");
            var mdataRefs = new List<MetadataReference>();
            foreach (var refPath in refs) {
                messages.Add($"Reference: {refPath}");
                mdataRefs.Add(
                    AssemblyMetadata.CreateFromFile(refPath).GetReference()
                    );    
            }

            // compile options
            var compileOpts =
                new CS.CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                    .WithOverflowChecks(true)
                    .WithPlatform(Platform.X64)
                    .WithOptimizationLevel(OptimizationLevel.Release);

            // create compilation job
            return CS.CSharpCompilation.Create(
                assemblyName: assemblyName,
                syntaxTrees: syntaxTrees,
                references: mdataRefs,
                options: compileOpts
                );
        }

        #endregion

        #region Visual Basic Compilation

        private static readonly VB.LanguageVersion MaxVBLanguageVersion =
            Enum.GetValues(typeof(VB.LanguageVersion))
                .Cast<VB.LanguageVersion>()
                .Max();

        public static bool CompileVisualBasic(
        IEnumerable<string> sourceFiles,
        string outputPath,
        IEnumerable<string> references,
        IEnumerable<KeyValuePair<string, object>> defines,
        out List<string> messages
        ) {
            VB.VisualBasicCompilation compilation =
                CreateVisualBasicCompilation(
                    sourceFiles,
                    Path.GetFileName(outputPath),
                    references,
                    defines,
                    out messages
                );

            // compile and write results
            var result = compilation.Emit(outputPath);
            foreach (var diag in result.Diagnostics)
                messages.Add(diag.ToString());

            return result.Success;
        }

        public static Assembly CompileVisualBasicToAssembly(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            IEnumerable<KeyValuePair<string, object>> defines,
            out List<string> messages
            ) {
            var compilation = CreateVisualBasicCompilation(
                sourceFiles,
                assemblyName,
                references,
                defines,
                out messages
                );
            // compile and write results
            var emitOpts = new EmitOptions();
            using (var assmData = new MemoryStream())
            using (var assmPdbData = new MemoryStream()) {
                var result =
                    compilation.Emit(
                        peStream: assmData,
                        pdbStream: assmPdbData,
                        options: emitOpts
                        );
                foreach (var diag in result.Diagnostics)
                    messages.Add(diag.ToString());

                // load assembly from memory stream
                assmData.Seek(0, SeekOrigin.Begin);
                if (assmData.Length > 0)
                    return Assembly.Load(
                        assmData.ToArray(),
                        assmPdbData.ToArray()
                        );
            }
            return null;
        }

        // TODO: implement resources https://stackoverflow.com/a/26853131/2350244
        private static VB.VisualBasicCompilation CreateVisualBasicCompilation(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            IEnumerable<KeyValuePair<string, object>> defines,
            out List<string> messages
            ) {
            // parse the source files
            var parseOpts =
                VB.VisualBasicParseOptions.Default
                .WithLanguageVersion(MaxVBLanguageVersion)
                .WithPreprocessorSymbols(defines);

            // and build syntax tree
            List<SyntaxTree> syntaxTrees = new List<SyntaxTree>();
            foreach (var sourceFile in sourceFiles)
                syntaxTrees.Add(
                    VB.VisualBasicSyntaxTree.ParseText(
                        text: File.ReadAllText(sourceFile),
                        options: parseOpts,
                        path: sourceFile,
                        encoding: Encoding.UTF8
                        )
                    );

            // collect references
            var refs = new List<string>();
            // add mscorelib
            refs.Add(typeof(object).Assembly.Location);
            foreach (var refFile in references)
                refs.Add(refFile);

            messages = new List<string>();
            messages.Add($"Define: {string.Join(";", defines)}");
            var mdataRefs = new List<MetadataReference>();
            foreach (var refPath in refs) {
                messages.Add($"Reference: {refPath}");
                mdataRefs.Add(
                    AssemblyMetadata.CreateFromFile(refPath).GetReference()
                    );
            }

            // compile options
            var compileOpts =
                new VB.VisualBasicCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                    .WithOverflowChecks(true)
                    .WithPlatform(Platform.X64)
                    .WithOptimizationLevel(OptimizationLevel.Release);

            // create compilation job
            return VB.VisualBasicCompilation.Create(
                assemblyName: assemblyName,
                syntaxTrees: syntaxTrees,
                references: mdataRefs,
                options: compileOpts
                );
        }
    }
    #endregion
}
