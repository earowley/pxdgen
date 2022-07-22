#    PxdGen - A C/C++ header conversion tool
#    Copyright (C) 2021  Eric Rowley

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations
import argparse
import sys
import os
import os.path
import glob
import clang.cindex
import pxdgen.utils as utils
from pxdgen.utils import TabWriter
from pxdgen.cursors import Namespace, block
from pxdgen.extensions import load_extensions
from colorama import Fore, Style, init as colorama_init
colorama_init()


FLAG_EXTRA_DECLS = "includerefs"
FLAG_IMPORT_ALL = "importall"
FLAG_ERROR_EXIT = "safe"
FLAG_SYS_HEADER = "sys"
FLAG_PARSE_DEFINES = "defines"


SEVERITY = {
    0: '',
    1: Fore.WHITE + "Remark" + Fore.RESET,
    2: Fore.YELLOW + "Warning" + Fore.RESET,
    3: Fore.RED + "Error" + Fore.RESET,
    4: Style.BRIGHT + Fore.RED + "Fatal" + Fore.RESET
}


def px_log(*args, source: str = "PxdGen"):
    source = f"[{source}]"
    print(f"{source:.<15}", *args, sep='', file=sys.stderr)


class PxdGen:
    def __init__(self, program_options: argparse.Namespace):
        """
        Main class for PxdGen supplementary script. CLI implementation.

        @param program_options: Options supplied to CLI.
        """
        dir_mode = os.path.isdir(program_options.header)
        file_mode = os.path.isfile(program_options.header)
        relpath = program_options.relpath or os.getcwd()

        if not dir_mode and not file_mode:
            exit(f"Unable to find input '{program_options.header}' on the file system")

        if not os.path.isdir(relpath):
            exit(f"Unable to find relative path '{relpath}'")

        if dir_mode and not program_options.output:
            request = input("Detected directory without an output location, are you sure you want to print the results to stdout? [y/n]")

            if request.lower() != 'y':
                exit("Use the `-o` flag to specify an output directory")

        if program_options.output and not os.path.isdir(program_options.output):
            os.makedirs(program_options.output)

        if program_options.libs:
            clang.cindex.Config.set_library_path(program_options.libs)

        try:
            self.index = clang.cindex.Index.create()
        except clang.cindex.LibclangError as e:
            msg = str(e)

            if "set_library_path" in msg:
                exit("Unable to find libclang.so. Specify the path to PxdGen with `-L`")

            exit(msg)

        clang_args = list()

        if program_options.include:
            for i in program_options.include:
                clang_args.append("-I")
                clang_args.append(i)

        if program_options.language:
            clang_args += ["-x", program_options.language]

        self.clang_args = clang_args
        self.opts = program_options
        self.dir_mode = dir_mode
        self.file_mode = file_mode
        self.relpath = relpath
        self.flags = set(program_options.flags)

        load_extensions()

    def run(self):
        """
        Run the program with parameters supplied in constructor.

        @return: None.
        """
        if self.opts.recursive and FLAG_EXTRA_DECLS in self.flags:
            exit(f"Recursion (-r) and extra declarations (-f{FLAG_EXTRA_DECLS}) should not be enabled simultaneously")

        to_parse = list()

        # Get the headers to parse
        if self.file_mode:
            to_parse.append(os.path.abspath(self.opts.header))
        elif self.dir_mode:
            for glob_term in ("**/*.h", "**/*.hpp"):
                for header in glob.glob(os.path.join(self.opts.header, glob_term), recursive=True):
                    to_parse.append(os.path.abspath(header))

        valid_headers = set(to_parse)

        if self.opts.verbose:
            px_log(f"PxDGen in {'file mode' if self.file_mode else 'directory mode'} parsing the following header{'s' if len(valid_headers) > 1 else ''}:")

            for h in valid_headers:
                px_log(h)
            px_log()

        # Context which contains a mapping of namespace->IOStream
        # The IOStream has the text for the __init__.pxd of each
        # namespace
        ctx = dict()
        parse_opts = clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD if FLAG_PARSE_DEFINES in self.flags else 0

        for file in to_parse:
            tu = self.index.parse(file, self.clang_args, options=parse_opts)

            if self.opts.verbose:
                px_log("Parsing ", file)

            for d in tu.diagnostics:
                if d.severity == 0:
                    continue
                if self.opts.verbose and d.severity < 3:
                    px_log(f"{SEVERITY[d.severity]}: {d.spelling}", source="Clang")
                elif d.severity >= 3:
                    px_log(f"{SEVERITY[d.severity]}: {d.spelling}", source="Clang")
                    if FLAG_ERROR_EXIT in self.flags:
                        exit()

            # Find the namespaces for the current file, and its associated cursors
            namespaces = utils.find_namespaces(tu.cursor, valid_headers, self.opts.recursive)
            # The C "top-level" namespace
            namespaces[''] = [tu.cursor]

            for space_name, cursors in namespaces.items():
                pxspace = Namespace(cursors, self.opts.recursive, file, valid_headers)

                if not pxspace.has_declarations:
                    continue

                imports, fwd, body = set(), TabWriter(), TabWriter()

                #  Imports are disabled if extra declarations are defined
                #  Extra declarations are disabled if recursive is enabled
                #  Imports are also disabled if output is directed to a single file/stream
                if FLAG_EXTRA_DECLS in self.flags and not self.opts.recursive:
                    fwd_decls = sorted(pxspace.forward_decls, key=lambda v: len(Namespace._get_all_assoc(v.cursor)))

                    if len(fwd_decls):
                        for line in block(fwd_decls, "toplevel", "cdef extern from *:", False):
                            fwd.writeline(line)
                elif self.opts.output or not self.opts.recursive:
                    for i in pxspace.import_strings(FLAG_IMPORT_ALL in self.flags or self.opts.recursive):
                        imports.add(i)

                for line in pxspace.lines(os.path.relpath(file, self.opts.relpath), FLAG_SYS_HEADER in self.flags):
                    body.writeline(line)

                body.writeline('')

                if self.opts.output:
                    pxd = os.path.splitext(os.path.basename(file))[0] + ".pxd"
                    out_path = os.path.join(self.opts.output, space_name.replace("::", os.path.sep))
                    out_file = os.path.join(out_path, pxd)
                    init = ctx.get(space_name, TabWriter())
                    init_import = os.path.relpath(out_file, self.opts.output).replace(os.path.sep, '.').replace(".pxd", '')
                    init.writeline(f"from {init_import} cimport *")
                    ctx[space_name] = init

                    if not os.path.isdir(out_path):
                        os.makedirs(out_path)

                    stream = open(out_file, 'w')
                else:
                    stream = sys.stdout

                try:
                    for i in sorted(imports):
                        stream.write(i)
                        stream.write('\n')

                    stream.write('\n')

                    if FLAG_EXTRA_DECLS in self.flags:
                        stream.write(fwd.getvalue())
                        stream.write('\n')

                    stream.write(body.getvalue())
                    stream.write('\n')
                finally:
                    if stream is not sys.stdout:
                        stream.close()

        if self.opts.output:
            for space_name in ctx:
                # For C "top-level", do not use __init__.pxd, because
                # The output directory is intended to be added to pxd
                # path
                if not space_name:
                    continue
                out_path = os.path.join(self.opts.output, space_name.replace("::", os.path.sep))

                with open(os.path.join(out_path, "__init__.pxd"), 'w') as out:
                    out.write(ctx[space_name].getvalue())


