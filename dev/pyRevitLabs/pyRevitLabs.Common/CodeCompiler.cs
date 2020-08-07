using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

namespace pyRevitLabs.Common {
    public static class CodeCompiler {
        public static bool CompileCSharp(
            IEnumerable<string> sourceFiles,
            string outputPath,
            IEnumerable<string> references,
            IEnumerable<string> defines = null,
            IEnumerable<string> resources = null,
            LanguageVersion langVersion = LanguageVersion.CSharp8
            ) {
            // prepare a file for logging
            string compileLog = Path.Combine(
                Path.GetDirectoryName(outputPath),
                Path.GetFileNameWithoutExtension(outputPath) + ".log"
                );


            // parse the source files
            var parseOpts =
                CSharpParseOptions.Default
                .WithLanguageVersion(langVersion)
                .WithPreprocessorSymbols(defines);

            // and build syntax tree
            List<SyntaxTree> syntaxTree = new List<SyntaxTree>();
            foreach (var sourceFile in sourceFiles)
                syntaxTree.Add(
                    CSharpSyntaxTree.ParseText(
                        File.ReadAllText(sourceFile),
                        path: sourceFile,
                        options: parseOpts
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
            var compilation = CSharpCompilation.Create(
                Path.GetFileName(outputPath),
                syntaxTree,
                refs,
                compileOpts
                );

            // compile and write results
            string diagMsg = string.Empty;
            var result = compilation.Emit(outputPath);
            foreach (var diag in result.Diagnostics)
                diagMsg += $"{diag}\n";
            File.AppendAllText(compileLog, diagMsg);
            return true;
        }
    }
}
