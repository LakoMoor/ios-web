#!/usr/bin/env python3
"""Apply explicit, guarded changes to the pinned upstream checkout."""
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
project = Path(__file__).resolve().parent.parent

def write(path, content):
    p = source / path
    if not p.exists() or p.read_text() != content:
        p.write_text(content)

def replace(path, old, new):
    p = source / path
    text = p.read_text()
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Upstream changed: {path}: expected patch anchor missing")
    p.write_text(text.replace(old, new, 1))

replace('qapi/ui.json', "{ 'name': 'none' },", "{ 'name': 'none' },\n    { 'name': 'browser' },")
replace('qapi/ui.json', '# @gtk: The GTK user interface.', '# @browser: Web Worker RGBA display for the browser WASM port.\n#\n# @gtk: The GTK user interface.')
replace('util/oslib-posix.c', '    char *pid_path;\n    size_t len;', '    char *pid_path;\n    gsize len;')
replace('hw/ssi/apple_spi.c', 'spi->iomem.size == 0', 'int128_eq(spi->iomem.size, int128_zero())')
replace('hw/usb/dev-tcp-remote.h', '    uint64_t handled;', '    uint32_t handled;')
replace('include/exec/vaddr.h', '''typedef uintptr_t vaddr;
#define VADDR_PRId PRIdPTR
#define VADDR_PRIu PRIuPTR
#define VADDR_PRIo PRIoPTR
#define VADDR_PRIx PRIxPTR
#define VADDR_PRIX PRIXPTR
#define VADDR_MAX UINTPTR_MAX''', '''#ifdef __EMSCRIPTEN__
typedef uint64_t vaddr;
#define VADDR_PRId PRId64
#define VADDR_PRIu PRIu64
#define VADDR_PRIo PRIo64
#define VADDR_PRIx PRIx64
#define VADDR_PRIX PRIX64
#define VADDR_MAX UINT64_MAX
#else
typedef uintptr_t vaddr;
#define VADDR_PRId PRIdPTR
#define VADDR_PRIu PRIuPTR
#define VADDR_PRIo PRIoPTR
#define VADDR_PRIx PRIxPTR
#define VADDR_PRIX PRIXPTR
#define VADDR_MAX UINTPTR_MAX
#endif''')
replace('include/exec/helper-head.h.inc', '#if __SIZEOF_POINTER__ == 4\n# define dh_alias_vaddr i32',
        '#if defined(__EMSCRIPTEN__)\n# define dh_alias_vaddr i64\n# define dh_typecode_vaddr dh_typecode_i64\n#elif __SIZEOF_POINTER__ == 4\n# define dh_alias_vaddr i32')
replace('include/exec/helper-head.h.inc', '# define dh_ctype_vaddr uintptr_t',
        '#ifdef __EMSCRIPTEN__\n# define dh_ctype_vaddr uint64_t\n#else\n# define dh_ctype_vaddr uintptr_t\n#endif')
replace('include/qemu/atomic.h', '#define ATOMIC_REG_SIZE  sizeof(void *)',
        '''#if defined(__EMSCRIPTEN__) && defined(__wasm_atomics__)
_Static_assert(__atomic_always_lock_free(8, 0), "WASM requires native i64 atomics");
#define ATOMIC_REG_SIZE 8
#else
#define ATOMIC_REG_SIZE sizeof(void *)
#endif''')
# wasm32 pointers remain 32-bit, but the TCI virtual registers must hold
# complete ARM64 guest addresses. i64 arithmetic is native to WebAssembly.
replace('tcg/tci/tcg-target-reg-bits.h', '#if UINTPTR_MAX == UINT32_MAX',
        '#if defined(__EMSCRIPTEN__)\n# define TCG_TARGET_REG_BITS 64\n#elif UINTPTR_MAX == UINT32_MAX')
