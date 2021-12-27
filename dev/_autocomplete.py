"""Generate and build autocompleter for pyRevit CLI"""
# pylint: disable=invalid-name,missing-class-docstring,missing-function-docstring
import os
import os.path as op
from typing import Dict
import re

from scripts import configs
from scripts import utils


# tokens
class GoToken(object):
    template = "{}"

    def __init__(self, token):
        self.token = token
        self.nodes = []

    def __repr__(self):
        return "<{} token={} childs={}>".format(
            self.__class__.__name__, self.token, len(self.nodes)
        )

    def __hash__(self):
        return hash("{}.{}".format(self.__class__.__name__, self.token))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)

    def find_node(self, token):
        if token == self.token:
            return self
        for node in self.nodes:
            if node.token == token:
                return node

    def write_go(self):
        go_code = "\n"
        for node in self.nodes:
            go_code += node.write_go()
            go_code += "\n"
        return self.template.format(go_code)


class GoFlags(GoToken):
    template = '"--{}": complete.PredictNothing,'

    def write_go(self):
        return self.template.format(self.token)


class GoCommand(GoToken):
    template = """"{0}": complete.Command{{
    Sub: complete.Commands{{
    {1}
    }},
    Flags: complete.Flags{{
    {2}
    }},
    }},
    """

    def __init__(self, token):
        super(GoCommand, self).__init__(token)
        self.flags = set()

    def update_flags(self, command_paths, flags):
        # get rid of the app name
        if command_paths:
            root_token = command_paths[0]
            command = self.find_node(root_token)
            if not command:
                command = GoCommand(root_token)
                self.nodes.append(command)
            command.update_flags(command_paths[1:], flags)
        else:
            self.flags.update([GoFlags(x) for x in flags])

    def write_go(self):
        go_code = ""
        for node in self.nodes:
            go_code += node.write_go()

        flags_go_code = ""
        for flag in self.flags:
            flags_go_code += flag.write_go()
            flags_go_code += "\n"
        return self.template.format(self.token, go_code, flags_go_code)


class GoApplication(GoCommand):
    template = """{0} := complete.Command{{
    Sub: complete.Commands{{
    {1}
    }},
    Flags: complete.Flags{{
    {2}
    }},
    }}
    complete.New("{0}", {0}).Run()"""


class GoCompleteFunc(GoToken):
    template = "func main() {{{}}}"

    def __init__(self, app):
        super(GoCompleteFunc, self).__init__("main")
        self.app = app

    def write_go(self):
        go_code = self.app.write_go()
        return self.template.format(go_code)


class GoImports(GoToken):
    template = "{} ({})"

    def __init__(self, sources):
        super(GoImports, self).__init__("import")
        self.sources = set(sources)

    def write_go(self):
        import_lines = ""
        for source in self.sources:
            import_lines += '"{}"'.format(source)
        return self.template.format(self.token, import_lines)


class GoPackage(GoToken):
    template = "{} {}"

    def __init__(self, name):
        super(GoPackage, self).__init__("package")
        self.name = name

    def write_go(self):
        return self.template.format(self.token, self.name)


class GoAst(GoToken):
    def __init__(self, nodes):
        super(GoAst, self).__init__(None)
        self.nodes = nodes


def extract_branch(space_delimited_string):
    return re.findall(r"\w+", space_delimited_string)


def parse_docopt_line(line, go_app):
    # cleanup extra characters
    line = line.strip()
    for char in ["[", "]", "|", "="]:
        line = line.replace(char, "")
    line = re.sub(r"<[a-zA-Z_]+?>", "", line)
    line = line.strip()

    # process flags
    flags = re.findall(r"\s--(\w+)\s?", line)
    for flag in flags:
        line = line.replace("--{}".format(flag), "")
    # remove short flags
    for sflag in re.findall(r"-(\w+)\s?", line):
        line = line.replace("-{}".format(sflag), "")
    line = line.strip()

    # process branches
    command_paths = []
    optionals = re.search(r"\((.+?)\)", line)
    if optionals:
        options_def = optionals.group()
        command_paths.extend(
            [
                extract_branch(line.replace(options_def, x))
                for x in re.findall(r"\w+", optionals.groups()[0])
            ]
        )
        line = line.replace(options_def, "").strip()
    command_paths.append(extract_branch(line))

    # report
    for command_path in command_paths:
        go_app.update_flags(command_path, flags)


def parse_docopts(docopts_filepath):
    # kickstart with pyrevit command
    go_app = GoApplication("pyrevit")
    go_app.flags.update(
        [GoFlags("verbose"), GoFlags("debug"),]
    )
    go_ast = GoAst(
        [
            GoPackage("main"),
            GoImports(["github.com/posener/complete"]),
            GoCompleteFunc(go_app),
        ]
    )

    with open(docopts_filepath, "r") as df:
        # read and skip first
        for line in df.readlines()[1:]:
            parse_docopt_line(line, go_app)

    return go_ast


def build_autocmp(_: Dict[str, str]):
    """Build CLI shell autocomplete utility"""
    print("Updating autocomplete utility dependencies...")
    utils.system(
        ["go", "get", "-u", r"./..."],
        cwd=op.abspath(configs.AUTOCOMPPATH)
        )
    print("Autocomplete utility dependencies successfully updated")

    # generate go autocomplete source from usage patterns
    go_ast = parse_docopts(configs.USAGEPATTERNS)
    if go_ast:
        go_code = go_ast.write_go()
        with open(configs.AUTOCOMP, "w") as gf:
            gf.write(go_code)

    print("Building autocomplete utility...")
    target = op.abspath(configs.AUTOCOMPBIN)
    utils.system(["go", "fmt", configs.AUTOCOMP])
    utils.system(
        ["go", "build", "-o", target, op.abspath(configs.AUTOCOMP)],
        cwd=op.abspath(configs.AUTOCOMPPATH)
        )
    print("Building autocomplete utility completed successfully")
    # os.remove(configs.AUTOCOMP)
