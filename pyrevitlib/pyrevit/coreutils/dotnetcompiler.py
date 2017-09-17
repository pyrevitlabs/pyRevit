from pyrevit import PyRevitException
from pyrevit.platform import Array, Dictionary
from pyrevit.platform import Compiler, CSharpCodeProvider
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


def _compile_dotnet(code_provider,
                    sourcefiles_list,
                    full_output_file_addr=None,
                    reference_list=None,
                    resource_list=None,
                    ):

    logger.debug('Compiling source files to: {}'.format(full_output_file_addr))
    logger.debug('References assemblies are: {}'.format(reference_list))

    compiler_params = Compiler.CompilerParameters()

    if full_output_file_addr is None:
        compiler_params.GenerateInMemory = True
    else:
        compiler_params.GenerateInMemory = False
        compiler_params.OutputAssembly = full_output_file_addr

    compiler_params.TreatWarningsAsErrors = False
    compiler_params.GenerateExecutable = False
    compiler_params.CompilerOptions = "/optimize"

    for reference in reference_list or []:
        logger.debug('Adding reference to compiler: {}'.format(reference))
        compiler_params.ReferencedAssemblies.Add(reference)

    for resource in resource_list or []:
        logger.debug('Adding resource to compiler: {}'.format(resource))
        compiler_params.EmbeddedResources.Add(resource)

    logger.debug('Compiling source files.')
    compiler = \
        code_provider.CompileAssemblyFromFile(compiler_params,
                                              Array[str](sourcefiles_list))

    if compiler.Errors.HasErrors:
        err_list = [unicode(err) for err in compiler.Errors.GetEnumerator()]
        err_str = '\n'.join(err_list)
        raise PyRevitException("Compile error: {}".format(err_str))

    if full_output_file_addr is None:
        logger.debug('Compile to memory successful: {}'
                     .format(compiler.CompiledAssembly))
        return compiler.CompiledAssembly
    else:
        logger.debug('Compile successful: {}'.format(compiler.PathToAssembly))
        return compiler.PathToAssembly


def compile_csharp(sourcefiles_list,
                   full_output_file_addr=None,
                   reference_list=None, resource_list=None):

    logger.debug('Getting csharp provider.')

    cleanedup_source_list = \
        [src.replace('\\', '\\\\') for src in sourcefiles_list]

    provider = \
        CSharpCodeProvider(Dictionary[str, str]({'CompilerVersion': 'v4.0'}))
    return _compile_dotnet(provider,
                           cleanedup_source_list,
                           full_output_file_addr,
                           reference_list, resource_list)