replace('tcg/tci.c', 'func = ((void **)ptr)[0];\n                cif = ((void **)ptr)[1];',
        'func = (void *)(uintptr_t)((tcg_target_ulong *)ptr)[0];\n                cif = (ffi_cif *)(uintptr_t)((tcg_target_ulong *)ptr)[1];')
# Inferno removed BFD and its disassembler infrastructure, but left this
# unused TCI disassembler behind. Keep the interpreter, omit the orphan.
p = source / 'tcg/tci.c'
s = p.read_text()
marker = '/*\n * Disassembler that matches the interpreter\n */'
if marker in s:
    p.write_text(s.split(marker, 1)[0])
replace('include/tcg/tcg.h', '#if __SIZEOF_POINTER__ == 4\ntypedef TCGv_i32 TCGv_vaddr;',
        '#if defined(__EMSCRIPTEN__)\ntypedef TCGv_i64 TCGv_vaddr;\n#elif __SIZEOF_POINTER__ == 4\ntypedef TCGv_i32 TCGv_vaddr;')
replace('include/tcg/tcg-op-common.h', 'TCGv_vaddr tcg_constant_vaddr(uintptr_t val);',
        'TCGv_vaddr tcg_constant_vaddr(uint64_t val);')
replace('tcg/tcg.c', '''TCGv_vaddr tcg_constant_vaddr(uintptr_t val)
{
    return temp_tcgv_vaddr(tcg_constant_internal(TCG_TYPE_PTR, val));
}''', '''TCGv_vaddr tcg_constant_vaddr(uint64_t val)
{
#ifdef __EMSCRIPTEN__
    return temp_tcgv_vaddr(tcg_constant_internal(TCG_TYPE_I64, val));
#else
    return temp_tcgv_vaddr(tcg_constant_internal(TCG_TYPE_PTR, val));
#endif
}''')
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
write('configs/meson/emscripten.txt', '''[built-in options]
c_args = ['-O2', '-pthread', '-matomics', '-mbulk-memory', '-I/opt/wasm/include']
cpp_args = ['-O2', '-pthread', '-matomics', '-mbulk-memory', '-I/opt/wasm/include']
c_link_args = ['-O2', '-L/opt/wasm/lib', '-pthread', '-sASYNCIFY=1', '-sASYNCIFY_IMPORTS=ffi_call_js', '-sFORCE_FILESYSTEM=1', '-lworkerfs.js', '-sALLOW_TABLE_GROWTH=1', '-sALLOW_MEMORY_GROWTH=1', '-sINITIAL_MEMORY=268435456', '-sMAXIMUM_MEMORY=4294967296', '-sSTACK_SIZE=2097152', '-sASYNCIFY_STACK_SIZE=1048576', '-sPTHREAD_POOL_SIZE=8', '-sWASM_BIGINT=1', '-sEXPORT_ES6=1', '-sMODULARIZE=1', '-sEXPORT_NAME=createInferno', '-sENVIRONMENT=worker,node', '-sEXPORTED_RUNTIME_METHODS=FS,WORKERFS,callMain']
''')
write('configs/devices/aarch64-softmmu/browser.mak', 'CONFIG_ARM_VIRT=y\nCONFIG_APPLE_SOC=y\nCONFIG_NVME_PCI=y\n')
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
replace('meson.build', 'host_os = host_machine.system()', """host_os = host_machine.system()
if host_os == 'emscripten'
  add_project_link_arguments('-sEXPORTED_FUNCTIONS=_main,_web_pointer,_web_control,_web_swap_mailbox,_web_swap_buffer,_web_swap_config,_web_swap_prepare,_web_swap_selftest,_web_swap_faults,_web_swap_evictions', language: 'c')
endif""")
replace('meson.build',
        "if host_long_bits < config_target['TARGET_LONG_BITS'].to_int()",
        "if host_long_bits < config_target['TARGET_LONG_BITS'].to_int() and \\\n        not (host_os == 'emscripten' and sym == 'CONFIG_TCG')")
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
