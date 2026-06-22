using System.Text.Encodings.Web;
using System.Text.Json;
using Build.Models;

namespace Build.Helpers;

public static class ProductDataHelper
{
    // pyrevit-products.json uses lowercase keys written by the legacy Python CLI.
    private static readonly JsonSerializerOptions ProductJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public static List<ProductRecord> LoadProducts(string path)
    {
        if (!File.Exists(path))
        {
            return [];
        }

        var json = File.ReadAllText(path);
        return JsonSerializer.Deserialize<List<ProductRecord>>(json, ProductJsonOptions) ?? [];
    }

    public static void SaveProducts(string path, IEnumerable<ProductRecord> products)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var json = JsonSerializer.Serialize(products, ProductJsonOptions);
        File.WriteAllText(path, json);
    }

    public static void SeedProductsFromTemplate(string templatePath, string dataPath)
    {
        if (!File.Exists(templatePath))
        {
            throw new FileNotFoundException("Missing product template.", templatePath);
        }

        if (File.Exists(dataPath))
        {
            return;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(dataPath)!);
        File.Copy(templatePath, dataPath, overwrite: false);
    }

    public static void InsertProduct(List<ProductRecord> products, ProductRecord product, bool cli, bool msi = false)
    {
        if (products.Any(x => x.Product == product.Product && x.Version == product.Version))
        {
            throw new InvalidOperationException($"{product.Product} product already exists with version {product.Version}");
        }

        if (cli)
        {
            var firstCliIndex = products.FindIndex(x => x.Product.Contains("CLI", StringComparison.Ordinal));
            var index = firstCliIndex >= 0 ? firstCliIndex : products.FindIndex(x => x.Product != "pyRevit");
            if (index < 0)
            {
                index = products.Count;
            }

            products.Insert(index, product);
            return;
        }

        products.Insert(0, product);
    }
}
