using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Represents an icon file associated with a component
    /// </summary>
    public class ComponentIcon
    {
        /// <summary>
        /// Full path to the icon file
        /// </summary>
        public string FilePath { get; set; }

        /// <summary>
        /// File name only (without path)
        /// </summary>
        public string FileName => Path.GetFileName(FilePath);

        /// <summary>
        /// File extension (e.g., ".png", ".ico")
        /// </summary>
        public string Extension => Path.GetExtension(FilePath);

        /// <summary>
        /// Size of the icon file in bytes
        /// </summary>
        public long FileSize { get; set; }

        /// <summary>
        /// Icon type based on naming convention
        /// </summary>
        public IconType Type { get; set; }

        /// <summary>
        /// Whether this is a dark theme variant of the icon
        /// </summary>
        public bool IsDark { get; set; }

        /// <summary>
        /// Size specification if present in filename (e.g., 16, 32, 64)
        /// </summary>
        public int? SizeSpecification { get; set; }

        /// <summary>
        /// Whether this icon exists and is accessible (cached to avoid repeated file checks)
        /// </summary>
        public bool IsValid { get; private set; }

        public ComponentIcon(string filePath)
        {
            FilePath = filePath;
            IsValid = File.Exists(filePath);
            if (IsValid)
            {
                var fileInfo = new FileInfo(filePath);
                FileSize = fileInfo.Length;
            }
            
            IsDark = DetectDarkIcon();
            Type = DetermineIconType();
            SizeSpecification = ExtractSizeFromFilename();
        }

        /// <summary>
        /// Regex pattern to detect dark icon variants in filenames.
        /// Matches patterns like: .dark., _dark., -dark., _dark_, -dark-, or ending with _dark, -dark, .dark
        /// Excludes filenames that start with "dark" to avoid false positives like "dark_icon.png"
        /// </summary>
        private static readonly Regex DarkIconPattern = new Regex(
            @"(?<!^dark)([._-]dark[._-]|[._-]dark$)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        /// <summary>
        /// Regex pattern to remove dark indicators from filenames for base type detection.
        /// </summary>
        private static readonly Regex DarkIndicatorRemovalPattern = new Regex(
            @"[._-]dark(?=[._-]|$)",
            RegexOptions.IgnoreCase | RegexOptions.Compiled);

        /// <summary>
        /// Detects if this icon is a dark theme variant based on filename patterns
        /// </summary>
        private bool DetectDarkIcon()
        {
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(FileName);
            return DarkIconPattern.IsMatch(fileNameWithoutExtension);
        }

        private IconType DetermineIconType()
        {
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(FileName).ToLowerInvariant();
            
            // Remove dark indicators for type detection to get base type
            var baseFileName = DarkIndicatorRemovalPattern.Replace(fileNameWithoutExtension, "");
            
            if (baseFileName.Contains("large"))
                return IsDark ? IconType.DarkLarge : IconType.Large;
            if (baseFileName.Contains("small"))
                return IsDark ? IconType.DarkSmall : IconType.Small;
            if (baseFileName.Contains("_16") || baseFileName.EndsWith("16.png") || baseFileName.EndsWith("16.ico"))
                return IsDark ? IconType.DarkSize16 : IconType.Size16;
            if (baseFileName.Contains("_32") || baseFileName.EndsWith("32.png") || baseFileName.EndsWith("32.ico"))
                return IsDark ? IconType.DarkSize32 : IconType.Size32;
            if (baseFileName.Contains("_64") || baseFileName.EndsWith("64.png") || baseFileName.EndsWith("64.ico"))
                return IsDark ? IconType.DarkSize64 : IconType.Size64;
            if (baseFileName.StartsWith("icon.") || baseFileName == "icon" + Extension.ToLowerInvariant())
                return IsDark ? IconType.DarkStandard : IconType.Standard;
            if (baseFileName.Contains("button"))
                return IsDark ? IconType.DarkButton : IconType.Button;
            if (baseFileName.Contains("cmd"))
                return IsDark ? IconType.DarkCommand : IconType.Command;
            
            return IsDark ? IconType.DarkOther : IconType.Standard;
        }

        private int? ExtractSizeFromFilename()
        {
            var fileName = FileName.ToLowerInvariant();
            
            // Look for size patterns like "_16", "_32", "_64", "16.png", etc.
            var sizePatterns = new[] { "16", "32", "64", "128", "256" };
            
            foreach (var size in sizePatterns)
            {
                if (fileName.Contains($"_{size}") || fileName.Contains($"{size}."))
                {
                    if (int.TryParse(size, out int sizeValue))
                        return sizeValue;
                }
            }
            
            return null;
        }

        public override string ToString()
        {
            var darkIndicator = IsDark ? " [Dark]" : "";
            return $"{FileName} ({Type}{darkIndicator}, {FileSize} bytes)";
        }
    }

    /// <summary>
    /// Types of icons based on naming conventions and usage
    /// </summary>
    public enum IconType
    {
        /// <summary>
        /// Standard icon (usually named "icon.*")
        /// </summary>
        Standard,
        
        /// <summary>
        /// Dark theme variant of standard icon
        /// </summary>
        DarkStandard,
        
        /// <summary>
        /// Small size variant
        /// </summary>
        Small,
        
        /// <summary>
        /// Dark theme variant of small icon
        /// </summary>
        DarkSmall,
        
        /// <summary>
        /// Large size variant
        /// </summary>
        Large,
        
        /// <summary>
        /// Dark theme variant of large icon
        /// </summary>
        DarkLarge,
        
        /// <summary>
        /// 16x16 pixel icon
        /// </summary>
        Size16,
        
        /// <summary>
        /// Dark theme variant of 16x16 pixel icon
        /// </summary>
        DarkSize16,
        
        /// <summary>
        /// 32x32 pixel icon
        /// </summary>
        Size32,
        
        /// <summary>
        /// Dark theme variant of 32x32 pixel icon
        /// </summary>
        DarkSize32,
        
        /// <summary>
        /// 64x64 pixel icon
        /// </summary>
        Size64,
        
        /// <summary>
        /// Dark theme variant of 64x64 pixel icon
        /// </summary>
        DarkSize64,
        
        /// <summary>
        /// Button-specific icon
        /// </summary>
        Button,
        
        /// <summary>
        /// Dark theme variant of button-specific icon
        /// </summary>
        DarkButton,
        
        /// <summary>
        /// Command-specific icon
        /// </summary>
        Command,
        
        /// <summary>
        /// Dark theme variant of command-specific icon
        /// </summary>
        DarkCommand,
        
        /// <summary>
        /// Other/unknown icon type
        /// </summary>
        Other,
        
        /// <summary>
        /// Dark theme variant of other/unknown icon type
        /// </summary>
        DarkOther
    }

    /// <summary>
    /// Collection of icons for a component with helper methods
    /// </summary>
    public class ComponentIconCollection : List<ComponentIcon>
    {
        /// <summary>
        /// Gets the primary icon (standard type first, then first available)
        /// </summary>
        public ComponentIcon PrimaryIcon => 
            this.FirstOrDefault(i => i.Type == IconType.Standard) ?? 
            this.FirstOrDefault();

        /// <summary>
        /// Gets the primary dark icon (dark standard type first, then first available dark icon)
        /// </summary>
        public ComponentIcon PrimaryDarkIcon =>
            this.FirstOrDefault(i => i.Type == IconType.DarkStandard) ??
            this.FirstOrDefault(i => i.IsDark);

        /// <summary>
        /// Gets icon by type
        /// </summary>
        public ComponentIcon GetByType(IconType type) => 
            this.FirstOrDefault(i => i.Type == type);

        /// <summary>
        /// Gets icon by size specification
        /// </summary>
        public ComponentIcon GetBySize(int size) => 
            this.FirstOrDefault(i => i.SizeSpecification == size);

        /// <summary>
        /// Gets icon by size specification and theme
        /// </summary>
        public ComponentIcon GetBySize(int size, bool isDark) =>
            this.FirstOrDefault(i => i.SizeSpecification == size && i.IsDark == isDark);

        /// <summary>
        /// Gets all icons of a specific file extension
        /// </summary>
        public IEnumerable<ComponentIcon> GetByExtension(string extension) => 
            this.Where(i => string.Equals(i.Extension, extension, StringComparison.OrdinalIgnoreCase));

        /// <summary>
        /// Gets all light theme icons
        /// </summary>
        public IEnumerable<ComponentIcon> LightIcons =>
            this.Where(i => !i.IsDark);

        /// <summary>
        /// Gets all dark theme icons
        /// </summary>
        public IEnumerable<ComponentIcon> DarkIcons =>
            this.Where(i => i.IsDark);

        /// <summary>
        /// Whether this collection has any valid icons
        /// </summary>
        public bool HasValidIcons => this.Any(i => i.IsValid);

        /// <summary>
        /// Whether this collection has any dark theme icons
        /// </summary>
        public bool HasDarkIcons => this.Any(i => i.IsDark);

        /// <summary>
        /// Whether this collection has any light theme icons
        /// </summary>
        public bool HasLightIcons => this.Any(i => !i.IsDark);

        /// <summary>
        /// Gets supported image file extensions
        /// </summary>
        public static readonly string[] SupportedExtensions = 
        {
            ".png", ".ico", ".jpg", ".jpeg", ".bmp", ".gif", ".svg"
        };

        /// <summary>
        /// Checks if a file extension is a supported image format
        /// </summary>
        public static bool IsSupportedImageExtension(string extension) =>
            Array.IndexOf(SupportedExtensions, extension?.ToLowerInvariant()) >= 0;
    }
}