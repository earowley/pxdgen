# PxdGen

PxdGen is a tool which uses Clang to convert C/C++ header files to Cython pxd files. It has two modes of operation: single-file mode and directory mode. Single file mode is well suited for C/C++ libraries that consolodate all definitions into a single header, while directory mode is better suited for large projects with many independent headers. There are some examples which use PxdGen on C/C++ libraries in the tests folder.

## Installation

    pip install pxdgen
    
## Requirements

+ [Clang](https://releases.llvm.org/download.html) - The version of libclang.(dll/so/dylib) on your system should match the version of the Python bindings to Clang. If it is not found by the standard library search path on your system, PxdGen allows you to point it to the library with -L.

## Bugs/Limitations

 + Experimental C++ support

## Usage

    pxdgen [-h] [-o OUTPUT] [-p RELPATH] [-r] [-x LANGUAGE] [-I INCLUDE] [-L LIBS] [-v] [-f FLAGS] header
    
    A tool that converts C/C++ headers to pxd files
    
    positional arguments:
      header                Path to C/C++ header file or project directory to parse
    
    optional arguments:
      -h, --help            show this help message and exit
      -o OUTPUT, --output OUTPUT
                            Path to output file or directory (defaults to stdout)
      -p RELPATH, --relpath RELPATH
                            Relative path to parse from (defaults to pwd)
      -r, --recursive       Include declarations from all nested headers
      -x LANGUAGE, --language LANGUAGE
                            Force Clang to use the specified language for interpretation
      -I INCLUDE, --include INCLUDE
                            Add a directory to Clang's include path
      -L LIBS, --libclang-path LIBS
                            Specify the path to a directory containing libclang and its dependencies
      -v, --verbose         Print the status of the application to stdout
      -f FLAGS, --flag FLAGS
                            Set a flag to further tune the program output
