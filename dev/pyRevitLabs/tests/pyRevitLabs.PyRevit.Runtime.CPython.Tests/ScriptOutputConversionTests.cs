namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>
/// Pins how <c>ScriptOutput.print_table</c> and friends turn CPython arguments into table cells.
/// Python objects reach C# as pythonnet wrappers rather than CLR enumerables, so these run the
/// shipped conversion helpers against real pythonnet objects.
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
}
