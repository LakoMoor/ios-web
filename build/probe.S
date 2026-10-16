/* SPDX-License-Identifier: AGPL-3.0-only
 * Bare-metal AArch64 test. No firmware or OS required.
 */
.section .text
.global _start
_start:
.if PAGED
    ldr x4, =0x100090000
.else
    ldr x4, =0x40090000
.endif
    ldr x3, =0x8877665544332211
    str x3, [x4]
    ldr x5, [x4]
    cmp x5, x3
    b.ne failure
    add x6, x5, #1
    sub x6, x6, #1
    cmp x6, x3
    b.ne failure
    lsr x6, x5, #32
    ldr x7, =0x88776655
    cmp x6, x7
    b.ne failure
    adr x0, success
    b print
failure:
    adr x0, failed
print:
    movz x1, #0x900, lsl #16
loop:
    ldrb w2, [x0], #1
    cbz w2, done
    strb w2, [x1]
    b loop
done:
    wfe
    b done
.ltorg
success:
.if PAGED
    .asciz "\r\nARM64_HIGH_ADDRESS_OK: code 0x100080000, data 0x100090000\r\nINFERNO_WASM_ARM64_OK\r\n64-bit arithmetic and paged guest RAM verified.\r\n"
.else
    .asciz "\r\nINFERNO_WASM_ARM64_OK\r\n64-bit arithmetic and resident guest RAM verified.\r\n"
.endif
failed:
    .asciz "\r\nINFERNO_WASM_ARM64_FAIL: guest data or arithmetic mismatch\r\n"
