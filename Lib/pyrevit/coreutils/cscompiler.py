import os.path as op

from pyrevit.core.exceptions import PyRevitException

# noinspection PyUnresolvedReferences
from System import Array

# noinspection PyUnresolvedReferences
from Microsoft.CSharp import CSharpCodeProvider
# noinspection PyUnresolvedReferences
from System.CodeDom import Compiler


def compile_to_asm(code, full_file_name, output_dir, reference_list=None):

    compiler_params = Compiler.CompilerParameters()
    compiler_params.OutputAssembly = op.join(output_dir, full_file_name)

    compiler_params.TreatWarningsAsErrors = False
    compiler_params.GenerateExecutable = False
    compiler_params.CompilerOptions = "/optimize"

    for reference in reference_list or []:
        compiler_params.ReferencedAssemblies.Add(reference)

    provider = CSharpCodeProvider()
    compiler = provider.CompileAssemblyFromSource(compiler_params, Array[str]([code]))

    if compiler.Errors.HasErrors:
        error_list = [str(err) for err in compiler.Errors.GetEnumerator()]
        raise PyRevitException("Compile error: {}".format(error_list))

    return compiler.PathToAssembly
