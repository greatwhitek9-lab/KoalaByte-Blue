#include <zephyr/kernel.h>
#include <zephyr/sys/util.h>

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "loading_display.h"

#define KOALA_ERROR_ALARM_FRAME_MS 180

static K_MUTEX_DEFINE(error_alarm_render_mutex);
static bool error_alarm_active;
static bool error_alarm_banner_phase;
static char error_alarm_message[96] = "ERROR";
static uint8_t error_alarm_from_frame;
static uint8_t error_alarm_to_frame;
static uint8_t error_alarm_blend;

void __real_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount);

static void render_error_alarm_phase_locked(void)
{
    if (error_alarm_banner_phase) {
        /* The status renderer provides the bright green ERROR phase. The
         * alternate real error-mouth frame retains its purple/lime lighting. */
        render_menu_status("ERROR");
    } else {
        __real_render_killerkoala_mouth(
            "error", error_alarm_message,
            error_alarm_from_frame, error_alarm_to_frame,
            error_alarm_blend);
    }
}

static void error_alarm_work_handler(struct k_work *work);
K_WORK_DELAYABLE_DEFINE(error_alarm_work, error_alarm_work_handler);

static void error_alarm_work_handler(struct k_work *work)
{
    ARG_UNUSED(work);

    k_mutex_lock(&error_alarm_render_mutex, K_FOREVER);
    if (!error_alarm_active) {
        k_mutex_unlock(&error_alarm_render_mutex);
        return;
    }
    error_alarm_banner_phase = !error_alarm_banner_phase;
    render_error_alarm_phase_locked();
    k_mutex_unlock(&error_alarm_render_mutex);

    (void)k_work_reschedule(&error_alarm_work,
                            K_MSEC(KOALA_ERROR_ALARM_FRAME_MS));
}

void __wrap_render_killerkoala_mouth(const char *state, const char *message,
                                     uint8_t from_frame_index,
                                     uint8_t to_frame_index,
                                     uint8_t blend_amount)
{
    bool is_error = state && strcmp(state, "error") == 0;
    bool start_alarm = false;

    k_mutex_lock(&error_alarm_render_mutex, K_FOREVER);
    if (is_error) {
        start_alarm = !error_alarm_active;
        error_alarm_active = true;
        error_alarm_from_frame = from_frame_index;
        error_alarm_to_frame = to_frame_index;
        error_alarm_blend = blend_amount;
        snprintf(error_alarm_message, sizeof(error_alarm_message), "%s",
                 message && message[0] ? message : "ERROR");

        /* Keep whichever phase the alarm worker selected. Normal 55 ms mouth
         * updates refresh the active phase but never postpone the 180 ms timer. */
        render_error_alarm_phase_locked();
    } else {
        error_alarm_active = false;
        error_alarm_banner_phase = false;
        (void)k_work_cancel_delayable(&error_alarm_work);
        __real_render_killerkoala_mouth(
            state, message, from_frame_index,
            to_frame_index, blend_amount);
    }
    k_mutex_unlock(&error_alarm_render_mutex);

    if (start_alarm) {
        (void)k_work_reschedule(&error_alarm_work,
                                K_MSEC(KOALA_ERROR_ALARM_FRAME_MS));
    }
}
