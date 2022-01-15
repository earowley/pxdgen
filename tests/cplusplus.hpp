#include <string>
#include <vector>

namespace Foo {
    template <typename T>
    class A {
        public:
        static void static_method();
        int instance_method(size_t a);

        std::string s;
        std::vector<std::string> vs;
        int *ip;
        T& t;
        T&& tt;

        // Todo
        class Inner {
            void* data;
        };

        private:
        int hidden;
    };

    typedef size_t& Sized;
    typedef void (*Action)(void *data);

    std::string& a_static_string;

    struct B {
        typedef std::vector<int> Dataset;
        double a;
        int (**foobar)(std::vector<std::vector<const char*>>);
    };

    typedef struct {
        struct B a;
        float f;
        B::Dataset data;
    } C;

    typedef enum {
        FOO = 10,
        BAR = 1,
        BAZ
    } Fooey;

    typedef union {
        void *somedata;
        std::vector<char*> veccc;
    } Uni;

    int a_function(int i, long l);

    struct forward_decl;
}
