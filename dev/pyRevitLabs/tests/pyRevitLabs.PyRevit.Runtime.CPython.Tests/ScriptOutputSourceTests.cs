namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>Guards CPython collection conversion at ScriptOutput's object-parameter boundary.</summary>
public class ScriptOutputSourceTests {
    private static readonly string Source = File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "Sources", "ScriptOutput.cs"));

    /// <summary>Python objects reach C# as pythonnet wrappers, not CLR enumerables.</summary>
    [Fact]
    public void CollectionHelpers_RecognizePythonNetObjects() {
        var rows = CSharpSource.MemberBody(Source, "private static List<List<string>> ToRows(object value)");
        var list = CSharpSource.MemberBody(Source, "private static List<string> ToList(object value)");
        var dictionary = CSharpSource.MemberBody(Source, "private static Dictionary<string, string> ToDictionary(object value)");

        Assert.Contains("PyObject", rows);
        Assert.Contains("PyObject", list);
        Assert.Contains("PyDict", dictionary);
    }

    /// <summary>An unsupported table payload must be visible in the output rather than discarded.</summary>
    [Fact]
    public void PrintTable_ReportsEmptyRows() {
        var body = CSharpSource.MemberBody(Source, "public void print_table(");

        Assert.Contains("print_md(", body);
    }
}
