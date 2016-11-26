import clr

from System import Array
from System.Environment import CurrentDirectory
from System.IO import Path, Directory

from System.CodeDom import Compiler
from Microsoft.CSharp import CSharpCodeProvider


def Generate(code, name, references=None, outputDirectory=None, inMemory=False):
    CompilerParams = Compiler.CompilerParameters()

    if outputDirectory is None:
        outputDirectory = Directory.GetCurrentDirectory()

    if not inMemory:
        CompilerParams.OutputAssembly = Path.Combine(outputDirectory, name + ".dll")
        CompilerParams.GenerateInMemory = False
    else:
        CompilerParams.GenerateInMemory = True

    CompilerParams.TreatWarningsAsErrors = False
    CompilerParams.GenerateExecutable = False
    CompilerParams.CompilerOptions = "/optimize"

    for reference in references or []:
        CompilerParams.ReferencedAssemblies.Add(reference)

    provider = CSharpCodeProvider()
    compile = provider.CompileAssemblyFromSource(CompilerParams, Array[str]([code]))

    if compile.Errors.HasErrors:
        error_list = [str(err) for err in compile.Errors.GetEnumerator()]
        raise Exception("Compile error: {}".format(error_list))

    if inMemory:
        return compile.CompiledAssembly

    return compile.PathToAssembly
