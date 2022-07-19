# Use python -i debug.py <target_file>

import os
import sys
import clang.cindex as cc
from configparser import ConfigParser


def find(name, base=None):
    parts = name.split('.')
    current = (base or tu.cursor).get_children()
    saved = list()
    i = 0
    while True:
        for child in current:
            if child.spelling == parts[i]:
                i += 1
                if i == len(parts):
                    return child
                saved.append(current)
                current = child.get_children()
                break
        else:
            if not len(saved):
                return None
            i -= 1
            current = saved.pop()


def dump(base, indent=0):
    print((' ' * indent) + f"{base.spelling} - {base.kind}")

    for child in base.get_children():
        dump(child, indent + 4)


args = sys.argv[1:]

if not len(args):
    exit("No file specified")

if not os.path.isfile(args[0]):
    exit(f"Invalid header file {args[0]}")

cfg = ConfigParser()
index = cc.Index.create()
cfg.read("configuration.ini")
include_args = ["-I", os.path.dirname(args[0])]
extra = cfg["Clang"]["include"]

if extra:
    include_args.extend(["-I", extra])

try:
    tu = index.parse(args[0], include_args)
except:
    tu = index.parse(args[0], include_args + ["-x", "c++"])

for diag in tu.diagnostics:
    print(diag.spelling)

cur = tu.cursor

sys.path.append("../src")
from pxdgen.cursors import *
from pxdgen.utils.utils import *
from pxdgen.extensions import load_extensions
load_extensions()
