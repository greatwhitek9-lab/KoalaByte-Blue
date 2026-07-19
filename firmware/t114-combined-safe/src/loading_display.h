#ifndef KOALABYTE_T114_LOADING_DISPLAY_H
#define KOALABYTE_T114_LOADING_DISPLAY_H

#include <stdbool.h>

bool loading_display_init(void);
bool loading_display_ready(void);
void render_loading_banner(const char *banner);
void render_killerkoala_mouth(const char *state, const char *message,
                              bool mouth_open);
void render_menu_status(const char *message);
void loading_display_end(void);

#endif
