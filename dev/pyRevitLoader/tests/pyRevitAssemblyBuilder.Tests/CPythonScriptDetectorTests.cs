#nullable enable
using System.IO;
using NUnit.Framework;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.Tests
{
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class CPythonScriptDetectorTests
    {
        private string _directory = string.Empty;

        [SetUp]
        public void CreateDirectory()
        {
            _directory = Path.Combine(Path.GetTempPath(), "cpython-detector-" + Path.GetRandomFileName());
            Directory.CreateDirectory(_directory);
        }

        [TearDown]
        public void DeleteDirectory()
        {
            Directory.Delete(_directory, recursive: true);
        }

        private ParsedComponent ComponentWithScript(string content, string? engineType = null)
        {
            var scriptPath = Path.Combine(_directory, "script.py");
            File.WriteAllText(scriptPath, content);
            var component = new ParsedComponent { ScriptPath = scriptPath };
            if (engineType != null)
                component.Engine = new EngineConfig { Type = engineType };
            return component;
        }

        private static ParsedExtension Extension(string? declaredEngine)
        {
            return new ParsedExtension { DeclaredPythonEngine = declaredEngine };
        }

        [TestCase("#! python3\nprint(1)\n")]
        [TestCase("# cpython\nprint(1)\n")]
        public void FirstLineNamesCPython_ReturnsTrue(string content)
        {
            Assert.That(CPythonScriptDetector.RunsOnCPython(ComponentWithScript(content), null), Is.True);
        }

        [TestCase("print(1)\n")]
        [TestCase("# -*- coding: utf-8 -*-\nprint('python3')\n")]
        [TestCase("")]
        public void NoMarkerOnFirstLine_ReturnsFalse(string content)
        {
            Assert.That(CPythonScriptDetector.RunsOnCPython(ComponentWithScript(content), null), Is.False);
        }

        [Test]
        public void MissingScript_ReturnsFalse()
        {
            var component = new ParsedComponent { ScriptPath = Path.Combine(_directory, "gone.py") };

            Assert.That(CPythonScriptDetector.RunsOnCPython(component, null), Is.False);
        }

        [Test]
        public void ExtensionDeclaresCPython_ReturnsTrueWithoutShebang()
        {
            var component = ComponentWithScript("print(1)\n");

            Assert.That(CPythonScriptDetector.RunsOnCPython(component, Extension("cpython")), Is.True);
        }

        [Test]
        public void ExtensionDeclaresIronPython_LeavesTheChoiceToTheFirstLine()
        {
            Assert.That(
                CPythonScriptDetector.RunsOnCPython(ComponentWithScript("print(1)\n"), Extension("ironpython")),
                Is.False);
            Assert.That(
                CPythonScriptDetector.RunsOnCPython(ComponentWithScript("#! python3\n"), Extension("ironpython")),
                Is.True);
        }

        [Test]
        public void BundleEngineTypeIronPython_BeatsShebangAndExtensionDeclaration()
        {
            var component = ComponentWithScript("#! python3\n", "IronPython");

            Assert.That(CPythonScriptDetector.RunsOnCPython(component, Extension("cpython")), Is.False);
        }

        [Test]
        public void BundleEngineTypeUnrecognized_UsesFirstLineAndIgnoresExtensionDeclaration()
        {
            Assert.That(
                CPythonScriptDetector.RunsOnCPython(ComponentWithScript("#! python3\n", "other"), null),
                Is.True);
            Assert.That(
                CPythonScriptDetector.RunsOnCPython(ComponentWithScript("print(1)\n", "other"), Extension("cpython")),
                Is.False);
        }

        [Test]
        public void BundleEngineTypeCPython_ReturnsTrueWithoutShebang()
        {
            var component = ComponentWithScript("print(1)\n", "cpython");

            Assert.That(CPythonScriptDetector.RunsOnCPython(component, null), Is.True);
        }
    }
}
