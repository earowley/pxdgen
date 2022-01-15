import sys
import os
sys.path.append("../scripts")
sys.path.append("../src")
from _pxdgen import PXDGen


TEST = "/usr/include/stdio.h"


class Dummy:
    pass


if __name__ == "__main__":
    opts = Dummy()
    opts.header = TEST
    opts.output = ''
    opts.relpath = os.path.dirname(TEST)
    opts.recursive = False
    opts.headers = list()
    opts.language = ''
    opts.include = list()
    opts.libs = ''
    opts.warning_level = 0
    opts.flags = list()
