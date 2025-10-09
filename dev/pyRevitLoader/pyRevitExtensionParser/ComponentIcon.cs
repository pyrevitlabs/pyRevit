using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

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
        /// Size specification if present in filename (e.g., 16, 32, 64)
        /// </summary>
        public int? SizeSpecification { get; set; }

        /// <summary>
        /// Whether this icon exists and is accessible
        /// </summary>
        public bool IsValid => File.Exists(FilePath);

        public ComponentIcon(string filePath)
        {
            FilePath = filePath;
            if (File.Exists(filePath))
            {
                var fileInfo = new FileInfo(filePath);
                FileSize = fileInfo.Length;
            }
            
            Type = DetermineIconType();
            SizeSpecification = ExtractSizeFromFilename();
        }

        private IconType DetermineIconType()
        {
            var fileName = FileName.ToLowerInvariant();
            
            if (fileName.Contains("large"))
                return IconType.Large;
            if (fileName.Contains("small"))
                return IconType.Small;
            if (fileName.Contains("_16") || fileName.EndsWith("16.png") || fileName.EndsWith("16.ico"))
                return IconType.Size16;
            if (fileName.Contains("_32") || fileName.EndsWith("32.png") || fileName.EndsWith("32.ico"))
                return IconType.Size32;
            if (fileName.Contains("_64") || fileName.EndsWith("64.png") || fileName.EndsWith("64.ico"))
                return IconType.Size64;
            if (fileName.StartsWith("icon.") || fileName == "icon" + Extension)
                return IconType.Standard;
            if (fileName.Contains("button"))
                return IconType.Button;
            if (fileName.Contains("cmd"))
                return IconType.Command;
            
            return IconType.Standard;
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
            return $"{FileName} ({Type}, {FileSize} bytes)";
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
        /// Small size variant
        /// </summary>
        Small,
        
        /// <summary>
        /// Large size variant
        /// </summary>
        Large,
        
        /// <summary>
        /// 16x16 pixel icon
        /// </summary>
        Size16,
        
        /// <summary>
        /// 32x32 pixel icon
        /// </summary>
        Size32,
        
        /// <summary>
        /// 64x64 pixel icon
        /// </summary>
        Size64,
        
        /// <summary>
        /// Button-specific icon
        /// </summary>
        Button,
        
        /// <summary>
        /// Command-specific icon
        /// </summary>
        Command,
        
        /// <summary>
        /// Other/unknown icon type
        /// </summary>
        Other
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
        /// Gets all icons of a specific file extension
        /// </summary>
        public IEnumerable<ComponentIcon> GetByExtension(string extension) => 
            this.Where(i => string.Equals(i.Extension, extension, StringComparison.OrdinalIgnoreCase));

        /// <summary>
        /// Whether this collection has any valid icons
        /// </summary>
        public bool HasValidIcons => this.Any(i => i.IsValid);

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