using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Drops the call-site rules IronPython contexts cache, so a reload can release the engines of
    /// earlier sessions.
    /// </summary>
    /// <remarks>
    /// A binder belongs to one context but caches rules for objects of whichever engine it was used
    /// on, and each rule references that engine's types and functions. IronPython runs some
    /// operations on objects of every engine through its default context (ctypes reads a library's
    /// <c>_handle</c> there, for example), and an engine that Revit keeps alive, such as one that
    /// registered a dockable pane, keeps binding objects of later engines. Those rules keep every
    /// earlier engine alive with all the modules it imported.
    /// </remarks>
    internal static class IronPythonRuleCaches {
        private const int MaxBinderContainerDepth = 2;

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private static readonly FieldInfo BinderRuleCacheField =
            typeof(CallSiteBinder).GetField("Cache", BindingFlags.Instance | BindingFlags.NonPublic);

        private static readonly List<WeakReference> startedContexts = new List<WeakReference>();

        /// <summary>
        /// Remembers the context of an engine this runtime started, without keeping it alive.
        /// </summary>
        internal static void Track(Microsoft.Scripting.Hosting.ScriptEngine engine) {
            var context = Microsoft.Scripting.Hosting.Providers.HostingHelpers.GetLanguageContext(engine);
            lock (startedContexts) {
                startedContexts.RemoveAll(reference => !reference.IsAlive);
                startedContexts.Add(new WeakReference(context));
            }
        }

        /// <summary>
        /// Drops the rule caches of every binder of the default context and of the tracked contexts
        /// that are still alive.
        /// </summary>
        /// <remarks>
        /// Dropping the rules only costs rebuilding them on next use. Each binder gets an empty cache
        /// rather than none, because the DLR reads the field twice without a lock and a binder in use
        /// on another thread must never see it turn null. Best effort: the binders are found by
        /// reflection, and a failure is logged and leaves the remaining caches in place.
        /// </remarks>
        /// <returns>Number of binders whose rule cache was dropped.</returns>
        internal static int Release() {
            if (BinderRuleCacheField == null
                || !BinderRuleCacheField.FieldType.IsAssignableFrom(typeof(Dictionary<Type, object>))) {
                logger.Warn("CallSiteBinder has no usable rule cache field; script engines of earlier sessions stay alive.");
                return 0;
            }

            int released = 0;
            List<object> contexts = LiveContexts();
            foreach (object context in contexts)
                released += ReleaseContextRules(context);

            logger.Debug("Released the rule caches of {0} binders in {1} IronPython contexts", released, contexts.Count);
            return released;
        }

        private static List<object> LiveContexts() {
            var contexts = new List<object>();
            object defaultContext = IronPython.Runtime.DefaultContext.Default?.LanguageContext;
            if (defaultContext != null)
                contexts.Add(defaultContext);

            lock (startedContexts) {
                startedContexts.RemoveAll(reference => !reference.IsAlive);
                foreach (WeakReference reference in startedContexts) {
                    object context = reference.Target;
                    if (context != null && !contexts.Contains(context))
                        contexts.Add(context);
                }
            }
            return contexts;
        }

        private static int ReleaseContextRules(object context) {
            const BindingFlags fieldFlags =
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
            int released = 0;
            for (Type type = context.GetType(); type != null; type = type.BaseType) {
                foreach (FieldInfo field in type.GetFields(fieldFlags)) {
                    try {
                        released += ReleaseBinderRules(field.GetValue(context), 0);
                    }
                    catch (Exception ex) {
                        logger.Debug(ex, "Could not release the rules held by {0}.{1}", type.Name, field.Name);
                    }
                }
            }
            return released;
        }

        private static int ReleaseBinderRules(object value, int depth) {
            if (value is CallSiteBinder binder) {
                BinderRuleCacheField.SetValue(binder, new Dictionary<Type, object>());
                return 1;
            }

            if (depth > MaxBinderContainerDepth)
                return 0;

            var items = new List<object>();
            if (value is IDictionary dictionary) {
                lock (dictionary)
                    foreach (object item in dictionary.Values)
                        items.Add(item);
            }
            else if (value is Array array && !array.GetType().GetElementType().IsValueType) {
                foreach (object item in array)
                    items.Add(item);
            }

            int released = 0;
            foreach (object item in items)
                released += ReleaseBinderRules(item, depth + 1);
            return released;
        }
    }
}
