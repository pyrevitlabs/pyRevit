#! python3
# TODO: cleanup docstrings
# TODO: implement docopt
"""Prefix IL dll namespace

This utility script, uses the IL disassembler (ildasm) and Assembler (ilasm)
on windows (also available with mono but yet not tested) to disassemble the
given .net dll files, modifies the assembly name and namespaces defined in the
IL assembly file (.il), and finally reassembles the IL into a new dll.

Usage:
    {cliname} (-h | --help)
    {cliname} (-V | --version)
    {cliname} <prefix> [--name-only] <dll-file>...

Options:
    -h, --help          Show this help
    <prefix>            Prefix to be applied to assembly name and namespaces
    <dll-file>          Target IL assemblies
    --name-only         Apply prefix to assembly name only (not namespaces)
    --dotnet-ver=       Use this dotnet version sdk (default =4.7)
    --ildasm-path=      ildasm.exe path
    --ilasm-path=       ilasm.exe path

    Debug Options
    --dasm              Only perform disassembly
    --nfix              Only perform assembly name change (expects .il file)
    --nsfix             Only perform namespace changes (expects .il file)
    --remove-pk         Only perform removing public key (expects .il file)
    --ilfix             Only perform IL fixes (expects .il file)
    --resfix            Only perform res file changes (expects .res file)
    --asm               Only perform assembly (expects .il and .res files)
    --debug             Print debug messages
    --verbose           Print reports from ildasm and ilasm

Examples:
    >>> ilpfxns "pyRevitLabs" ./MadMilkman.Ini.dll
    ... ./pyRevitLabs.MadMilkman.Ini.dll

"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
#pylint: disable=global-statement
import sys
import errno
import subprocess
import os
import os.path as op
import codecs
import re

# pipenv dependencies
# from docopt import docopt


__binname__ = op.splitext(op.basename(__file__))[0] # grab script name
__version__ = '1.0'


class CMDArgs:
    """Data type to hold command line args"""
    def __init__(self, args):
        self.prefix = args['<prefix>']
        self.ilbins = args['<dll-file>']
        self.dasm = args['--dasm']
        self.nsfix = args['--nsfix']
        self.ilfix = args['--ilfix']
        self.resfix = args['--resfix']
        self.asm = args['--asm']
        self.rempk = args['--remove-pk']
        self.dotnetver = args['--dotnet-ver']
        self.ildasm_path = args['--ildasm-path']
        self.ilasm_path = args['--ilasm-path']
        self.debug = args['--debug']
        self.verbose = args['--verbose']


# this tool tries to find the ildasm.exe and ilasm.exe
# but you can manually set their override paths here
ILDASM_EXE = None
# https://docs.microsoft.com/en-us/dotnet/framework/tools/ildasm-exe-il-disassembler
ILASM_EXE = None
# https://docs.microsoft.com/en-us/dotnet/framework/tools/ilasm-exe-il-assembler

# .net method to get their paths
# https://stackoverflow.com/a/28530783/2350244
ILDASM_ROOT = r"%PROGRAMFILES(X86)%\Microsoft SDKs\Windows"
ILASM_ROOT = r"C:\Windows\Microsoft.NET\Framework"


# tracking whether misc corrections have been applied to IL
# seems like the .net 4.8 ildasm has regressions
HAD_FIXES = False


def panic(msg, errcode=errno.EIO):
    """Panic, print message to stderr and exit"""
    print(msg, file=sys.stderr)
    sys.exit(errcode)


def find_ildasm_path():
    """Find full path of dotnet sdk binaries"""
    # TODO: modify to find the latest sdk?
    root = op.expandvars(ILDASM_ROOT)
    for ventry in os.listdir(root):
        if re.match(r"v\d+\.", ventry):
            bin_dir = op.join(root, ventry, 'bin')
            for netfxentry in os.listdir(bin_dir):
                if re.match(r"NETFX\s4\.7", netfxentry):
                    ildasm_path = op.join(bin_dir, netfxentry, 'ildasm.exe')
                    print("using ildasm (.net 4.7 sdk): %s" %
                          ildasm_path.lower())
                    return ildasm_path
                elif re.match(r"NETFX\s4\.7", netfxentry):
                    panic(
                        ".net 4.8 exists but seems to have regressions. "
                        "please install the .net 4.7 sdk"
                    )


def find_ilasm_path():
    """Find full path of dotnet sdk binaries"""
    # TODO: modify to find the latest sdk?
    root = op.expandvars(ILASM_ROOT)
    for ventry in os.listdir(root):
        if re.match(r"v4\.", ventry):
            ilasm_path = op.join(root, ventry, 'ilasm.exe')
            print("using ilasm (%s): %s" %
                  (ventry.lower(), ilasm_path.lower()))
            return ilasm_path


def run_ilprocess(name, args):
    """Run IL utility with given args"""
    runargs = [name]
    runargs.extend(args)
    return subprocess.run(runargs, capture_output=True)


def ildasm(ns_prefix, il_binary):
    """Disassemble IL bindary to .il file"""
    ildasm_exe = find_ildasm_path() or ILDASM_EXE
    if not (ildasm_exe and op.exists(ildasm_exe)):
        panic("can not find ildasm")
    il_file_name = ns_prefix + '.' + op.splitext(op.basename(il_binary))[0] + '.il'
    il_file = op.join(op.dirname(il_binary), il_file_name)
    res = run_ilprocess(ildasm_exe, [
        '"%s"' % il_binary,
        '/NOBAR',
        '/TYPELIST',
        # '/ALL',
        '/OUT="%s"' % il_file
        ])
    if res.returncode != 0:
        panic("Error disassembling %s" % il_binary, errcode=res.returncode)
    return il_file


def extract_namespaces(il_file):
    """Find namespaces listed in given IL file"""
    extern_ns_list = set()
    ns_list = set()
    record_ns = False
    with codecs.open(il_file, 'r') as ilf:
        for illine in ilf.readlines():
            # start/pause recording namespaces
            if illine.startswith('.typelist'):
                record_ns = True
            elif illine.startswith('}'):
                record_ns = False

            if record_ns:
                tokens = illine.strip().split('.')
                if tokens and tokens[0].isalnum():
                    ns_list.add(tokens[0])

            # grab extern namespaces
            ext_ns_m = re.match(r'.assembly extern\s(.+)$', illine)
            if ext_ns_m:
                extern_ns_list.add(ext_ns_m.groups()[0])

            if illine.startswith('.module'):
                break

    return ns_list - extern_ns_list


def fix_resfiles(cwd, nsdict):
    """Fix name of extracted resource files based on given ns rename dict"""
    for entry in os.listdir(cwd):
        for cur_ns, new_ns in nsdict.items():
            if entry.startswith(cur_ns) \
                    and not entry.endswith('.dll') \
                    and op.isfile(op.join(cwd, entry)):
                os.rename(
                    op.join(cwd, entry),
                    op.join(cwd, entry.replace(cur_ns, new_ns))
                    )


# FIXME: https://developercommunity.visualstudio.com/solutions/806165/view.html
IL_FIXES = {
    r"ldc\.r4(\s+)inf":   r"ldc.r4\g<1>(00 00 80 7F)",
    r"ldc\.r4(\s+)-inf":  r"ldc.r4\g<1>(00 00 80 FF)",
    r"ldc\.r8(\s+)inf":   r"ldc.r8\g<1>(00 00 00 00 00 00 F0 7F)",
    r"ldc\.r8(\s+)-inf":  r"ldc.r8\g<1>(00 00 00 00 00 00 F0 FF)",
}

def apply_il_fixes(il_line):
    """Apply misc IL corrections"""
    global HAD_FIXES
    # FIXME: with .net 4.8 https://github.com/dotnet/roslyn/issues/35147#issuecomment-485033534
    if il_line.startswith('.custom (UNKNOWN_OWNER)'):
        HAD_FIXES = True
        return il_line, -1

    for kpat, krepl in IL_FIXES.items():
        il_line = re.sub(kpat, krepl, il_line)
        if il_line != il_line:
            HAD_FIXES = True

    return il_line, 0


def fixns(il_file, ns_prefix):
    """Fixed the namespaces in given .il file"""
    illines = []
    cur_ns_list = extract_namespaces(il_file)
    nsdict = {x: '%s.%s' % (ns_prefix, x) for x in cur_ns_list}
    if cur_ns_list:
        skipping_pk = False
        with codecs.open(il_file, 'r') as ilf:
            for illine in ilf.readlines():
                # discard public key start --------------
                if '.publickey =' in illine:
                    skipping_pk = True
                    continue
                elif skipping_pk and '.hash algorithm' in illine:
                    skipping_pk = False
                    continue
                if skipping_pk:
                    continue
                # discard public key end ----------------

                edited_line = illine
                edited_line, err = apply_il_fixes(edited_line)
                if err == 0:
                    for cur_ns, new_ns in nsdict.items():
                        edited_line = \
                            re.sub(
                                r"([\s:(])%s" % cur_ns,
                                r"\g<1>%s" % new_ns,
                                edited_line
                            )
                    illines.append(edited_line)
        with codecs.open(il_file, 'w') as ilf:
            ilf.writelines(illines)
    if HAD_FIXES:
        print("IL fixes has been applied")
    return nsdict


def ilasm(il_file):
    """Assemble IL binary from .il file"""
    ilasm_exe = find_ilasm_path() or ILDASM_EXE
    if not (ilasm_exe and op.exists(ilasm_exe)):
        panic("Can not find ilasm")
    il_name = op.splitext(op.basename(il_file))[0]
    cwd = op.dirname(il_file)
    new_il_binary_name = il_name + '.dll'
    new_il_binary = op.join(cwd, new_il_binary_name)
    ilasm_args = [
        '%s' % il_file,
        '/DLL',
        '/OUTPUT=%s' % new_il_binary,
    ]
    # FIXME: currently this func skips the .res files
    # il_res = op.join(cwd, il_name + '.res')
    # if op.exists(il_res):
    #     ilasm_args.append('/RESOURCE="%s"' % il_res)

    res = run_ilprocess(ilasm_exe, ilasm_args)
    if res.returncode != 0 \
            or 'Operation completed successfully' not in str(res.stdout):
        panic("Error assembling %s" % il_file, errcode=res.returncode)
    return new_il_binary


def cleanup(cwd, ns_prefix):
    """Cleanup temp files around given new IL binary"""
    # FIXME: is not perfect, artifacts still remain
    # FIXME: ensure other files in the same dir are not deleted
    for entry in os.listdir(cwd):
        if entry.startswith(ns_prefix) \
                and not entry.endswith('.dll') \
                and op.isfile(op.join(cwd, entry)):
            rm_target = op.join(cwd, entry)
            print("cleaning %s" % rm_target)
            os.remove(rm_target)


def ilpfxns(ns_prefix, il_binary):
    """Orchestrate prefixing namespace"""
    # TODO: cleanup cwd and libname getters, multiple funcs calc this atm
    cwd = op.dirname(il_binary)
    # disassemble
    # new il file is renamed with ns_prefix
    il_file = ildasm(ns_prefix, il_binary)

    # # fix namespaces
    # fixedns_dict = fixns(il_file, ns_prefix)
    # # fix misc resouce file names to include prefix
    # fix_resfiles(cwd, fixedns_dict)

    # # reassemble
    new_il_binary = ''
    # new_il_binary = ilasm(il_file)

    # # remove temp files
    # cleanup(cwd, ns_prefix)
    return new_il_binary


def print_help():
    """Print help"""
    print(__doc__)
    sys.exit(errno.EINVAL)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_help()

    # cmdargs = CMDArgs(
    #     # process args
    #     docopt(
    #         __doc__.format(cliname=__binname__),
    #         version='{} {}'.format(__binname__, __version__)
    #     ))
    prefix = sys.argv[1]
    for targetdll in sys.argv[2:]:
        print("\033[1m==> fixing %s\033[0m" % op.basename(targetdll))
        print("applying \"%s\" prefix to IL namespaces" % prefix)
        newdll = ilpfxns(prefix, targetdll)
        print("successfilly generated new IL binary: %s" % newdll.lower())
