using System;
using System.Collections.Generic;
using System.IO;

namespace pyRevitExtensionParserTest.TestHelpers
{
    /// <summary>
    /// Helper class for creating pyRevit extension structures for testing.
    /// Reduces boilerplate when creating temporary extensions with tabs, panels, and buttons.
    /// </summary>
    public class TestExtensionBuilder
    {
        private readonly string _basePath;
        private readonly string _extensionName;
        private readonly string _extensionPath;

        /// <summary>
        /// Gets the full path to the extension directory.
        /// </summary>
        public string ExtensionPath => _extensionPath;

        /// <summary>
        /// Creates a new TestExtensionBuilder that will create an extension in the specified base path.
        /// </summary>
        /// <param name="basePath">The base directory where the extension will be created.</param>
        /// <param name="extensionName">The name of the extension (without .extension suffix).</param>
        public TestExtensionBuilder(string basePath, string extensionName)
        {
            _basePath = basePath;
            _extensionName = extensionName;
            _extensionPath = Path.Combine(basePath, $"{extensionName}.extension");
        }

        /// <summary>
        /// Creates the extension directory structure.
        /// </summary>
        public TestExtensionBuilder Create()
        {
            Directory.CreateDirectory(_extensionPath);
            return this;
        }

        /// <summary>
        /// Adds a tab to the extension.
        /// </summary>
        /// <param name="tabName">The name of the tab (without .tab suffix).</param>
        /// <returns>A TabBuilder for further configuration.</returns>
        public TabBuilder AddTab(string tabName)
        {
            var tabPath = Path.Combine(_extensionPath, $"{tabName}.tab");
            Directory.CreateDirectory(tabPath);
            return new TabBuilder(tabPath);
        }

        /// <summary>
        /// Creates a minimal extension with a single tab, panel, and push button.
        /// </summary>
        public static string CreateMinimalExtension(
            string basePath, 
            string extensionName,
            string tabName = "TestTab",
            string panelName = "TestPanel",
            string buttonName = "TestButton",
            string scriptContent = "pass")
        {
            var builder = new TestExtensionBuilder(basePath, extensionName);
            builder.Create()
                .AddTab(tabName)
                .AddPanel(panelName)
                .AddPushButton(buttonName, scriptContent);
            
            return builder.ExtensionPath;
        }

        /// <summary>
        /// Creates a push button in the specified directory.
        /// </summary>
        public static string CreatePushButton(
            string parentDir, 
            string buttonName, 
            string scriptContent = "pass",
            string? bundleYaml = null)
        {
            var buttonDir = Path.Combine(parentDir, $"{buttonName}.pushbutton");
            Directory.CreateDirectory(buttonDir);
            File.WriteAllText(Path.Combine(buttonDir, "script.py"), scriptContent);
            
            if (!string.IsNullOrEmpty(bundleYaml))
            {
                File.WriteAllText(Path.Combine(buttonDir, "bundle.yaml"), bundleYaml);
            }
            
            return buttonDir;
        }

        /// <summary>
        /// Creates a pulldown menu in the specified directory.
        /// </summary>
        public static string CreatePulldown(
            string parentDir,
            string pulldownName,
            string? bundleYaml = null)
        {
            var pulldownDir = Path.Combine(parentDir, $"{pulldownName}.pulldown");
            Directory.CreateDirectory(pulldownDir);
            
            if (!string.IsNullOrEmpty(bundleYaml))
            {
                File.WriteAllText(Path.Combine(pulldownDir, "bundle.yaml"), bundleYaml);
            }
            
            return pulldownDir;
        }

        /// <summary>
        /// Writes a bundle.yaml file to the specified directory.
        /// </summary>
        public static void WriteBundleYaml(string dir, string yamlContent)
        {
            File.WriteAllText(Path.Combine(dir, "bundle.yaml"), yamlContent);
        }

