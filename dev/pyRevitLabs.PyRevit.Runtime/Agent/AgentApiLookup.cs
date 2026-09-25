using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Answers <c>lookup_api</c> by reflecting over the RevitAPI and RevitAPIUI assemblies
    /// loaded in this Revit, so agents check signatures against the exact version they are
    /// scripting instead of guessing.
    /// </summary>
    /// <remarks>
    /// Pure reflection, no Revit API calls, so it is safe on the pipe thread and never waits
    /// for Revit to be idle.
    /// </remarks>
    internal static class AgentApiLookup {
        private const int MaxMembers = 400;
        private const int MaxMatches = 40;
        private const int MaxEnumValues = 600;
        private const int MaxSuggestions = 10;

        private static readonly Lazy<Type[]> PublicTypes = new Lazy<Type[]>(LoadPublicTypes);

        /// <param name="query">
        /// A type (<c>Wall</c>, <c>Autodesk.Revit.DB.Wall</c>) or a member
        /// (<c>Wall.Create</c>, <c>ElementId.Value</c>).
        /// </param>
        public static JToken Lookup(string query) {
            if (string.IsNullOrWhiteSpace(query))
                throw new AgentException("invalid_params", "'name' is required.");
            query = query.Trim();

            var types = FindTypes(query);
            string memberName = null;
            if (types.Count == 0) {
                var lastDot = query.LastIndexOf('.');
                if (lastDot > 0) {
                    types = FindTypes(query.Substring(0, lastDot));
                    memberName = query.Substring(lastDot + 1);
                }
            }

            if (types.Count == 0) {
                var needle = query.Split('.').Last();
                return new JObject {
                    ["found"] = false,
                    ["query"] = query,
                    ["suggestions"] = new JArray(
                        PublicTypes.Value
                            .Where(t => t.Name.IndexOf(needle, StringComparison.OrdinalIgnoreCase) >= 0)
                            .Select(t => t.FullName)
                            .OrderBy(name => name.Length)
                            .Take(MaxMatches)),
                };
            }

            if (types.Count > 1) {
                return new JObject {
                    ["found"] = true,
                    ["ambiguous"] = true,
                    ["matches"] = new JArray(types.Select(t => t.FullName).Take(MaxMatches)),
                };
            }

            return DescribeType(types[0], memberName);
        }

        private static List<Type> FindTypes(string name) {
            var exact = PublicTypes.Value.Where(t => t.FullName == name).ToList();
            if (exact.Count > 0)
                return exact;
            return PublicTypes.Value
                .Where(t => string.Equals(t.Name, name, StringComparison.OrdinalIgnoreCase)
                            || string.Equals(t.FullName, name, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }

        private static JObject DescribeType(Type type, string memberName) {
            var description = new JObject {
                ["found"] = true,
                ["full_name"] = type.FullName,
                ["kind"] = KindOf(type),
                ["base_type"] = type.BaseType != null && type.BaseType != typeof(object)
                    ? type.BaseType.FullName
                    : null,
                ["assembly"] = type.Assembly.GetName().Name,
                ["namespace"] = type.Namespace,
                ["python_import"] = type.IsNested ? null : $"from {type.Namespace} import {type.Name}",
                ["obsolete"] = ObsoleteMessage(type),
            };

            if (!type.IsEnum && !type.IsInterface) {
                var creation = CreationMethods(type);
                description["creation"] = creation.Count > 0
                    ? new JArray(creation)
                    : (JToken)"No factory found on the type or on doc.Create; look for constructors below or for methods on related types.";
            }

            if (type.IsEnum && memberName == null) {
                description["values"] = new JArray(Enum.GetNames(type).Take(MaxEnumValues));
                return description;
            }

            if (type.IsEnum) {
                var value = Enum.GetNames(type).FirstOrDefault(name => string.Equals(name, memberName, StringComparison.OrdinalIgnoreCase));
                if (value != null) {
                    description["member"] = value;
                    description["members"] = new JArray(FormatType(type) + "." + value);
                    return description;
                }
                return MemberNotFound(description, type, memberName, Enum.GetNames(type));
            }

            var flags = BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static;
            if (memberName == null)
                flags |= BindingFlags.DeclaredOnly;

            var members = type.GetMembers(flags)
                .Where(member => memberName == null
                                 || string.Equals(member.Name, memberName, StringComparison.OrdinalIgnoreCase))
                .Where(IsListed)
                .Select(DescribeMember)
                .Where(signature => signature != null)
                .Distinct()
                .ToList();

            if (memberName != null) {
                if (members.Count == 0)
                    return MemberNotFound(description, type, memberName,
                        type.GetMembers(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static)
                            .Where(IsListed)
                            .Select(member => member.Name)
                            .Distinct());
                description["member"] = memberName;
            }
            else {
                description["members_note"] = "Declared members only; see base_type for inherited ones.";
            }

            description["members_truncated"] = members.Count > MaxMembers;
            description["members"] = new JArray(members.Take(MaxMembers));
            return description;
        }

        /// <summary>
        /// A lookup whose type exists but whose member doesn't. <c>found</c> is false so the
        /// answer can't be mistaken for a hit, and the closest names are suggested; for enums
        /// the other Revit enums are searched too, because agents often guess the wrong enum
        /// (<c>BuiltInCategory.X</c> for a <c>BuiltInParameter</c>).
        /// </summary>
        private static JObject MemberNotFound(JObject description, Type type, string memberName, IEnumerable<string> candidates) {
            var tokens = NameTokens(memberName);
            var sameType = RankByTokens(candidates, tokens)
                .Select(name => FormatType(type) + "." + name)
                .Take(MaxSuggestions)
                .ToList();

            var result = new JObject {
                ["found"] = false,
                ["type_found"] = true,
                ["full_name"] = type.FullName,
                ["member"] = memberName,
                ["message"] = $"{FormatType(type)} has no member named '{memberName}'.",
                ["suggestions"] = new JArray(sameType),
            };

            if (type.IsEnum) {
                var otherEnums = PublicTypes.Value
                    .Where(other => other.IsEnum && other != type && other.Namespace != null && other.Namespace.StartsWith("Autodesk.Revit"))
                    .SelectMany(other => Enum.GetNames(other).Select(name => new { Type = other, Name = name }))
                    .Select(entry => new { entry.Type, entry.Name, Score = TokenScore(entry.Name, tokens) })
                    .Where(entry => entry.Score > 0)
                    .OrderByDescending(entry => entry.Score)
                    .ThenBy(entry => entry.Name.Length)
                    .Take(MaxSuggestions)
                    .Select(entry => FormatType(entry.Type) + "." + entry.Name)
                    .ToList();
                if (otherEnums.Count > 0)
                    result["in_other_enums"] = new JArray(otherEnums);
            }
            return result;
        }

        private static IEnumerable<string> RankByTokens(IEnumerable<string> candidates, List<string> tokens) {
            return candidates
                .Select(name => new { Name = name, Score = TokenScore(name, tokens) })
                .Where(entry => entry.Score > 0)
                .OrderByDescending(entry => entry.Score)
                .ThenBy(entry => entry.Name.Length)
                .Select(entry => entry.Name);
        }

        private static int TokenScore(string name, List<string> tokens) {
            var nameTokens = NameTokens(name);
            return tokens.Count(token => nameTokens.Contains(token)) * 10
                + tokens.Count(token => name.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0);
        }

        private static List<string> NameTokens(string name) {
            var spaced = System.Text.RegularExpressions.Regex.Replace(name ?? string.Empty, "([a-z0-9])([A-Z])", "$1_$2");
            return spaced.Split(new[] { '_', '.' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(token => token.ToLowerInvariant())
                .Where(token => token.Length > 1 && token != "param" && token != "get" && token != "set")
                .Distinct()
                .ToList();
        }

        private static bool IsListed(MemberInfo member) {
            if (member is MethodInfo method)
                return !method.IsSpecialName;
            return member is ConstructorInfo || member is PropertyInfo || member is FieldInfo || member is EventInfo;
        }

        private static string DescribeMember(MemberInfo member) {
            var obsolete = ObsoleteMessage(member);
            var prefix = obsolete != null ? "[Obsolete: " + obsolete + "] " : string.Empty;

            switch (member) {
                case ConstructorInfo constructor:
                    return prefix + "new " + FormatType(constructor.DeclaringType) + "(" + FormatParameters(constructor) + ")";
                case MethodInfo method:
                    return prefix + (method.IsStatic ? "static " : string.Empty)
                        + FormatType(method.ReturnType) + " " + method.Name + "(" + FormatParameters(method) + ")";
                case PropertyInfo property:
                    var accessors = (property.CanRead && property.GetGetMethod() != null ? "get; " : string.Empty)
                        + (property.CanWrite && property.GetSetMethod() != null ? "set; " : string.Empty);
                    var isStatic = (property.GetGetMethod() ?? property.GetSetMethod())?.IsStatic == true;
                    var indexParameters = property.GetIndexParameters();
                    if (indexParameters.Length > 0 && property.Name != "Item") {
                        var index = string.Join(", ", indexParameters.Select(FormatParameter));
                        var calls = new List<string>();
                        if (property.GetGetMethod() != null)
                            calls.Add($"get_{property.Name}({index})");
                        if (property.GetSetMethod() != null)
                            calls.Add($"set_{property.Name}({index}, {FormatType(property.PropertyType)} value)");
                        return prefix + FormatType(property.PropertyType) + " " + property.Name + "[" + index + "] { " + accessors
                            + "} (indexed property; from Python call " + string.Join(" / ", calls) + ")";
                    }
                    var name = indexParameters.Length > 0
                        ? "this[" + string.Join(", ", indexParameters.Select(FormatParameter)) + "]"
                        : property.Name;
                    return prefix + (isStatic ? "static " : string.Empty)
                        + FormatType(property.PropertyType) + " " + name + " { " + accessors + "}";
                case FieldInfo field:
                    return prefix + (field.IsStatic ? "static " : string.Empty) + FormatType(field.FieldType) + " " + field.Name;
                case EventInfo eventInfo:
                    return prefix + "event " + FormatType(eventInfo.EventHandlerType) + " " + eventInfo.Name;
                default:
                    return null;
            }
        }

        /// <summary>
        /// Ways to create <paramref name="type"/>: its own static factories (Wall.Create,
        /// Point.Create) and the <c>doc.Create</c> / <c>doc.FamilyCreate</c> / <c>app.Create</c>
        /// methods that return it (NewFootPrintRoof, NewRoom), which agents otherwise miss.
        /// </summary>
        private static List<string> CreationMethods(Type type) {
            var found = new List<string>();
            var flags = BindingFlags.Public | BindingFlags.Static;
            foreach (var method in type.GetMethods(flags)) {
                if (!method.IsSpecialName && type.IsAssignableFrom(method.ReturnType))
                    found.Add(type.Name + "." + method.Name + "(" + FormatParameters(method) + ")");
            }

            foreach (var factory in PublicTypes.Value.Where(t => t.Namespace == "Autodesk.Revit.Creation")) {
                var receiver = CreationReceiver(factory);
                if (receiver == null)
                    continue;
                foreach (var method in factory.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)) {
                    if (!method.IsSpecialName && method.ReturnType != typeof(object) && type.IsAssignableFrom(method.ReturnType))
                        found.Add(receiver + "." + method.Name + "(" + FormatParameters(method) + ")");
                }
            }

            if (found.Any(signature => signature.Contains("out ")))
                found.Add("Note: Revit rejects a null out argument on many of these; from Python pass a pre-filled clr.Reference[T](T()) and read .Value (see the revit-scripting skill), or use the kit helper.");
            return found.Distinct().Take(40).ToList();
        }

        private static string CreationReceiver(Type factory) {
            switch (factory.Name) {
                case "Document":
                case "ItemFactoryBase":
                    return "doc.Create";
                case "FamilyItemFactory":
                    return "doc.FamilyCreate";
                case "Application":
                    return "app.Create";
                default:
                    return null;
            }
        }

        private static string FormatParameters(MethodBase method) {
            return string.Join(", ", method.GetParameters().Select(FormatParameter));
        }

        private static string FormatParameter(ParameterInfo parameter) {
            var type = parameter.ParameterType;
            var modifier = string.Empty;
            if (type.IsByRef) {
                modifier = parameter.IsOut ? "out " : "ref ";
                type = type.GetElementType();
            }
            return modifier + FormatType(type) + " " + parameter.Name;
        }

        private static string FormatType(Type type) {
            if (type == null)
                return "void";
            if (type == typeof(void))
                return "void";
            if (type.IsArray)
                return FormatType(type.GetElementType()) + "[]";
            if (type.IsGenericType) {
                var name = type.Name;
                var tick = name.IndexOf('`');
                if (tick > 0)
                    name = name.Substring(0, tick);
                return name + "<" + string.Join(", ", type.GetGenericArguments().Select(FormatType)) + ">";
            }
            return type.Name;
        }

        private static string KindOf(Type type) {
            if (type.IsEnum) return "enum";
            if (type.IsInterface) return "interface";
            if (type.IsValueType) return "struct";
            if (typeof(Delegate).IsAssignableFrom(type)) return "delegate";
            return type.IsAbstract ? (type.IsSealed ? "static class" : "abstract class") : "class";
        }

        private static string ObsoleteMessage(MemberInfo member) {
            var attribute = member.GetCustomAttributes(typeof(ObsoleteAttribute), false)
                .OfType<ObsoleteAttribute>()
                .FirstOrDefault();
            if (attribute == null)
                return null;
            return string.IsNullOrEmpty(attribute.Message) ? "obsolete" : attribute.Message;
        }

        private static Type[] LoadPublicTypes() {
            var assemblies = new[] { typeof(Document).Assembly, typeof(UIApplication).Assembly };
            return assemblies.SelectMany(SafeGetTypes).Where(t => t != null && (t.IsPublic || t.IsNestedPublic)).ToArray();
        }

        private static IEnumerable<Type> SafeGetTypes(Assembly assembly) {
            try {
                return assembly.GetTypes();
            }
            catch (ReflectionTypeLoadException ex) {
                return ex.Types.Where(t => t != null);
            }
        }
    }
}
