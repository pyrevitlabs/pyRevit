using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Python.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Runs <c>PythonTableData</c>, the Python-to-table conversions behind <c>ScriptOutput</c>, against
/// live pythonnet objects.
/// </summary>
/// <remarks>
/// The Runtime assembly cannot be loaded outside Revit, so the shipped <c>PythonTableData.cs</c> is
/// compiled on its own into a standalone fixture. The observations are taken on the interpreter the
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
    public const string SequenceRows = "sequence-rows";
    public const string SequenceCells = "sequence-cells";
    public const string EmptyTable = "empty-table";
    public const string FilledTable = "filled-table";

    private static readonly string[] Keys = [
        NoneCells, NoneListItems, StringRows, StringTable, ScalarTable, StringList, RaisingRows, RaisingCells,
        Dictionary, SequenceRows, SequenceCells, EmptyTable, FilledTable,
    ];

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

        class Sequence:
            def __init__(self, *items):
                self._items = list(items)
            def __len__(self):
                return len(self._items)
            def __getitem__(self, index):
                return self._items[index]

        sequence_rows = Sequence(Sequence("a", 1), Sequence("b", None))
        sequence_cells = Sequence("x", 2)
        """;

    private const string FixtureType = "PyRevitLabs.PyRevit.Runtime.PythonTableData";

    public static IReadOnlyDictionary<string, string> Observe() {
        var observations = new Dictionary<string, string>();
        Type fixture;
        try {
            fixture = Compile();
        }
        catch (Exception ex) {
            string failure = Describe(ex);
            foreach (var key in Keys)
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
        observations[SequenceRows] = Observe(() => Rows(fixture, scope.Get("sequence_rows")));
        observations[SequenceCells] = Observe(() => Cells(fixture, scope.Get("sequence_cells")));
        observations[EmptyTable] = Observe(() => Warning(fixture, scope.Eval("[]")));
        observations[FilledTable] = Observe(() => Warning(fixture, scope.Eval("[[1]]")));
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
            var cells = (List<string>)Invoke(fixture, "ToCells", value)!;
            return string.Join("|", cells);
        }
    }

    private static string Entries(Type fixture, PyObject value) {
        using (value) {
            var entries = (Dictionary<string, string>)Invoke(fixture, "ToDictionary", value)!;
            return string.Join(";", entries.Select(entry => entry.Key + "=" + entry.Value));
        }
    }

    private static string Warning(Type fixture, PyObject value) {
        using (value) {
            var rows = (List<List<string>>)Invoke(fixture, "ToRows", value)!;
            return (string?)Invoke(fixture, "EmptyTableWarning", rows) ?? "<render>";
        }
    }

    private static object? Invoke(Type fixture, string name, object value) {
        var method = fixture.GetMethod(name, BindingFlags.Public | BindingFlags.Static)!;
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
        string path = Path.Combine(AppContext.BaseDirectory, "Sources", "PythonTableData.cs");
        var source = File.ReadAllText(path);

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
        return Assembly.Load(assemblyStream.ToArray()).GetType(FixtureType, throwOnError: true)!;
    }
}
