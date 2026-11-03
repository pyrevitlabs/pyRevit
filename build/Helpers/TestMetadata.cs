using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace Build.Helpers;

internal sealed record ClassifiedTest(string Source, string ClassName, string Method, string Environment, string Level);
internal sealed record TestCatalogRequest(string Project, string Framework, string[] Sources, string[] Defines);
internal sealed record TestCatalogSuite(string Project, string Framework, IReadOnlyList<ClassifiedTest> Tests);

internal static class TestMetadata {
    private static readonly HashSet<string> TestAttributes = ["Test", "TestCase", "TestCaseSource", "TestMethod", "DataTestMethod", "Fact", "Theory"];
    private static readonly HashSet<string> Levels = ["Unit", "Integration", "E2E", "Performance"];
    private static readonly HashSet<string> Environments = ["HostFree", "Revit"];
    private static readonly HashSet<string> PurposeCategories = ["Regression"];

    internal static IReadOnlyList<ClassifiedTest> Read(string source, string path, IEnumerable<string>? defines = null) {
        var options = new CSharpParseOptions(LanguageVersion.Preview, preprocessorSymbols: defines);
        var root = CSharpSyntaxTree.ParseText(source, options).GetRoot();
        var tests = new List<ClassifiedTest>();
        foreach (var method in root.DescendantNodes().OfType<MethodDeclarationSyntax>()) {
            if (!method.AttributeLists.SelectMany(list => list.Attributes).Any(attribute => TestAttributes.Contains(Name(attribute))))
                continue;
            var type = method.Ancestors().OfType<ClassDeclarationSyntax>().First();
            var defaults = ReadTags(type.AttributeLists.SelectMany(list => list.Attributes), path);
            var overrides = ReadTags(method.AttributeLists.SelectMany(list => list.Attributes), path);
            string environment = overrides.GetValueOrDefault("Environment") ?? defaults.GetValueOrDefault("Environment") ?? "";
            string level = overrides.GetValueOrDefault("Level") ?? defaults.GetValueOrDefault("Level") ?? "";
            if (!Environments.Contains(environment) || !Levels.Contains(level))
                throw new InvalidDataException($"{path}: {type.Identifier}.{method.Identifier} requires Environment and Level metadata.");
            if (defaults.GetValueOrDefault("Environment") == "Revit" && environment != "Revit")
                throw new InvalidDataException($"{path}: a Revit fixture cannot override its environment to HostFree.");
            tests.Add(new(path, type.Identifier.ValueText, method.Identifier.ValueText, environment, level));
        }
        return tests;
    }

    private static string Name(AttributeSyntax attribute) => attribute.Name.ToString().Split('.').Last().Replace("Attribute", "");

    private static Dictionary<string, string> ReadTags(IEnumerable<AttributeSyntax> attributes, string path) {
        var tags = new Dictionary<string, string>();
        foreach (var attribute in attributes) {
            var values = attribute.ArgumentList?.Arguments
                .Select(argument => argument.Expression)
                .OfType<LiteralExpressionSyntax>()
                .Where(literal => literal.IsKind(SyntaxKind.StringLiteralExpression))
                .Select(literal => literal.Token.ValueText).ToArray() ?? [];
            if (Name(attribute) == "Trait" && values.Length == 2 && values[0] is "Environment" or "Level")
                AddTag(tags, values[0], values[1]);
            if (Name(attribute) is "Category" or "TestCategory" && values.Length == 1) {
                if (Environments.Contains(values[0])) AddTag(tags, "Environment", values[0]);
                if (Levels.Contains(values[0])) AddTag(tags, "Level", values[0]);
                if (!Environments.Contains(values[0]) && !Levels.Contains(values[0]) && !PurposeCategories.Contains(values[0]))
                    throw new InvalidDataException($"{path}: unknown test category '{values[0]}'; use an Environment, a Level or a declared purpose category.");
            }
        }
        return tags;
    }

    private static void AddTag(Dictionary<string, string> tags, string key, string value) {
        if (tags.ContainsKey(key)) throw new InvalidDataException($"Conflicting {key} tags.");
        tags.Add(key, value);
    }
}
