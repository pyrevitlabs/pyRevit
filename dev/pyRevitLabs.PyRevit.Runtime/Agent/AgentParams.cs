using System;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Typed reads of request parameters that fail as <c>invalid_params</c> naming the parameter
    /// and the expected type, instead of a .NET conversion message.
    /// </summary>
    /// <remarks>
    /// The JSON type must match: a string is never read as a number or a Boolean, and an integer
    /// parameter takes only a whole number (<c>1280.0</c> but not <c>1280.5</c>). A missing or null
    /// parameter reads as the type's default.
    /// </remarks>
    internal static class AgentParams {
        public static T Get<T>(JObject parameters, string name) {
            var token = parameters[name];
            if (token == null || token.Type == JTokenType.Null)
                return default;
            var type = Nullable.GetUnderlyingType(typeof(T)) ?? typeof(T);
            if (!HasJsonType(token, type))
                throw new AgentException("invalid_params", $"'{name}' must be {Expected(type)}.");
            try {
                return parameters.Value<T>(name);
            }
            catch (OverflowException) {
                throw new AgentException("invalid_params", $"'{name}' is out of range.");
            }
        }

        private static bool HasJsonType(JToken token, Type type) {
            if (type == typeof(string))
                return token.Type == JTokenType.String || token.Type == JTokenType.Date;
            if (type == typeof(bool))
                return token.Type == JTokenType.Boolean;
            if (type == typeof(int) || type == typeof(long))
                return token.Type == JTokenType.Integer || token.Type == JTokenType.Float && IsWhole(token.Value<double>());
            return token.Type == JTokenType.Integer || token.Type == JTokenType.Float;
        }

        private static bool IsWhole(double number) {
            return !double.IsInfinity(number) && Math.Floor(number) == number;
        }

        private static string Expected(Type type) {
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
