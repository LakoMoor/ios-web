/* SPDX-License-Identifier: AGPL-3.0-only */
#include "qemu/osdep.h"
#include "qemu/module.h"
#include "ui/console.h"
#include "ui/input.h"
#include "system/runstate.h"
#include <emscripten.h>

static DisplayChangeListener listener;
static DisplaySurface *surface;
static pixman_image_t *rgba;
static bool dirty;
static int pending_action;
static int pointer_x, pointer_y, pointer_down, pointer_pending;

EMSCRIPTEN_KEEPALIVE void web_pointer(int x, int y, int down)
{
    pointer_x = x; pointer_y = y; pointer_down = down; pointer_pending = 1;
}
EMSCRIPTEN_KEEPALIVE void web_control(int action) { pending_action = action; }

static void browser_refresh(DisplayChangeListener *dcl)
{
    if (pending_action == 1) {
        vm_stop(RUN_STATE_PAUSED);
        EM_ASM({ postMessage({type: 'paused', paused: true}); });
    }
    if (pending_action == 2) {
        vm_start();
        EM_ASM({ postMessage({type: 'paused', paused: false}); });
    }
    if (pending_action == 3) { qemu_system_shutdown_request(SHUTDOWN_CAUSE_HOST_UI); }
    pending_action = 0;
    if (pointer_pending) {
        qemu_input_queue_abs(dcl->con, INPUT_AXIS_X, pointer_x, 0, 32767);
        qemu_input_queue_abs(dcl->con, INPUT_AXIS_Y, pointer_y, 0, 32767);
        qemu_input_queue_btn(dcl->con, INPUT_BUTTON_LEFT, pointer_down);
        qemu_input_event_sync();
        pointer_pending = 0;
    }
    graphic_hw_update(dcl->con);
    if (!dirty || !surface || !rgba) { return; }
    int w = surface_width(surface), h = surface_height(surface);
    pixman_image_composite32(PIXMAN_OP_SRC, surface->image, NULL, rgba,
                            0, 0, 0, 0, 0, 0, w, h);
    uint8_t *data = (uint8_t *)pixman_image_get_data(rgba);
    EM_ASM({
        const offset = $0 >>> 0;
        const buffer = HEAPU8.slice(offset, offset + $1 * $2 * 4).buffer;
        postMessage({type: 'frame', width: $1, height: $2, buffer}, [buffer]);
    }, data, w, h);
    dirty = false;
}
static void browser_update(DisplayChangeListener *dcl, int x, int y, int w, int h)
{ dirty = true; }
static void browser_switch(DisplayChangeListener *dcl, DisplaySurface *s)
{
    surface = s;
    if (rgba) { pixman_image_unref(rgba); }
    rgba = pixman_image_create_bits(PIXMAN_a8b8g8r8, surface_width(s),
                                   surface_height(s), NULL, 0);
    dirty = true;
}
static const DisplayChangeListenerOps browser_ops = {
    .dpy_name = "browser",
    .dpy_refresh = browser_refresh,
    .dpy_gfx_update = browser_update,
    .dpy_gfx_switch = browser_switch,
};
static void browser_init(DisplayState *ds, DisplayOptions *opts)
{
    listener.ops = &browser_ops;
    listener.con = qemu_console_lookup_by_index(0);
    listener.update_interval = 33;
    register_displaychangelistener(&listener);
    EM_ASM({ postMessage({type: 'display-ready'}); });
}
static QemuDisplay browser_display = {
    .type = DISPLAY_TYPE_BROWSER,
    .init = browser_init,
};
static void register_browser(void) { qemu_display_register(&browser_display); }
type_init(register_browser);
