# Use python -i debug.py <target_file>

import os
import sys
import clang.cindex as cc


def find(name, base=None):
    base = base or tu.cursor
    for child in base.get_children():
        if child.spelling == name:
            return child


def dump(base, indent=0):
    print((' ' * indent) + f"{base.spelling} - {base.kind}")

    for child in base.get_children():
        dump(child, indent + 4)


args = sys.argv[1:]

if not len(args):
    exit("No file specified")

if not os.path.isfile(args[0]):
    exit(f"Invalid header file {args[0]}")

index = cc.Index.create()
tu    = index.parse(args[0] , ["-I", "/usr/lib/clang/13.0.1/include", "-I", os.path.dirname(args[0])])

for diag in tu.diagnostics:
    print(diag.spelling)

