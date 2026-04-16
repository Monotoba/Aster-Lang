#include "aster_runtime.h"

int main() {
    AsterValue hello = aster_string("Hello from Aster Runtime!");
    aster_print(hello);

    AsterValue a = aster_int(10);
    AsterValue b = aster_int(32);
    AsterValue c = aster_add(a, b);
    
    printf("10 + 32 = ");
    aster_print(c);

    return 0;
}
