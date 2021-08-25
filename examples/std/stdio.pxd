#  PXDGEN AUTO-DEFINED TYPES
cdef extern from *:
#    Bug: anonymous declarations
#    ctypedef struct (anonymous union at /usr/include/x86_64-linux-gnu/bits/types/__mbstate_t.h:16:3):
#        pass
    ctypedef struct __builtin_va_list:
        pass


cdef extern from "stdio.h":
    ctypedef unsigned long size_t
    ctypedef __builtin_va_list va_list
    ctypedef __builtin_va_list __gnuc_va_list
    ctypedef unsigned char __u_char
    ctypedef unsigned short __u_short
    ctypedef unsigned int __u_int
    ctypedef unsigned long __u_long
    ctypedef signed char __int8_t
    ctypedef unsigned char __uint8_t
    ctypedef short __int16_t
    ctypedef unsigned short __uint16_t
    ctypedef int __int32_t
    ctypedef unsigned int __uint32_t
    ctypedef long __int64_t
    ctypedef unsigned long __uint64_t
    ctypedef __int8_t __int_least8_t
    ctypedef __uint8_t __uint_least8_t
    ctypedef __int16_t __int_least16_t
    ctypedef __uint16_t __uint_least16_t
    ctypedef __int32_t __int_least32_t
    ctypedef __uint32_t __uint_least32_t
    ctypedef __int64_t __int_least64_t
    ctypedef __uint64_t __uint_least64_t
    ctypedef long __quad_t
    ctypedef unsigned long __u_quad_t
    ctypedef long __intmax_t
    ctypedef unsigned long __uintmax_t
    ctypedef unsigned long __dev_t
    ctypedef unsigned int __uid_t
    ctypedef unsigned int __gid_t
    ctypedef unsigned long __ino_t
    ctypedef unsigned long __ino64_t
    ctypedef unsigned int __mode_t
    ctypedef unsigned long __nlink_t
    ctypedef long __off_t
    ctypedef long __off64_t
    ctypedef int __pid_t
    ctypedef struct __fsid_t:
        int __val[2]
    ctypedef long __clock_t
    ctypedef unsigned long __rlim_t
    ctypedef unsigned long __rlim64_t
    ctypedef unsigned int __id_t
    ctypedef long __time_t
    ctypedef unsigned int __useconds_t
    ctypedef long __suseconds_t
    ctypedef int __daddr_t
    ctypedef int __key_t
    ctypedef int __clockid_t
    ctypedef void* __timer_t
    ctypedef long __blksize_t
    ctypedef long __blkcnt_t
    ctypedef long __blkcnt64_t
    ctypedef unsigned long __fsblkcnt_t
    ctypedef unsigned long __fsblkcnt64_t
    ctypedef unsigned long __fsfilcnt_t
    ctypedef unsigned long __fsfilcnt64_t
    ctypedef long __fsword_t
    ctypedef long __ssize_t
    ctypedef long __syscall_slong_t
    ctypedef unsigned long __syscall_ulong_t
    ctypedef __off64_t __loff_t
    ctypedef char* __caddr_t
    ctypedef long __intptr_t
    ctypedef unsigned int __socklen_t
    ctypedef int __sig_atomic_t
    ctypedef struct __mbstate_t:
        int __count
#        (anonymous union at /usr/include/x86_64-linux-gnu/bits/types/__mbstate_t.h:16:3) __value
    struct _G_fpos_t:
        __off_t __pos
        __mbstate_t __state
    ctypedef _G_fpos_t __fpos_t
    struct _G_fpos64_t:
        __off64_t __pos
        __mbstate_t __state
    ctypedef _G_fpos64_t __fpos64_t
    struct _IO_FILE:
        pass
    ctypedef _IO_FILE __FILE
    struct _IO_FILE:
        pass
    ctypedef _IO_FILE FILE
    struct _IO_FILE:
        pass
    struct _IO_marker:
        pass
    struct _IO_codecvt:
        pass
    struct _IO_wide_data:
        pass
    ctypedef void _IO_lock_t
    struct _IO_FILE:
        int _flags
        char* _IO_read_ptr
        char* _IO_read_end
        char* _IO_read_base
        char* _IO_write_base
        char* _IO_write_ptr
        char* _IO_write_end
        char* _IO_buf_base
        char* _IO_buf_end
        char* _IO_save_base
        char* _IO_backup_base
        char* _IO_save_end
        _IO_marker* _markers
        _IO_FILE* _chain
        int _fileno
        int _flags2
        __off_t _old_offset
        unsigned short _cur_column
        signed char _vtable_offset
        char _shortbuf[1]
        _IO_lock_t* _lock
        __off64_t _offset
        _IO_codecvt* _codecvt
        _IO_wide_data* _wide_data
        _IO_FILE* _freeres_list
        void* _freeres_buf
        size_t __pad5
        int _mode
        char _unused2[20]
