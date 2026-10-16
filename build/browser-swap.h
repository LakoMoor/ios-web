/* SPDX-License-Identifier: AGPL-3.0-only */
#ifndef BROWSER_SWAP_H
#define BROWSER_SWAP_H
#include "system/memory.h"
bool web_swap_enabled(void);
bool web_swap_is_region(MemoryRegion *mr);
void web_swap_ram_init(MemoryRegion *mr, Object *owner, uint64_t size);
void web_swap_copy_out(uint64_t offset, void *dest, size_t len);
void *web_swap_pin_framebuffer(uint64_t offset, size_t len);
#endif
