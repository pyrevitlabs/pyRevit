using System;
using System.Collections.Generic;
using System.Diagnostics;
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
    pyrevit-doctor <doctor_command> [--dryrun] [--force] [--keep-config]

    Arguments & Options:
        <doctor_command>         Doctor command to run
        --dryrun                 Report what would be removed without changing anything
        --force                  Also purge uninstall entries whose install is still present
                                 (purge-installs, purge-all)
        --keep-config            Keep pyRevit_config.ini instead of backing it up to Documents
                                 and deleting it (purge-files, purge-all)

";

        static DoctorCommand[] Commands = new DoctorCommand[] {
            new DoctorCommand {
                Name = "purge-installs",
                HelpMsg = "Clean up records of old installations from registry",
                Command = PurgeInstalls.Run
            },
            new DoctorCommand {
                Name = "purge-files",
                HelpMsg = "Delete install and data folders, Revit add-in manifests and PATH entries",
                Command = session => PurgeFiles.Run(session, MachineLocations.FromEnvironment())
            },
            new DoctorCommand {
                Name = "purge-all",
                HelpMsg = "Run purge-files and purge-installs and remove MCP registrations",
                Command = session => PurgeAll.Run(session, MachineLocations.FromEnvironment())
            }
        };

        public static Version DoctorVersion => Assembly.GetExecutingAssembly().GetName().Version;

        static void Main(string[] args) {
            var options = new PurgeOptions {
                DryRun = args.Contains("--dryrun"),
                Force = args.Contains("--force"),
                KeepConfig = args.Contains("--keep-config"),
            };

            if (args.Contains("--version") || args.Contains("-V"))
                Console.WriteLine(DoctorVersion);
            else if (args.Contains("--help") || args.Contains("-h"))
                Console.WriteLine(helpMessage);
            else if (args.Contains("--wrappedhelp"))
                Console.WriteLine(WrappedHelp.From(helpMessage));
            else if (args.Contains("--list"))
                PrintCommands();

            else if (args.Length > 0) {
                var commandName = args.FirstOrDefault(arg => !arg.StartsWith("-"));
                var requested = Commands.FirstOrDefault(x => x.Name == commandName);
                if (requested.Name != null)
                    RunCommand(requested, options);
                else {
                    Console.Error.WriteLine(commandName == null
                        ? "No doctor command given."
                        : $"Unknown doctor command \"{commandName}\".");
                    PrintCommands();
                    Environment.ExitCode = 1;
                }
            }
            else {
                if (AskForCommand() is DoctorCommand command) {
                    RunCommand(command, options);
                    Console.WriteLine("Press any key to close");
                    Console.ReadLine();
                }
            }
        }

        static void RunCommand(DoctorCommand command, PurgeOptions options) {
            if (IsRevitRunning()) {
                if (!options.DryRun) {
                    Console.Error.WriteLine("Revit.exe is running. Close Revit and run the command again.");
                    Environment.ExitCode = 1;
                    return;
                }
                Console.WriteLine("Warning: Revit.exe is running. Without --dryrun this command would abort.");
            }

            var session = new PurgeSession(options, Console.Out);
            command.Command(session);
            session.PrintSummary();
            if (session.FailedCount > 0)
                Environment.ExitCode = 1;
        }

        static bool IsRevitRunning() => Process.GetProcessesByName("Revit").Length > 0;

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
        public Action<PurgeSession> Command;
    }
}
