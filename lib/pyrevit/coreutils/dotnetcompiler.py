from pyrevit import PyRevitException
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from System import Array
# noinspection PyUnresolvedReferences
from System.Collections.Generic import Dictionary
# noinspection PyUnresolvedReferences
from Microsoft.CSharp import CSharpCodeProvider
# noinspection PyUnresolvedReferences
from System.CodeDom import Compiler


logger = get_logger(__name__)


def compile_csharp(sourcecode_list, full_output_file_addr=None, reference_list=None, resource_list=None):
    logger.debug('Compiling source sourcecode_list to: {}'.format(full_output_file_addr))
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

    logger.debug('Getting sourcecode_list provider.')
    provider = CSharpCodeProvider(Dictionary[str, str]({'CompilerVersion': 'v4.0'}))
    logger.debug('Compiling source sourcecode_list.')
    compiler = provider.CompileAssemblyFromSource(compiler_params, Array[str](sourcecode_list))

    if compiler.Errors.HasErrors:
        error_list = [str(err) for err in compiler.Errors.GetEnumerator()]
        raise PyRevitException("Compile error: {}".format(error_list))

    if full_output_file_addr is None:
        logger.debug('Compile to memory successful: {}'.format(compiler.CompiledAssembly))
        return compiler.CompiledAssembly
    else:
        logger.debug('Compile successful: {}'.format(compiler.PathToAssembly))
        return compiler.PathToAssembly
