using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.PyRevit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitCLI {
    internal static class PyRevitCLICloneCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        PrintClones() {
            PyRevitCLIAppCmds.PrintHeader("Registered Clones (full git repos)");
            var clones = PyRevitClones.GetRegisteredClones().OrderBy(x => x.Name);
            foreach (var clone in clones.Where(c => c.IsRepoDeploy))
                Console.WriteLine(clone);

            PyRevitCLIAppCmds.PrintHeader("Registered Clones (deployed from archive/image)");
            foreach (var clone in clones.Where(c => !c.IsRepoDeploy))
                Console.WriteLine(clone);
        }

        internal static void
        PrintAttachments(int revitYear = 0) {
            PyRevitCLIAppCmds.PrintHeader("Attachments");
            foreach (var attachment in PyRevitAttachments.GetAttachments().OrderByDescending(x => x.Product.Version)) {
                if (revitYear == 0)
                    Console.WriteLine(attachment);
                else if (revitYear == attachment.Product.ProductYear)
                    Console.WriteLine(attachment);
            }
        }

        internal static void
        CreateClone(string cloneName, string deployName, string branchName, string repoUrl, string imagePath, string destPath) {
            // FIXME: implement image
            if (cloneName != null) {
                // if deployment requested or image path is provided
                if (imagePath != null || deployName != null)
                    PyRevitClones.DeployFromImage(
                        cloneName,
                        deploymentName: deployName,
                        branchName: branchName,
                        imagePath: imagePath,
                        destPath: destPath
                        );
                // otherwise clone the full repo
                else
                    PyRevitClones.DeployFromRepo(
                        cloneName,
                        deploymentName: deployName,
                        branchName: branchName,
                        repoUrl: repoUrl,
                        destPath: destPath
                        );
            }
        }

        internal static void
        PrintCloneInfo(string cloneName) {
            PyRevitCLIAppCmds.PrintHeader("Clone info");
            Console.WriteLine(PyRevitClones.GetRegisteredClone(cloneName));
        }

        internal static void
        OpenClone(string cloneName) {
            CommonUtils.OpenInExplorer(PyRevitClones.GetRegisteredClone(cloneName).ClonePath);
        }

        internal static void
        RegisterClone(string cloneName, string clonePath, bool force) {
            if (clonePath != null)
                PyRevitClones.RegisterClone(cloneName, clonePath, forceUpdate: force);
        }

        internal static void
        ForgetClone(bool allClones, string cloneName) {
            if (allClones)
                PyRevitClones.UnregisterAllClones();
            else
                PyRevitClones.UnregisterClone(
                    PyRevitClones.GetRegisteredClone(cloneName)
                    );
        }

        internal static void
        RenameClone(string cloneName, string cloneNewName) {
            if (cloneNewName != null) {
                PyRevitClones.RenameClone(cloneName, cloneNewName);
            }
        }

        internal static void
        DeleteClone(bool allClones, string cloneName, bool clearConfigs) {
            if (allClones)
                PyRevitClones.DeleteAllClones(clearConfigs: clearConfigs);
            else {
                if (cloneName != null)
                    PyRevitClones.Delete(PyRevitClones.GetRegisteredClone(cloneName), clearConfigs: clearConfigs);
            }
        }

        internal static void
        GetSetCloneBranch(string cloneName, string branchName) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                if (clone != null) {
                    if (clone.IsRepoDeploy) {
                        if (branchName != null) {
                            clone.SetBranch(branchName);
                        }
                        else {
                            Console.WriteLine(string.Format("Clone \"{0}\" is on branch \"{1}\"",
                                                             clone.Name, clone.Branch));
                        }
                    }
                    else
                        PyRevitCLIAppCmds.ReportCloneAsNoGit(clone);
                }
            }
        }

        internal static void
        GetSetCloneTag(string cloneName, string tagName) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                // get version for git clones
                if (clone.IsRepoDeploy) {
                    if (tagName != null) {
                        clone.SetTag(tagName);
                    }
                    else {
                        logger.Error("Version finder not yet implemented for git clones.");
                        // TODO: grab version from repo (last tag?)
                    }
                }
                // get version for other clones
                else {
                    if (tagName != null) {
                        logger.Error("Version setter not yet implemented for clones.");
                        // TODO: set version for archive clones?
                    }
                    else {
                        Console.WriteLine(clone.ModuleVersion);
                    }
                }
            }
        }

        internal static void
        GetSetCloneCommit(string cloneName, string commitHash) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                if (clone.IsRepoDeploy) {
                    if (commitHash != null) {
                        clone.SetCommit(commitHash);
                    }
                    else {
                        Console.WriteLine(string.Format("Clone \"{0}\" is on commit \"{1}\"",
                                                         clone.Name, clone.Commit));
                    }
                }
                else
                    PyRevitCLIAppCmds.ReportCloneAsNoGit(clone);
            }
        }

        internal static void
        GetSetCloneOrigin(string cloneName, string originUrl, bool reset) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                if (clone.IsRepoDeploy) {
                    if (originUrl != null || reset) {
                        string newUrl =
                            reset ? PyRevitConsts.OriginalRepoPath : originUrl;
                        clone.SetOrigin(newUrl);
                    }
                    else {
                        Console.WriteLine(string.Format("Clone \"{0}\" origin is at \"{1}\"",
                                                        clone.Name, clone.Origin));
                    }
                }
                else
                    PyRevitCLIAppCmds.ReportCloneAsNoGit(clone);
            }
        }

        internal static void
        PrintCloneDeployments(string cloneName) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                PyRevitCLIAppCmds.PrintHeader(string.Format("Deployments for \"{0}\"", clone.Name));
                foreach (var dep in clone.GetConfiguredDeployments()) {
                    Console.WriteLine(string.Format("\"{0}\" deploys:", dep.Name));
                    foreach (var path in dep.Paths)
                        Console.WriteLine("    " + path);
                    Console.WriteLine();
                }
            }
        }

        internal static void
        PrintCloneEngines(string cloneName) {
            if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                PyRevitCLIAppCmds.PrintHeader(string.Format("Deployments for \"{0}\"", clone.Name));
                foreach (var engine in clone.GetConfiguredEngines()) {
                    Console.WriteLine(engine);
                }
            }
        }

        internal static void
        UpdateClone(bool allClones, string cloneName) {
            // TODO: ask for closing running Revits

            // prepare a list of clones to be updated
            var targetClones = new List<PyRevitClone>();
            // separate the clone that this process might be running from
            // this is used to update this clone from outside since the dlls will be locked
            PyRevitClone myClone = null;

            // all clones
            if (allClones) {
                foreach (var clone in PyRevitClones.GetRegisteredClones())
                    if (PyRevitCLIAppCmds.IsRunningInsideClone(clone))
                        myClone = clone;
                    else
                        targetClones.Add(clone);
            }
            // or single clone
            else {
                if (cloneName != null) {
                    var clone = PyRevitClones.GetRegisteredClone(cloneName);
                    if (PyRevitCLIAppCmds.IsRunningInsideClone(clone))
                        myClone = clone;
                    else
                        targetClones.Add(clone);
                }
            }

            // update clones that do not include this process
            foreach (var clone in targetClones) {
                logger.Debug("Updating clone \"{0}\"", clone.Name);
                PyRevitClones.Update(clone);
            }

            // now update myClone if any, as last step
            if (myClone != null)
                throw new PyRevitException("Can not update clone that contains this command line utility. "
                                           + "Use installer to update.");

        }

        internal static void
        AttachClone(string cloneName,
                    bool latest, bool dynamoSafe, string engineVersion,
                    string revitYear, bool installed, bool attached,
                    bool allUsers) {
            var clone = PyRevitClones.GetRegisteredClone(cloneName);

            // grab engine version
            int engineVer = 0;
            int.TryParse(engineVersion, out engineVer);

            if (latest) {
                logger.Debug("Attaching on latest engine...");
                var latestCloneEngine = 
                    clone.GetEngines().Where(x => x.Runtime).OrderByDescending(x => x.Version).First();
                logger.Debug(string.Format("Latest engine: {0}", latestCloneEngine));
                if (latestCloneEngine != null)
                    engineVer = latestCloneEngine.Version;
                else
                    throw new PyRevitException("Can not determine latest runtime engine for this clone.");
            }
            else if (dynamoSafe) {
                logger.Debug("Attaching on dynamo-safe engine");
                engineVer = PyRevitConsts.ConfigsDynamoCompatibleEnginerVer;
            }

            // decide targets revits to attach to
            int revitYearNumber = 0;
            if (installed)
                foreach (var revit in RevitProduct.ListInstalledProducts())
                    PyRevitAttachments.Attach(revit.ProductYear, clone, engineVer: engineVer, allUsers: allUsers);
            else if (attached)
                foreach (var attachment in PyRevitAttachments.GetAttachments())
                    PyRevitAttachments.Attach(attachment.Product.ProductYear, clone, engineVer: engineVer, allUsers: allUsers);
            else if (int.TryParse(revitYear, out revitYearNumber))
                PyRevitAttachments.Attach(revitYearNumber, clone, engineVer: engineVer, allUsers: allUsers);
        }

        internal static void
        DetachClone(string revitYear, bool all) {
            if (revitYear != null) {
                int revitYearNumber = 0;
                if (int.TryParse(revitYear, out revitYearNumber))
                    PyRevitAttachments.Detach(revitYearNumber);
                else
                    throw new PyRevitException(string.Format("Invalid Revit year \"{0}\"", revitYear));
            }
            else if (all)
                PyRevitAttachments.DetachAll();
        }

        internal static void
        ListAttachments(string revitYear) {
            if (revitYear != null) {
                int revitYearNumber = 0;
                if (int.TryParse(revitYear, out revitYearNumber))
                    PrintAttachments(revitYear: revitYearNumber);
                else
                    throw new PyRevitException(string.Format("Invalid Revit year \"{0}\"", revitYear));
            }
            else
                PrintAttachments();
        }

        internal static void
        SwitchAttachment(string cloneName, string revitYear) {
            var clone = PyRevitClones.GetRegisteredClone(cloneName);
            if (revitYear != null) {
                int revitYearNumber = 0;
                if (int.TryParse(revitYear, out revitYearNumber)) {
                    var attachment = PyRevitAttachments.GetAttached(revitYearNumber);
                    if (attachment != null) {
                        if (attachment.Engine != null) {
                            PyRevitAttachments.Attach(attachment.Product.ProductYear,
                                           clone,
                                           engineVer: attachment.Engine.Version,
                                           allUsers: attachment.AllUsers);
                        }
                        else
                            throw new PyRevitException(
                                string.Format("Can not determine attachment engine for Revit \"{0}\"",
                                              revitYear)
                                );
                    }
                    else
                        throw new PyRevitException(
                            string.Format("Can not determine existing attachment for Revit \"{0}\"",
                                          revitYear)
                            );
                }
                else
                    throw new PyRevitException(string.Format("Invalid Revit year \"{0}\"", revitYear));
            }
            else {
                // read current attachments and reattach using the same config with the new clone
                foreach (var attachment in PyRevitAttachments.GetAttachments()) {
                    if (attachment.Engine != null) {
                        PyRevitAttachments.Attach(
                            attachment.Product.ProductYear,
                            clone,
                            engineVer: attachment.Engine.Version,
                            allUsers: attachment.AllUsers);
                    }
                    else
                        throw new PyRevitException("Can not determine attachment engine.");
                }
            }
        }

        internal static void
        BuildImage(string cloneName, string configFile, string imageFilePath) {
            if (configFile is null || configFile == string.Empty)
                throw new PyRevitException("Config file must be specified.");
            else {
                var paths = File.ReadAllLines(configFile);

                var destPath = Path.GetDirectoryName(imageFilePath);
                if (!CommonUtils.VerifyPath(destPath))
                    throw new PyRevitException(
                        string.Format("Destination path does not exist: \"{0}\"", destPath)
                        );

                PyRevitClones.CreateImageFromClone(PyRevitClones.GetRegisteredClone(cloneName), paths, imageFilePath);
            }
        }
    }
}
