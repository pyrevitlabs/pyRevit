using System;
using System.Reflection;
using System.Reflection.Emit;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class TypeMakerService
    {
        public void DefineCommandType(IExtension extension, ICommandComponent command, ModuleBuilder moduleBuilder)
        {
            var typeBuilder = moduleBuilder.DefineType(
                name: command.UniqueId,
                attr: TypeAttributes.Public | TypeAttributes.Class
            );

            if (!string.IsNullOrEmpty(command.Tooltip))
            {
                var attrBuilder = new CustomAttributeBuilder(
                    typeof(System.ComponentModel.DescriptionAttribute).GetConstructor(new[] { typeof(string) }),
                    new object[] { command.Tooltip }
                );
                typeBuilder.SetCustomAttribute(attrBuilder);
            }

            // Emit a default constructor
            typeBuilder.DefineDefaultConstructor(MethodAttributes.Public);

            // Create the type (works in .NET Standard 2.0 via CreateTypeInfo)
            _ = typeBuilder.CreateTypeInfo();
        }
    }
}
