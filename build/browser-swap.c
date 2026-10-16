/* SPDX-License-Identifier: AGPL-3.0-only
 * Conservative paged RAM via QEMU's MMIO slow path. This deliberately does
 * not expose movable page pointers to the TLB, translator, DMA or display.
 * Execution from this memory uses QEMU's existing one-shot instruction TBs.
 * It trades speed for a bounded, correct RAM footprint and a 64-bit guest
 * physical address space independently of the 32-bit host pointer range.
 */
#include "qemu/osdep.h"
#include "qemu/error-report.h"
#include "qemu/thread.h"
#include "qemu/units.h"
#include "system/browser-swap.h"
#include <emscripten.h>
#include <emscripten/threading.h>
#include <stdatomic.h>
#define PAGE_SHIFT 16
#define PAGE_SIZE (1u << PAGE_SHIFT)
static _Atomic int32_t mailbox[8];
static uint8_t transfer_page[PAGE_SIZE];
static unsigned budget_mb, guest_pages, slots_count;
static int *page_map, lru_head = -1, lru_tail = -1;
static uint8_t *cache;
static QemuMutex cache_lock;
typedef struct Slot { unsigned page; int prev, next; bool valid, dirty; } Slot;
static Slot *slots;
static uint64_t misses, evictions;
static uint64_t pinned_begin;
static size_t pinned_len;
static uint8_t *pinned_data;
EM_JS(void, web_swap_prepare_js, (void), { Module.webSwapMemory = HEAPU8.buffer; });
EMSCRIPTEN_KEEPALIVE void web_swap_prepare(void) { web_swap_prepare_js(); }
EMSCRIPTEN_KEEPALIVE uintptr_t web_swap_mailbox(void) { return (uintptr_t)mailbox; }
EMSCRIPTEN_KEEPALIVE uintptr_t web_swap_buffer(void) { return (uintptr_t)transfer_page; }
EMSCRIPTEN_KEEPALIVE void web_swap_config(unsigned mb) { budget_mb = mb; }
EMSCRIPTEN_KEEPALIVE unsigned web_swap_faults(void) { return misses; }
EMSCRIPTEN_KEEPALIVE unsigned web_swap_evictions(void) { return evictions; }
bool web_swap_enabled(void) { return budget_mb != 0; }
static void disk_io(int op, unsigned page)
{
    atomic_store(&mailbox[1], page);
    atomic_store(&mailbox[2], 0);
    atomic_store_explicit(&mailbox[0], op, memory_order_release);
    emscripten_futex_wake((void *)&mailbox[0], INT_MAX);
    while (atomic_load_explicit(&mailbox[0], memory_order_acquire)) {
        int result = emscripten_futex_wait((void *)&mailbox[0], op, 60000);
        if (result == -ETIMEDOUT) {
            error_report("Browser swap timed out after 60 seconds");
            abort();
        }
    }
    if (atomic_load(&mailbox[2])) {
        error_report("Browser swap I/O failed (quota, permissions or storage error)");
        abort();
    }
}
static void touch(int index)
{
    Slot *slot = &slots[index];
    if (lru_head == index) return;
    if (slot->prev >= 0) slots[slot->prev].next = slot->next;
    if (slot->next >= 0) slots[slot->next].prev = slot->prev;
    if (lru_tail == index) lru_tail = slot->prev;
    slot->prev = -1; slot->next = lru_head;
    if (lru_head >= 0) slots[lru_head].prev = index;
    lru_head = index;
    if (lru_tail < 0) lru_tail = index;
}
static uint8_t *resolve(unsigned page)
{
    int index = page_map[page];
    if (index < 0) {
        misses++;
        index = lru_tail;
        Slot *slot = &slots[index];
        if (slot->valid) {
            if (slot->dirty) {
                memcpy(transfer_page, cache + (size_t)index * PAGE_SIZE, PAGE_SIZE);
                disk_io(2, slot->page);
            }
            page_map[slot->page] = -1;
            evictions++;
        }
        disk_io(1, page);
        memcpy(cache + (size_t)index * PAGE_SIZE, transfer_page, PAGE_SIZE);
        slot->page = page; slot->valid = true; slot->dirty = false;
        page_map[page] = index;
    }
    touch(index);
    return cache + (size_t)index * PAGE_SIZE;
}
static void access_bytes(uint64_t addr, void *buffer, size_t len, bool write)
{
    uint8_t *p = buffer;
    qemu_mutex_lock(&cache_lock);
    while (len) {
        if (pinned_len && addr >= pinned_begin && addr < pinned_begin + pinned_len) {
            size_t n = MIN(len, pinned_begin + pinned_len - addr);
            if (write) memcpy(pinned_data + addr - pinned_begin, p, n);
            else memcpy(p, pinned_data + addr - pinned_begin, n);
            p += n; addr += n; len -= n;
            continue;
        }
        unsigned page = addr >> PAGE_SHIFT, offset = addr & (PAGE_SIZE - 1);
        size_t n = MIN(len, PAGE_SIZE - offset);
        if (pinned_len && addr < pinned_begin) n = MIN(n, pinned_begin - addr);
        if (page >= guest_pages) { error_report("Browser swap access outside guest RAM"); abort(); }
        uint8_t *resident = resolve(page);
        if (write) { memcpy(resident + offset, p, n); slots[page_map[page]].dirty = true; }
        else memcpy(p, resident + offset, n);
        p += n; addr += n; len -= n;
    }
    qemu_mutex_unlock(&cache_lock);
}
void web_swap_copy_out(uint64_t offset, void *dest, size_t len) { access_bytes(offset, dest, len, false); }
void *web_swap_pin_framebuffer(uint64_t offset, size_t len)
{
    if (pinned_len == len && pinned_begin == offset) return pinned_data;
    if (pinned_len) {
        size_t old_len = pinned_len; pinned_len = 0;
        access_bytes(pinned_begin, pinned_data, old_len, true);
    }
    uint8_t *fresh = g_malloc(len);
    access_bytes(offset, fresh, len, false);
    g_free(pinned_data);
    pinned_data = fresh; pinned_begin = offset; pinned_len = len;
    return pinned_data;
}
static uint64_t swap_read(void *opaque, hwaddr addr, unsigned size)
{
    uint64_t value = 0; access_bytes(addr, &value, size, false); return value;
}
static void swap_write(void *opaque, hwaddr addr, uint64_t value, unsigned size)
{ access_bytes(addr, &value, size, true); }
static const MemoryRegionOps ops = {
    .read = swap_read, .write = swap_write, .endianness = DEVICE_LITTLE_ENDIAN,
    .valid = { .min_access_size = 1, .max_access_size = 8, .unaligned = true },
    .impl = { .min_access_size = 1, .max_access_size = 8, .unaligned = true },
};
bool web_swap_is_region(MemoryRegion *mr) { return mr && mr->ops == &ops; }
static void cache_init(uint64_t size)
{
    guest_pages = (size + PAGE_SIZE - 1) >> PAGE_SHIFT;
    slots_count = MIN((uint64_t)budget_mb * 16, guest_pages);
    cache = g_malloc0((size_t)slots_count * PAGE_SIZE);
    slots = g_new0(Slot, slots_count);
    page_map = g_new(int, guest_pages);
    for (unsigned p = 0; p < guest_pages; p++) page_map[p] = -1;
    for (unsigned i = 0; i < slots_count; i++) { slots[i].prev = i ? (int)i-1 : -1; slots[i].next = i+1 < slots_count ? (int)i+1 : -1; }
    lru_head = 0; lru_tail = slots_count - 1;
    qemu_mutex_init(&cache_lock);
}
EMSCRIPTEN_KEEPALIVE int web_swap_selftest(void)
{
    /* Force several complete cache turnovers, then verify every cold page. */
    unsigned saved_budget = budget_mb;
    budget_mb = 4;
    cache_init(16 * MiB);
    for (unsigned page = 0; page < guest_pages; page++) {
        uint64_t marker = UINT64_C(0x1234567800000000) | page;
        access_bytes((uint64_t)page * PAGE_SIZE + 101, &marker, 8, true);
    }
    int success = 1;
    for (unsigned page = 0; page < guest_pages; page++) {
        uint64_t value;
        access_bytes((uint64_t)page * PAGE_SIZE + 101, &value, 8, false);
        if (value != (UINT64_C(0x1234567800000000) | page)) success = 0;
    }
    uint64_t crossing = UINT64_C(0x8877665544332211), value;
    access_bytes(PAGE_SIZE - 3, &crossing, 8, true);
    access_bytes(PAGE_SIZE - 3, &value, 8, false);
    success &= value == crossing;
    g_free(page_map); g_free(slots); g_free(cache); qemu_mutex_destroy(&cache_lock);
    disk_io(4, 0);
    page_map = NULL; slots = NULL; cache = NULL;
    budget_mb = saved_budget; misses = evictions = 0;
    return success;
}
void web_swap_ram_init(MemoryRegion *mr, Object *owner, uint64_t size)
{
    cache_init(size);
    memory_region_init_io(mr, owner, &ops, NULL, "browser-paged-ram", size);
    info_report("Browser paged RAM: %" PRIu64 " MiB guest, %u MiB resident cache", size >> 20, budget_mb);
}