#    ctypedef __gnuc_va_list va_list
    ctypedef __off_t off_t
    ctypedef __ssize_t ssize_t
    ctypedef __fpos_t fpos_t
    FILE* stdin
    FILE* stdout
    FILE* stderr
    int remove(const char* __filename)
    int rename(const char* __old, const char* __new)
    int renameat(int __oldfd, const char* __old, int __newfd, const char* __new)
    FILE* tmpfile()
    char* tmpnam(char* __s)
    char* tmpnam_r(char* __s)
    char* tempnam(const char* __dir, const char* __pfx)
    int fclose(FILE* __stream)
    int fflush(FILE* __stream)
    int fflush_unlocked(FILE* __stream)
    FILE* fopen(const char *__filename, const char *__modes)
    FILE* freopen(const char *__filename, const char *__modes, FILE *__stream)
    FILE* fdopen(int __fd, const char* __modes)
    FILE* fmemopen(void* __s, size_t __len, const char* __modes)
    FILE* open_memstream(char** __bufloc, size_t* __sizeloc)
    void setbuf(FILE *__stream, char *__buf)
    int setvbuf(FILE *__stream, char *__buf, int __modes, size_t __n)
    void setbuffer(FILE *__stream, char *__buf, size_t __size)
    void setlinebuf(FILE* __stream)
    int fprintf(FILE *__stream, const char *__format)
    int printf(const char *__format)
    int sprintf(char *__s, const char *__format)
    int vfprintf(FILE *__s, const char *__format, __gnuc_va_list __arg)
    int vprintf(const char *__format, __gnuc_va_list __arg)
    int vsprintf(char *__s, const char *__format, __gnuc_va_list __arg)
    int snprintf(char *__s, size_t __maxlen, const char *__format)
    int vsnprintf(char *__s, size_t __maxlen, const char *__format, __gnuc_va_list __arg)
    int vdprintf(int __fd, const char *__fmt, __gnuc_va_list __arg)
    int dprintf(int __fd, const char *__fmt)
    int fscanf(FILE *__stream, const char *__format)
    int scanf(const char *__format)
    int sscanf(const char *__s, const char *__format)
    int fscanf(FILE *__stream, const char *__format)
    int scanf(const char *__format)
    int sscanf(const char *__s, const char *__format)
    int vfscanf(FILE *__s, const char *__format, __gnuc_va_list __arg)
    int vscanf(const char *__format, __gnuc_va_list __arg)
    int vsscanf(const char *__s, const char *__format, __gnuc_va_list __arg)
    int vfscanf(FILE *__s, const char *__format, __gnuc_va_list __arg)
    int vscanf(const char *__format, __gnuc_va_list __arg)
    int vsscanf(const char *__s, const char *__format, __gnuc_va_list __arg)
    int fgetc(FILE* __stream)
    int getc(FILE* __stream)
    int getchar()
    int getc_unlocked(FILE* __stream)
    int getchar_unlocked()
    int fgetc_unlocked(FILE* __stream)
    int fputc(int __c, FILE* __stream)
    int putc(int __c, FILE* __stream)
    int putchar(int __c)
    int fputc_unlocked(int __c, FILE* __stream)
    int putc_unlocked(int __c, FILE* __stream)
    int putchar_unlocked(int __c)
    int getw(FILE* __stream)
    int putw(int __w, FILE* __stream)
    char* fgets(char *__s, int __n, FILE *__stream)
    __ssize_t __getdelim(char **__lineptr, size_t *__n, int __delimiter, FILE *__stream)
    __ssize_t getdelim(char **__lineptr, size_t *__n, int __delimiter, FILE *__stream)
    __ssize_t getline(char **__lineptr, size_t *__n, FILE *__stream)
    int fputs(const char *__s, FILE *__stream)
    int puts(const char* __s)
    int ungetc(int __c, FILE* __stream)
    unsigned long fread(void *__ptr, size_t __size, size_t __n, FILE *__stream)
    unsigned long fwrite(const void *__ptr, size_t __size, size_t __n, FILE *__s)
    size_t fread_unlocked(void *__ptr, size_t __size, size_t __n, FILE *__stream)
    size_t fwrite_unlocked(const void *__ptr, size_t __size, size_t __n, FILE *__stream)
    int fseek(FILE* __stream, long __off, int __whence)
    long ftell(FILE* __stream)
    void rewind(FILE* __stream)
    int fseeko(FILE* __stream, __off_t __off, int __whence)
    __off_t ftello(FILE* __stream)
    int fgetpos(FILE *__stream, fpos_t *__pos)
    int fsetpos(FILE* __stream, const fpos_t* __pos)
    void clearerr(FILE* __stream)
    int feof(FILE* __stream)
    int ferror(FILE* __stream)
    void clearerr_unlocked(FILE* __stream)
    int feof_unlocked(FILE* __stream)
    int ferror_unlocked(FILE* __stream)
    void perror(const char* __s)
    int sys_nerr
    const char *const sys_errlist[]
    int fileno(FILE* __stream)
    int fileno_unlocked(FILE* __stream)
    FILE* popen(const char* __command, const char* __modes)
    int pclose(FILE* __stream)
    char* ctermid(char* __s)
    void flockfile(FILE* __stream)
    int ftrylockfile(FILE* __stream)
    void funlockfile(FILE* __stream)
    int __uflow(FILE*)
    int __overflow(FILE*, int)


