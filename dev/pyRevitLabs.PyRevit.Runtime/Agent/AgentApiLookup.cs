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
                ["obsolete"] = ObsoleteMessage(type),
            };

            if (type.IsEnum && memberName == null) {
                description["values"] = new JArray(Enum.GetNames(type).Take(MaxEnumValues));
                return description;
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
                description["member"] = memberName;
                if (members.Count == 0)
                    description["member_found"] = false;
            }
            else {
                description["members_note"] = "Declared members only; see base_type for inherited ones.";
            }

            description["members_truncated"] = members.Count > MaxMembers;
            description["members"] = new JArray(members.Take(MaxMembers));
            return description;
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
