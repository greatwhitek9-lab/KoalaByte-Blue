#ifndef KOALABYTE_T114_LOADING_DISPLAY_H
#define KOALABYTE_T114_LOADING_DISPLAY_H

#include <stdbool.h>

bool loading_display_init(void);
bool loading_display_ready(void);
void render_loading_banner(const char *banner);
void loading_display_end(void);

#endif
