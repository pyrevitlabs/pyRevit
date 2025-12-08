using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Represents an icon file associated with a component.
    /// Only two icon patterns are supported: "icon.png" (light) and "icon.dark.png" (dark).
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
        /// Whether this is a dark theme variant of the icon (icon.dark.png)
        /// </summary>
        public bool IsDark { get; set; }

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
            Type = IsDark ? IconType.DarkStandard : IconType.Standard;
        }

        /// <summary>
        /// Detects if this icon is a dark theme variant.
        /// Only "icon.dark.png" pattern is supported (case-insensitive).
        /// </summary>
        private bool DetectDarkIcon()
        {
            var fileNameWithoutExtension = Path.GetFileNameWithoutExtension(FileName);
            return string.Equals(fileNameWithoutExtension, "icon.dark", StringComparison.OrdinalIgnoreCase);
        }

        public override string ToString()
        {
            var darkIndicator = IsDark ? " [Dark]" : "";
            return $"{FileName} ({Type}{darkIndicator}, {FileSize} bytes)";
        }
    }

    /// <summary>
    /// Types of icons. Only Standard (icon.png) and DarkStandard (icon.dark.png) are supported.
    /// </summary>
    public enum IconType
    {
        /// <summary>
        /// Standard icon (icon.png)
        /// </summary>
        Standard,
        
        /// <summary>
        /// Dark theme variant (icon.dark.png)
        /// </summary>
        DarkStandard
    }

    /// <summary>
    /// Collection of icons for a component with helper methods.
    /// Only supports icon.png (light) and icon.dark.png (dark).
    /// </summary>
    public class ComponentIconCollection : List<ComponentIcon>
    {
        /// <summary>
        /// Gets the primary icon (standard light icon)
        /// </summary>
        public ComponentIcon PrimaryIcon => 
            this.FirstOrDefault(i => i.Type == IconType.Standard) ?? 
            this.FirstOrDefault(i => !i.IsDark);

        /// <summary>
        /// Gets the primary dark icon (icon.dark.png)
        /// </summary>
        public ComponentIcon PrimaryDarkIcon =>
            this.FirstOrDefault(i => i.Type == IconType.DarkStandard);

        /// <summary>
        /// Gets icon by type
        /// </summary>
        public ComponentIcon GetByType(IconType type) => 
            this.FirstOrDefault(i => i.Type == type);

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