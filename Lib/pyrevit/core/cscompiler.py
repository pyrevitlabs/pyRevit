import os.path as op

from Microsoft.CSharp import CSharpCodeProvider
from System import Array
from System.CodeDom import Compiler
from pyrevit.config.config import ASSEMBLY_FILE_TYPE
from pyrevit.core.exceptions import PyRevitException


def compile_to_asm(code, name, output_dir, references=None):

    compiler_params = Compiler.CompilerParameters()
    compiler_params.OutputAssembly = op.join(output_dir, name + ASSEMBLY_FILE_TYPE)

    compiler_params.TreatWarningsAsErrors = False
    compiler_params.GenerateExecutable = False
    compiler_params.CompilerOptions = "/optimize"

    for reference in references or []:
        compiler_params.ReferencedAssemblies.Add(reference)

    provider = CSharpCodeProvider()
    compiler = provider.CompileAssemblyFromSource(compiler_params, Array[str]([code]))

    if compiler.Errors.HasErrors:
        error_list = [str(err) for err in compiler.Errors.GetEnumerator()]
        raise PyRevitException("Compile error: {}".format(error_list))

    return compiler.PathToAssembly