        /// <summary>
        /// Creates a simple test icon (PNG format) at the specified path.
        /// </summary>
        public static void CreateTestIcon(string filePath, int width = 16, int height = 16)
        {
            // Create a minimal valid PNG file
            // PNG header + minimal IHDR + empty IDAT + IEND
            var pngData = CreateMinimalPng(width, height);
            File.WriteAllBytes(filePath, pngData);
        }

        /// <summary>
        /// Creates a minimal valid PNG file in memory.
        /// </summary>
        private static byte[] CreateMinimalPng(int width, int height)
        {
            using (var ms = new MemoryStream())
            {
                // PNG signature
                ms.Write(new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A }, 0, 8);

                // IHDR chunk
                var ihdr = new byte[13];
                WriteInt32BE(ihdr, 0, width);
                WriteInt32BE(ihdr, 4, height);
                ihdr[8] = 8;  // bit depth
                ihdr[9] = 2;  // color type (RGB)
                ihdr[10] = 0; // compression
                ihdr[11] = 0; // filter
                ihdr[12] = 0; // interlace
                WriteChunk(ms, "IHDR", ihdr);

                // Minimal IDAT chunk (compressed empty scanlines)
                var idat = new byte[] { 0x08, 0xD7, 0x63, 0x60, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01 };
                WriteChunk(ms, "IDAT", idat);

                // IEND chunk
                WriteChunk(ms, "IEND", new byte[0]);

                return ms.ToArray();
            }
        }

        private static void WriteInt32BE(byte[] buffer, int offset, int value)
        {
            buffer[offset] = (byte)(value >> 24);
            buffer[offset + 1] = (byte)(value >> 16);
            buffer[offset + 2] = (byte)(value >> 8);
            buffer[offset + 3] = (byte)value;
        }

        private static void WriteChunk(MemoryStream ms, string type, byte[] data)
        {
            // Write length
            var lengthBytes = new byte[4];
            WriteInt32BE(lengthBytes, 0, data.Length);
            ms.Write(lengthBytes, 0, 4);

            // Write type
            var typeBytes = System.Text.Encoding.ASCII.GetBytes(type);
            ms.Write(typeBytes, 0, 4);

            // Write data
            ms.Write(data, 0, data.Length);

            // Calculate and write CRC
            var crcData = new byte[4 + data.Length];
            Array.Copy(typeBytes, 0, crcData, 0, 4);
            Array.Copy(data, 0, crcData, 4, data.Length);
            var crc = CalculateCrc32(crcData);
            var crcBytes = new byte[4];
            WriteInt32BE(crcBytes, 0, (int)crc);
            ms.Write(crcBytes, 0, 4);
        }

