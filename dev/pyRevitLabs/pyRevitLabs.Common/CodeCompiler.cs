using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

namespace pyRevitLabs.Common {
    public static class CodeCompiler {
        private static readonly LanguageVersion MaxLanguageVersion =
            Enum.GetValues(typeof(LanguageVersion))
                .Cast<LanguageVersion>()
                .Max();

        public static bool CompileCSharp(
            IEnumerable<string> sourceFiles,
            string outputPath,
            IEnumerable<string> references,
            IEnumerable<string> defines,
            bool log
            ) {
            // prepare a file for logging
            string compileLog = Path.Combine(
                Path.GetDirectoryName(outputPath),
                Path.GetFileNameWithoutExtension(outputPath) + ".log"
                );

            CSharpCompilation compilation =
                CreateCSharpCompilation(
                    sourceFiles,
                    Path.GetFileName(outputPath),
                    references,
                    defines
                );

            // compile and write results
            string diagMsg = string.Empty;
            var result = compilation.Emit(outputPath);
            foreach (var diag in result.Diagnostics)
                diagMsg += $"{diag}\n";

            if (log)
                File.AppendAllText(compileLog, diagMsg);

            return true;
        }

        public static Assembly CompileCSharpToAssembly(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            out List<string> messages,
            IEnumerable<string> defines = null
            ) {
            var compilation = CreateCSharpCompilation(
                sourceFiles,
                assemblyName,
                references,
                defines
                );
            // compile and write results
            messages = new List<string>();
            using (var assmData = new MemoryStream()) {
                var result = compilation.Emit(assmData);
                foreach (var diag in result.Diagnostics)
                    messages.Append(diag.ToString());

                // load assembly from memory stream
                assmData.Seek(0, SeekOrigin.Begin);
                if (assmData.Length > 0)
                    return Assembly.Load(assmData.ToArray());
            }
            return null;
        }

        // TODO: implement resources https://stackoverflow.com/a/26853131/2350244
        private static CSharpCompilation CreateCSharpCompilation(
            IEnumerable<string> sourceFiles,
            string assemblyName,
            IEnumerable<string> references,
            IEnumerable<string> defines
            ) {
            // parse the source files
            var parseOpts =
                CSharpParseOptions.Default
                .WithLanguageVersion(MaxLanguageVersion)
                .WithPreprocessorSymbols(defines);

            // and build syntax tree
            List<SyntaxTree> syntaxTree = new List<SyntaxTree>();
            foreach (var sourceFile in sourceFiles)
                syntaxTree.Add(
                    CSharpSyntaxTree.ParseText(
                        text: File.ReadAllText(sourceFile),
                        options: parseOpts,
                        path: sourceFile
                        )
                    );

            // collect references
            string corelib = typeof(object).Assembly.Location;
            List<MetadataReference> refs =
                new List<MetadataReference> {
                    AssemblyMetadata.CreateFromFile(corelib).GetReference()
                };
            foreach (var refFile in references)
                refs.Add(
                    AssemblyMetadata.CreateFromFile(refFile).GetReference()
                    );

            // compile options
            var compileOpts =
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                    .WithOverflowChecks(true)
                    .WithOptimizationLevel(OptimizationLevel.Release);

            // create compilation job
            return CSharpCompilation.Create(
                assemblyName,
                syntaxTree,
                refs,
                compileOpts
                );
        }
    }
}
