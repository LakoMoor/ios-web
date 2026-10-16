#!/usr/bin/env python3
"""Apply explicit, guarded changes to the pinned upstream checkout."""
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
project = Path(__file__).resolve().parent.parent

def replace(path, old, new):
    p = source / path
    text = p.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Upstream changed: {path}: expected patch anchor missing")
    p.write_text(text.replace(old, new, 1))

replace('qapi/ui.json', "{ 'name': 'none' },", "{ 'name': 'none' },\n    { 'name': 'browser' },")
replace('ui/meson.build', 'system_ss.add(pixman)', "if host_os == 'emscripten'\n  system_ss.add(files('browser-display.c', 'browser-swap.c'))\nendif\nsystem_ss.add(pixman)")
shutil.copyfile(project / 'build/browser-display.c', source / 'ui/browser-display.c')
replace('util/qemu-timer.c', '#include "qemu/osdep.h"', '#include "qemu/osdep.h"\n#ifdef __EMSCRIPTEN__\n#include <emscripten.h>\n#include <emscripten/threading.h>\n#endif')
replace('util/qemu-timer.c', 'int qemu_poll_ns(GPollFD *fds, guint nfds, int64_t timeout)\n{', '''int qemu_poll_ns(GPollFD *fds, guint nfds, int64_t timeout)
{
#ifdef __EMSCRIPTEN__
    /* Yield the hosting Worker so file/input/control messages are delivered.
     * Called with BQL released, allowing the vCPU pthread to progress. */
    if (emscripten_is_main_runtime_thread()) {
        emscripten_sleep(timeout == 0 ? 0 : 1);
        return g_poll(fds, nfds, 0);
    }
#endif''')
# The module runs in a dedicated Worker, where WORKERFS has FileReaderSync.
# Do not proxy its main() to a browser-main pthread (that breaks WORKERFS).
(source / 'configs/meson/emscripten.txt').write_text('''[built-in options]
c_args = ['-pthread']
cpp_args = ['-pthread']
c_link_args = ['-pthread', '-sASYNCIFY=1', '-sASYNCIFY_IMPORTS=ffi_call_js', '-sFORCE_FILESYSTEM=1', '-lworkerfs.js', '-sALLOW_TABLE_GROWTH=1', '-sALLOW_MEMORY_GROWTH=1', '-sINITIAL_MEMORY=268435456', '-sMAXIMUM_MEMORY=4294967296', '-sSTACK_SIZE=2097152', '-sASYNCIFY_STACK_SIZE=1048576', '-sPTHREAD_POOL_SIZE=8', '-sWASM_BIGINT=1', '-sEXPORT_ES6=1', '-sMODULARIZE=1', '-sEXPORT_NAME=createInferno', '-sENVIRONMENT=worker,node', '-sEXPORTED_RUNTIME_METHODS=FS,WORKERFS,callMain', '-sEXPORTED_FUNCTIONS=_main,_web_pointer,_web_control']
''')
(source / 'configs/devices/aarch64-softmmu/browser.mak').write_text('CONFIG_ARM_VIRT=y\nCONFIG_APPLE_SOC=y\nCONFIG_RAMFB=y\n')
shutil.copyfile(project / 'build/browser-swap.c', source / 'ui/browser-swap.c')
shutil.copyfile(project / 'build/browser-swap.h', source / 'include/system/browser-swap.h')
replace('ui/meson.build', "system_ss.add(files('browser-display.c'))", "system_ss.add(files('browser-display.c', 'browser-swap.c'))")
replace('hw/core/machine.c', '#include "qemu/osdep.h"', '#include "qemu/osdep.h"\n#ifdef __EMSCRIPTEN__\n#include "system/browser-swap.h"\n#endif')
replace('hw/core/machine.c', 'if (machine->ram_size > (2047 << 20) && HOST_LONG_BITS == 32)', '''if (machine->ram_size > (2047 << 20) && HOST_LONG_BITS == 32
#ifdef __EMSCRIPTEN__
            && !web_swap_enabled()
#endif
        )''')
replace('hw/core/machine.c', '    if (machine->memdev) {\n        ram_addr_t backend_size', '''#ifdef __EMSCRIPTEN__
    if (web_swap_enabled()) {
        machine->ram = g_new0(MemoryRegion, 1);
        web_swap_ram_init(machine->ram, OBJECT(machine), machine->ram_size);
    }
#endif
    if (machine->memdev) {
        ram_addr_t backend_size''')
replace('hw/core/machine.c', '} else if (machine_class->default_ram_id && machine->ram_size &&', '} else if (!machine->ram && machine_class->default_ram_id && machine->ram_size &&')
replace('hw/display/apple_displaypipe_v4.c', '#include "qemu/osdep.h"', '#include "qemu/osdep.h"\n#ifdef __EMSCRIPTEN__\n#include "system/browser-swap.h"\n#endif')
replace('hw/display/apple_displaypipe_v4.c', '    snap = memory_region_snapshot_and_clear_dirty(', '''#ifdef __EMSCRIPTEN__
    if (web_swap_enabled()) {
        dpy_gfx_update_full(adp->console);
        qatomic_or(&adp->int_status, R_CONTROL_INT_OUTPUT_READY_MASK);
        adp_v4_update_irqs(adp);
        return;
    }
#endif
    snap = memory_region_snapshot_and_clear_dirty(''')
replace('hw/display/apple_displaypipe_v4.c', '    return memory_region_get_ram_ptr(adp->vram_mr) + adp->vram_off +', '''#ifdef __EMSCRIPTEN__
    if (web_swap_enabled()) {
        return web_swap_pin_framebuffer(adp->vram_off + adp->fb_off,
                                       adp->height * adp->width * sizeof(uint32_t));
    }
#endif
    return memory_region_get_ram_ptr(adp->vram_mr) + adp->vram_off +''')
config = source / 'configs/meson/emscripten.txt'
config.write_text(config.read_text().replace('_web_control\'', '_web_control,_web_swap_mailbox,_web_swap_buffer,_web_swap_config,_web_swap_prepare,_web_swap_selftest,_web_swap_faults,_web_swap_evictions\''))
replace('hw/core/loader.c', '#include "qemu/osdep.h"', '#include "qemu/osdep.h"\n#ifdef __EMSCRIPTEN__\n#include "system/browser-swap.h"\n#endif')
replace('hw/core/loader.c', '''            address_space_write_rom(rom->as, rom->addr, MEMTXATTRS_UNSPECIFIED,
                                    rom->data, rom->datasize);''', '''#ifdef __EMSCRIPTEN__
            MemoryRegionSection section = memory_region_find(
                rom->as->root, rom->addr, 1);
            if (web_swap_is_region(section.mr)) {
                address_space_write(rom->as, rom->addr, MEMTXATTRS_UNSPECIFIED,
                                    rom->data, rom->datasize);
            } else
#endif
            {
                address_space_write_rom(rom->as, rom->addr, MEMTXATTRS_UNSPECIFIED,
                                        rom->data, rom->datasize);
            }
#ifdef __EMSCRIPTEN__
            memory_region_unref(section.mr);
#endif''')
