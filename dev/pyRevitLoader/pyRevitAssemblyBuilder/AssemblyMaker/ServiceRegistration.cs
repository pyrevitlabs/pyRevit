using Microsoft.Extensions.DependencyInjection;
using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitAssemblyBuilder.Startup
{
    public static class ServiceRegistration
    {
        public static IServiceCollection AddAssemblyBuilder(this IServiceCollection services)
        {
            services.AddSingleton<ICommandTypeGenerator, DefaultCommandTypeGenerator>();
            services.AddSingleton<AssemblyBuilderService>();
            return services;
        }
    }
}
