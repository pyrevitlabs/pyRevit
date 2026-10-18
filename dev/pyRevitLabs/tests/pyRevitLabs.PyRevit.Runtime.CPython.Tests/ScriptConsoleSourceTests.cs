using System.Reflection;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace PyRevitLabs.PyRevit.Runtime.CPython.Tests;

/// <summary>Guards output fallback invariants without loading the Revit-hosted WPF assembly.</summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class ScriptConsoleSourceTests {
    private const string FallbackGate = "if (_renderer.Failure != RendererFailure.None)";

    private static readonly string Source = File.ReadAllText(
        Path.Combine(AppContext.BaseDirectory, "Sources", "ScriptConsole.cs"));

    /// <summary>The first flush must show the window before testing runtime availability.</summary>
    [Fact]
    public void Flush_ShowsWindowBeforeChoosingFallback() {
        var body = CSharpSource.MemberBody(Source, "private void FlushPendingEntries()");
        var ensureReady = body.IndexOf("EnsureDocumentReady();", StringComparison.Ordinal);
        var fallback = body.IndexOf(FallbackGate, StringComparison.Ordinal);
        Assert.True(ensureReady >= 0 && fallback > ensureReady);
    }

    /// <summary>Fallback writes and scrolling remain inside the UI gate with a null guard.</summary>
    [Fact]
    public void Flush_MarshalsFallbackAndReportsUnavailableOutput() {
        var body = CSharpSource.MemberBody(Source, "private void FlushPendingEntries()");
        Assert.Contains("ScriptOutputUi.TryBeginInvoke", body);
        var dispatch = body.IndexOf("ScriptOutputUi.TryBeginInvoke", StringComparison.Ordinal);
        var guard = body.IndexOf("_plainTextOutput == null", StringComparison.Ordinal);
        var append = body.IndexOf("_plainTextOutput.AppendText", StringComparison.Ordinal);
        Assert.True(dispatch >= 0 && guard > dispatch && append > guard);
        Assert.True(CSharpSource.IsInBlockOf(body, "if (!ScriptOutputUi.TryBeginInvoke", "_plainTextOutput.AppendText"));
        Assert.True(CSharpSource.IsInBlockOf(body, "if (!ScriptOutputUi.TryBeginInvoke", "_plainTextOutput.ScrollToEnd"));
        Assert.True(CSharpSource.IsInBlockOf(body, "if (_plainTextOutput == null)", "ReportOutputLossOnce();"));
        Assert.Contains("ReportOutputLossOnce();", body[(body.IndexOf("_plainTextOutput.ScrollToEnd", StringComparison.Ordinal))..]);
    }

    /// <summary>Freeze buffers new output until Unfreeze appends it to the fallback.</summary>
    [Fact]
    public void Freeze_PairsWithUnfreezeWithoutRequiringWebView() {
        var freeze = CSharpSource.MemberBody(Source, "public void Freeze()");
        Assert.Contains("_frozen = true;", freeze);
        Assert.DoesNotContain(FallbackGate, freeze);
        var unfreeze = CSharpSource.MemberBody(Source, "public void Unfreeze()");
        Assert.True(CSharpSource.IsInBlockOf(unfreeze, FallbackGate, "_pendingHtml.Append(snapshot);"));
        Assert.Contains("_frozenPendingHtml.Clear();", unfreeze);
        Assert.Contains("_frozen = false;", unfreeze);
        Assert.Contains("QueueFlush();", unfreeze);
    }

    /// <summary>Plain-text conversion preserves table columns, rows, block breaks, and entities.</summary>
    /// <param name="html">The rendered HTML fragment.</param>
    /// <param name="expected">The readable plain-text representation.</param>
    [Theory]
    [InlineData("<table><tr><td>a</td><td>b</td></tr></table>", "a\tb")]
    [InlineData("<table><thead><tr><th>Name</th><th>Age</th></tr></thead><tbody><tr><td>Bob</td><td>42</td></tr></tbody></table>", "Name\tAge\nBob\t42\n")]
    [InlineData("<h1>Title</h1><p>A &amp; B<br/>C</p><li>Item</li>", "Title\nA & B\nC\nItem\n")]
    [InlineData("<div>&lt;tag&gt;</div><pre>line 1<br>line 2</pre>", "<tag>\nline 1\nline 2\n")]
    [InlineData("", "")]
    public void ToPlainText_PreservesReadableStructure(string html, string expected) {
        Assert.Equal(expected, ConvertToPlainText.Value(html));
    }

    private static readonly Lazy<Func<string, string>> ConvertToPlainText = new(() => {
        var method = CSharpSyntaxTree.ParseText(Source).GetRoot().DescendantNodes()
            .OfType<MethodDeclarationSyntax>().Single(member => member.Identifier.ValueText == "ToPlainText");
        var source = "using System.Text.RegularExpressions; internal static class PlainTextFixture { " + method + " }";
        var references = ((string)AppContext.GetData("TRUSTED_PLATFORM_ASSEMBLIES")!).Split(Path.PathSeparator)
            .Select(path => MetadataReference.CreateFromFile(path));
        var compilation = CSharpCompilation.Create("PlainTextFixture", [CSharpSyntaxTree.ParseText(source)],
            references, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary));
        using var assemblyStream = new MemoryStream();
        var result = compilation.Emit(assemblyStream);
        Assert.True(result.Success, string.Join(Environment.NewLine, result.Diagnostics));
        var converter = Assembly.Load(assemblyStream.ToArray()).GetType("PlainTextFixture")!
            .GetMethod("ToPlainText", BindingFlags.NonPublic | BindingFlags.Static)!;
        return converter.CreateDelegate<Func<string, string>>();
    });
}
