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
            out List<string> messages
            ) {
            CSharpCompilation compilation =
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
            using (var assmData = new MemoryStream()) {
                var result = compilation.Emit(assmData);
                foreach (var diag in result.Diagnostics)
                    messages.Add(diag.ToString());

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
            IEnumerable<string> defines,
            out List<string> messages
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
                new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
                    .WithOverflowChecks(true)
                    .WithPlatform(Platform.X64)
                    .WithOptimizationLevel(OptimizationLevel.Release);

            // create compilation job
            return CSharpCompilation.Create(
                assemblyName,
                syntaxTree,
                mdataRefs,
                compileOpts
                );
        }
    }
}
