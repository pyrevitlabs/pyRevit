namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Pins how <c>ScriptOutput.print_table</c> and friends turn CPython arguments into table cells.
/// Python objects reach C# as pythonnet wrappers rather than CLR enumerables, so these run the
/// shipped <c>PythonTableData</c> conversions against real pythonnet objects.
/// </summary>
public class ScriptOutputConversionTests {
    private static string Observed(string observation) =>
        InterpreterLifecycleProbe.Record.ScriptOutputConversions[observation];

    /// <summary>Python <c>None</c> renders as an empty cell, as a CLR <c>null</c> does.</summary>
    [Fact]
    public void NoneCells_RenderEmpty() {
        Assert.Equal("1||a;", Observed(ScriptOutputConversionProbe.NoneCells));
        Assert.Equal("x|", Observed(ScriptOutputConversionProbe.NoneListItems));
    }

    /// <summary>A string row is one cell, not one cell per character.</summary>
    [Fact]
    public void StringRows_StayWhole() {
        Assert.Equal("abc;x|y", Observed(ScriptOutputConversionProbe.StringRows));
        Assert.Equal("abc", Observed(ScriptOutputConversionProbe.StringList));
    }

    /// <summary>
    /// A string or scalar passed as the whole table yields no rows, so <c>print_table</c> reports
    /// the missing table instead of rendering characters or failing.
    /// </summary>
    [Fact]
    public void NonTablePayloads_YieldNoRows() {
        Assert.Equal(string.Empty, Observed(ScriptOutputConversionProbe.StringTable));
        Assert.Equal(string.Empty, Observed(ScriptOutputConversionProbe.ScalarTable));
    }

    /// <summary>
    /// An exception raised while iterating the user's data reaches the script instead of
    /// producing a silently truncated table.
    /// </summary>
    [Fact]
    public void ErrorsRaisedDuringIteration_Propagate() {
        string rows = Observed(ScriptOutputConversionProbe.RaisingRows);
        string cells = Observed(ScriptOutputConversionProbe.RaisingCells);

        Assert.StartsWith("error: PythonException", rows);
        Assert.Contains("rows boom", rows);
        Assert.StartsWith("error: PythonException", cells);
        Assert.Contains("cells boom", cells);
    }

    /// <summary>Python dicts convert entry by entry.</summary>
    [Fact]
    public void Dictionaries_ConvertEntries() {
        Assert.Equal("k=1", Observed(ScriptOutputConversionProbe.Dictionary));
    }

    /// <summary>
    /// Objects iterable only through the <c>__len__</c>/<c>__getitem__</c> sequence protocol convert
    /// item by item, as Python's <c>iter()</c> would, for both rows and cells.
    /// </summary>
    [Fact]
    public void SequenceProtocolObjects_ConvertItemByItem() {
        Assert.Equal("a|1;b|", Observed(ScriptOutputConversionProbe.SequenceRows));
        Assert.Equal("x|2", Observed(ScriptOutputConversionProbe.SequenceCells));
    }

    /// <summary>
    /// pythonnet releases the GIL around CLR calls made from a script, so the conversions must take
    /// it themselves; calling the CPython API without it crashes Revit.
    /// </summary>
    [Fact]
    public void Conversions_TakeTheGilWhenTheCallerReleasedIt() {
        Assert.Equal("a|1;b|/a||1/k=1", Observed(ScriptOutputConversionProbe.ReleasedGil));
    }

    /// <summary>
    /// <c>print_html_table</c> prints this warning instead of an empty table; <c>print_table</c>
    /// prints nothing, as both did before CPython support.
    /// </summary>
    [Fact]
    public void EmptyTableData_HasAWarningForTheHtmlTable() {
        Assert.Equal("### :warning: No table_data list", Observed(ScriptOutputConversionProbe.EmptyTable));
        Assert.Equal("<render>", Observed(ScriptOutputConversionProbe.FilledTable));
    }

    /// <summary><c>print_html_table</c> takes the empty-table warning from <c>PythonTableData</c>.</summary>
    [Fact]
    public void HtmlTablePrinter_UsesEmptyTableWarning() {
        string body = ScriptOutputMember("public void print_html_table(");

        Assert.True(CSharpSource.IsInBlockOf(body, "if (emptyTableWarning != null)", "return;"),
            "print_html_table must stop when PythonTableData.EmptyTableWarning reports no rows");
        Assert.Contains("PythonTableData.EmptyTableWarning(rows)", body);
    }

    /// <summary><c>print_table</c> prints nothing for table data that yields no rows.</summary>
    [Fact]
    public void TablePrinter_SkipsEmptyTableData() {
        string body = ScriptOutputMember("public void print_table(");

        Assert.True(CSharpSource.IsInBlockOf(body, "if (rows.Count == 0)", "return;"),
            "print_table must stop when the table data yields no rows");
        Assert.DoesNotContain("EmptyTableWarning", body);
    }

    private static string ScriptOutputMember(string declaration) {
        string source = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Sources", "ScriptOutput.cs"));
        return CSharpSource.MemberBody(source, declaration);
    }
}
