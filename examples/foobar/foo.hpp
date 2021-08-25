#include <stdio.h>
#include <string>
#include <vector>

namespace Turbo
{
	class Foo
	{
		int a;
		int b;
		
		public:
		float c;
		long d;
		
		static int getStaticInt(std::string s, std::vector v);
		float getNSFloat(FILE *f);
	}
}