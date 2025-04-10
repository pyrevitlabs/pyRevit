using System.Reflection.Emit;
using System.Reflection;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class DefaultCommandTypeGenerator : ICommandTypeGenerator
    {
        public void DefineCommandType(IExtension extension, ICommandComponent command, ModuleBuilder moduleBuilder)
        {
            var typeBuilder = moduleBuilder.DefineType(
                name: command.UniqueId,
                attr: TypeAttributes.Public | TypeAttributes.Class
            );

            var attrBuilder = new CustomAttributeBuilder(
                typeof(System.ComponentModel.DescriptionAttribute).GetConstructor(new[] { typeof(string) }),
                new object[] { command.Tooltip }
            );
            typeBuilder.SetCustomAttribute(attrBuilder);

            typeBuilder.CreateType();
        }
    }
}