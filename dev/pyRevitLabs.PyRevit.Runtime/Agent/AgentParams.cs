using System;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Typed reads of request parameters that fail as <c>invalid_params</c> naming the parameter
    /// and the expected type, instead of a .NET conversion message.
    /// </summary>
    internal static class AgentParams {
        public static T Get<T>(JObject parameters, string name) {
            try {
                return parameters.Value<T>(name);
            }
            catch (OverflowException) {
                throw new AgentException("invalid_params", $"'{name}' is out of range.");
            }
            catch (Exception ex) when (ex is FormatException || ex is InvalidCastException) {
                throw new AgentException("invalid_params", $"'{name}' must be {Expected(typeof(T))}.");
            }
        }

        private static string Expected(Type type) {
            type = Nullable.GetUnderlyingType(type) ?? type;
            if (type == typeof(string))
                return "a string";
            if (type == typeof(bool))
                return "true or false";
            if (type == typeof(int) || type == typeof(long))
                return "an integer";
            return "a number";
        }
    }
}