def main():
    """
    Entry point for PxdGen CLI.

    @return: None
    """
    args = sys.argv[1:]

    argp = argparse.ArgumentParser(description="A tool that converts C/C++ headers to pxd files")
    argp.add_argument("header",
                      help="Path to C/C++ header file or project directory to parse")
    argp.add_argument("-o", "--output",
                      help="Path to output file or directory (defaults to stdout)")
    argp.add_argument("-p", "--relpath",
                      help="Relative path to parse from (defaults to pwd)")
    argp.add_argument("-r", "--recursive",
                      action="store_true",
                      help="Include declarations from all nested headers")
    argp.add_argument("-x", "--language",
                      help="Force Clang to use the specified language for interpretation")
    argp.add_argument("-I", "--include",
                      action="append",
                      help="Add a directory to Clang's include path")
    argp.add_argument("-L", "--libclang-path",
                      dest="libs",
                      help="Specify the path to a directory containing libclang and its dependencies")
    argp.add_argument("-v", "--verbose",
                      action="store_true",
                      help="Print the status of the application to stdout")
    argp.add_argument("-f", "--flag",
                      action="append",
                      dest="flags",
                      default=[],
                      help="Set a flag to further tune the program output")

    opts = argp.parse_args(args)
    proc = PxdGen(opts)
    proc.run()
