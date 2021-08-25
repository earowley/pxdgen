# PxdGen

PxdGen is a tool which uses Clang to convert C/C++ header files to Cython pxd files. It has two modes of operation: single-file mode and directory mode. Single file mode is well suited for C/C++ libraries that consolodate all definitions into a single header, while directory mode is better suited for large projects with many independent headers. There are examples of each in the examples folder.

## Simple Example

Below would be a simple way to use string.h functions from Cython (assuming Cython's libc.string did not exist):

    pxdgen -o string.pxd -fautodefine /usr/include/string.h
    
The 'autodefine' flag assumes unknown declarations are defined "somewhere" within the headers #included in string.h. It places automatic declarations at the top of the output file. The resulting file looks something like:

    #  string.pxd
    
    #  PXDGEN AUTO-DEFINED TYPES
    cdef extern from *:
        ctypedef struct locale_t:
            pass


    cdef extern from "string.h":
        void* memcpy(void *__dest, const void *__src, size_t __n)
        void* memmove(void* __dest, const void* __src, size_t __n)
        void* memccpy(void *__dest, const void *__src, int __c, size_t __n)
        void* memset(void* __s, int __c, size_t __n)
        int memcmp(const void* __s1, const void* __s2, size_t __n)
        void* memchr(const void* __s, int __c, size_t __n)
        char* strcpy(char *__dest, const char *__src)
        char* strncpy(char *__dest, const char *__src, size_t __n)
        char* strcat(char *__dest, const char *__src)
        char* strncat(char *__dest, const char *__src, size_t __n)
        int strcmp(const char* __s1, const char* __s2)
        int strncmp(const char* __s1, const char* __s2, size_t __n)
        int strcoll(const char* __s1, const char* __s2)
        unsigned long strxfrm(char *__dest, const char *__src, size_t __n)
        int strcoll_l(const char* __s1, const char* __s2, locale_t __l)
        size_t strxfrm_l(char* __dest, const char* __src, size_t __n, locale_t __l)
        char* strdup(const char* __s)
        char* strndup(const char* __string, size_t __n)
        char* strchr(const char* __s, int __c)
        char* strrchr(const char* __s, int __c)
        unsigned long strcspn(const char* __s, const char* __reject)
        unsigned long strspn(const char* __s, const char* __accept)
        char* strpbrk(const char* __s, const char* __accept)
        char* strstr(const char* __haystack, const char* __needle)
        char* strtok(char *__s, const char *__delim)
        char* __strtok_r(char *__s, const char *__delim, char **__save_ptr)
        char* strtok_r(char *__s, const char *__delim, char **__save_ptr)
        unsigned long strlen(const char* __s)
        size_t strnlen(const char* __string, size_t __maxlen)
        char* strerror(int __errnum)
        int strerror_r(int __errnum, char* __buf, size_t __buflen)
        char* strerror_l(int __errnum, locale_t __l)
        void explicit_bzero(void* __s, size_t __n)
        char* strsep(char **__stringp, const char *__delim)
        char* strsignal(int __sig)
        char* __stpcpy(char *__dest, const char *__src)
        char* stpcpy(char *__dest, const char *__src)
        char* __stpncpy(char *__dest, const char *__src, size_t __n)
        char* stpncpy(char *__dest, const char *__src, size_t __n)

The string.pxd Cython header may then be used like:

    #  cstring.pyx

    cimport string

    def strcmp(str s1, str s2):
        cdef bytes cs1 = s1.encode(), cs2 = s2.encode()
        
        return string.strcmp(<char*> cs1, <char*> cs2)

To compile:

    cythonize --3str --inplace cstring.pyx

To use:

    Python 3.8.10 (default, Jun  2 2021, 10:49:15)
    [GCC 9.4.0] on linux
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import cstring
    >>> cstring.strcmp("foo", "bar")
    4
    >>> cstring.strcmp("bar", "foo")
    -4
    >>> cstring.strcmp("baz", "baz")
    0
    >>>
    
There are more C stdlib examples in the examples folder. Each wraps the C standard library without the use of Cython's libc.*.

## Requirements

+ [Clang](https://releases.llvm.org/download.html) - Make sure libclang is on your $PATH, or direct pxdgen to the correct path with -L.

## Installation

    pip install pxdgen

## Bugs/Limitations

 + No Union support yet
 + Anonymous struct/enum/union declarations do not output properly
 + Experimental C++ support
 + Experimental type resolution
 + Declarations with C/C++ keywords in the name are sometimes not output properly

## Usage

    usage: pxdgen [-h] [-o OUTPUT] [-r] [-I INCLUDE] [-H HEADERS] [-W WARNING_LEVEL] [-L LIBS] [-x LANGUAGE] [-D] [-f FLAGS] header

    Converts a C/C++ header file to a pxd file

    positional arguments:
    header                Path to C/C++ header or directory file to parse

    optional arguments:
    -h, --help            show this help message and exit
    -o OUTPUT, --output OUTPUT
                            Path to output file or directory, if any
    -r, --recursive-includes
                            Include declarations from other included headers
    -I INCLUDE, --include INCLUDE
                            Add a directory to Clang's include path
    -H HEADERS, --headers HEADERS
                            Specify a glob term to identify valid headers to parse
    -W WARNING_LEVEL, --warning-level WARNING_LEVEL
                            Flag to set the warning level of the current run
    -L LIBS, --libclang-path LIBS
                            Specify a path to a directory containing libclang and its dependencies
    -x LANGUAGE, --language LANGUAGE
                            Force Clang to use the specified language for interpretation, such as 'c++'
    -D, --directory       Use pxdgen to parse a directory tree
    -f FLAGS, --flag FLAGS
                            Set a pxdgen flag to further tune the program output

