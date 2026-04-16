
#include "aster_runtime.h"

AsterValue __lambda1(AsterValue x);
AsterValue aster_main(void);

AsterValue __lambda1(AsterValue x) {
    return aster_add(x, aster_int(10));
}

AsterValue aster_main(void) {
    AsterValue (*adder)(AsterValue) = __lambda1;
    aster_print(adder(aster_int(5)));
    return ASTER_NIL_VAL;
}

int main(void) {
    aster_main();
    return 0;
}
