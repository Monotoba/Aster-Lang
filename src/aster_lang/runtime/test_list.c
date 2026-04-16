#include "aster_runtime.h"

int main() {
    AsterValue list = aster_list_new();
    aster_list_append(list, aster_int(10));
    aster_list_append(list, aster_int(20));
    
    printf("List length: %zu\n", aster_list_len(list));
    printf("Index 0: ");
    aster_print(aster_list_get(list, aster_int(0)));
    printf("Index 1: ");
    aster_print(aster_list_get(list, aster_int(1)));
    
    return 0;
}
