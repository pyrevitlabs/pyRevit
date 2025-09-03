using System.Drawing;

using Console = Colorful.Console;


namespace pyRevitCLI
{
    internal static class PyRevitCLIColorfulConsole
    {
        private static readonly Color CommandColor = Color.Yellow;
        private static readonly Color HeaderColor = Color.Cyan;
        private static readonly Color AccentColor = Color.FromArgb(126, 226, 110);

        internal static void WriteLine(string text)
        {
            Console.WriteLine(text);
        }

        internal static void WriteHeader(string text)
        {
            Console.WriteLine(text, HeaderColor);
        }

        internal static void WriteCommand(string command, string description, int indent)
        {
            string outputFormat = "        {0,-" + indent.ToString() + "}";
            Console.Write(string.Format(outputFormat, command), CommandColor);
            Console.WriteLine(description);
        }

        internal static void WriteUsage(string line)
        {
            var lineParts = line.Split(new char[] { ' ' }, 2);
            Console.Write(lineParts[0] + " ", AccentColor);
            Console.WriteLine(lineParts[1]);
        }
    }
}
