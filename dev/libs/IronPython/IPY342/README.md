# IronPython 3.4.2 drop-in assemblies

`IronPython.dll` and `Microsoft.Dynamic.dll` built from upstream IronPython 3.4.2 and DLR
1.3.5 with the fixes for issue #3918 below. The pyRevit build copies them over the NuGet
`IronPython` 3.4.2 / `DynamicLanguageRuntime` 1.3.5 assemblies it deploys to
`bin/<netfx|netcore>/engines/IPY342` (see `dev/pyRevitLoader/Directory.Build.targets`).
Every other IronPython and DLR assembly still comes from NuGet.

They keep the upstream identity (`Version=3.4.2.0` / `1.3.5.0`,
`PublicKeyToken=7f709c5b713576e1`), signed with the `Build/Key.snk` the upstream
repositories ship, so they load wherever the NuGet assemblies do.

## Fixes

- **Rethrow outside the catch block.** Each Python frame used to rethrow an exception from
  inside a `catch`, which on .NET nests a new exception dispatch on the stack being
  unwound, about 12 KB per frame. An exception raised about 100 calls deep overflowed
  Revit's 1 MB main thread and crashed Revit. Both the DLR interpreter and IronPython's
  compiled frames now leave the catch block first and rethrow with `ExceptionDispatchInfo`.
- **Recursion check on light-throw targets.** After more than 20 exceptions passed through a
  function, IronPython swapped in a target without the recursion check, so the next deep
  recursion ignored the limit and overflowed the stack.

## Sources

| Assembly | Repository | Branch | Commit |
|---|---|---|---|
| `IronPython.dll` | `pyrevitlabs/ironpython3`, from upstream tag `v3.4.2` (`f5bb69b2`) | `v3.4.2-rethrow-fix` | `688fca70e6c62896f6611244202dc5a55bc90c22` |
| `Microsoft.Dynamic.dll` | `pyrevitlabs/dlr`, from upstream tag `v1.3.5` (`7e887d98`) | `v1.3.5-rethrow-fix` | `52a513e84329ae764ae25e676e9e1185c344e5f2` |

The same fixes are on `fix/rethrow-stack-depth` in the `dev/modules/pyRevitLabs.dlr` and
`dev/modules/pyRevitLabs.ironpython2` forks the IronPython 2.7.12 engine is built from. The
`pyRevitLabs.dlr3` and `pyRevitLabs.ironpython3` submodules are not part of the build and
stay unpatched.

## Rebuild

```powershell
git clone -b v3.4.2-rethrow-fix https://github.com/pyrevitlabs/ironpython3 ipy342
git clone -b v1.3.5-rethrow-fix https://github.com/pyrevitlabs/dlr ipy342/Src/DLR
cd ipy342/Src/IronPython
dotnet build IronPython.csproj -c Release -f net462
dotnet build IronPython.csproj -c Release -f net8.0
```

Copy `ipy342/bin/Release/<tfm>/IronPython.dll` and
`ipy342/Src/DLR/bin/Release/<tfm>/Microsoft.Dynamic.dll` into `net462/` and `net8.0/`.

## SHA-256

```text
d21c960decea81dd62cc290ac434fed0156517e34dffbf6e963c7ca9c6c3db83  net462/IronPython.dll
e1556ba17cc6c0899980c5eec1b6345bf21743e595b8ec687edd9c32da6b68bb  net462/Microsoft.Dynamic.dll
9af1cc8b57784fa128cbe30aa9e5c3635b6e8988b27270808be05a4137588e53  net8.0/IronPython.dll
2f21dddd6d185a069f352c94ff9acfe3c6789f0b99ec2d849d4fecbc0c98021a  net8.0/Microsoft.Dynamic.dll
```

Builds are not byte-for-byte reproducible, so a rebuild gives different hashes; update this
list with the files you commit.
