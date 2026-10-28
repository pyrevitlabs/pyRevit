using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Runs <c>ScriptOutput</c>'s Python-to-table conversions against live pythonnet objects.
/// </summary>
/// <remarks>
/// <c>ScriptOutput</c> cannot be loaded outside Revit, so its conversion helpers are compiled from
/// the shipped source into a standalone fixture. The observations are taken on the interpreter the
/// lifecycle probe brings up, because pythonnet can only be initialized once per process.
/// Each observation is the rendered result, or <c>error: </c> followed by the exception type and
/// message the conversion threw.
/// </remarks>
internal static class ScriptOutputConversionProbe {
    public const string NoneCells = "none-cells";
    public const string NoneListItems = "none-list-items";
    public const string StringRows = "string-rows";
    public const string StringTable = "string-table";
    public const string ScalarTable = "scalar-table";
    public const string StringList = "string-list";
    public const string RaisingRows = "raising-rows";
    public const string RaisingCells = "raising-cells";
    public const string Dictionary = "dictionary";

    private const string Fixtures = """
        def raising_rows():
            yield ["first"]
            raise ValueError("rows boom")

        def raising_cells():
            yield "cell"
            raise ValueError("cells boom")

        none_cells = [[1, None, "a"], (None,)]
        none_list_items = ("x", None)
        string_rows = ["abc", ("x", "y")]
        """;

    private static readonly string[] HelperNames = ["ToRows", "ToList", "ToDictionary", "ToCellText"];

    public static IReadOnlyDictionary<string, string> Observe() {
        var observations = new Dictionary<string, string>();
        Type fixture;
        try {
            fixture = Compile();
        }
        catch (Exception ex) {
            string failure = Describe(ex);
            foreach (var key in new[] { NoneCells, NoneListItems, StringRows, StringTable, ScalarTable, StringList, RaisingRows, RaisingCells, Dictionary })
                observations[key] = failure;
            return observations;
        }

        using Py.GILState gil = Py.GIL();
        using PyModule scope = Py.CreateScope();
        scope.Exec(Fixtures);

        observations[NoneCells] = Observe(() => Rows(fixture, scope.Get("none_cells")));
        observations[NoneListItems] = Observe(() => Cells(fixture, scope.Get("none_list_items")));
        observations[StringRows] = Observe(() => Rows(fixture, scope.Get("string_rows")));
        observations[StringTable] = Observe(() => Rows(fixture, new PyString("abc")));
        observations[ScalarTable] = Observe(() => Rows(fixture, new PyInt(42)));
        observations[StringList] = Observe(() => Cells(fixture, new PyString("abc")));
        observations[RaisingRows] = Observe(() => Rows(fixture, scope.Eval("raising_rows()")));
        observations[RaisingCells] = Observe(() => Cells(fixture, scope.Eval("raising_cells()")));
        observations[Dictionary] = Observe(() => Entries(fixture, scope.Eval("{'k': 1}")));
        return observations;
    }

    private static string Rows(Type fixture, PyObject value) {
        using (value) {
            var rows = (List<List<string>>)Invoke(fixture, "ToRows", value)!;
            return string.Join(";", rows.Select(row => string.Join("|", row)));
        }
    }

    private static string Cells(Type fixture, PyObject value) {
        using (value) {
            var cells = (List<string>)Invoke(fixture, "ToList", value)!;
            return string.Join("|", cells);
        }
    }

    private static string Entries(Type fixture, PyObject value) {
        using (value) {
            var entries = (Dictionary<string, string>)Invoke(fixture, "ToDictionary", value)!;
            return string.Join(";", entries.Select(entry => entry.Key + "=" + entry.Value));
        }
    }

    private static object? Invoke(Type fixture, string name, object value) {
        var method = fixture.GetMethod(name, BindingFlags.NonPublic | BindingFlags.Static)!;
        try {
            return method.Invoke(null, [value]);
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null) {
            throw ex.InnerException;
        }
    }

    private static string Observe(Func<string> conversion) {
        try {
            return conversion();
        }
        catch (Exception ex) {
            return Describe(ex);
        }
    }

    private static string Describe(Exception ex) => "error: " + ex.GetType().Name + ": " + ex.Message;

    private static Type Compile() {
        string path = Path.Combine(AppContext.BaseDirectory, "Sources", "ScriptOutput.cs");
        var helpers = CSharpSyntaxTree.ParseText(File.ReadAllText(path)).GetRoot().DescendantNodes()
            .OfType<MethodDeclarationSyntax>()
            .Where(method => HelperNames.Contains(method.Identifier.ValueText))
            .Select(method => method.ToFullString());
        var source = """
            using System;
            using System.Collections;
            using System.Collections.Generic;
            using PyDict = Python.Runtime.PyDict;
            using PyIterable = Python.Runtime.PyIterable;
            using PyObject = Python.Runtime.PyObject;
            using PyString = Python.Runtime.PyString;
            internal static class ScriptOutputConversionFixture {
            """ + string.Join(Environment.NewLine, helpers) + "}";

        var references = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator)
            .Append(typeof(PyObject).Assembly.Location)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Select(reference => MetadataReference.CreateFromFile(reference));
        var compilation = CSharpCompilation.Create("ScriptOutputConversionFixture", [CSharpSyntaxTree.ParseText(source)],
            references, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        using var assemblyStream = new MemoryStream();
        var result = compilation.Emit(assemblyStream);
        if (!result.Success)
            throw new InvalidOperationException(string.Join(Environment.NewLine, result.Diagnostics));
        return Assembly.Load(assemblyStream.ToArray()).GetType("ScriptOutputConversionFixture")!;
    }
}