        private static uint CalculateCrc32(byte[] data)
        {
            uint crc = 0xFFFFFFFF;
            foreach (var b in data)
            {
                crc ^= b;
                for (int i = 0; i < 8; i++)
                {
                    crc = (crc & 1) != 0 ? (crc >> 1) ^ 0xEDB88320 : crc >> 1;
                }
            }
            return ~crc;
        }
    }

    /// <summary>
    /// Builder for configuring a tab within an extension.
    /// </summary>
    public class TabBuilder
    {
        private readonly string _tabPath;

        internal TabBuilder(string tabPath)
        {
            _tabPath = tabPath;
        }

        /// <summary>
        /// Gets the full path to the tab directory.
        /// </summary>
        public string TabPath => _tabPath;

        /// <summary>
        /// Adds a panel to the tab.
        /// </summary>
        public PanelBuilder AddPanel(string panelName)
        {
            var panelPath = Path.Combine(_tabPath, $"{panelName}.panel");
            Directory.CreateDirectory(panelPath);
            return new PanelBuilder(panelPath, this);
        }
    }

    /// <summary>
    /// Builder for configuring a panel within a tab.
    /// </summary>
    public class PanelBuilder
    {
        private readonly string _panelPath;
        private readonly TabBuilder _parent;

        internal PanelBuilder(string panelPath, TabBuilder parent)
        {
            _panelPath = panelPath;
            _parent = parent;
        }

        /// <summary>
        /// Gets the full path to the panel directory.
        /// </summary>
        public string PanelPath => _panelPath;

        /// <summary>
        /// Gets the parent tab builder.
        /// </summary>
        public TabBuilder Parent => _parent;

        /// <summary>
        /// Adds a push button to the panel.
        /// </summary>
        public PanelBuilder AddPushButton(string buttonName, string scriptContent = "pass", string? bundleYaml = null)
        {
            TestExtensionBuilder.CreatePushButton(_panelPath, buttonName, scriptContent, bundleYaml);
            return this;
        }

        /// <summary>
        /// Adds a pulldown menu to the panel.
        /// </summary>
        public PulldownBuilder AddPulldown(string pulldownName, string? bundleYaml = null)
        {
            var pulldownPath = TestExtensionBuilder.CreatePulldown(_panelPath, pulldownName, bundleYaml);
            return new PulldownBuilder(pulldownPath, this);
        }

        /// <summary>
        /// Sets the bundle.yaml content for this panel.
        /// </summary>
        public PanelBuilder WithBundleYaml(string yamlContent)
        {
            TestExtensionBuilder.WriteBundleYaml(_panelPath, yamlContent);
            return this;
        }
    }

    /// <summary>
    /// Builder for configuring a pulldown menu within a panel.
    /// </summary>
    public class PulldownBuilder
    {
        private readonly string _pulldownPath;
        private readonly PanelBuilder _parent;

        internal PulldownBuilder(string pulldownPath, PanelBuilder parent)
        {
            _pulldownPath = pulldownPath;
            _parent = parent;
        }

        /// <summary>
        /// Gets the full path to the pulldown directory.
        /// </summary>
        public string PulldownPath => _pulldownPath;

        /// <summary>
        /// Gets the parent panel builder.
        /// </summary>
        public PanelBuilder Parent => _parent;

        /// <summary>
        /// Adds a push button to the pulldown.
        /// </summary>
        public PulldownBuilder AddPushButton(string buttonName, string scriptContent = "pass", string? bundleYaml = null)
        {
            TestExtensionBuilder.CreatePushButton(_pulldownPath, buttonName, scriptContent, bundleYaml);
            return this;
        }

        /// <summary>
        /// Sets the bundle.yaml content for this pulldown.
        /// </summary>
        public PulldownBuilder WithBundleYaml(string yamlContent)
        {
            TestExtensionBuilder.WriteBundleYaml(_pulldownPath, yamlContent);
            return this;
        }
    }

    /// <summary>
    /// Provides pre-built test extension structures for common test scenarios.
    /// These methods create comprehensive extension structures that can be shared across tests.
    /// </summary>
    public static class TestExtensionFactory
    {
        /// <summary>
        /// Creates a comprehensive test extension with multiple localized buttons, pulldowns, 
        /// tooltips, icons, and other features that were previously in TestPanelOne/Two/Three.
        /// </summary>
        public static string CreateComprehensiveTestExtension(string basePath)
        {
            var builder = new TestExtensionBuilder(basePath, "TestExtension");
            builder.Create();

            var tabBuilder = builder.AddTab("TestTab");

            // === Panel One: Localization Tests ===
            var panelOne = tabBuilder.AddPanel("LocalizationPanel");
            
            // Button with full localization (replaces PanelOneButton1)
            panelOne.AddPushButton("LocalizedButton", "print('localized')", @"title:
  fr_fr: TEST TITLE 1 FR
  en_us: TEST TITLE 1 EN
  de_de: TEST TITLE 1 DE
tooltip: 
  fr_fr: >-
    TEST TOOLTIP FR
  en_us: >-
    TEST TOOLTIP EN
  de_de: >-
    TEST TOOLTIP DE
author: Roman Golev");

            // Button without bundle (replaces PanelOneButton2)
            panelOne.AddPushButton("SimpleButton", "print('simple')");

            // Panel button (replaces Debug Dialog Config.panelbutton in TestPanelOne)
            CreatePanelButton(panelOne.PanelPath, "LocalizationConfig", "print('config')", @"title: Localization Config
tooltip: Configure localization settings
author: Test Author");

            // === Panel Two: Pulldown and Tooltip Tests ===
            var panelTwo = tabBuilder.AddPanel("PulldownPanel");

            // Pulldown with layout, children, and localized content (replaces TestPulldown)
            var pulldown = panelTwo.AddPulldown("TestPulldown", @"layout:
  - SubButton2
  - SubButton1
tooltip:
  en_us: This is a test tooltip for the pulldown button
title:
  en_us: Test Pulldown
author: Test Author");
            
            // Add child buttons to pulldown
            pulldown.AddPushButton("SubButton1", "print('sub1')", @"title:
  en_us: Sub Button One
tooltip:
  en_us: This is the first sub-button in the pulldown.
author: Test Author");

            pulldown.AddPushButton("SubButton2", "print('sub2')", @"title:
  en_us: Sub Button Two
tooltip:
  en_us: This is the second sub-button in the pulldown.
author: Test Author");

            // About button with multiple locales (replaces TestAbout)
            panelTwo.AddPushButton("TestAbout", "print('about')", @"title:
  en_us: About pyRevit
  ru: О pyRevit

tooltip:
  ru: >-
    О pyRevit. Открывает сайт блога pyRevit.
  en_us: >-
    About pyRevit. Opens the pyRevit blog website. You can find detailed information on how pyRevit works, updates about the new tools and changes, and a lot of other information there.
  fr_fr: >-
    À propos de pyRevit. Ouvre le site web du blog pyRevit.
  es_es: >-
    Sobre pyRevit. Abre el blog online de pyRevit.

author: test_doc");

            // Create icon files for TestAbout
            var aboutButtonPath = Path.Combine(panelTwo.PanelPath, "TestAbout.pushbutton");
            TestExtensionBuilder.CreateTestIcon(Path.Combine(aboutButtonPath, "icon.png"), 32, 32);
            TestExtensionBuilder.CreateTestIcon(Path.Combine(aboutButtonPath, "icon.dark.png"), 32, 32);

            // Tooltip test button with multiline (replaces TestTooltip)
            var tooltipButtonPath = panelTwo.AddPushButton("TestTooltip", "print('tooltip')", @"title:
  en_us: Test Tooltip Button
  ru: Тестовая Кнопка Подсказки
tooltip:
  en_us: >-
    This is a test tooltip in English. It should show only this English text
    and not include any other language versions or raw YAML content.
  ru: >-
    Это тестовая подсказка на русском языке.
author: Test Author");

            // Create icons for TestTooltip
            var tooltipBtnPath = Path.Combine(panelTwo.PanelPath, "TestTooltip.pushbutton");
            TestExtensionBuilder.CreateTestIcon(Path.Combine(tooltipBtnPath, "icon.png"), 32, 32);
            TestExtensionBuilder.CreateTestIcon(Path.Combine(tooltipBtnPath, "icon.dark.png"), 32, 32);

            // Selection context button (replaces SelectionTest from ParserTests.panel)
            // Note: Using "Selection Test" with space to match folder name convention "Selection Test.pushbutton"
            panelTwo.AddPushButton("Selection Test", "print('selection')", @"title: Selection Test
tooltip: Test command that requires element selection
author: Test User
context: selection");

            // === Panel Three: Stack Tests ===
            var panelThree = tabBuilder.AddPanel("StackPanel");
            var stackPath = Path.Combine(panelThree.PanelPath, "test_stack.stack");
            Directory.CreateDirectory(stackPath);
            
            TestExtensionBuilder.CreatePushButton(stackPath, "StackButton1", "print('stack1')");
            TestExtensionBuilder.CreatePushButton(stackPath, "StackButton2", "print('stack2')");

            return builder.ExtensionPath;
        }

        /// <summary>
        /// Creates a panel button component.
        /// </summary>
        public static string CreatePanelButton(string parentDir, string buttonName, string scriptContent = "pass", string? bundleYaml = null)
        {
            var buttonDir = Path.Combine(parentDir, $"{buttonName}.panelbutton");
            Directory.CreateDirectory(buttonDir);
            File.WriteAllText(Path.Combine(buttonDir, "script.py"), scriptContent);
            
            if (!string.IsNullOrEmpty(bundleYaml))
            {
                File.WriteAllText(Path.Combine(buttonDir, "bundle.yaml"), bundleYaml);
            }
            
            return buttonDir;
        }

        /// <summary>
        /// Creates a test extension specifically for icon-related tests.
        /// Uses existing icons from Debug.panel in pyRevitDevTools.
        /// </summary>
        public static string CreateIconTestExtension(string basePath)
        {
            var builder = new TestExtensionBuilder(basePath, "IconTestExtension");
            builder.Create();

            var tabBuilder = builder.AddTab("IconTab");
            var panel = tabBuilder.AddPanel("IconPanel");

            // Button with both light and dark icons
            var btn1Path = panel.AddPushButton("ButtonWithIcons", "print('icons')").PanelPath;
            var button1Dir = Path.Combine(btn1Path, "ButtonWithIcons.pushbutton");
            TestExtensionBuilder.CreateTestIcon(Path.Combine(button1Dir, "icon.png"), 32, 32);
            TestExtensionBuilder.CreateTestIcon(Path.Combine(button1Dir, "icon.dark.png"), 32, 32);

            // Button with only light icon
            panel.AddPushButton("ButtonLightOnly", "print('light only')");
            var button2Dir = Path.Combine(panel.PanelPath, "ButtonLightOnly.pushbutton");
            TestExtensionBuilder.CreateTestIcon(Path.Combine(button2Dir, "icon.png"), 32, 32);

            // Button with no icons
            panel.AddPushButton("ButtonNoIcons", "print('no icons')");

            // Button with icon_ prefix variants
            panel.AddPushButton("ButtonIconVariants", "print('variants')");
            var button4Dir = Path.Combine(panel.PanelPath, "ButtonIconVariants.pushbutton");
            TestExtensionBuilder.CreateTestIcon(Path.Combine(button4Dir, "icon_small.png"), 16, 16);
            TestExtensionBuilder.CreateTestIcon(Path.Combine(button4Dir, "icon_large.png"), 32, 32);

            return builder.ExtensionPath;
        }

        /// <summary>
        /// Creates a test extension for separator and slideout tests.
        /// </summary>
        public static string CreateSeparatorTestExtension(string basePath)
        {
            var builder = new TestExtensionBuilder(basePath, "SeparatorTestExtension");
            builder.Create();

            var tabBuilder = builder.AddTab("SeparatorTab");
            
            // Panel with separator in layout
            var panelWithSeparator = tabBuilder.AddPanel("PanelWithSeparator");
            panelWithSeparator.WithBundleYaml(@"layout:
  - Button1
  - '-----'
  - Button2");
            panelWithSeparator.AddPushButton("Button1", "print('btn1')");
            panelWithSeparator.AddPushButton("Button2", "print('btn2')");

            // Panel with slideout marker
            var panelWithSlideout = tabBuilder.AddPanel("PanelWithSlideout");
            panelWithSlideout.WithBundleYaml(@"layout:
  - MainButton
  - '>>>>>'
  - SlideoutButton");
            panelWithSlideout.AddPushButton("MainButton", "print('main')");
            panelWithSlideout.AddPushButton("SlideoutButton", "print('slideout')");

            // Panel with multiple separators
            var panelMultipleSeparators = tabBuilder.AddPanel("MultipleSeparatorsPanel");
            panelMultipleSeparators.WithBundleYaml(@"layout:
  - First
  - '-----'
  - Second  
  - '-----'
  - Third
  - '-----'
  - Fourth");
            panelMultipleSeparators.AddPushButton("First", "print('1')");
            panelMultipleSeparators.AddPushButton("Second", "print('2')");
            panelMultipleSeparators.AddPushButton("Third", "print('3')");
            panelMultipleSeparators.AddPushButton("Fourth", "print('4')");

            return builder.ExtensionPath;
        }
    }
}
