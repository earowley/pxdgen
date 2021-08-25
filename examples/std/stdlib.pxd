#  PXDGEN IMPORTS
from libc.stdint cimport int32_t

#  PXDGEN AUTO-DEFINED TYPES
cdef extern from *:
    ctypedef struct wchar_t:
        pass


cdef extern from "stdlib.h":
    ctypedef struct div_t:
        int quot
        int rem
    ctypedef struct ldiv_t:
        long quot
        long rem
    ctypedef struct lldiv_t:
        long long quot
        long long rem
    size_t __ctype_get_mb_cur_max()
    double atof(const char* __nptr)
    int atoi(const char* __nptr)
    long atol(const char* __nptr)
    long long atoll(const char* __nptr)
    double strtod(const char *__nptr, char **__endptr)
    float strtof(const char *__nptr, char **__endptr)
    long double strtold(const char *__nptr, char **__endptr)
    long strtol(const char *__nptr, char **__endptr, int __base)
    unsigned long strtoul(const char *__nptr, char **__endptr, int __base)
    long long strtoq(const char *__nptr, char **__endptr, int __base)
    unsigned long long strtouq(const char *__nptr, char **__endptr, int __base)
    long long strtoll(const char *__nptr, char **__endptr, int __base)
    unsigned long long strtoull(const char *__nptr, char **__endptr, int __base)
    char* l64a(long __n)
    long a64l(const char* __s)
    long random()
    void srandom(unsigned int __seed)
    char* initstate(unsigned int __seed, char* __statebuf, size_t __statelen)
    char* setstate(char* __statebuf)
    struct random_data:
        int32_t* fptr
        int32_t* rptr
        int32_t* state
        int rand_type
        int rand_deg
        int rand_sep
        int32_t* end_ptr
    int random_r(random_data *__buf, int32_t *__result)
    int srandom_r(unsigned int __seed, random_data* __buf)
    int initstate_r(unsigned int __seed, char *__statebuf, size_t __statelen, random_data *__buf)
    int setstate_r(char *__statebuf, random_data *__buf)
    int rand()
    void srand(unsigned int __seed)
    int rand_r(unsigned int* __seed)
    double drand48()
    double erand48(unsigned short __xsubi[3])
    long lrand48()
    long nrand48(unsigned short __xsubi[3])
    long mrand48()
    long jrand48(unsigned short __xsubi[3])
    void srand48(long __seedval)
    unsigned short* seed48(unsigned short __seed16v[3])
    void lcong48(unsigned short __param[7])
    struct drand48_data:
        unsigned short __x[3]
        unsigned short __old_x[3]
        unsigned short __c
        unsigned short __init
        unsigned long long __a
    int drand48_r(drand48_data *__buffer, double *__result)
    int erand48_r(unsigned short __xsubi[3], drand48_data *__buffer, double *__result)
    int lrand48_r(drand48_data *__buffer, long *__result)
    int nrand48_r(unsigned short __xsubi[3], drand48_data *__buffer, long *__result)
    int mrand48_r(drand48_data *__buffer, long *__result)
    int jrand48_r(unsigned short __xsubi[3], drand48_data *__buffer, long *__result)
    int srand48_r(long __seedval, drand48_data* __buffer)
    int seed48_r(unsigned short __seed16v[3], drand48_data* __buffer)
    int lcong48_r(unsigned short __param[7], drand48_data* __buffer)
    void* malloc(size_t __size)
    void* calloc(size_t __nmemb, size_t __size)
    void* realloc(void* __ptr, size_t __size)
    void* reallocarray(void* __ptr, size_t __nmemb, size_t __size)
    void free(void* __ptr)
    void* valloc(size_t __size)
    int posix_memalign(void** __memptr, size_t __alignment, size_t __size)
    void* aligned_alloc(size_t __alignment, size_t __size)
    void abort()
    int atexit(void (*__func)())
    int at_quick_exit(void (*__func)())
    int on_exit(void (*__func)(int, void *), void* __arg)
    void exit(int __status)
    void quick_exit(int __status)
    void _Exit(int __status)
    char* getenv(const char* __name)
    int putenv(char* __string)
    int setenv(const char* __name, const char* __value, int __replace)
    int unsetenv(const char* __name)
    int clearenv()
    char* mktemp(char* __template)
    int mkstemp(char* __template)
    int mkstemps(char* __template, int __suffixlen)
    char* mkdtemp(char* __template)
    int system(const char* __command)
    char* realpath(const char *__name, char *__resolved)
    ctypedef int (*__compar_fn_t)(const void *, const void *)
    void* bsearch(const void* __key, const void* __base, size_t __nmemb, size_t __size, __compar_fn_t __compar)
    void qsort(void* __base, size_t __nmemb, size_t __size, __compar_fn_t __compar)
    int abs(int __x)
    long labs(long __x)
    long long llabs(long long __x)
    div_t div(int __numer, int __denom)
    ldiv_t ldiv(long __numer, long __denom)
    lldiv_t lldiv(long long __numer, long long __denom)
    char* ecvt(double __value, int __ndigit, int *__decpt, int *__sign)
    char* fcvt(double __value, int __ndigit, int *__decpt, int *__sign)
    char* gcvt(double __value, int __ndigit, char* __buf)
    char* qecvt(long double __value, int __ndigit, int *__decpt, int *__sign)
    char* qfcvt(long double __value, int __ndigit, int *__decpt, int *__sign)
    char* qgcvt(long double __value, int __ndigit, char* __buf)
    int ecvt_r(double __value, int __ndigit, int *__decpt, int *__sign, char *__buf, size_t __len)
    int fcvt_r(double __value, int __ndigit, int *__decpt, int *__sign, char *__buf, size_t __len)
    int qecvt_r(long double __value, int __ndigit, int *__decpt, int *__sign, char *__buf, size_t __len)
    int qfcvt_r(long double __value, int __ndigit, int *__decpt, int *__sign, char *__buf, size_t __len)
    int mblen(const char* __s, size_t __n)
    int mbtowc(wchar_t *__pwc, const char *__s, size_t __n)
    int wctomb(char* __s, wchar_t __wchar)
    size_t mbstowcs(wchar_t *__pwcs, const char *__s, size_t __n)
    size_t wcstombs(char *__s, const wchar_t *__pwcs, size_t __n)
    int rpmatch(const char* __response)
    int getsubopt(char **__optionp, char *const *__tokens, char **__valuep)
    int getloadavg(double __loadavg[], int __nelem)


