#include <string>
#include <vector>

#define CPP_FOO 5
#define CPP_BAR 5.0F
#define CPP_FUNC(x) other_func(x, 5)

namespace Foo {
    template <typename T>
    class A {
        public:
        // Constructor
        A(T t);

        // Constructor with template
        template <typename U>
        A(U u);

        // static method
        static void static_method(long *p);

        // instance method test, size_t no-import
        int instance_method(size_t a);

        // function pointer decl
        void (*fptrfield)(int);

        // Basic c++ decl
        std::string s;

        // Template decl
        std::vector<std::string> vs;

        // Pointer decl
        int *ip;

        // Plain field decl
        long l;

        // LVR decl + template type
        T& t;

        // RVR decl
        T&& tt;
        
        // bool renames to bint
        bool truefalse;

        // Inner class decl
        class Inner {
            public:
            void* data;
        };

        // Private decl
        private:
        int hidden;
    };

    // typedef decl
    typedef int TypedefInt;
    typedef size_t& SizedRef;

    // typedef a function pointer
    typedef void (*Action)(void *data);

    // extern var
    extern std::string a_static_string;

    // struct decl
    struct B {
        // inner typedef
        typedef std::vector<int> Dataset;
        // plain field
        double a;
        // reference a local typedef
        Dataset local_dataset;
        // try to break pxdgen
        int (**foobar)(std::vector<std::vector<const char*>>);
    };

    typedef struct {
        // Reference something in the same namespace
        struct B a;
        // Reference something in different namespace, but same file in output
        B::Dataset data;
    } C;

    // enum decl
    typedef enum {
        FOO = 10,
        BAR = 1,
        BAZ
    } D;

    // union decl
    typedef union {
        void *somedata;
        std::vector<char*> veccc;
        A<int>::Inner inner_inst;
    } E;

    // function decl
    int a_function(int i, long l);

    // forward decl
    struct forward_decl;
}

// Another namespace, goes into another package
namespace Bar {

    typedef int BarInt;

    // Inner namepace, still a different file
    namespace Baz {
        // should get imported
        typedef BarInt BazInt;
        // should import Foo.B as Foo_B and reference Dataset as Foo_B.Dataset
        Foo::B::Dataset get_dataset();
    }

    class A {
        public:
        // should get imported
        Foo::D foo_d_enum;
    };
}
