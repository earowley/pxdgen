#  PXDGEN AUTO-DEFINED TYPES
cdef extern from *:
    ctypedef struct __locale_data:
        pass


cdef extern from "time.h":
    ctypedef unsigned long size_t
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
    ctypedef __clock_t clock_t
    ctypedef __time_t time_t
    struct tm:
        int tm_sec
        int tm_min
        int tm_hour
        int tm_mday
        int tm_mon
        int tm_year
        int tm_wday
        int tm_yday
        int tm_isdst
        long tm_gmtoff
        const char* tm_zone
    struct timespec:
        __time_t tv_sec
        __syscall_slong_t tv_nsec
    ctypedef __clockid_t clockid_t
    ctypedef __timer_t timer_t
    struct itimerspec:
        timespec it_interval
        timespec it_value
    struct sigevent:
        pass
    ctypedef __pid_t pid_t
    struct __locale_struct:
        __locale_data* __locales[13]
        const unsigned short* __ctype_b
        const int* __ctype_tolower
        const int* __ctype_toupper
        const char* __names[13]
    ctypedef __locale_struct* __locale_t
    ctypedef __locale_t locale_t
    clock_t clock()
    time_t time(time_t* __timer)
    double difftime(time_t __time1, time_t __time0)
    time_t mktime(tm* __tp)
    size_t strftime(char *__s, size_t __maxsize, const char *__format, const tm *__tp)
    size_t strftime_l(char *__s, size_t __maxsize, const char *__format, const tm *__tp, locale_t __loc)
    tm* gmtime(const time_t* __timer)
    tm* localtime(const time_t* __timer)
    tm* gmtime_r(const time_t *__timer, tm *__tp)
    tm* localtime_r(const time_t *__timer, tm *__tp)
    char* asctime(const tm* __tp)
    char* ctime(const time_t* __timer)
    char* asctime_r(const tm *__tp, char *__buf)
    char* ctime_r(const time_t *__timer, char *__buf)
    char* __tzname[2]
    int __daylight
    long __timezone
    char* tzname[2]
    void tzset()
    int daylight
    long timezone
    time_t timegm(tm* __tp)
    time_t timelocal(tm* __tp)
    int dysize(int __year)
    int nanosleep(const timespec* __requested_time, timespec* __remaining)
    int clock_getres(clockid_t __clock_id, timespec* __res)
    int clock_gettime(clockid_t __clock_id, timespec* __tp)
    int clock_settime(clockid_t __clock_id, const timespec* __tp)
    int clock_nanosleep(clockid_t __clock_id, int __flags, const timespec* __req, timespec* __rem)
    int clock_getcpuclockid(pid_t __pid, clockid_t* __clock_id)
    int timer_create(clockid_t __clock_id, sigevent *__evp, timer_t *__timerid)
    int timer_delete(timer_t __timerid)
    int timer_settime(timer_t __timerid, int __flags, const itimerspec *__value, itimerspec *__ovalue)
    int timer_gettime(timer_t __timerid, itimerspec* __value)
    int timer_getoverrun(timer_t __timerid)
    int timespec_get(timespec* __ts, int __base)


