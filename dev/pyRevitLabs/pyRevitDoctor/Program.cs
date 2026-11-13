using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

using pyRevitDoctor.Properties;

namespace pyRevitDoctor {
    class Program {
        const string helpMessage = @"Fix potential or real problems

Usage:
    pyrevit-doctor (-V | --version)
    pyrevit-doctor (-h | --help)
    pyrevit-doctor [--list]
    pyrevit-doctor <doctor_command> [--dryrun]

    Arguments & Options:
        <doctor_command>         Doctor command to run

";

        static DoctorCommand[] Commands = new DoctorCommand[] {
            new DoctorCommand {
                Name = "purge-installs",
                HelpMsg = "Clean up records of old installations from registry",
                Command = PurgeInstalls.PurgeOldInstalls
            }
        };

        public static Version DoctorVersion => Assembly.GetExecutingAssembly().GetName().Version;

        static void Main(string[] args) {
            bool dryrun = args.Contains("--dryrun");

            if (args.Contains("--version") || args.Contains("-V"))
                Console.WriteLine(DoctorVersion);
            else if (args.Contains("--help") || args.Contains("-h"))
                Console.WriteLine(helpMessage);
            else if (args.Contains("--wrappedhelp"))
                Console.WriteLine(helpMessage.Replace("pyrevit-doctor (-V | --version)\n", "").Replace("pyrevit-doctor", "pyrevit doctor"));
            else if (args.Contains("--list"))
                PrintCommands();

            else if (args.Length > 0) {
                var commandName = DoctorArguments.FindCommandName(args);
                var command = Commands.FirstOrDefault(x => x.Name == commandName);
                if (command.Command != null)
                    command.Command(dryrun);
                else {
                    Console.Error.WriteLine($"Unknown command \"{commandName ?? args[0]}\". Run \"pyrevit-doctor --list\" to see the available commands.");
                    Environment.ExitCode = 1;
                }
            }
            else {
                if (AskForCommand() is DoctorCommand command) {
                    command.Command(dryrun);
                    Console.WriteLine("Press any key to close");
                    Console.ReadLine();
                }
            }
        }

        static DoctorCommand? AskForCommand() {
            Console.WriteLine("Select a commands to run:");
            uint commandId = 1;
            foreach (var command in Commands)
                Console.WriteLine($"    {commandId++}) {command.Name,-25} {command.HelpMsg}");
            Console.Write("\nEnter Command Id: ");

            if (int.TryParse(Console.ReadLine(), out int cmdId)) {
                if (cmdId > 0 && cmdId <= Commands.Length)
                    return Commands[cmdId - 1];
            }
            return null;
        }

        static void PrintCommands() {
            Console.WriteLine("Available Commands:");
            foreach (var command in Commands)
                Console.WriteLine($"    {command.Name,-25} {command.HelpMsg}");
        }

        public static List<Product> LoadProducts() => ProductCatalog.Parse(Resources.ProductInfo);
    }

    struct DoctorCommand {
        public string Name;
        public string HelpMsg;
        public Action<bool> Command;
    }
}
