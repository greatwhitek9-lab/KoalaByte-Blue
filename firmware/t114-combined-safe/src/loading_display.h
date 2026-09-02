#ifndef KOALABYTE_T114_LOADING_DISPLAY_H
#define KOALABYTE_T114_LOADING_DISPLAY_H

#include <stdbool.h>
#include <stdint.h>

bool loading_display_init(void);
bool loading_display_ready(void);
void render_killerkoala_boot_splash(void);
void render_koalagotchi_action(const char *action_title, uint8_t frame_index);
void render_loading_banner(const char *banner);
void render_killerkoala_mouth(const char *state, const char *message,
                              uint8_t from_frame_index,
                              uint8_t to_frame_index,
                              uint8_t blend_amount);
void render_menu_status(const char *message);

/* Canonical centered Koalagotchi HUD state. */
void koala_centered_set_status(int health, const char *mood,
                               const char *expression);
void koala_centered_set_action_progress(int progress_percent);

void loading_display_end(void);

#endif
